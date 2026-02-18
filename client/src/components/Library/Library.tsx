import { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { BookMeta } from '../../types';
import { fetchBooks, uploadBook } from '../../services/api';
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
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      for (const file of files) {
        const name = file.name.replace(/\.epub$/i, '');
        const book = await uploadBook(file, name);
        setBooks(prev => [book, ...prev]);
      }
    } catch {
      setError('Failed to upload book. Make sure it is a valid EPUB file.');
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/epub+zip': ['.epub'] },
    multiple: true,
  });

  return (
    <div className="library">
      <div className="library-header">
        <h1>Your Library</h1>
        <p className="library-subtitle">
          Upload an EPUB to start reading with inline media
        </p>
      </div>

      <div
        {...getRootProps()}
        className={`library-dropzone ${isDragActive ? 'active' : ''} ${uploading ? 'uploading' : ''}`}
      >
        <input {...getInputProps()} />
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
            <button
              key={book.id}
              className="book-card"
              onClick={() => onSelectBook(book)}
            >
              <div className="book-cover">
                {book.coverUrl ? (
                  <img src={book.coverUrl} alt={book.title} />
                ) : (
                  <div className="book-cover-placeholder">
                    <span>{book.title[0]}</span>
                  </div>
                )}
              </div>
              <div className="book-info">
                <h3 className="book-title">{book.title}</h3>
                <p className="book-author">{book.author}</p>
              </div>
            </button>
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
