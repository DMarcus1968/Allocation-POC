import { useRef, useState, useEffect } from 'react';
import { ResolvedMedia } from '../../types';
import './InlinePlayer.css';

interface Props {
  media: ResolvedMedia;
  onClose: () => void;
}

export default function InlinePlayer({ media, onClose }: Props) {
  return (
    <div className="inline-player">
      <div className="inline-player-card">
        <button className="inline-player-close" onClick={onClose}>&times;</button>

        <div className="inline-player-header">
          {media.thumbnailUrl && (
            <img className="inline-player-thumb" src={media.thumbnailUrl} alt="" />
          )}
          <div className="inline-player-meta">
            <span className="inline-player-title">{media.title}</span>
            <span className="inline-player-creator">{media.creator}</span>
            <span className={`inline-player-type inline-player-type--${media.type}`}>
              {media.provider === 'wikipedia' ? '\u2139 Artist' : media.type === 'music' ? '\u266B Music' : media.type === 'visual_art' ? '\u25CF Art' : '\u25B6 Film'}
            </span>
          </div>
        </div>

        <div className="inline-player-body">
          {media.provider === 'youtube' && media.youtubeVideoId && (
            <YouTubeEmbed videoId={media.youtubeVideoId} />
          )}
          {media.provider === 'spotify' && media.previewUrl && (
            <AudioPlayer url={media.previewUrl} />
          )}
          {media.provider === 'image' && media.imageUrl && (
            <ImageView
              url={media.imageUrl}
              attribution={media.imageAttribution}
              source={media.imageSource}
            />
          )}
          {media.provider === 'wikipedia' && (
            <WikipediaView
              summary={media.wikipediaSummary}
              url={media.wikipediaUrl || `https://en.wikipedia.org/wiki/${encodeURIComponent(media.title)}`}
              thumbnailUrl={media.thumbnailUrl}
            />
          )}
          {media.provider === 'youtube-search' && media.youtubeSearchQuery && (
            <YouTubeSearchLink query={media.youtubeSearchQuery} title={media.title} creator={media.creator} />
          )}
          {/* Fallback when no playable content */}
          {media.provider !== 'wikipedia' && !media.youtubeVideoId && !media.previewUrl && !media.imageUrl && !media.youtubeSearchQuery && (
            <div className="inline-player-empty">
              <p>No preview available for this reference.</p>
              <p className="inline-player-entity">
                <strong>{media.title}</strong> by {media.creator}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function YouTubeEmbed({ videoId }: { videoId: string }) {
  if (!/^[\w-]+$/.test(videoId)) return null;
  return (
    <div className="inline-player-video">
      <iframe
        src={`https://www.youtube.com/embed/${videoId}?autoplay=1`}
        allow="autoplay; encrypted-media"
        allowFullScreen
        title="Video"
      />
    </div>
  );
}

function AudioPlayer({ url }: { url: string }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTime = () => setProgress(audio.currentTime);
    const onLoad = () => setDuration(audio.duration);
    const onEnd = () => setPlaying(false);

    audio.addEventListener('timeupdate', onTime);
    audio.addEventListener('loadedmetadata', onLoad);
    audio.addEventListener('ended', onEnd);

    return () => {
      audio.removeEventListener('timeupdate', onTime);
      audio.removeEventListener('loadedmetadata', onLoad);
      audio.removeEventListener('ended', onEnd);
      audio.pause();
    };
  }, []);

  const toggle = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) audio.pause();
    else audio.play();
    setPlaying(!playing);
  };

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    audio.currentTime = pct * duration;
  };

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  return (
    <div className="audio-player">
      <audio ref={audioRef} src={url} preload="metadata" />
      <button className="audio-play-btn" onClick={toggle}>
        {playing ? '\u23F8' : '\u25B6'}
      </button>
      <div className="audio-progress" onClick={seek}>
        <div className="audio-progress-bar" style={{ width: duration ? `${(progress / duration) * 100}%` : '0%' }} />
      </div>
      <span className="audio-time">{fmt(progress)} / {fmt(duration)}</span>
    </div>
  );
}

function ImageView({ url, attribution, source }: { url: string; attribution?: string; source?: string }) {
  return (
    <div className="image-view">
      <img src={url} alt="" className="image-view-img" />
      {attribution && (
        <p className="image-view-attr">
          {source ? <a href={source} target="_blank" rel="noopener noreferrer">{attribution}</a> : attribution}
        </p>
      )}
    </div>
  );
}

function WikipediaView({ summary, url, thumbnailUrl }: { summary?: string; url: string; thumbnailUrl?: string }) {
  return (
    <div className="wiki-view">
      {thumbnailUrl && <img src={thumbnailUrl} alt="" className="wiki-view-img" />}
      {summary && <p className="wiki-view-summary">{summary}</p>}
      <a href={url} target="_blank" rel="noopener noreferrer" className="wiki-view-link">
        Read on Wikipedia
      </a>
    </div>
  );
}

function YouTubeSearchLink({ query, title, creator }: { query: string; title: string; creator: string }) {
  const url = `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
  return (
    <div className="yt-search-link">
      <a href={url} target="_blank" rel="noopener noreferrer" className="yt-search-btn">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
          <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
        </svg>
        Watch "{title}" on YouTube
      </a>
      <p className="yt-search-hint">by {creator}</p>
    </div>
  );
}
