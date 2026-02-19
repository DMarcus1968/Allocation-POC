import { BookMeta, DemoBookData, MediaReference, ResolvedMedia } from '../types';

const API_BASE = '/api';

export async function fetchBooks(): Promise<BookMeta[]> {
  const res = await fetch(`${API_BASE}/books`);
  const data = await res.json();
  return data.books;
}

export async function uploadBook(file: File, title?: string, author?: string): Promise<BookMeta> {
  const form = new FormData();
  form.append('book', file);
  if (title) form.append('title', title);
  if (author) form.append('author', author);

  const res = await fetch(`${API_BASE}/books`, { method: 'POST', body: form });
  if (!res.ok) throw new Error('Upload failed');
  return res.json();
}

export function getBookFileUrl(bookId: string): string {
  return `${API_BASE}/books/${bookId}/file`;
}

export interface AnalyzeResult {
  references: MediaReference[];
  resolvedMedia: ResolvedMedia[];
  notice?: string;
}

export async function fetchDemoBook(): Promise<DemoBookData> {
  const res = await fetch(`${API_BASE}/books/demo/chapters`);
  if (!res.ok) throw new Error('Failed to load demo book');
  return res.json();
}

export async function analyzePassage(
  bookId: string,
  cfiRange: string,
  text: string
): Promise<AnalyzeResult> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bookId, cfiRange, text }),
  });
  if (!res.ok) throw new Error('Analysis failed');
  return res.json();
}
