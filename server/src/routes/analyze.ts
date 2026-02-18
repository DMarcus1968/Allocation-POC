import { Router, Request, Response } from 'express';
import { analyzeText } from '../services/ai-recognition.js';
import { resolveAllMedia } from '../services/media-resolver.js';
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
    // Check cache first
    let references = getCachedAnalysis(bookId, cfiRange);
    if (!references) {
      references = await analyzeText(text);
      setCachedAnalysis(bookId, cfiRange, references);
    }

    // Resolve media for each reference (also with caching)
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
