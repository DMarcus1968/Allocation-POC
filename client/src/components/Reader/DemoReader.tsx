import { useEffect, useState, useRef, useCallback } from 'react';
import { BookMeta, DemoChapter, MediaReference, ResolvedMedia } from '../../types';
import { fetchDemoBook, analyzePassage } from '../../services/api';
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
  const [analyzing, setAnalyzing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [inlineRefId, setInlineRefId] = useState<string | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

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

  // Clean up any active inline player
  const cleanupInlinePlayer = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    contentRef.current?.querySelectorAll('.fn-inline-player').forEach(el => el.remove());
    setInlineRefId(null);
  }, []);

  // Create an inline media player below the paragraph containing the reference
  const openInlinePlayer = useCallback((ref: MediaReference, media: ResolvedMedia, markEl: HTMLElement) => {
    const container = contentRef.current;
    if (!container) return;

    // If this ref is already open, toggle it off
    const existing = container.querySelector(`.fn-inline-player[data-ref-id="${ref.id}"]`);
    if (existing) {
      cleanupInlinePlayer();
      return;
    }

    // Close any other open inline player first
    cleanupInlinePlayer();
    setInlineRefId(ref.id);

    // Walk up to find the block-level parent to insert after
    let insertAfter: HTMLElement = markEl;
    while (insertAfter.parentElement && insertAfter.parentElement !== container) {
      if (['P', 'DIV', 'BLOCKQUOTE', 'H2', 'H3'].includes(insertAfter.tagName)) break;
      insertAfter = insertAfter.parentElement;
    }

    // Build the inline player element
    const player = document.createElement('div');
    player.className = `fn-inline-player fn-inline-player--${ref.type}`;
    player.dataset.refId = ref.id;

    // --- Header row: thumbnail + title/creator + close ---
    const header = document.createElement('div');
    header.className = 'fn-inline-header';

    if (media.thumbnailUrl) {
      const thumb = document.createElement('img');
      thumb.className = 'fn-inline-thumb';
      thumb.src = media.thumbnailUrl;
      thumb.alt = media.title;
      header.appendChild(thumb);
    }

    const textDiv = document.createElement('div');
    textDiv.className = 'fn-inline-text';
    const titleEl = document.createElement('strong');
    titleEl.textContent = media.title;
    const creatorEl = document.createElement('span');
    creatorEl.textContent = media.creator;
    textDiv.appendChild(titleEl);
    textDiv.appendChild(creatorEl);
    header.appendChild(textDiv);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'fn-inline-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', () => cleanupInlinePlayer());
    header.appendChild(closeBtn);

    player.appendChild(header);

    // --- Media body ---
    if (media.previewUrl) {
      // Spotify audio preview with progress bar
      const audio = new Audio(media.previewUrl);
      audioRef.current = audio;

      const controls = document.createElement('div');
      controls.className = 'fn-inline-audio-controls';

      const playPauseBtn = document.createElement('button');
      playPauseBtn.className = 'fn-inline-play-pause';
      playPauseBtn.textContent = '\u25B6';

      const progressWrap = document.createElement('div');
      progressWrap.className = 'fn-inline-progress-wrap';
      const progressBar = document.createElement('div');
      progressBar.className = 'fn-inline-progress-bar';
      progressWrap.appendChild(progressBar);

      const timeDisplay = document.createElement('span');
      timeDisplay.className = 'fn-inline-time';
      timeDisplay.textContent = '0:00';

      audio.addEventListener('play', () => { playPauseBtn.textContent = '\u275A\u275A'; });
      audio.addEventListener('pause', () => { playPauseBtn.textContent = '\u25B6'; });
      audio.addEventListener('ended', () => { playPauseBtn.textContent = '\u25B6'; });
      audio.addEventListener('timeupdate', () => {
        const pct = audio.duration ? (audio.currentTime / audio.duration) * 100 : 0;
        progressBar.style.width = `${pct}%`;
        const mins = Math.floor(audio.currentTime / 60);
        const secs = Math.floor(audio.currentTime % 60).toString().padStart(2, '0');
        timeDisplay.textContent = `${mins}:${secs}`;
      });

      playPauseBtn.addEventListener('click', () => {
        if (audio.paused) audio.play();
        else audio.pause();
      });

      progressWrap.addEventListener('click', (ev) => {
        const rect = progressWrap.getBoundingClientRect();
        const pct = (ev.clientX - rect.left) / rect.width;
        if (audio.duration) audio.currentTime = pct * audio.duration;
      });

      controls.appendChild(playPauseBtn);
      controls.appendChild(progressWrap);
      controls.appendChild(timeDisplay);
      player.appendChild(controls);

      audio.play().catch(() => {});

    } else if (media.youtubeVideoId && /^[\w-]+$/.test(media.youtubeVideoId)) {
      // YouTube embed
      const videoWrap = document.createElement('div');
      videoWrap.className = 'fn-inline-video';
      const iframe = document.createElement('iframe');
      iframe.src = `https://www.youtube.com/embed/${media.youtubeVideoId}?autoplay=1`;
      iframe.allow = 'autoplay; encrypted-media';
      iframe.allowFullscreen = true;
      iframe.title = media.title;
      videoWrap.appendChild(iframe);
      player.appendChild(videoWrap);

    } else if (media.imageUrl) {
      // Artwork image
      const imgWrap = document.createElement('div');
      imgWrap.className = 'fn-inline-image';
      const img = document.createElement('img');
      img.src = media.imageUrl;
      img.alt = media.title;
      imgWrap.appendChild(img);

      if (media.imageAttribution) {
        const attr = document.createElement('p');
        attr.className = 'fn-inline-attr';
        attr.textContent = media.imageAttribution;
        imgWrap.appendChild(attr);
      }
      player.appendChild(imgWrap);
    }

    // Insert into the DOM right after the paragraph
    insertAfter.insertAdjacentElement('afterend', player);

    // Smooth-scroll the player into view
    setTimeout(() => player.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 50);
  }, [cleanupInlinePlayer]);

  // Highlight references in the rendered HTML + add inline play buttons
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

        range.surroundContents(mark);

        // Create the small inline play/view button
        const playBtn = document.createElement('button');
        playBtn.className = `fn-play-btn fn-play-btn--${ref.type}`;
        playBtn.dataset.refId = ref.id;

        if (ref.type === 'visual_art') {
          playBtn.innerHTML = '&#9673;'; // ◉ view icon
          playBtn.title = `View ${ref.entity.title}`;
        } else {
          playBtn.innerHTML = '&#9654;'; // ▶ play icon
          playBtn.title = `${ref.type === 'music' ? 'Play' : 'Watch'} ${ref.entity.title}`;
        }

        const media = resolvedMedia.get(ref.id);

        // Click handler: open inline player
        const handleClick = (e: Event) => {
          e.stopPropagation();
          if (!media) return;
          openInlinePlayer(ref, media, mark);
        };

        playBtn.addEventListener('click', handleClick);
        mark.addEventListener('click', handleClick);

        // Insert the button right after the mark
        mark.insertAdjacentElement('afterend', playBtn);
        break;
      }
    }

    // Cleanup audio on unmount / re-injection
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
        audioRef.current = null;
      }
    };
  }, [references, resolvedMedia, currentChapter, openInlinePlayer]);

  // Sidebar click: scroll to reference and open inline player
  const handleSidebarClick = (ref: MediaReference) => {
    const media = resolvedMedia.get(ref.id);
    if (!media || !contentRef.current) return;

    const mark = contentRef.current.querySelector(`mark[data-ref-id="${ref.id}"]`) as HTMLElement | null;
    if (mark) {
      mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setTimeout(() => openInlinePlayer(ref, media, mark), 350);
    }
  };

  const goToChapter = (idx: number) => {
    cleanupInlinePlayer();
    setCurrentChapter(idx);
    setReferences([]);
    setResolvedMedia(new Map());
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
                    inlineRefId === ref.id ? 'selected' : ''
                  }`}
                  onClick={() => handleSidebarClick(ref)}
                >
                  <span className="sidebar-icon">
                    {ref.type === 'music' ? '\u266A' : ref.type === 'film' ? '\u25B6' : '\uD83D\uDDBC'}
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
    </div>
  );
}
