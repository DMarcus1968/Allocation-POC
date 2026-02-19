import Anthropic from '@anthropic-ai/sdk';
import { MediaReference, MediaType } from '../types/index.js';
import { randomUUID } from 'crypto';

const client = new Anthropic();

const SYSTEM_PROMPT = `You are an expert media reference detector for FootNote, a book reading app that lets readers instantly listen to or view media mentioned in books.

Given a passage of text from a book, find EVERY reference to real media works. Be thorough — scan every sentence. In memoirs and autobiographies, media references are often woven into narrative (e.g., "we'd blast [song] driving down the highway" or "I first heard [artist] on the radio").

Media types to detect:
- **music**: song titles, album titles, band/artist names performing specific works, concerts, musical compositions, radio songs, jukebox plays
- **visual_art**: paintings, sculptures, photographs, murals, art installations
- **film**: movies, documentaries, TV shows, TV programs

Detection guidelines:
1. Find ALL real, specific works — err on the side of inclusion. If a song, album, or artist is named, include it.
2. Song and album titles are references even when mentioned casually in passing.
3. When an artist is mentioned in the context of their music (e.g., "listening to Dylan"), identify the artist and set kind to "artist_mention".
4. Include the EXACT text span from the passage — copy it character-for-character including any punctuation or quotes.
5. Rate confidence from 0.5 (possible reference) to 1.0 (certain reference). Include anything above 0.5.
6. Ignore references to books, novels, and written literature.
7. When text mentions a specific venue/concert (e.g., "the show at the Stone Pony"), treat it as type "music" with kind "performance".

Respond with ONLY valid JSON:
{
  "references": [
    {
      "text_span": "exact quoted text from the passage",
      "start_offset": 0,
      "end_offset": 10,
      "type": "music",
      "entity": {
        "title": "Work Title",
        "creator": "Artist/Creator Name",
        "kind": "song|album|artist_mention|performance|painting|sculpture|photograph|movie|documentary|tv_show",
        "year": 1978
      },
      "confidence": 0.85
    }
  ]
}

If no media references are found, return: {"references": []}`;

export async function analyzeText(text: string): Promise<MediaReference[]> {
  if (!text.trim()) return [];

  const message = await client.messages.create({
    model: 'claude-sonnet-4-5-20250929',
    max_tokens: 8192,
    system: SYSTEM_PROMPT,
    messages: [
      {
        role: 'user',
        content: `Analyze this passage for media references:\n\n${text}`,
      },
    ],
  });

  const content = message.content[0];
  if (content.type !== 'text') return [];

  try {
    // Strip markdown code fences if present (e.g. ```json ... ```)
    const raw = content.text.replace(/^```(?:json)?\s*\n?/m, '').replace(/\n?```\s*$/m, '');
    const parsed = JSON.parse(raw);
    return (parsed.references || []).map((ref: any) => ({
      id: randomUUID(),
      textSpan: ref.text_span,
      startOffset: ref.start_offset,
      endOffset: ref.end_offset,
      type: ref.type as MediaType,
      entity: {
        title: ref.entity.title,
        creator: ref.entity.creator,
        kind: ref.entity.kind,
        year: ref.entity.year,
      },
      confidence: ref.confidence,
    }));
  } catch {
    console.error('Failed to parse AI response:', content.text);
    return [];
  }
}
