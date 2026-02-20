import { Router, Request, Response } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { randomUUID } from 'crypto';
import { saveBook, getBooks, getBook, deleteBookRecord } from '../db/cache.js';
import { DEMO_BOOK } from '../services/demo-book.js';
import { parseEpub } from '../services/epub-parser.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const UPLOADS_DIR = path.join(__dirname, '..', '..', 'data', 'books');

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOADS_DIR),
  filename: (_req, file, cb) => cb(null, `${randomUUID()}${path.extname(file.originalname)}`),
});

const upload = multer({
  storage,
  fileFilter: (_req, file, cb) => {
    if (file.mimetype === 'application/epub+zip' || file.originalname.endsWith('.epub')) {
      cb(null, true);
    } else {
      cb(new Error('Only EPUB files are accepted'));
    }
  },
  limits: { fileSize: 100 * 1024 * 1024 },
});

const router = Router();

// GET /api/books — list all books
router.get('/', (_req: Request, res: Response) => {
  const uploadedBooks = getBooks().map((b: any) => ({
    id: b.id,
    title: b.title,
    author: b.author,
    coverImage: b.cover_image || undefined,
  }));
  const demoEntry = {
    id: DEMO_BOOK.id,
    title: DEMO_BOOK.title,
    author: DEMO_BOOK.author,
    isDemo: true,
  };
  res.json({ books: [demoEntry, ...uploadedBooks] });
});

// GET /api/books/:id/chapters — get book chapters
router.get('/:id/chapters', async (req: Request, res: Response) => {
  const id = req.params.id as string;

  // Demo book
  if (id === DEMO_BOOK.id) {
    res.json({
      id: DEMO_BOOK.id,
      title: DEMO_BOOK.title,
      author: DEMO_BOOK.author,
      chapters: DEMO_BOOK.chapters,
    });
    return;
  }

  // Uploaded book — parse EPUB
  const book = getBook(id);
  if (!book) {
    res.status(404).json({ error: 'Book not found' });
    return;
  }

  const filePath = path.join(UPLOADS_DIR, book.file_name);
  if (!fs.existsSync(filePath)) {
    res.status(404).json({ error: 'EPUB file not found on disk' });
    return;
  }

  try {
    const buffer = fs.readFileSync(filePath);
    const parsed = await parseEpub(buffer, id as string);

    // Backfill cover image if the DB record is missing it
    if (parsed.coverImage && !book.cover_image) {
      saveBook(book.id, book.title, book.author, book.file_name, book.chapter_count, parsed.coverImage);
      console.log(`  Backfilled cover image for "${book.title}"`);
    }

    res.json(parsed);
  } catch (err) {
    console.error('EPUB parse error:', err);
    res.status(500).json({ error: 'Failed to parse EPUB' });
  }
});

// POST /api/books — upload an EPUB
router.post('/', (req: Request, res: Response) => {
  upload.single('book')(req, res, async (err: any) => {
    if (err) {
      res.status(400).json({ error: err.message || 'Upload failed' });
      return;
    }
    if (!req.file) {
      res.status(400).json({ error: 'No file uploaded' });
      return;
    }

    try {
      const buffer = fs.readFileSync(req.file.path);
      const bookId = randomUUID();
      const parsed = await parseEpub(buffer, bookId);

      saveBook(bookId, parsed.title, parsed.author, req.file.filename, parsed.chapters.length, parsed.coverImage);

      res.json({
        id: bookId,
        title: parsed.title,
        author: parsed.author,
        chapterCount: parsed.chapters.length,
        coverImage: parsed.coverImage,
      });
    } catch (parseErr) {
      console.error('EPUB parse error on upload:', parseErr);
      // Still save with basic info
      const bookId = randomUUID();
      saveBook(bookId, req.body.title || 'Untitled', req.body.author || 'Unknown', req.file!.filename, 0);
      res.json({ id: bookId, title: req.body.title || 'Untitled', author: req.body.author || 'Unknown' });
    }
  });
});

// DELETE /api/books/:id
router.delete('/:id', (req: Request, res: Response) => {
  const book = getBook(req.params.id as string);
  if (!book) {
    res.status(404).json({ error: 'Book not found' });
    return;
  }
  const filePath = path.join(UPLOADS_DIR, book.file_name);
  if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
  deleteBookRecord(book.id);
  res.json({ ok: true });
});

export default router;
