import { BookInfo, BookData, AnalyzeResult } from './types';

const BASE = '/api';

export async function fetchBooks(): Promise<BookInfo[]> {
  const res = await fetch(`${BASE}/books`);
  const data = await res.json();
  return data.books;
}

export async function fetchBookChapters(bookId: string): Promise<BookData> {
  const res = await fetch(`${BASE}/books/${bookId}/chapters`);
  if (!res.ok) throw new Error('Failed to load book');
  return res.json();
}

export async function uploadBook(file: File): Promise<BookInfo> {
  const form = new FormData();
  form.append('book', file);
  const res = await fetch(`${BASE}/books`, { method: 'POST', body: form });
  if (!res.ok) throw new Error('Upload failed');
  return res.json();
}

export async function deleteBook(bookId: string): Promise<void> {
  await fetch(`${BASE}/books/${bookId}`, { method: 'DELETE' });
}

export async function analyzeChapter(
  bookId: string,
  chapterIndex: number,
  text: string
): Promise<AnalyzeResult> {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bookId, chapterIndex, text }),
  });
  if (!res.ok) throw new Error('Analysis failed');
  return res.json();
}
