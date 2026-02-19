import { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { fetchBooks, uploadBook, deleteBook } from '../../api';
import { BookInfo } from '../../types';
import './Library.css';

interface Props {
  onSelectBook: (id: string) => void;
}

export default function Library({ onSelectBook }: Props) {
  const [books, setBooks] = useState<BookInfo[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadBooks = useCallback(async () => {
    try {
      const list = await fetchBooks();
      setBooks(list);
    } catch {
      setError('Failed to load library');
    }
  }, []);

  useEffect(() => { loadBooks(); }, [loadBooks]);

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      await uploadBook(file);
      await loadBooks();
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [loadBooks]);

  const handleDelete = async (e: React.MouseEvent, bookId: string) => {
    e.stopPropagation();
    try {
      await deleteBook(bookId);
      await loadBooks();
    } catch {
      setError('Failed to delete book');
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/epub+zip': ['.epub'] },
    multiple: false,
    noClick: books.length > 0,
  });

  return (
    <div className="library">
      <header className="library-header">
        <h1 className="library-logo">FootNote</h1>
        <p className="library-tagline">Drop a book. Discover what's inside.</p>
      </header>

      <div
        {...getRootProps()}
        className={`library-content ${isDragActive ? 'drag-active' : ''}`}
      >
        <input {...getInputProps()} />

        {isDragActive && (
          <div className="drop-overlay">
            <div className="drop-overlay-content">
              <div className="drop-icon">+</div>
              <p>Drop your EPUB here</p>
            </div>
          </div>
        )}

        {books.length === 0 && !uploading && (
          <div className="library-empty">
            <div className="empty-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                <line x1="12" y1="8" x2="12" y2="14" />
                <line x1="9" y1="11" x2="15" y2="11" />
              </svg>
            </div>
            <p className="empty-title">Drop an EPUB to get started</p>
            <p className="empty-subtitle">or click anywhere to browse</p>
          </div>
        )}

        {uploading && (
          <div className="library-uploading">
            <div className="spinner" />
            <p>Parsing your book...</p>
          </div>
        )}

        {error && <div className="library-error">{error}</div>}

        {books.length > 0 && (
          <div className="book-grid">
            {books.map(book => (
              <button
                key={book.id}
                className={`book-card ${book.isDemo ? 'book-card--demo' : ''}`}
                onClick={() => onSelectBook(book.id)}
              >
                <div className="book-card-spine" />
                <div className="book-card-cover">
                  <span className="book-card-title">{book.title}</span>
                  <span className="book-card-author">{book.author}</span>
                  {book.isDemo && <span className="book-card-badge">Demo</span>}
                </div>
                {!book.isDemo && (
                  <button
                    className="book-card-delete"
                    onClick={(e) => handleDelete(e, book.id)}
                    title="Remove book"
                  >
                    &times;
                  </button>
                )}
              </button>
            ))}

            <label className="book-card book-card--add">
              <input
                type="file"
                accept=".epub"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onDrop([file]);
                }}
              />
              <div className="book-card-cover book-card-cover--add">
                <span className="add-icon">+</span>
                <span className="book-card-title">Add Book</span>
              </div>
            </label>
          </div>
        )}
      </div>
    </div>
  );
}
