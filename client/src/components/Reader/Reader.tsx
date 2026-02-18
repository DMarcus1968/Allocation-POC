import { useEffect, useRef, useState, useCallback } from 'react';
import ePub, { Book, Rendition } from 'epubjs';
import { BookMeta, MediaReference, ResolvedMedia } from '../../types';
import { analyzePassage, getBookFileUrl } from '../../services/api';
import MediaCard from '../MediaCard/MediaCard';
import MiniPlayer from '../MiniPlayer/MiniPlayer';
import './Reader.css';

interface Props {
  book: BookMeta;
  onBack: () => void;
}

export default function Reader({ book, onBack }: Props) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const bookRef = useRef<Book | null>(null);
  const renditionRef = useRef<Rendition | null>(null);

  const [references, setReferences] = useState<MediaReference[]>([]);
  const [resolvedMedia, setResolvedMedia] = useState<Map<string, ResolvedMedia>>(new Map());
  const [selectedRef, setSelectedRef] = useState<MediaReference | null>(null);
  const [activeMedia, setActiveMedia] = useState<ResolvedMedia | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [currentCfi, setCurrentCfi] = useState<string>('');
  const [chapterTitle, setChapterTitle] = useState<string>('');

  // Load EPUB
  useEffect(() => {
    if (!viewerRef.current) return;

    const epubBook = ePub(getBookFileUrl(book.id));
    bookRef.current = epubBook;

    const rendition = epubBook.renderTo(viewerRef.current, {
      width: '100%',
      height: '100%',
      spread: 'none',
      flow: 'paginated',
    });

    renditionRef.current = rendition;
    rendition.display();

    // Track location changes for analysis
    rendition.on('relocated', (location: any) => {
      const cfi = location.start?.cfi;
      if (cfi) setCurrentCfi(cfi);
    });

    // Track chapter changes
    rendition.on('rendered', (section: any) => {
      const nav = epubBook.navigation;
      if (nav) {
        const tocItem = nav.toc.find(
          (item: any) => item.href && section.href?.includes(item.href)
        );
        if (tocItem) setChapterTitle(tocItem.label?.trim() || '');
      }
    });

    // Keyboard navigation
    rendition.on('keyup', (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') rendition.prev();
      if (e.key === 'ArrowRight') rendition.next();
    });

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') rendition.prev();
      if (e.key === 'ArrowRight') rendition.next();
    };
    document.addEventListener('keyup', handleKeyUp);

    return () => {
      document.removeEventListener('keyup', handleKeyUp);
      epubBook.destroy();
    };
  }, [book.id]);

  // Analyze visible text when page changes
  const analyzeCurrentPage = useCallback(async () => {
    const rendition = renditionRef.current;
    if (!rendition || !currentCfi || analyzing) return;

    setAnalyzing(true);
    try {
      // Get visible text from the current page
      const contents = rendition.getContents();
      let visibleText = '';
      for (const content of contents as unknown as any[]) {
        const doc = content.document;
        if (doc?.body) {
          visibleText = doc.body.innerText || doc.body.textContent || '';
        }
      }

      if (!visibleText.trim()) {
        setAnalyzing(false);
        return;
      }

      const result = await analyzePassage(book.id, currentCfi, visibleText);

      setReferences(result.references);

      // Merge resolved media into our map
      const newMap = new Map(resolvedMedia);
      for (const media of result.resolvedMedia) {
        newMap.set(media.referenceId, media);
      }
      setResolvedMedia(newMap);

      // Highlight references in the text
      highlightReferences(result.references);
    } catch (err) {
      console.error('Analysis failed:', err);
    } finally {
      setAnalyzing(false);
    }
  }, [book.id, currentCfi, analyzing, resolvedMedia]);

  // Debounced analysis on page change
  useEffect(() => {
    if (!currentCfi) return;
    const timer = setTimeout(analyzeCurrentPage, 500);
    return () => clearTimeout(timer);
  }, [currentCfi]); // eslint-disable-line react-hooks/exhaustive-deps

  const highlightReferences = (refs: MediaReference[]) => {
    const rendition = renditionRef.current;
    if (!rendition) return;

    // For now, we mark references inline by finding their text spans
    // A full implementation would use CFI ranges for precise highlighting
    const contents = rendition.getContents();
    for (const content of contents as unknown as any[]) {
      const doc = content.document as Document;
      if (!doc?.body) continue;

      for (const ref of refs) {
        const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
        let node: Node | null;
        while ((node = walker.nextNode())) {
          const text = node.textContent || '';
          const idx = text.indexOf(ref.textSpan);
          if (idx === -1) continue;

          const range = doc.createRange();
          range.setStart(node, idx);
          range.setEnd(node, idx + ref.textSpan.length);

          const mark = doc.createElement('mark');
          mark.className = `footnote-mark footnote-mark--${ref.type}`;
          mark.dataset.refId = ref.id;
          mark.title = `${ref.entity.title} — ${ref.entity.creator}`;
          mark.addEventListener('click', () => {
            setSelectedRef(ref);
            const media = resolvedMedia.get(ref.id);
            if (media) setActiveMedia(media);
          });

          range.surroundContents(mark);
          break; // Only highlight first occurrence
        }
      }
    }
  };

  const handlePrev = () => renditionRef.current?.prev();
  const handleNext = () => renditionRef.current?.next();

  const handleRefClick = (ref: MediaReference) => {
    setSelectedRef(ref);
    const media = resolvedMedia.get(ref.id);
    if (media) setActiveMedia(media);
  };

  return (
    <div className="reader">
      <div className="reader-toolbar">
        <button className="reader-back" onClick={onBack}>
          &larr; Library
        </button>
        <div className="reader-chapter">{chapterTitle}</div>
        <div className="reader-status">
          {analyzing && <span className="analyzing-badge">Analyzing...</span>}
          {references.length > 0 && (
            <span className="ref-count">{references.length} media found</span>
          )}
        </div>
      </div>

      <div className="reader-content">
        <button className="reader-nav reader-nav--prev" onClick={handlePrev}>
          &#8249;
        </button>

        <div className="reader-viewer" ref={viewerRef} />

        <button className="reader-nav reader-nav--next" onClick={handleNext}>
          &#8250;
        </button>
      </div>

      {/* Sidebar: media references found on this page */}
      {references.length > 0 && (
        <div className="reader-sidebar">
          <h3 className="sidebar-title">Media on this page</h3>
          <div className="sidebar-refs">
            {references.map(ref => (
              <button
                key={ref.id}
                className={`sidebar-ref sidebar-ref--${ref.type} ${
                  selectedRef?.id === ref.id ? 'selected' : ''
                }`}
                onClick={() => handleRefClick(ref)}
              >
                <span className="ref-type-icon">
                  {ref.type === 'music' ? '♪' : ref.type === 'film' ? '▶' : '🖼'}
                </span>
                <div className="ref-details">
                  <span className="ref-entity-title">{ref.entity.title}</span>
                  <span className="ref-entity-creator">{ref.entity.creator}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Media card overlay */}
      {selectedRef && (
        <MediaCard
          reference={selectedRef}
          media={resolvedMedia.get(selectedRef.id) || null}
          onClose={() => setSelectedRef(null)}
          onPlay={(media) => setActiveMedia(media)}
        />
      )}

      {/* Persistent mini-player */}
      {activeMedia && (
        <MiniPlayer
          media={activeMedia}
          onClose={() => setActiveMedia(null)}
        />
      )}
    </div>
  );
}
