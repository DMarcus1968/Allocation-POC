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

    let references = getCachedAnalysis(bookId, chapterIndex);
    if (!references) {
      references = await analyzeText(text);
      setCachedAnalysis(bookId, chapterIndex, references);
    }

    const resolvedMedia: ResolvedMedia[] = [];
    const unresolvedRefs = [];

    for (const ref of references) {
      const cached = getCachedMedia(ref.id);
      if (cached && cached.provider !== 'youtube-search') {
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
