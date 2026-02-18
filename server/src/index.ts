import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { initDb } from './db/cache.js';
import analyzeRouter from './routes/analyze.js';
import booksRouter from './routes/books.js';
import { DEMO_MODE } from './services/demo-data.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3001;

// Ensure data directories exist
const dataDir = path.join(__dirname, '..', 'data');
const booksDir = path.join(dataDir, 'books');
if (!fs.existsSync(booksDir)) fs.mkdirSync(booksDir, { recursive: true });

// Initialize database
initDb();

const app = express();
app.use(cors());
app.use(express.json({ limit: '5mb' }));

// API routes
app.use('/api/analyze', analyzeRouter);
app.use('/api/books', booksRouter);

// Health check
app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', name: 'FootNote API', demoMode: DEMO_MODE });
});

app.listen(PORT, () => {
  console.log(`FootNote API running on http://localhost:${PORT}`);
  if (DEMO_MODE) {
    console.log('Running in DEMO MODE (no API keys needed)');
    console.log('Upload any EPUB to read — media references are detected by keyword matching');
  }
});
