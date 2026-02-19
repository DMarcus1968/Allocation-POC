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
      chapter_index INTEGER NOT NULL,
      references_json TEXT NOT NULL,
      created_at INTEGER DEFAULT (unixepoch()),
      PRIMARY KEY (book_id, chapter_index)
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
      file_name TEXT NOT NULL,
      chapter_count INTEGER DEFAULT 0,
      created_at INTEGER DEFAULT (unixepoch())
    );
  `);
}

export function getCachedAnalysis(bookId: string, chapterIndex: number): MediaReference[] | null {
  const row = db.prepare(
    'SELECT references_json FROM analysis_cache WHERE book_id = ? AND chapter_index = ?'
  ).get(bookId, chapterIndex) as { references_json: string } | undefined;
  return row ? JSON.parse(row.references_json) : null;
}

export function setCachedAnalysis(bookId: string, chapterIndex: number, refs: MediaReference[]) {
  db.prepare(
    'INSERT OR REPLACE INTO analysis_cache (book_id, chapter_index, references_json) VALUES (?, ?, ?)'
  ).run(bookId, chapterIndex, JSON.stringify(refs));
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

export function saveBook(id: string, title: string, author: string, fileName: string, chapterCount: number) {
  db.prepare(
    'INSERT OR REPLACE INTO books (id, title, author, file_name, chapter_count) VALUES (?, ?, ?, ?, ?)'
  ).run(id, title, author, fileName, chapterCount);
}

export function getBooks() {
  return db.prepare('SELECT * FROM books ORDER BY created_at DESC').all();
}

export function getBook(id: string) {
  return db.prepare('SELECT * FROM books WHERE id = ?').get(id) as
    | { id: string; title: string; author: string; file_name: string; chapter_count: number }
    | undefined;
}

export function deleteBookRecord(id: string) {
  db.prepare('DELETE FROM books WHERE id = ?').run(id);
  db.prepare('DELETE FROM analysis_cache WHERE book_id = ?').run(id);
}
