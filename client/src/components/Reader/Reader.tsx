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
  const analysisInFlight = useRef<string | null>(null);

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

    // Prevent duplicate concurrent calls (e.g., from React StrictMode double-effect)
    if (analysisInFlight.current === cacheKey) return;
    analysisInFlight.current = cacheKey;

    setAnalyzing(true);
    setAnalysisNotice(null);
    try {
      const chapter = book.chapters[idx];
      // Extract plain text from HTML for analysis
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = chapter.html;
      const text = tempDiv.textContent || '';

      const result = await analyzeChapter(book.id, idx, text);

      // Another call may have populated the cache while we waited
      if (annotationCache.current.has(cacheKey)) {
        setAnnotations(annotationCache.current.get(cacheKey)!);
        return;
      }

      const ann = { references: result.references, resolvedMedia: result.resolvedMedia || [] };
      annotationCache.current.set(cacheKey, ann);
      setAnnotations(ann);
      if (result.notice) setAnalysisNotice(result.notice);
    } catch {
      setAnnotations(null);
      setAnalysisNotice('Reference detection failed — check that ANTHROPIC_API_KEY is set in server/.env');
    } finally {
      analysisInFlight.current = null;
      setAnalyzing(false);
    }
  }, []);

  // When chapter changes, analyze it
  useEffect(() => {
    if (!book) return;

    // Show cached annotations immediately to avoid flicker on back-navigation
    const cacheKey = `${book.id}-${chapterIndex}`;
    if (annotationCache.current.has(cacheKey)) {
      setAnnotations(annotationCache.current.get(cacheKey)!);
    } else {
      setAnnotations(null);
    }

    setActiveMedia(null);
    setAnalysisNotice(null);
    runAnalysis(book, chapterIndex);
  }, [book, chapterIndex, runAnalysis]);

  // Inject highlights into chapter HTML
  useEffect(() => {
    if (!contentRef.current || !book) return;

    const chapter = book.chapters[chapterIndex];
    if (!chapter) return;

    // Set raw chapter HTML first
    contentRef.current.innerHTML = chapter.html;

    // If we have annotations, inject highlights by walking the DOM
    // This handles HTML entities, curly quotes, and text split across elements
    if (annotations && annotations.references.length > 0) {
      injectHighlightsDOM(contentRef.current, annotations.references, annotations.resolvedMedia);
    }

    // Attach click handlers to highlight marks
    const marks = contentRef.current.querySelectorAll('[data-ref-id]');
    marks.forEach(mark => {
      mark.addEventListener('click', () => {
        const refId = mark.getAttribute('data-ref-id');
        let media = annotations?.resolvedMedia.find(m => m.referenceId === refId);

        // Client-side fallback: if server didn't resolve, build a minimal info card
        if (!media && refId) {
          const ref = annotations?.references.find(r => r.id === refId);
          if (ref) {
            media = {
              referenceId: ref.id,
              type: ref.type,
              provider: 'wikipedia',
              title: ref.entity.title,
              creator: ref.entity.creator,
              wikipediaUrl: `https://en.wikipedia.org/w/index.php?search=${encodeURIComponent(ref.entity.title)}`,
              wikipediaSummary: `${ref.entity.title} by ${ref.entity.creator}.`,
            };
          }
        }

        if (media) {
          setActiveMedia(prev => prev?.referenceId === media!.referenceId ? null : media!);
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
 * Inject highlight <mark> elements by walking DOM text nodes.
 * This handles HTML entities, curly quotes, and text split across elements
 * far more reliably than regex on raw HTML strings.
 */
function injectHighlightsDOM(
  container: HTMLElement,
  references: MediaReference[],
  resolvedMedia: ResolvedMedia[]
) {
  const mediaMap = new Map(resolvedMedia.map(m => [m.referenceId, m]));
  // Sort by text span length (longest first) to avoid partial matches
  const sorted = [...references].sort((a, b) => b.textSpan.length - a.textSpan.length);

  for (const ref of sorted) {
    if (!ref.textSpan) continue;
    const media = mediaMap.get(ref.id);
    const range = findTextRange(container, ref.textSpan);
    if (!range) continue;

    const isArtist = ref.entity.kind === 'artist_mention';
    const mark = document.createElement('mark');
    mark.className = `fn-mark fn-mark--${ref.type}${isArtist ? ' fn-mark--artist' : ''} fn-mark--has-media`;
    mark.setAttribute('data-ref-id', ref.id);
    if (isArtist) mark.setAttribute('data-ref-kind', 'artist_mention');

    try {
      range.surroundContents(mark);
    } catch {
      const fragment = range.extractContents();
      mark.appendChild(fragment);
      range.insertNode(mark);
    }

    const iconSpan = document.createElement('span');
    iconSpan.className = 'fn-mark-icon';
    iconSpan.textContent = isArtist ? '\u2139' : getTypeIcon(ref.type);
    mark.appendChild(iconSpan);
  }
}

/** Normalize curly quotes, smart quotes, and dashes for fuzzy matching */
function normalizeForMatch(str: string): string {
  return str
    .replace(/[\u2018\u2019\u201A\u201B\u0060\u00B4]/g, "'")
    .replace(/[\u201C\u201D\u201E\u201F]/g, '"')
    .replace(/[\u2013\u2014]/g, '-');
}

/** Find a text string in the DOM and return a Range covering it.
 *  Skips text already inside .fn-mark elements so repeated entities
 *  match successive occurrences instead of double-wrapping the first. */
function findTextRange(container: HTMLElement, searchText: string): Range | null {
  // Collect text nodes, skipping those already highlighted
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (node.parentElement?.closest('.fn-mark')) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  const textNodes: Text[] = [];
  let node: Text | null;
  while ((node = walker.nextNode() as Text | null)) {
    textNodes.push(node);
  }

  // Build concatenated text with position mapping
  let fullText = '';
  const segments: { node: Text; start: number; length: number }[] = [];
  for (const tn of textNodes) {
    const content = tn.textContent || '';
    segments.push({ node: tn, start: fullText.length, length: content.length });
    fullText += content;
  }

  // Try exact match first, then normalized match
  const normalizedFull = normalizeForMatch(fullText);
  const normalizedSearch = normalizeForMatch(searchText);
  let idx = fullText.indexOf(searchText);
  if (idx === -1) idx = normalizedFull.indexOf(normalizedSearch);
  if (idx === -1) {
    // Try case-insensitive as last resort
    idx = normalizedFull.toLowerCase().indexOf(normalizedSearch.toLowerCase());
  }
  if (idx === -1) return null;

  const endIdx = idx + normalizedSearch.length;

  // Map character positions back to text nodes
  let startNode: Text | null = null;
  let startOffset = 0;
  let endNode: Text | null = null;
  let endOffset = 0;

  for (const seg of segments) {
    const segEnd = seg.start + seg.length;
    if (!startNode && idx < segEnd) {
      startNode = seg.node;
      startOffset = idx - seg.start;
    }
    if (endIdx <= segEnd) {
      endNode = seg.node;
      endOffset = endIdx - seg.start;
      break;
    }
  }

  if (!startNode || !endNode) return null;

  const range = document.createRange();
  range.setStart(startNode, startOffset);
  range.setEnd(endNode, endOffset);
  return range;
}

function getTypeIcon(type: string): string {
  switch (type) {
    case 'music': return '\u266B';
    case 'visual_art': return '\u25CF';
    case 'film': return '\u25B6';
    default: return '\u2022';
  }
}
