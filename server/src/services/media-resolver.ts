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
      previewUrl: isAlbum ? undefined : item.preview_url || undefined,
      spotifyUri: item.uri,
      youtubeSearchQuery: `${ref.entity.title} ${ref.entity.creator}`,
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

async function fetchWithTimeout(url: string, timeoutMs = 5000, headers?: Record<string, string>): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { signal: controller.signal, headers });
  } finally {
    clearTimeout(timer);
  }
}

async function resolveYouTubeFree(ref: MediaReference, forType: 'music' | 'film' = 'film'): Promise<ResolvedMedia | null> {
  const query = `${ref.entity.title} ${ref.entity.creator}`;

  // Strategy 1: Scrape YouTube search results page directly (most reliable)
  try {
    const res = await fetchWithTimeout(
      `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`,
      8000,
      { 'Accept-Language': 'en-US,en;q=0.9' }
    );
    if (res.ok) {
      const html = await res.text();
      const match = html.match(/"videoId":"([\w-]{11})"/);
      if (match) {
        const videoId = match[1];
        console.log(`  Resolved "${ref.entity.title}" via YouTube scrape -> ${videoId}`);
        return {
          referenceId: ref.id,
          type: forType,
          provider: 'youtube',
          title: ref.entity.title,
          creator: ref.entity.creator,
          thumbnailUrl: `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`,
          youtubeVideoId: videoId,
        };
      }
    }
  } catch (err) {
    console.log(`  YouTube scrape failed for "${ref.entity.title}", trying Piped/Invidious...`);
  }

  // Strategy 2: Try Piped/Invidious APIs as backup
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

async function resolveWikipedia(ref: MediaReference): Promise<ResolvedMedia | null> {
  // For artist mentions, the artist name is typically in both title and creator
  const query = ref.entity.title || ref.entity.creator;
  try {
    // Try Wikipedia REST API for a clean summary (direct page lookup)
    const res = await fetchWithTimeout(
      `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(query)}`,
      5000
    );
    if (res.ok) {
      const data = await res.json();
      // Accept standard articles; skip disambiguation pages (too generic)
      if (data.type === 'standard' && data.extract) {
        console.log(`  Resolved "${query}" via Wikipedia`);
        return {
          referenceId: ref.id,
          type: ref.type,
          provider: 'wikipedia',
          title: data.title,
          creator: ref.entity.creator,
          thumbnailUrl: data.thumbnail?.source,
          wikipediaUrl: data.content_urls?.desktop?.page,
          wikipediaSummary: data.extract,
        };
      }
    }

    // Fallback: search Wikipedia with contextual hint based on reference type
    const typeHint = ref.type === 'music' ? 'musician OR band OR singer OR composer'
      : ref.type === 'film' ? 'director OR actor OR filmmaker'
      : ref.type === 'visual_art' ? 'artist OR painter OR sculptor'
      : '';
    const searchQuery = typeHint ? `${query} ${typeHint}` : query;

    const searchRes = await fetchWithTimeout(
      `https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(searchQuery)}&srlimit=3&format=json&origin=*`,
      5000
    );
    if (searchRes.ok) {
      const searchData = await searchRes.json();
      const results = searchData.query?.search;
      if (results?.length) {
        // Try each result until we get a standard article with a real extract
        for (const result of results) {
          const summaryRes = await fetchWithTimeout(
            `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(result.title)}`,
            5000
          );
          if (!summaryRes.ok) continue;
          const data = await summaryRes.json();
          if (data.type === 'standard' && data.extract) {
            console.log(`  Resolved "${query}" via Wikipedia search -> ${data.title}`);
            return {
              referenceId: ref.id,
              type: ref.type,
              provider: 'wikipedia',
              title: data.title,
              creator: ref.entity.creator,
              thumbnailUrl: data.thumbnail?.source,
              wikipediaUrl: data.content_urls?.desktop?.page,
              wikipediaSummary: data.extract,
            };
          }
        }
      }
    }
  } catch (err) {
    console.error(`Wikipedia resolution failed for "${query}":`, err);
  }
  return null;
}

async function resolveImage(ref: MediaReference): Promise<ResolvedMedia | null> {
  const query = `${ref.entity.title} ${ref.entity.creator}`;
  try {
    const res = await fetch(
      `https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=${encodeURIComponent(query)}&gsrlimit=1&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=800&format=json&origin=*`
    );
    const data = await res.json();
    const pages = data.query?.pages;
    if (pages) {
      const page = Object.values(pages)[0] as any;
      const imageInfo = page.imageinfo?.[0];
      if (imageInfo) {
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
      }
    }
  } catch (err) {
    console.error('Wikimedia search failed:', err);
  }

  // Fallback: try Wikipedia for context about the artwork
  console.log(`  Wikimedia Commons failed for "${ref.entity.title}", trying Wikipedia...`);
  return resolveWikipedia(ref);
}

/**
 * Build a minimal fallback result so every reference is always clickable.
 * Shows the entity info with a Wikipedia search link.
 */
function buildFallback(ref: MediaReference): ResolvedMedia {
  const query = ref.entity.title || ref.entity.creator;
  console.log(`  Using info fallback for "${query}"`);
  return {
    referenceId: ref.id,
    type: ref.type,
    provider: 'wikipedia',
    title: ref.entity.title,
    creator: ref.entity.creator,
    wikipediaUrl: `https://en.wikipedia.org/w/index.php?search=${encodeURIComponent(query)}`,
    wikipediaSummary: ref.entity.year
      ? `${ref.entity.title} by ${ref.entity.creator} (${ref.entity.year}).`
      : `${ref.entity.title} by ${ref.entity.creator}.`,
  };
}

export async function resolveMedia(ref: MediaReference): Promise<ResolvedMedia> {
  let result: ResolvedMedia | null = null;

  // Artist mentions get Wikipedia pages, not playable media
  if (ref.entity.kind === 'artist_mention') {
    result = await resolveWikipedia(ref);
  } else {
    switch (ref.type) {
      case 'music': result = await resolveMusic(ref); break;
      case 'film': result = await resolveYouTube(ref, 'film'); break;
      case 'visual_art': result = await resolveImage(ref); break;
    }
  }

  // Every reference must resolve to something — never leave a dead click
  return result || buildFallback(ref);
}

export async function resolveAllMedia(refs: MediaReference[]): Promise<ResolvedMedia[]> {
  const results = await Promise.allSettled(refs.map(resolveMedia));
  return results
    .filter((r): r is PromiseFulfilledResult<ResolvedMedia> => r.status === 'fulfilled')
    .map(r => r.value);
}
