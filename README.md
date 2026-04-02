# Meeting Notes — Local Conference Call Listener

A local CLI tool that captures audio from your video conference calls (Zoom, Teams, Google Meet, etc.) **without any app integration**, transcribes the audio using Whisper, and generates structured meeting notes with decisions and action items via Claude.

Everything runs locally except the final summarization step (Claude API).

## Quick Start

```bash
# Install
pip install -e .

# Set your API key
export ANTHROPIC_API_KEY='your-key-here'

# Run
meeting-notes
```

The tool will:
1. Show available audio devices — pick your system audio loopback
2. Record until you press **Ctrl+C**
3. Transcribe the audio locally with Whisper
4. Send the transcript to Claude for structured notes
5. Save everything to the `output/` directory

## Platform Setup for System Audio Capture

The key requirement is capturing **system audio output** (what you hear in your speakers/headphones), not microphone input.

### Linux (PulseAudio / PipeWire)
Select the **"Monitor of ..."** device. This is the loopback device that captures all system audio output. No additional setup needed.

### macOS
macOS doesn't expose system audio as an input device natively. Install a virtual audio device:
1. Install [BlackHole](https://github.com/ExistentialAudio/BlackHole) (free, open source)
2. Create a Multi-Output Device in Audio MIDI Setup (your speakers + BlackHole)
3. Set the Multi-Output as your system output
4. Select BlackHole as the input device in this tool

### Windows
Select a **WASAPI Loopback** device. The tool automatically detects and labels these.

## Usage

```bash
# Interactive device selection
meeting-notes

# Specify device by index or name
meeting-notes --device 5
meeting-notes --device "Monitor"

# Use a more accurate (but slower) Whisper model
meeting-notes --whisper-model medium

# Only transcribe, skip AI summarization
meeting-notes --transcript-only

# Generate notes from a previously saved transcript
meeting-notes --from-transcript output/2024-01-15_143022_transcript.txt
```

## Output

Each session saves three files to `output/`:
- `YYYY-MM-DD_HHMMSS_recording.wav` — raw audio backup
- `YYYY-MM-DD_HHMMSS_transcript.txt` — full text transcript
- `YYYY-MM-DD_HHMMSS_meeting_notes.md` — structured notes with:
  - **Summary** — what was discussed
  - **Key Decisions** — what was decided
  - **Action Items** — who does what, by when
  - **Open Questions** — unresolved topics

## Dependencies

- **sounddevice** — cross-platform audio capture (wraps PortAudio)
- **openai-whisper** — local speech-to-text (includes PyTorch)
- **anthropic** — Claude API client for summarization
- **numpy** — audio array processing

## Whisper Model Sizes

| Model  | Size   | Speed     | Accuracy   |
|--------|--------|-----------|------------|
| tiny   | 39 MB  | Fastest   | Lower      |
| base   | 74 MB  | Fast      | Good       |
| small  | 244 MB | Moderate  | Better     |
| medium | 769 MB | Slow      | Very good  |
| large  | 1.5 GB | Slowest   | Best       |

Default is `base`. Use `--whisper-model tiny` for speed or `--whisper-model medium` for accuracy.
