import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchBookChapters, analyzeChapter } from '../../api';
import { BookData, MediaReference, ResolvedMedia } from '../../types';
import InlinePlayer from '../InlinePlayer/InlinePlayer';
import './Reader.css';

interface Props {
  bookId: string;
  onBack: () => void;
}

interface ChapterAnnotations {
  references: MediaReference[];
  resolvedMedia: ResolvedMedia[];
}

export default function Reader({ bookId, onBack }: Props) {
  const [book, setBook] = useState<BookData | null>(null);
  const [chapterIndex, setChapterIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [annotations, setAnnotations] = useState<ChapterAnnotations | null>(null);
  const [analysisNotice, setAnalysisNotice] = useState<string | null>(null);
  const [activeMedia, setActiveMedia] = useState<ResolvedMedia | null>(null);
  const [tocOpen, setTocOpen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const annotationCache = useRef<Map<string, ChapterAnnotations>>(new Map());

  // Load book
  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchBookChapters(bookId)
      .then(setBook)
      .catch(() => setError('Failed to load book'))
      .finally(() => setLoading(false));
  }, [bookId]);

  // Analyze chapter for references
  const runAnalysis = useCallback(async (book: BookData, idx: number) => {
    const cacheKey = `${book.id}-${idx}`;
    if (annotationCache.current.has(cacheKey)) {
      setAnnotations(annotationCache.current.get(cacheKey)!);
      return;
    }

    setAnalyzing(true);
    setAnalysisNotice(null);
    try {
      const chapter = book.chapters[idx];
      // Extract plain text from HTML for analysis
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = chapter.html;
      const text = tempDiv.textContent || '';

      const result = await analyzeChapter(book.id, idx, text);
      const ann = { references: result.references, resolvedMedia: result.resolvedMedia || [] };
      annotationCache.current.set(cacheKey, ann);
      setAnnotations(ann);
      if (result.notice) setAnalysisNotice(result.notice);
    } catch {
      setAnnotations(null);
      setAnalysisNotice('Reference detection failed — check that ANTHROPIC_API_KEY is set in server/.env');
    } finally {
      setAnalyzing(false);
    }
  }, []);

  // When chapter changes, analyze it
  useEffect(() => {
    if (!book) return;
    setAnnotations(null);
    setActiveMedia(null);
    setAnalysisNotice(null);
    runAnalysis(book, chapterIndex);
  }, [book, chapterIndex, runAnalysis]);

  // Inject highlights into chapter HTML
  useEffect(() => {
    if (!contentRef.current || !book) return;

    const chapter = book.chapters[chapterIndex];
    if (!chapter) return;

    // Start with raw chapter HTML
    let html = chapter.html;

    // If we have annotations, inject highlight marks
    if (annotations && annotations.references.length > 0) {
      html = injectHighlights(html, annotations.references, annotations.resolvedMedia);
    }

    contentRef.current.innerHTML = html;

    // Attach click handlers to highlight marks
    const marks = contentRef.current.querySelectorAll('[data-ref-id]');
    marks.forEach(mark => {
      mark.addEventListener('click', () => {
        const refId = mark.getAttribute('data-ref-id');
        const media = annotations?.resolvedMedia.find(m => m.referenceId === refId);
        if (media) {
          setActiveMedia(prev => prev?.referenceId === media.referenceId ? null : media);
          // Scroll the mark into view
          mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      });
    });

    // Scroll to top on chapter change
    contentRef.current.scrollTop = 0;
  }, [book, chapterIndex, annotations]);

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (!book) return;
      if (e.key === 'ArrowLeft' && chapterIndex > 0) {
        setChapterIndex(i => i - 1);
      } else if (e.key === 'ArrowRight' && chapterIndex < book.chapters.length - 1) {
        setChapterIndex(i => i + 1);
      } else if (e.key === 'Escape') {
        if (activeMedia) setActiveMedia(null);
        else if (tocOpen) setTocOpen(false);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [book, chapterIndex, activeMedia, tocOpen]);

  if (loading) {
    return (
      <div className="reader-loading">
        <div className="spinner" />
        <p>Loading book...</p>
      </div>
    );
  }

  if (error || !book) {
    return (
      <div className="reader-error">
        <p>{error || 'Something went wrong'}</p>
        <button onClick={onBack}>Back to Library</button>
      </div>
    );
  }

  const chapter = book.chapters[chapterIndex];
  const totalChapters = book.chapters.length;
  const refCount = annotations?.references.length || 0;

  return (
    <div className="reader">
      {/* Top bar */}
      <header className="reader-bar">
        <button className="reader-bar-btn" onClick={onBack} title="Back to library">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
        </button>

        <div className="reader-bar-center">
          <span className="reader-bar-title">{book.title}</span>
          <span className="reader-bar-chapter">{chapter?.title}</span>
        </div>

        <button
          className="reader-bar-btn"
          onClick={() => setTocOpen(!tocOpen)}
          title="Table of contents"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="15" y2="12" />
            <line x1="3" y1="18" x2="18" y2="18" />
          </svg>
        </button>
      </header>

      {/* TOC sidebar */}
      {tocOpen && (
        <div className="reader-toc-overlay" onClick={() => setTocOpen(false)}>
          <nav className="reader-toc" onClick={e => e.stopPropagation()}>
            <h3>Contents</h3>
            {book.chapters.map((ch, i) => (
              <button
                key={i}
                className={`reader-toc-item ${i === chapterIndex ? 'active' : ''}`}
                onClick={() => { setChapterIndex(i); setTocOpen(false); }}
              >
                {ch.title}
              </button>
            ))}
          </nav>
        </div>
      )}

      {/* Reading area */}
      <main className="reader-main">
        <article className="reader-content" ref={contentRef} />

        {/* Analyzing indicator */}
        {analyzing && (
          <div className="reader-analyzing">
            <div className="analyzing-dot" />
            Discovering references...
          </div>
        )}

        {/* Reference count badge */}
        {!analyzing && refCount > 0 && (
          <div className="reader-ref-count">
            {refCount} reference{refCount !== 1 ? 's' : ''} found
          </div>
        )}

        {/* Analysis notice (demo mode or error) */}
        {!analyzing && analysisNotice && (
          <div className="reader-notice">
            {analysisNotice}
          </div>
        )}
      </main>

      {/* Inline media player */}
      {activeMedia && (
        <InlinePlayer media={activeMedia} onClose={() => setActiveMedia(null)} />
      )}

      {/* Bottom navigation */}
      <footer className="reader-nav">
        <button
          className="reader-nav-btn"
          disabled={chapterIndex === 0}
          onClick={() => setChapterIndex(i => i - 1)}
        >
          Previous
        </button>

        <div className="reader-nav-dots">
          {book.chapters.map((_, i) => (
            <button
              key={i}
              className={`reader-nav-dot ${i === chapterIndex ? 'active' : ''}`}
              onClick={() => setChapterIndex(i)}
              title={book.chapters[i].title}
            />
          ))}
        </div>

        <button
          className="reader-nav-btn"
          disabled={chapterIndex === totalChapters - 1}
          onClick={() => setChapterIndex(i => i + 1)}
        >
          Next
        </button>
      </footer>
    </div>
  );
}

/**
 * Inject highlight <mark> elements into chapter HTML for each reference.
 * We do this as string manipulation before setting innerHTML,
 * which is simpler and more reliable than post-render DOM walking.
 */
function injectHighlights(
  html: string,
  references: MediaReference[],
  resolvedMedia: ResolvedMedia[]
): string {
  // Sort references by text span length (longest first) to avoid partial matches
  const sorted = [...references].sort((a, b) => b.textSpan.length - a.textSpan.length);
  const mediaMap = new Map(resolvedMedia.map(m => [m.referenceId, m]));

  for (const ref of sorted) {
    const media = mediaMap.get(ref.id);
    const typeClass = `fn-mark--${ref.type}`;
    const hasMedia = media ? 'fn-mark--has-media' : '';
    const icon = getTypeIcon(ref.type);

    // Only replace within text content (not inside HTML tags)
    // Use a regex that matches the text span but not inside < >
    const escaped = escapeRegex(ref.textSpan);
    const regex = new RegExp(`(?<=>)([^<]*?)(${escaped})([^<]*?)(?=<)`, 'g');

    html = html.replace(regex, (_match, before, span, after) => {
      return `${before}<mark class="fn-mark ${typeClass} ${hasMedia}" data-ref-id="${ref.id}">${span}<span class="fn-mark-icon">${icon}</span></mark>${after}`;
    });

    // Also try to match text that starts a text node (after a tag)
    // Fallback: simple replace for <strong>text</strong> patterns
    if (!html.includes(`data-ref-id="${ref.id}"`)) {
      // Try matching within <strong> or <em> tags
      const simpleRegex = new RegExp(`(<(?:strong|em|b|i)[^>]*>)(${escaped})(</(?:strong|em|b|i)>)`, 'gi');
      html = html.replace(simpleRegex, (_, open, span, close) => {
        return `${open}<mark class="fn-mark ${typeClass} ${hasMedia}" data-ref-id="${ref.id}">${span}<span class="fn-mark-icon">${icon}</span></mark>${close}`;
      });
    }
  }

  return html;
}

function getTypeIcon(type: string): string {
  switch (type) {
    case 'music': return '\u266B';
    case 'visual_art': return '\u25CF';
    case 'film': return '\u25B6';
    default: return '\u2022';
  }
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
