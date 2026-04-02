import sys

import numpy as np


def _chunk_audio(audio: np.ndarray, sample_rate: int,
                 chunk_secs: int = 300, overlap_secs: int = 15) -> list[np.ndarray]:
    """Split audio into overlapping chunks."""
    chunk_samples = chunk_secs * sample_rate
    overlap_samples = overlap_secs * sample_rate
    step = chunk_samples - overlap_samples

    chunks = []
    start = 0
    while start < len(audio):
        end = min(start + chunk_samples, len(audio))
        chunks.append(audio[start:end])
        if end == len(audio):
            break
        start += step

    return chunks


def _deduplicate_overlap(prev_text: str, curr_text: str, overlap_words: int = 20) -> str:
    """Remove duplicated text at the boundary between two chunks."""
    prev_words = prev_text.split()
    curr_words = curr_text.split()

    if not prev_words or not curr_words:
        return curr_text

    # Look for overlap: find where the end of prev matches the start of curr
    tail = prev_words[-overlap_words:]

    best_match = 0
    for start_idx in range(min(len(curr_words), overlap_words)):
        match_len = 0
        for j in range(min(len(tail), len(curr_words) - start_idx)):
            if tail[-(j + 1)].lower() == curr_words[start_idx + match_len].lower():
                match_len += 1
            else:
                break
        if match_len >= 3:  # Need at least 3 consecutive words to count as overlap
            best_match = max(best_match, start_idx + match_len)

    if best_match > 0:
        return " ".join(curr_words[best_match:])
    return curr_text


def transcribe(audio: np.ndarray, sample_rate: int = 16000,
               model_size: str = "base", chunk_secs: int = 300,
               overlap_secs: int = 15) -> str:
    """Transcribe audio array to text using Whisper.

    Handles long audio by chunking with overlap and deduplication.
    """
    print("Loading Whisper model...")
    try:
        import whisper
    except ImportError:
        print("Error: openai-whisper is not installed.")
        print("Install it with: pip install openai-whisper")
        sys.exit(1)

    model = whisper.load_model(model_size)
    print(f"Using Whisper model: {model_size}")

    duration = len(audio) / sample_rate
    chunks = _chunk_audio(audio, sample_rate, chunk_secs, overlap_secs)

    print(f"Audio duration: {duration:.1f}s — split into {len(chunks)} chunk(s)")

    transcript_parts = []
    for i, chunk in enumerate(chunks):
        print(f"  Transcribing chunk {i + 1}/{len(chunks)}...")

        # Whisper expects float32 audio normalized to [-1, 1]
        chunk = chunk.astype(np.float32)

        # Pad or trim to fit whisper's expectations
        result = model.transcribe(chunk, fp16=False, language="en")
        chunk_text = result["text"].strip()

        if transcript_parts and chunk_text:
            chunk_text = _deduplicate_overlap(transcript_parts[-1], chunk_text)

        if chunk_text:
            transcript_parts.append(chunk_text)

    transcript = " ".join(transcript_parts)
    word_count = len(transcript.split())
    print(f"Transcription complete: {word_count} words")

    return transcript
