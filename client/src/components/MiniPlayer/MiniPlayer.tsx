import { useState, useRef, useEffect } from 'react';
import { ResolvedMedia } from '../../types';
import './MiniPlayer.css';

interface Props {
  media: ResolvedMedia;
  onClose: () => void;
}

export default function MiniPlayer({ media, onClose }: Props) {
  const [playing, setPlaying] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Handle Spotify audio preview
  useEffect(() => {
    if (media.provider === 'spotify' && media.previewUrl) {
      const audio = new Audio(media.previewUrl);
      audioRef.current = audio;

      audio.addEventListener('ended', () => setPlaying(false));
      audio.play().then(() => setPlaying(true)).catch(() => {});

      return () => {
        audio.pause();
        audio.src = '';
      };
    }
  }, [media]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (playing) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setPlaying(!playing);
  };

  // YouTube player
  if (media.provider === 'youtube' && media.youtubeVideoId) {
    return (
      <div className={`mini-player mini-player--youtube ${expanded ? 'expanded' : ''}`}>
        <div className="mini-player-bar">
          <div className="mini-player-info">
            <span className="mini-player-type">▶</span>
            <div className="mini-player-text">
              <span className="mini-player-title">{media.title}</span>
              <span className="mini-player-creator">{media.creator}</span>
            </div>
          </div>
          <div className="mini-player-controls">
            <button onClick={() => setExpanded(!expanded)}>
              {expanded ? '▾' : '▴'}
            </button>
            <button className="mini-player-close" onClick={onClose}>
              &times;
            </button>
          </div>
        </div>
        {expanded && (
          <div className="mini-player-video">
            <iframe
              src={`https://www.youtube.com/embed/${media.youtubeVideoId}?autoplay=1`}
              allow="autoplay; encrypted-media"
              allowFullScreen
              title={media.title}
            />
          </div>
        )}
      </div>
    );
  }

  // Image viewer
  if (media.provider === 'image' && media.imageUrl) {
    return (
      <div className={`mini-player mini-player--image ${expanded ? 'expanded' : ''}`}>
        <div className="mini-player-bar">
          <div className="mini-player-info">
            <span className="mini-player-type mini-player-type--art">art</span>
            <div className="mini-player-text">
              <span className="mini-player-title">{media.title}</span>
              <span className="mini-player-creator">{media.creator}</span>
            </div>
          </div>
          <div className="mini-player-controls">
            <button onClick={() => setExpanded(!expanded)}>
              {expanded ? '▾' : '▴'}
            </button>
            <button className="mini-player-close" onClick={onClose}>
              &times;
            </button>
          </div>
        </div>
        {expanded && (
          <div className="mini-player-image">
            <img src={media.imageUrl} alt={media.title} />
            {media.imageAttribution && (
              <p className="image-attribution">{media.imageAttribution}</p>
            )}
          </div>
        )}
      </div>
    );
  }

  // Spotify audio player (default)
  return (
    <div className="mini-player mini-player--spotify">
      <div className="mini-player-bar">
        {media.thumbnailUrl && (
          <img
            className="mini-player-thumb"
            src={media.thumbnailUrl}
            alt={media.title}
          />
        )}
        <div className="mini-player-info">
          <div className="mini-player-text">
            <span className="mini-player-title">{media.title}</span>
            <span className="mini-player-creator">{media.creator}</span>
          </div>
        </div>
        <div className="mini-player-controls">
          {media.previewUrl && (
            <button className="play-btn" onClick={togglePlay}>
              {playing ? '❚❚' : '▶'}
            </button>
          )}
          {media.spotifyUri && (
            <a
              className="spotify-link"
              href={`https://open.spotify.com/${media.spotifyUri.replace('spotify:', '').replace(/:/g, '/')}`}
              target="_blank"
              rel="noopener noreferrer"
              title="Open in Spotify"
            >
              ↗
            </a>
          )}
          <button className="mini-player-close" onClick={onClose}>
            &times;
          </button>
        </div>
      </div>
    </div>
  );
}
