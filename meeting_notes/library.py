"""Meeting notes library — index, search, and manage saved meeting notes."""

import json
from datetime import datetime
from pathlib import Path


INDEX_FILENAME = "meeting_index.json"


def _load_index(output_dir: Path) -> list[dict]:
    """Load the meeting index from disk."""
    index_path = output_dir / INDEX_FILENAME
    if index_path.exists():
        return json.loads(index_path.read_text())
    return []


def _save_index(output_dir: Path, index: list[dict]):
    """Save the meeting index to disk."""
    index_path = output_dir / INDEX_FILENAME
    index_path.write_text(json.dumps(index, indent=2))


def add_meeting(output_dir: Path, timestamp: str, notes_file: str,
                transcript_file: str, audio_file: str, notes_text: str) -> dict:
    """Add a meeting to the index and return the entry."""
    index = _load_index(output_dir)

    # Extract first line of Summary section as title
    title = "Untitled Meeting"
    for line in notes_text.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("---"):
            title = line[:100]
            break

    # Parse date from timestamp (YYYY-MM-DD_HHMMSS)
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%d_%H%M%S")
        date_display = dt.strftime("%B %d, %Y at %I:%M %p")
        date_sort = dt.isoformat()
    except ValueError:
        date_display = timestamp
        date_sort = timestamp

    entry = {
        "id": timestamp,
        "title": title,
        "date_display": date_display,
        "date_sort": date_sort,
        "notes_file": notes_file,
        "transcript_file": transcript_file,
        "audio_file": audio_file,
        "word_count": len(notes_text.split()),
        "keywords": _extract_keywords(notes_text),
    }

    # Avoid duplicates
    index = [e for e in index if e["id"] != timestamp]
    index.append(entry)
    # Sort newest first
    index.sort(key=lambda e: e["date_sort"], reverse=True)

    _save_index(output_dir, index)
    return entry


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from meeting notes for search indexing."""
    # Common words to skip
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how", "all", "both",
        "each", "few", "more", "most", "other", "some", "such", "no", "nor",
        "not", "only", "own", "same", "so", "than", "too", "very", "just",
        "because", "but", "and", "or", "if", "while", "about", "that", "this",
        "these", "those", "it", "its", "my", "your", "his", "her", "our",
        "their", "what", "which", "who", "whom", "we", "they", "he", "she",
        "you", "i", "me", "him", "us", "them",
    }

    words = text.lower().split()
    # Clean punctuation
    cleaned = []
    for w in words:
        w = w.strip(".,;:!?()[]{}\"'`#*-_/\\")
        if len(w) >= 3 and w not in stop_words and w.isalpha():
            cleaned.append(w)

    # Return unique keywords, preserving order of first appearance
    seen = set()
    unique = []
    for w in cleaned:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique


def search_meetings(output_dir: Path, query: str) -> list[dict]:
    """Search meetings by keyword. Returns matching entries sorted by relevance."""
    index = _load_index(output_dir)
    if not query.strip():
        return index

    query_words = query.lower().split()
    results = []

    for entry in index:
        score = 0
        searchable = (
            entry.get("title", "").lower() + " " +
            entry.get("date_display", "").lower() + " " +
            " ".join(entry.get("keywords", []))
        )

        for qw in query_words:
            if qw in searchable:
                score += 1
            # Partial match on keywords
            for kw in entry.get("keywords", []):
                if qw in kw:
                    score += 0.5

        if score > 0:
            results.append((score, entry))

    results.sort(key=lambda x: (-x[0], x[1]["date_sort"]), reverse=False)
    return [entry for _, entry in results]


def get_all_meetings(output_dir: Path) -> list[dict]:
    """Return all meetings sorted newest first."""
    return _load_index(output_dir)


def rebuild_index(output_dir: Path) -> int:
    """Scan the output directory and rebuild the index from existing files."""
    notes_files = sorted(output_dir.glob("*_meeting_notes.md"), reverse=True)
    index = []

    for notes_path in notes_files:
        # Extract timestamp from filename: YYYY-MM-DD_HHMMSS_meeting_notes.md
        name = notes_path.stem  # e.g., 2026-04-02_224959_meeting_notes
        parts = name.replace("_meeting_notes", "")
        timestamp = parts

        notes_text = notes_path.read_text()
        transcript_file = f"{timestamp}_transcript.txt"
        audio_file = f"{timestamp}_recording.wav"

        # Extract title from notes
        title = "Untitled Meeting"
        in_summary = False
        for line in notes_text.split("\n"):
            stripped = line.strip()
            if stripped.lower().startswith("## summary"):
                in_summary = True
                continue
            if in_summary and stripped and not stripped.startswith("#"):
                title = stripped[:100]
                break

        try:
            dt = datetime.strptime(timestamp, "%Y-%m-%d_%H%M%S")
            date_display = dt.strftime("%B %d, %Y at %I:%M %p")
            date_sort = dt.isoformat()
        except ValueError:
            date_display = timestamp
            date_sort = timestamp

        entry = {
            "id": timestamp,
            "title": title,
            "date_display": date_display,
            "date_sort": date_sort,
            "notes_file": notes_path.name,
            "transcript_file": transcript_file,
            "audio_file": audio_file,
            "word_count": len(notes_text.split()),
            "keywords": _extract_keywords(notes_text),
        }
        index.append(entry)

    index.sort(key=lambda e: e["date_sort"], reverse=True)
    _save_index(output_dir, index)
    return len(index)
