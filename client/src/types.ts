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
  provider: 'spotify' | 'youtube' | 'youtube-search' | 'image';
  title: string;
  creator: string;
  thumbnailUrl?: string;
  spotifyTrackId?: string;
  previewUrl?: string;
  spotifyUri?: string;
  youtubeVideoId?: string;
  youtubeSearchQuery?: string;
  imageUrl?: string;
  imageSource?: string;
  imageAttribution?: string;
}

export interface BookChapter {
  title: string;
  html: string;
}

export interface BookInfo {
  id: string;
  title: string;
  author: string;
  isDemo?: boolean;
}

export interface BookData {
  id: string;
  title: string;
  author: string;
  chapters: BookChapter[];
}

export interface AnalyzeResult {
  references: MediaReference[];
  resolvedMedia: ResolvedMedia[];
  notice?: string;
}
