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
const PORT = process.env.PORT || 3001;

// Ensure data directories exist
const booksDir = path.join(__dirname, '..', 'data', 'books');
if (!fs.existsSync(booksDir)) fs.mkdirSync(booksDir, { recursive: true });

initDb();

const app = express();
app.use(cors());
app.use(express.json({ limit: '5mb' }));

app.use('/api/analyze', analyzeRouter);
app.use('/api/books', booksRouter);

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', demoMode: DEMO_MODE });
});

// Serve client dist in production
const clientDist = path.resolve(__dirname, '..', '..', 'client', 'dist');
if (fs.existsSync(clientDist)) {
  app.use(express.static(clientDist));
  app.get('*', (_req, res) => {
    res.sendFile(path.join(clientDist, 'index.html'));
  });
}

app.listen(Number(PORT), '0.0.0.0', () => {
  console.log(`FootNote server on http://localhost:${PORT}`);
  if (DEMO_MODE) console.log('Demo mode — no API keys needed for the built-in demo book');
});
