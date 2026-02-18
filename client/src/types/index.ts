export type MediaType = 'music' | 'visual_art' | 'film';

export interface MediaEntity {
  title: string;
  creator: string;
  kind: string;
  year?: number;
}

export interface MediaReference {
  id: string;
  textSpan: string;
  startOffset: number;
  endOffset: number;
  type: MediaType;
  entity: MediaEntity;
  confidence: number;
}

export interface ResolvedMedia {
  referenceId: string;
  type: MediaType;
  provider: 'spotify' | 'youtube' | 'image';
  title: string;
  creator: string;
  thumbnailUrl?: string;
  // Spotify
  spotifyTrackId?: string;
  previewUrl?: string;
  spotifyUri?: string;
  // YouTube
  youtubeVideoId?: string;
  // Image
  imageUrl?: string;
  imageSource?: string;
  imageAttribution?: string;
}

export interface BookMeta {
  id: string;
  title: string;
  author: string;
  coverUrl?: string;
  fileName: string;
}

export interface PageAnalysis {
  bookId: string;
  cfiRange: string;
  references: MediaReference[];
}
