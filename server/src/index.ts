import 'dotenv/config';
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
const PORT = process.env.PORT || 4000;

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

// Serve client dist (with no-cache headers to prevent stale builds)
const clientDist = path.resolve(__dirname, '..', '..', 'client', 'dist');
console.log('Client dist path:', clientDist, 'exists:', fs.existsSync(clientDist));
if (fs.existsSync(clientDist)) {
  app.use(express.static(clientDist, {
    setHeaders: (res) => {
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    },
  }));
  // SPA fallback — serve index.html for all non-API routes
  app.get('*', (_req, res) => {
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.sendFile(path.join(clientDist, 'index.html'));
  });
}

app.listen(Number(PORT), '0.0.0.0', () => {
  console.log(`FootNote API running on http://0.0.0.0:${PORT}`);
  if (DEMO_MODE) {
    console.log('Running in DEMO MODE (no API keys needed)');
    console.log('Upload any EPUB to read — media references are detected by keyword matching');
  }
});
