import Anthropic from '@anthropic-ai/sdk';
import { MediaReference, MediaType } from '../types/index.js';
import { randomUUID } from 'crypto';

const client = new Anthropic();

const SYSTEM_PROMPT = `You are a media reference detector for a book reading application called FootNote.

Given a passage of text from a book, identify ALL references to real, specific media works:
- **music**: songs, albums, performances, concerts, musical compositions
- **visual_art**: paintings, sculptures, photographs, art installations
- **film**: movies, documentaries, TV shows, video clips

Rules:
1. Only identify references to REAL, SPECIFIC works (not generic mentions like "a song" or "some painting")
2. Include the exact text span from the passage that references the work
3. Classify each reference by its media type
4. Provide the most likely specific work being referenced, including creator and year if inferable
5. Rate your confidence (0.0-1.0) that this is a genuine media reference
6. For music references, distinguish between songs, albums, and performances
7. Ignore references to books/literature (the reader is already reading)

Respond with ONLY valid JSON in this exact format:
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
        "kind": "song|album|performance|painting|sculpture|photograph|movie|documentary|tv_show",
        "year": 1978
      },
      "confidence": 0.95
    }
  ]
}

If no media references are found, return: {"references": []}`;

export async function analyzeText(text: string): Promise<MediaReference[]> {
  if (!text.trim()) return [];

  const message = await client.messages.create({
    model: 'claude-sonnet-4-5-20250929',
    max_tokens: 4096,
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
    const parsed = JSON.parse(content.text);
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
