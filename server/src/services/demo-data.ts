import { MediaReference, ResolvedMedia } from '../types/index.js';
import { randomUUID } from 'crypto';

/**
 * Demo data: pre-built media references for sample text passages.
 * Used when no ANTHROPIC_API_KEY is set, so the app works out of the box.
 */

interface DemoReference {
  textSpan: string;
  type: 'music' | 'visual_art' | 'film';
  entity: {
    title: string;
    creator: string;
    kind: string;
    year?: number;
  };
  resolved: {
    provider: 'spotify' | 'youtube' | 'image';
    thumbnailUrl?: string;
    spotifyUri?: string;
    previewUrl?: string;
    youtubeVideoId?: string;
    imageUrl?: string;
    imageSource?: string;
    imageAttribution?: string;
  };
}

const DEMO_DATABASE: DemoReference[] = [
  // Music references
  {
    textSpan: 'Like a Rolling Stone',
    type: 'music',
    entity: { title: 'Like a Rolling Stone', creator: 'Bob Dylan', kind: 'song', year: 1965 },
    resolved: {
      provider: 'youtube',
      thumbnailUrl: 'https://i.ytimg.com/vi/IwOfCgkyEj0/mqdefault.jpg',
      youtubeVideoId: 'IwOfCgkyEj0',
    },
  },
  {
    textSpan: 'Bohemian Rhapsody',
    type: 'music',
    entity: { title: 'Bohemian Rhapsody', creator: 'Queen', kind: 'song', year: 1975 },
    resolved: {
      provider: 'youtube',
      thumbnailUrl: 'https://i.ytimg.com/vi/fJ9rUzIMcZQ/mqdefault.jpg',
      youtubeVideoId: 'fJ9rUzIMcZQ',
    },
  },
  {
    textSpan: 'A Love Supreme',
    type: 'music',
    entity: { title: 'A Love Supreme', creator: 'John Coltrane', kind: 'album', year: 1965 },
    resolved: {
      provider: 'youtube',
      thumbnailUrl: 'https://i.ytimg.com/vi/vMCHDC2Lurk/mqdefault.jpg',
      youtubeVideoId: 'vMCHDC2Lurk',
    },
  },
  {
    textSpan: 'Kind of Blue',
    type: 'music',
    entity: { title: 'Kind of Blue', creator: 'Miles Davis', kind: 'album', year: 1959 },
    resolved: {
      provider: 'youtube',
      thumbnailUrl: 'https://i.ytimg.com/vi/zqNTltOGh5c/mqdefault.jpg',
      youtubeVideoId: 'zqNTltOGh5c',
    },
  },
  {
    textSpan: 'Imagine',
    type: 'music',
    entity: { title: 'Imagine', creator: 'John Lennon', kind: 'song', year: 1971 },
    resolved: {
      provider: 'youtube',
      thumbnailUrl: 'https://i.ytimg.com/vi/YkgkThdzX-8/mqdefault.jpg',
      youtubeVideoId: 'YkgkThdzX-8',
    },
  },
  {
    textSpan: 'Clair de Lune',
    type: 'music',
    entity: { title: 'Clair de Lune', creator: 'Claude Debussy', kind: 'performance', year: 1905 },
    resolved: {
      provider: 'youtube',
      thumbnailUrl: 'https://i.ytimg.com/vi/CvFH_6DNRCY/mqdefault.jpg',
      youtubeVideoId: 'CvFH_6DNRCY',
    },
  },
  {
    textSpan: 'Moonlight Sonata',
    type: 'music',
    entity: { title: 'Piano Sonata No. 14 (Moonlight Sonata)', creator: 'Ludwig van Beethoven', kind: 'performance', year: 1801 },
    resolved: {
      provider: 'youtube',
      thumbnailUrl: 'https://i.ytimg.com/vi/4Tr0otuiQuU/mqdefault.jpg',
      youtubeVideoId: '4Tr0otuiQuU',
    },
  },
  // Visual art references
  {
    textSpan: 'Starry Night',
    type: 'visual_art',
    entity: { title: 'The Starry Night', creator: 'Vincent van Gogh', kind: 'painting', year: 1889 },
    resolved: {
      provider: 'image',
      imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/800px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg',
      imageSource: 'https://commons.wikimedia.org/wiki/File:Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg',
      imageAttribution: 'Vincent van Gogh, Public domain, via Wikimedia Commons',
      thumbnailUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/300px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg',
    },
  },
  {
    textSpan: 'Mona Lisa',
    type: 'visual_art',
    entity: { title: 'Mona Lisa', creator: 'Leonardo da Vinci', kind: 'painting', year: 1503 },
    resolved: {
      provider: 'image',
      imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg',
      imageSource: 'https://commons.wikimedia.org/wiki/File:Mona_Lisa,_by_Leonardo_da_Vinci,_from_C2RMF_retouched.jpg',
      imageAttribution: 'Leonardo da Vinci, Public domain, via Wikimedia Commons',
      thumbnailUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/300px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg',
    },
  },
  {
    textSpan: 'Girl with a Pearl Earring',
    type: 'visual_art',
    entity: { title: 'Girl with a Pearl Earring', creator: 'Johannes Vermeer', kind: 'painting', year: 1665 },
    resolved: {
      provider: 'image',
      imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/1665_Girl_with_a_Pearl_Earring.jpg/800px-1665_Girl_with_a_Pearl_Earring.jpg',
      imageSource: 'https://commons.wikimedia.org/wiki/File:1665_Girl_with_a_Pearl_Earring.jpg',
      imageAttribution: 'Johannes Vermeer, Public domain, via Wikimedia Commons',
      thumbnailUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/1665_Girl_with_a_Pearl_Earring.jpg/300px-1665_Girl_with_a_Pearl_Earring.jpg',
    },
  },
  {
    textSpan: 'The Persistence of Memory',
    type: 'visual_art',
    entity: { title: 'The Persistence of Memory', creator: 'Salvador Dalí', kind: 'painting', year: 1931 },
    resolved: {
      provider: 'image',
      imageUrl: 'https://upload.wikimedia.org/wikipedia/en/d/dd/The_Persistence_of_Memory.jpg',
      imageSource: 'https://en.wikipedia.org/wiki/The_Persistence_of_Memory',
      imageAttribution: 'Salvador Dalí',
      thumbnailUrl: 'https://upload.wikimedia.org/wikipedia/en/d/dd/The_Persistence_of_Memory.jpg',
    },
  },
  {
    textSpan: 'The Great Wave',
    type: 'visual_art',
    entity: { title: 'The Great Wave off Kanagawa', creator: 'Katsushika Hokusai', kind: 'painting', year: 1831 },
    resolved: {
      provider: 'image',
      imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Tsunami_by_hokusai_19th_century.jpg/800px-Tsunami_by_hokusai_19th_century.jpg',
      imageSource: 'https://commons.wikimedia.org/wiki/File:Tsunami_by_hokusai_19th_century.jpg',
      imageAttribution: 'Katsushika Hokusai, Public domain, via Wikimedia Commons',
      thumbnailUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Tsunami_by_hokusai_19th_century.jpg/300px-Tsunami_by_hokusai_19th_century.jpg',
    },
  },
  // Film references
  {
    textSpan: 'Casablanca',
    type: 'film',
    entity: { title: 'Casablanca', creator: 'Michael Curtiz', kind: 'movie', year: 1942 },
    resolved: {
      provider: 'youtube',
      thumbnailUrl: 'https://i.ytimg.com/vi/BkL9l7qovsE/mqdefault.jpg',
      youtubeVideoId: 'BkL9l7qovsE',
    },
  },
  {
    textSpan: 'Citizen Kane',
    type: 'film',
    entity: { title: 'Citizen Kane', creator: 'Orson Welles', kind: 'movie', year: 1941 },
    resolved: {
      provider: 'youtube',
      thumbnailUrl: 'https://i.ytimg.com/vi/8dxqKJHmMbA/mqdefault.jpg',
      youtubeVideoId: '8dxqKJHmMbA',
    },
  },
  {
    textSpan: '2001: A Space Odyssey',
    type: 'film',
    entity: { title: '2001: A Space Odyssey', creator: 'Stanley Kubrick', kind: 'movie', year: 1968 },
    resolved: {
      provider: 'youtube',
      thumbnailUrl: 'https://i.ytimg.com/vi/oR_e9y-bka0/mqdefault.jpg',
      youtubeVideoId: 'oR_e9y-bka0',
    },
  },
  {
    textSpan: 'The Godfather',
    type: 'film',
    entity: { title: 'The Godfather', creator: 'Francis Ford Coppola', kind: 'movie', year: 1972 },
    resolved: {
      provider: 'youtube',
      thumbnailUrl: 'https://i.ytimg.com/vi/UaVTIH8mujA/mqdefault.jpg',
      youtubeVideoId: 'UaVTIH8mujA',
    },
  },
];

