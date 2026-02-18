import Database from 'better-sqlite3';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { MediaReference, ResolvedMedia } from '../types/index.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.join(__dirname, '..', '..', 'data', 'footnote.db');

let db: Database.Database;

export function initDb() {
  const dir = path.dirname(DB_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');

  db.exec(`
    CREATE TABLE IF NOT EXISTS analysis_cache (
      book_id TEXT NOT NULL,
      cfi_range TEXT NOT NULL,
      references_json TEXT NOT NULL,
      created_at INTEGER DEFAULT (unixepoch()),
      PRIMARY KEY (book_id, cfi_range)
    );

    CREATE TABLE IF NOT EXISTS resolved_media_cache (
      reference_id TEXT PRIMARY KEY,
      resolved_json TEXT NOT NULL,
      created_at INTEGER DEFAULT (unixepoch())
    );

    CREATE TABLE IF NOT EXISTS books (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      cover_url TEXT,
      file_name TEXT NOT NULL,
      created_at INTEGER DEFAULT (unixepoch())
    );
  `);
}

export function getCachedAnalysis(bookId: string, cfiRange: string): MediaReference[] | null {
  const row = db.prepare(
    'SELECT references_json FROM analysis_cache WHERE book_id = ? AND cfi_range = ?'
  ).get(bookId, cfiRange) as { references_json: string } | undefined;
  return row ? JSON.parse(row.references_json) : null;
}

export function setCachedAnalysis(bookId: string, cfiRange: string, refs: MediaReference[]) {
  db.prepare(
    'INSERT OR REPLACE INTO analysis_cache (book_id, cfi_range, references_json) VALUES (?, ?, ?)'
  ).run(bookId, cfiRange, JSON.stringify(refs));
}

export function getCachedMedia(referenceId: string): ResolvedMedia | null {
  const row = db.prepare(
    'SELECT resolved_json FROM resolved_media_cache WHERE reference_id = ?'
  ).get(referenceId) as { resolved_json: string } | undefined;
  return row ? JSON.parse(row.resolved_json) : null;
}

export function setCachedMedia(referenceId: string, media: ResolvedMedia) {
  db.prepare(
    'INSERT OR REPLACE INTO resolved_media_cache (reference_id, resolved_json) VALUES (?, ?)'
  ).run(referenceId, JSON.stringify(media));
}

export function saveBook(id: string, title: string, author: string, fileName: string, coverUrl?: string) {
  db.prepare(
    'INSERT OR REPLACE INTO books (id, title, author, file_name, cover_url) VALUES (?, ?, ?, ?, ?)'
  ).run(id, title, author, fileName, coverUrl || null);
}

export function getBooks() {
  return db.prepare('SELECT * FROM books ORDER BY created_at DESC').all();
}
