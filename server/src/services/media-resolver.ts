import { MediaReference, ResolvedMedia } from '../types/index.js';

const SPOTIFY_CLIENT_ID = process.env.SPOTIFY_CLIENT_ID || '';
const SPOTIFY_CLIENT_SECRET = process.env.SPOTIFY_CLIENT_SECRET || '';
const YOUTUBE_API_KEY = process.env.YOUTUBE_API_KEY || '';

let spotifyToken: string | null = null;
let spotifyTokenExpiry = 0;

async function getSpotifyToken(): Promise<string | null> {
  if (!SPOTIFY_CLIENT_ID || !SPOTIFY_CLIENT_SECRET) return null;
  if (spotifyToken && Date.now() < spotifyTokenExpiry) return spotifyToken;

  try {
    const res = await fetch('https://accounts.spotify.com/api/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        Authorization: `Basic ${Buffer.from(`${SPOTIFY_CLIENT_ID}:${SPOTIFY_CLIENT_SECRET}`).toString('base64')}`,
      },
      body: 'grant_type=client_credentials',
    });
    const data = await res.json();
    spotifyToken = data.access_token;
    spotifyTokenExpiry = Date.now() + (data.expires_in - 60) * 1000;
    return spotifyToken;
  } catch (err) {
    console.error('Spotify auth failed:', err);
    return null;
  }
}

