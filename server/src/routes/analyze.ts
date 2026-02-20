import { Router, Request, Response } from 'express';
import { analyzeText } from '../services/ai-recognition.js';
import { resolveAllMedia } from '../services/media-resolver.js';
import { analyzeDemoText, DEMO_MODE } from '../services/demo-data.js';
import {
  getCachedAnalysis,
  setCachedAnalysis,
  getCachedMedia,
  setCachedMedia,
} from '../db/cache.js';
import { AnalyzeRequest, ResolvedMedia } from '../types/index.js';

const router = Router();

router.post('/', async (req: Request, res: Response) => {
  const { bookId, chapterIndex, text } = req.body as AnalyzeRequest;

  if (!bookId || chapterIndex === undefined || !text) {
    res.status(400).json({ error: 'bookId, chapterIndex, and text are required' });
    return;
  }

  try {
    if (DEMO_MODE) {
      const result = analyzeDemoText(text);
      if (bookId !== 'demo-book-001' && result.references.length === 0) {
        res.json({
          ...result,
          notice: 'Demo mode: set ANTHROPIC_API_KEY to enable AI-powered reference detection for uploaded books.',
        });
        return;
      }
      res.json(result);
      return;
    }

    // Skip trivially short chapters (cover pages, front matter images, etc.)
    const trimmedText = text.trim();
    if (trimmedText.length < 100) {
      console.log(`  Chapter ${chapterIndex}: skipped (only ${trimmedText.length} chars — likely front matter)`);
      res.json({ references: [], resolvedMedia: [] });
      return;
    }

    let references = getCachedAnalysis(bookId, chapterIndex);
    if (!references) {
      console.log(`  Analyzing chapter ${chapterIndex} (${trimmedText.length} chars)...`);
      const rawRefs = await analyzeText(trimmedText);

      // Deduplicate: keep only the first occurrence of each unique entity
      const seen = new Set<string>();
      references = rawRefs
        .filter(ref => ref.entity?.title && ref.entity?.creator)
        .filter(ref => {
          const key = `${ref.entity.title.toLowerCase()}|${ref.entity.creator.toLowerCase()}|${ref.type}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });

      setCachedAnalysis(bookId, chapterIndex, references);
      console.log(`  Chapter ${chapterIndex}: ${references.length} references found (${rawRefs.length - references.length} duplicates removed)`);
      for (const ref of references) {
        console.log(`    - "${ref.textSpan}" (${ref.type}, ${ref.entity.title} by ${ref.entity.creator})`);
      }
    } else {
      console.log(`  Chapter ${chapterIndex}: ${references.length} references (cached)`);
    }

    const resolvedMedia: ResolvedMedia[] = [];
    const unresolvedRefs = [];

    for (const ref of references) {
      const cached = getCachedMedia(ref.id);
      // Re-resolve if: no cache, youtube-search fallback, or artist_mention cached as non-wikipedia
      const isStale = cached && ref.entity.kind === 'artist_mention' && cached.provider !== 'wikipedia';
      if (cached && cached.provider !== 'youtube-search' && !isStale) {
        resolvedMedia.push(cached);
      } else {
        unresolvedRefs.push(ref);
      }
    }

    if (unresolvedRefs.length > 0) {
      const freshMedia = await resolveAllMedia(unresolvedRefs);
      for (const media of freshMedia) {
        setCachedMedia(media.referenceId, media);
        resolvedMedia.push(media);
      }
    }

    res.json({ references, resolvedMedia });
  } catch (err) {
    console.error('Analysis failed:', err);
    res.status(500).json({ error: 'Analysis failed' });
  }
});

export default router;
