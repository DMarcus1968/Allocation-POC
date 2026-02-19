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

// POST /api/analyze — analyze a passage of text for media references
router.post('/', async (req: Request, res: Response) => {
  const { bookId, cfiRange, text } = req.body as AnalyzeRequest;

  if (!bookId || !cfiRange || !text) {
    res.status(400).json({ error: 'bookId, cfiRange, and text are required' });
    return;
  }

  try {
    // Demo mode: use built-in pattern matching (no API keys needed)
    if (DEMO_MODE) {
      const result = analyzeDemoText(text);
      // If this is an uploaded book (not the demo), let the user know
      if (bookId !== 'demo-book-001' && result.references.length === 0) {
        res.json({
          ...result,
          notice: 'Demo mode: media detection for uploaded books requires an ANTHROPIC_API_KEY. The built-in demo book works without API keys.',
        });
        return;
      }
      res.json(result);
      return;
    }

    // Full mode: use Claude AI + real media APIs
    let references = getCachedAnalysis(bookId, cfiRange);
    if (!references) {
      references = await analyzeText(text);
      setCachedAnalysis(bookId, cfiRange, references);
    }

    const resolvedMedia: ResolvedMedia[] = [];
    const unresolvedRefs = [];

    for (const ref of references) {
      const cached = getCachedMedia(ref.id);
      if (cached) {
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
