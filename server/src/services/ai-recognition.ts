import Anthropic from '@anthropic-ai/sdk';
import { MediaReference, MediaType } from '../types/index.js';
import { randomUUID } from 'crypto';

const client = new Anthropic();

const SYSTEM_PROMPT = `You are an expert media reference detector for FootNote, a book reading app that lets readers instantly listen to or view media mentioned in books.

Given a passage of text from a book, find EVERY reference to real media works. Be thorough — scan every sentence. In memoirs and autobiographies, media references are often woven into narrative.

Media types to detect:
- **music**: song titles, album titles, band/artist names, concerts, musical compositions
- **visual_art**: paintings, sculptures, photographs, murals, art installations
- **film**: movies, documentaries, TV shows, TV programs

CRITICAL detection rules:
1. **Quoted titles are ALWAYS references.** Text like "Growin' Up," "For You," "Thunder Road" — each quoted title is a separate reference. Detect EVERY ONE individually.
2. **Lists of titles**: When the text lists several titles (e.g., '"Song A," "Song B," "Song C" and "Song D"'), each title is its own reference. Do not skip any.
3. **Song and album titles** are references even when mentioned casually in passing. Any named song or album = a reference.
4. **Artist/band names** mentioned in the context of their music (e.g., "listening to Dylan," "a Beatles fan") should be detected with kind "artist_mention". The text_span should be just the artist name.
5. Include the EXACT text span from the passage — copy it character-for-character. For quoted titles, include ONLY the text inside the quotes, not the quote marks themselves.
6. Rate confidence from 0.5 to 1.0. Include anything above 0.5.
7. Ignore references to books, novels, and written literature.
8. Specific venues/concerts (e.g., "the show at the Stone Pony") → type "music", kind "performance".

Respond with ONLY valid JSON:
{
  "references": [
    {
      "text_span": "exact text from the passage",
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
    return (parsed.references || [])
      .filter((ref: any) => ref && ref.text_span && ref.entity && ref.entity.title
        && ['music', 'visual_art', 'film'].includes(ref.type))
      .map((ref: any) => ({
        id: randomUUID(),
        textSpan: ref.text_span,
        startOffset: ref.start_offset,
        endOffset: ref.end_offset,
        type: ref.type as MediaType,
        entity: {
          title: ref.entity.title,
          creator: ref.entity.creator || 'Unknown',
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
