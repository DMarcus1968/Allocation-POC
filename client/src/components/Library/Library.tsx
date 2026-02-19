import { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { BookMeta } from '../../types';
import { fetchBooks, uploadBook, deleteBook } from '../../services/api';
import './Library.css';

interface Props {
  onSelectBook: (book: BookMeta) => void;
}

export default function Library({ onSelectBook }: Props) {
  const [books, setBooks] = useState<BookMeta[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchBooks().then(setBooks).catch(() => setError('Failed to load books'));
  }, []);

  const onDrop = useCallback(async (files: File[]) => {
    console.log('[FootNote] onDrop fired, files:', files.length, files.map(f => f.name));
    setError(`Drop received: ${files.length} file(s) — ${files.map(f => f.name).join(', ')}`);

    if (files.length === 0) return;

    // Validate extension client-side (server also validates)
    const epubs = files.filter(f => f.name.toLowerCase().endsWith('.epub'));
    if (epubs.length === 0) {
      setError('Only .epub files are supported.');
      return;
    }

    setUploading(true);
    setError(null);
    try {
      for (const file of epubs) {
        const name = file.name.replace(/\.epub$/i, '');
        console.log('[FootNote] Uploading:', name);
        const book = await uploadBook(file, name);
        console.log('[FootNote] Upload success:', book);
        setBooks(prev => [book, ...prev]);
      }
    } catch (err) {
      console.error('[FootNote] Upload error:', err);
      setError('Failed to upload book. Make sure it is a valid EPUB file.');
    } finally {
      setUploading(false);
    }
  }, []);

  const handleDelete = async (e: React.MouseEvent, bookId: string) => {
    e.stopPropagation();
    try {
      await deleteBook(bookId);
      setBooks(prev => prev.filter(b => b.id !== bookId));
    } catch {
      setError('Failed to delete book');
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
  });

  return (
    <div className="library">
      <div className="library-header">
        <h1>Your Library</h1>
        <p className="library-subtitle">
          Upload an EPUB to start reading with inline media (v3 — port 4000)
        </p>
      </div>

      <div
        {...getRootProps()}
        className={`library-dropzone ${isDragActive ? 'active' : ''} ${uploading ? 'uploading' : ''}`}
      >
        <input {...getInputProps({ accept: '.epub' })} />
        {uploading ? (
          <p>Uploading...</p>
        ) : isDragActive ? (
          <p>Drop your EPUB here</p>
        ) : (
          <div className="dropzone-content">
            <span className="dropzone-icon">+</span>
            <p>Drag & drop an EPUB here, or click to browse</p>
          </div>
        )}
      </div>

      {error && <p className="library-error">{error}</p>}

      {books.length > 0 && (
        <div className="library-grid">
          {books.map(book => (
            <div
              key={book.id}
              className={`book-card ${book.isDemo ? 'book-card--demo' : ''}`}
              onClick={() => onSelectBook(book)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && onSelectBook(book)}
            >
              {!book.isDemo && (
                <button
                  className="book-delete"
                  onClick={(e) => handleDelete(e, book.id)}
                  title="Remove from library"
                >
                  &times;
                </button>
              )}
              <div className="book-cover">
                {book.coverUrl ? (
                  <img src={book.coverUrl} alt={book.title} />
                ) : (
                  <div className={`book-cover-placeholder ${book.isDemo ? 'demo-cover' : ''}`}>
                    {book.isDemo ? (
                      <div className="demo-cover-content">
                        <span className="demo-cover-icon">♪</span>
                        <span className="demo-cover-label">DEMO</span>
                      </div>
                    ) : (
                      <span>{(book.title || '?')[0]}</span>
                    )}
                  </div>
                )}
              </div>
              <div className="book-info">
                <h3 className="book-title">{book.title || 'Untitled'}</h3>
                <p className="book-author">{book.author}</p>
                {book.isDemo && (
                  <p className="book-demo-tag">Try it out &rarr;</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {books.length === 0 && !error && (
        <div className="library-empty">
          <p>No books yet. Upload an EPUB to get started!</p>
        </div>
      )}
    </div>
  );
}