async function resolveMusic(ref: MediaReference): Promise<ResolvedMedia | null> {
  const token = await getSpotifyToken();
  if (!token) return resolveYouTube(ref, 'music');

  const query = `${ref.entity.kind === 'album' ? 'album' : 'track'}:${ref.entity.title} artist:${ref.entity.creator}`;
  const type = ref.entity.kind === 'album' ? 'album' : 'track';

  try {
    const res = await fetch(
      `https://api.spotify.com/v1/search?q=${encodeURIComponent(query)}&type=${type}&limit=1`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const data = await res.json();
    const items = type === 'album' ? data.albums?.items : data.tracks?.items;
    if (!items?.length) return resolveYouTube(ref, 'music');

    const item = items[0];
    const isAlbum = type === 'album';
    return {
      referenceId: ref.id,
      type: 'music',
      provider: 'spotify',
      title: item.name,
      creator: isAlbum ? item.artists[0]?.name : item.artists?.map((a: any) => a.name).join(', '),
      thumbnailUrl: (isAlbum ? item.images : item.album?.images)?.[0]?.url,
      spotifyTrackId: isAlbum ? undefined : item.id,
      previewUrl: isAlbum ? undefined : item.preview_url,
      spotifyUri: item.uri,
    };
  } catch (err) {
    console.error('Spotify search failed:', err);
    return resolveYouTube(ref, 'music');
  }
}

async function resolveYouTube(ref: MediaReference, forType: 'music' | 'film' = 'film'): Promise<ResolvedMedia | null> {
  if (!YOUTUBE_API_KEY) return resolveYouTubeFree(ref, forType);

  const query = `${ref.entity.title} ${ref.entity.creator}`;
  try {
    const res = await fetch(
      `https://www.googleapis.com/youtube/v3/search?part=snippet&q=${encodeURIComponent(query)}&type=video&maxResults=1&key=${YOUTUBE_API_KEY}`
    );
    const data = await res.json();
    const item = data.items?.[0];
    if (!item) return resolveYouTubeFree(ref, forType);

    return {
      referenceId: ref.id,
      type: forType,
      provider: 'youtube',
      title: ref.entity.title,
      creator: ref.entity.creator,
      thumbnailUrl: item.snippet.thumbnails?.medium?.url,
      youtubeVideoId: item.id.videoId,
    };
  } catch (err) {
    console.error('YouTube API failed, trying free fallback:', err);
    return resolveYouTubeFree(ref, forType);
  }
}

// Free YouTube search instances (no API key required)
const FREE_SEARCH_INSTANCES = [
  { type: 'piped' as const, url: 'https://pipedapi.kavin.rocks' },
  { type: 'piped' as const, url: 'https://pipedapi.adminforge.de' },
  { type: 'invidious' as const, url: 'https://inv.nadeko.net' },
  { type: 'invidious' as const, url: 'https://vid.puffyan.us' },
];

async function fetchWithTimeout(url: string, timeoutMs = 5000): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function resolveYouTubeFree(ref: MediaReference, forType: 'music' | 'film' = 'film'): Promise<ResolvedMedia | null> {
  const query = `${ref.entity.title} ${ref.entity.creator}`;

  for (const instance of FREE_SEARCH_INSTANCES) {
    try {
      if (instance.type === 'piped') {
        const res = await fetchWithTimeout(
          `${instance.url}/search?q=${encodeURIComponent(query)}&filter=videos`
        );
        if (!res.ok) continue;
        const data = await res.json();
        const item = data.items?.[0];
        if (!item?.url) continue;
        const videoId = item.url.replace('/watch?v=', '');
        if (!videoId) continue;
        console.log(`  Resolved "${ref.entity.title}" via Piped -> ${videoId}`);
        return {
          referenceId: ref.id,
          type: forType,
          provider: 'youtube',
          title: ref.entity.title,
          creator: ref.entity.creator,
          thumbnailUrl: item.thumbnail,
          youtubeVideoId: videoId,
        };
      } else {
        const res = await fetchWithTimeout(
          `${instance.url}/api/v1/search?q=${encodeURIComponent(query)}&type=video`
        );
        if (!res.ok) continue;
        const data = await res.json();
        const item = Array.isArray(data) ? data[0] : null;
        if (!item?.videoId) continue;
        console.log(`  Resolved "${ref.entity.title}" via Invidious -> ${item.videoId}`);
        return {
          referenceId: ref.id,
          type: forType,
          provider: 'youtube',
          title: ref.entity.title,
          creator: ref.entity.creator,
          thumbnailUrl: item.videoThumbnails?.[3]?.url,
          youtubeVideoId: item.videoId,
        };
      }
    } catch {
      continue;
    }
  }

  // Ultimate fallback: provide a YouTube search link
  console.log(`  No video ID found for "${ref.entity.title}" — using search link fallback`);
  return {
    referenceId: ref.id,
    type: forType,
    provider: 'youtube-search',
    title: ref.entity.title,
    creator: ref.entity.creator,
    youtubeSearchQuery: query,
  };
}

async function resolveImage(ref: MediaReference): Promise<ResolvedMedia | null> {
  const query = `${ref.entity.title} ${ref.entity.creator}`;
  try {
    const res = await fetch(
      `https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=${encodeURIComponent(query)}&gsrlimit=1&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=800&format=json&origin=*`
    );
    const data = await res.json();
    const pages = data.query?.pages;
    if (!pages) return null;

    const page = Object.values(pages)[0] as any;
    const imageInfo = page.imageinfo?.[0];
    if (!imageInfo) return null;

    const meta = imageInfo.extmetadata || {};
    return {
      referenceId: ref.id,
      type: 'visual_art',
      provider: 'image',
      title: ref.entity.title,
      creator: ref.entity.creator,
      imageUrl: imageInfo.thumburl || imageInfo.url,
      imageSource: imageInfo.descriptionurl,
      imageAttribution: meta.Artist?.value || ref.entity.creator,
      thumbnailUrl: imageInfo.thumburl,
    };
  } catch (err) {
    console.error('Wikimedia search failed:', err);
    return null;
  }
}

export async function resolveMedia(ref: MediaReference): Promise<ResolvedMedia | null> {
  switch (ref.type) {
    case 'music': return resolveMusic(ref);
    case 'film': return resolveYouTube(ref, 'film');
    case 'visual_art': return resolveImage(ref);
    default: return null;
  }
}

export async function resolveAllMedia(refs: MediaReference[]): Promise<ResolvedMedia[]> {
  const results = await Promise.allSettled(refs.map(resolveMedia));
  return results
    .filter((r): r is PromiseFulfilledResult<ResolvedMedia | null> => r.status === 'fulfilled')
    .map(r => r.value)
    .filter((r): r is ResolvedMedia => r !== null);
}
