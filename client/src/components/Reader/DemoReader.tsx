import { useEffect, useState, useRef, useCallback } from 'react';
import { BookMeta, DemoChapter, MediaReference, ResolvedMedia } from '../../types';
import { fetchDemoBook, analyzePassage } from '../../services/api';
import MediaCard from '../MediaCard/MediaCard';
import MiniPlayer from '../MiniPlayer/MiniPlayer';
import './DemoReader.css';

interface Props {
  book: BookMeta;
  onBack: () => void;
}

export default function DemoReader({ book, onBack }: Props) {
  const [chapters, setChapters] = useState<DemoChapter[]>([]);
  const [currentChapter, setCurrentChapter] = useState(0);
  const [references, setReferences] = useState<MediaReference[]>([]);
  const [resolvedMedia, setResolvedMedia] = useState<Map<string, ResolvedMedia>>(new Map());
  const [selectedRef, setSelectedRef] = useState<MediaReference | null>(null);
  const [activeMedia, setActiveMedia] = useState<ResolvedMedia | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [loading, setLoading] = useState(true);
  const contentRef = useRef<HTMLDivElement>(null);

  // Load demo book
  useEffect(() => {
    fetchDemoBook()
      .then(data => {
        setChapters(data.chapters);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load demo:', err);
        setLoading(false);
      });
  }, []);

  // Analyze chapter text when chapter changes
  const analyzeChapter = useCallback(async () => {
    if (!chapters[currentChapter] || analyzing) return;

    setAnalyzing(true);
    try {
      // Extract plain text from the HTML
      const tmp = document.createElement('div');
      tmp.innerHTML = chapters[currentChapter].html;
      const text = tmp.textContent || tmp.innerText || '';

      const result = await analyzePassage(
        book.id,
        `chapter-${currentChapter}`,
        text
      );

      setReferences(result.references);

      const newMap = new Map<string, ResolvedMedia>();
      for (const media of result.resolvedMedia) {
        newMap.set(media.referenceId, media);
      }
      setResolvedMedia(newMap);
    } catch (err) {
      console.error('Analysis failed:', err);
    } finally {
      setAnalyzing(false);
    }
  }, [book.id, currentChapter, chapters, analyzing]);

  useEffect(() => {
    if (chapters.length > 0) {
      analyzeChapter();
    }
  }, [currentChapter, chapters.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // Highlight references in the rendered HTML
  useEffect(() => {
    if (!contentRef.current || references.length === 0) return;

    const container = contentRef.current;
    for (const ref of references) {
      const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
      let node: Node | null;
      while ((node = walker.nextNode())) {
        const text = node.textContent || '';
        const idx = text.indexOf(ref.textSpan);
        if (idx === -1) continue;

        const range = document.createRange();
        range.setStart(node, idx);
        range.setEnd(node, idx + ref.textSpan.length);

        const mark = document.createElement('mark');
        mark.className = `fn-highlight fn-highlight--${ref.type}`;
        mark.dataset.refId = ref.id;
        mark.title = `${ref.entity.title} — ${ref.entity.creator}`;
        mark.style.cursor = 'pointer';
        mark.addEventListener('click', () => {
          setSelectedRef(ref);
          const media = resolvedMedia.get(ref.id);
          if (media) setActiveMedia(media);
        });

        range.surroundContents(mark);
        break;
      }
    }
  }, [references, resolvedMedia, currentChapter]);

  const handleRefClick = (ref: MediaReference) => {
    setSelectedRef(ref);
    const media = resolvedMedia.get(ref.id);
    if (media) setActiveMedia(media);
  };

  const goToChapter = (idx: number) => {
    setCurrentChapter(idx);
    setReferences([]);
    setResolvedMedia(new Map());
    setSelectedRef(null);
    contentRef.current?.scrollTo(0, 0);
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' && currentChapter < chapters.length - 1) {
        goToChapter(currentChapter + 1);
      } else if (e.key === 'ArrowLeft' && currentChapter > 0) {
        goToChapter(currentChapter - 1);
      }
    };
    document.addEventListener('keyup', handleKey);
    return () => document.removeEventListener('keyup', handleKey);
  }, [currentChapter, chapters.length]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <div className="demo-reader">
        <div className="demo-loading">Loading demo book...</div>
      </div>
    );
  }

  return (
    <div className="demo-reader">
      {/* Toolbar */}
      <div className="demo-toolbar">
        <button className="demo-back" onClick={onBack}>
          &larr; Library
        </button>
        <div className="demo-chapter-title">
          {chapters[currentChapter]?.title || ''}
        </div>
        <div className="demo-status">
          {analyzing && <span className="demo-analyzing">Scanning for media...</span>}
          {!analyzing && references.length > 0 && (
            <span className="demo-found">{references.length} media found</span>
          )}
        </div>
      </div>

      <div className="demo-layout">
        {/* Chapter navigation */}
        <nav className="demo-toc">
          <h4 className="toc-label">Chapters</h4>
          {chapters.map((ch, i) => (
            <button
              key={i}
              className={`toc-item ${i === currentChapter ? 'active' : ''}`}
              onClick={() => goToChapter(i)}
            >
              {ch.title}
            </button>
          ))}
        </nav>

        {/* Main reading area */}
        <div className="demo-content-area">
          <button
            className="demo-nav demo-nav--prev"
            disabled={currentChapter === 0}
            onClick={() => goToChapter(currentChapter - 1)}
          >
            &#8249;
          </button>

          <div
            className="demo-content"
            ref={contentRef}
            dangerouslySetInnerHTML={{
              __html: chapters[currentChapter]?.html || '',
            }}
          />

          <button
            className="demo-nav demo-nav--next"
            disabled={currentChapter === chapters.length - 1}
            onClick={() => goToChapter(currentChapter + 1)}
          >
            &#8250;
          </button>
        </div>

        {/* Media sidebar */}
        {references.length > 0 && (
          <aside className="demo-sidebar">
            <h4 className="sidebar-label">Media on this page</h4>
            <div className="sidebar-list">
              {references.map(ref => (
                <button
                  key={ref.id}
                  className={`sidebar-item sidebar-item--${ref.type} ${
                    selectedRef?.id === ref.id ? 'selected' : ''
                  }`}
                  onClick={() => handleRefClick(ref)}
                >
                  <span className="sidebar-icon">
                    {ref.type === 'music' ? '♪' : ref.type === 'film' ? '▶' : '🖼'}
                  </span>
                  <div className="sidebar-text">
                    <span className="sidebar-entity-title">{ref.entity.title}</span>
                    <span className="sidebar-entity-creator">{ref.entity.creator}</span>
                  </div>
                </button>
              ))}
            </div>
          </aside>
        )}
      </div>

      {/* Page indicator */}
      <div className="demo-pagination">
        {chapters.map((_, i) => (
          <button
            key={i}
            className={`page-dot ${i === currentChapter ? 'active' : ''}`}
            onClick={() => goToChapter(i)}
          />
        ))}
      </div>

      {/* Media card overlay */}
      {selectedRef && (
        <MediaCard
          reference={selectedRef}
          media={resolvedMedia.get(selectedRef.id) || null}
          onClose={() => setSelectedRef(null)}
          onPlay={(media) => setActiveMedia(media)}
        />
      )}

      {/* Mini player */}
      {activeMedia && (
        <MiniPlayer
          media={activeMedia}
          onClose={() => setActiveMedia(null)}
        />
      )}
    </div>
  );
}