/**
 * Scan text for known demo references using simple substring matching.
 */
export function analyzeDemoText(text: string): { references: MediaReference[]; resolvedMedia: ResolvedMedia[] } {
  const references: MediaReference[] = [];
  const resolvedMedia: ResolvedMedia[] = [];

  for (const demo of DEMO_DATABASE) {
    const idx = text.indexOf(demo.textSpan);
    if (idx === -1) continue;

    const id = randomUUID();
    const ref: MediaReference = {
      id,
      textSpan: demo.textSpan,
      startOffset: idx,
      endOffset: idx + demo.textSpan.length,
      type: demo.type,
      entity: demo.entity,
      confidence: 0.95,
    };
    references.push(ref);

    const media: ResolvedMedia = {
      referenceId: id,
      type: demo.type,
      provider: demo.resolved.provider,
      title: demo.entity.title,
      creator: demo.entity.creator,
      thumbnailUrl: demo.resolved.thumbnailUrl,
      spotifyUri: demo.resolved.spotifyUri,
      previewUrl: demo.resolved.previewUrl,
      youtubeVideoId: demo.resolved.youtubeVideoId,
      imageUrl: demo.resolved.imageUrl,
      imageSource: demo.resolved.imageSource,
      imageAttribution: demo.resolved.imageAttribution,
    };
    resolvedMedia.push(media);
  }

  return { references, resolvedMedia };
}

export const DEMO_MODE = !process.env.ANTHROPIC_API_KEY;
