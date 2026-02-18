import { ResolvedMedia } from '../../types';
import './Lightbox.css';

interface Props {
  media: ResolvedMedia;
  onClose: () => void;
}

export default function Lightbox({ media, onClose }: Props) {
  if (!media.imageUrl) return null;

  return (
    <div className="lightbox-overlay" onClick={onClose}>
      <div className="lightbox-content" onClick={e => e.stopPropagation()}>
        <button className="lightbox-close" onClick={onClose}>
          &times;
        </button>
        <img
          className="lightbox-image"
          src={media.imageUrl}
          alt={media.title}
        />
        <div className="lightbox-info">
          <h3>{media.title}</h3>
          <p>{media.creator}</p>
          {media.imageAttribution && media.imageAttribution !== media.creator && (
            <p className="lightbox-attribution">{media.imageAttribution}</p>
          )}
          {media.imageSource && (
            <a
              className="lightbox-source"
              href={media.imageSource}
              target="_blank"
              rel="noopener noreferrer"
            >
              View source
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
