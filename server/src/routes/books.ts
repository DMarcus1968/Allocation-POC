import { Router, Request, Response } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { randomUUID } from 'crypto';
import { saveBook, getBooks, getBook, deleteBookRecord } from '../db/cache.js';
import { DEMO_BOOK } from '../services/demo-book.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const UPLOADS_DIR = path.join(__dirname, '..', '..', 'data', 'books');

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOADS_DIR),
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname);
    cb(null, `${randomUUID()}${ext}`);
  },
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

// GET /api/books — list all books (includes demo book)
router.get('/', (_req: Request, res: Response) => {
  const uploadedBooks = getBooks();
  const demoEntry = {
    id: DEMO_BOOK.id,
    title: DEMO_BOOK.title,
    author: DEMO_BOOK.author,
    file_name: '',
    isDemo: true,
  };
  res.json({ books: [demoEntry, ...uploadedBooks] });
});

// GET /api/books/demo/chapters — get demo book chapters
router.get('/demo/chapters', (_req: Request, res: Response) => {
  res.json({
    id: DEMO_BOOK.id,
    title: DEMO_BOOK.title,
    author: DEMO_BOOK.author,
    chapters: DEMO_BOOK.chapters,
  });
});

// POST /api/books — upload an EPUB
router.post('/', (req: Request, res: Response) => {
  upload.single('book')(req, res, (err: any) => {
    if (err) {
      console.error('Upload error:', err);
      res.status(400).json({ error: err.message || 'Upload failed' });
      return;
    }
    if (!req.file) {
      res.status(400).json({ error: 'No file uploaded' });
      return;
    }

    const { title, author } = req.body;
    const bookId = randomUUID();

    saveBook(bookId, title || 'Untitled', author || 'Unknown', req.file.filename);

    res.json({
      id: bookId,
      title: title || 'Untitled',
      author: author || 'Unknown',
      fileName: req.file.filename,
    });
  });
});

// GET /api/books/:id/file — serve the EPUB file for the reader
router.get('/:id/file', (req: Request, res: Response) => {
  const books = getBooks() as any[];
  const book = books.find((b: any) => b.id === req.params.id);
  if (!book) {
    res.status(404).json({ error: 'Book not found' });
    return;
  }
  const filePath = path.join(UPLOADS_DIR, book.file_name);
  if (!fs.existsSync(filePath)) {
    res.status(404).json({ error: 'EPUB file not found on disk. Please re-upload the book.' });
    return;
  }
  res.sendFile(filePath);
});

// DELETE /api/books/:id — remove a book and its file
router.delete('/:id', (req: Request, res: Response) => {
  const book = getBook(req.params.id);
  if (!book) {
    res.status(404).json({ error: 'Book not found' });
    return;
  }
  // Remove file from disk
  const filePath = path.join(UPLOADS_DIR, book.file_name);
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
  }
  // Remove DB records
  deleteBookRecord(book.id);
  res.json({ ok: true });
});

export default router;
