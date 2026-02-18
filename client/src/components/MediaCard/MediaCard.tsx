import { MediaReference, ResolvedMedia } from '../../types';
import './MediaCard.css';

interface Props {
  reference: MediaReference;
  media: ResolvedMedia | null;
  onClose: () => void;
  onPlay: (media: ResolvedMedia) => void;
}

export default function MediaCard({ reference, media, onClose, onPlay }: Props) {
  const typeLabel =
    reference.type === 'music' ? 'Music' :
    reference.type === 'film' ? 'Film' :
    'Art';

  const typeClass = `media-card--${reference.type}`;

  return (
    <div className="media-card-overlay" onClick={onClose}>
      <div className={`media-card ${typeClass}`} onClick={e => e.stopPropagation()}>
        <div className="media-card-header">
          <span className={`media-card-type type--${reference.type}`}>
            {typeLabel}
          </span>
          <button className="media-card-close" onClick={onClose}>
            &times;
          </button>
        </div>

        {media?.thumbnailUrl && (
          <div className="media-card-thumb">
            <img src={media.thumbnailUrl} alt={reference.entity.title} />
          </div>
        )}

        <div className="media-card-info">
          <h3 className="media-card-title">{reference.entity.title}</h3>
          <p className="media-card-creator">{reference.entity.creator}</p>
          {reference.entity.year && (
            <p className="media-card-year">{reference.entity.year}</p>
          )}
          <p className="media-card-kind">{reference.entity.kind}</p>
        </div>

        <div className="media-card-quote">
          <q>{reference.textSpan}</q>
        </div>

        {media && (
          <div className="media-card-actions">
            {media.provider === 'spotify' && media.previewUrl && (
              <button
                className="media-btn media-btn--spotify"
                onClick={() => onPlay(media)}
              >
                &#9654; Play Preview
              </button>
            )}
            {media.provider === 'spotify' && media.spotifyUri && (
              <a
                className="media-btn media-btn--spotify-link"
                href={`https://open.spotify.com/${media.spotifyUri.replace('spotify:', '').replace(/:/g, '/')}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open in Spotify
              </a>
            )}
            {media.provider === 'youtube' && media.youtubeVideoId && (
              <button
                className="media-btn media-btn--youtube"
                onClick={() => onPlay(media)}
              >
                &#9654; Watch
              </button>
            )}
            {media.provider === 'image' && media.imageUrl && (
              <a
                className="media-btn media-btn--image"
                href={media.imageSource || media.imageUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                View Full Image
              </a>
            )}
          </div>
        )}

        {!media && (
          <div className="media-card-no-media">
            <p>Media not found on available services</p>
          </div>
        )}
      </div>
    </div>
  );
}
