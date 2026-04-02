import argparse
import sys
from datetime import datetime
from pathlib import Path

from .audio import list_devices, print_devices, record, save_wav
from .config import Config
from .summarize import generate_notes
from .transcribe import transcribe


def select_device(devices: list[dict], device_arg: str | None) -> dict:
    """Resolve the audio device from user input or interactive selection."""
    if not devices:
        print("No audio input devices found. Check your audio setup.")
        sys.exit(1)

    # If --device was passed, try to match by index or name substring
    if device_arg is not None:
        try:
            idx = int(device_arg)
            for dev in devices:
                if dev["index"] == idx:
                    return dev
            print(f"Device index {idx} not found.")
            sys.exit(1)
        except ValueError:
            # Match by name substring
            matches = [d for d in devices if device_arg.lower() in d["name"].lower()]
            if len(matches) == 1:
                return matches[0]
            elif len(matches) > 1:
                print(f"Multiple devices match '{device_arg}':")
                for d in matches:
                    print(f"  [{d['index']}] {d['name']}")
                print("Use the device index to be more specific.")
                sys.exit(1)
            else:
                print(f"No device matching '{device_arg}' found.")
                sys.exit(1)

    # Interactive selection
    while True:
        try:
            choice = input("\nEnter device index: ").strip()
            idx = int(choice)
            for dev in devices:
                if dev["index"] == idx:
                    return dev
            print(f"Invalid index: {idx}")
        except (ValueError, EOFError):
            print("Please enter a valid device index.")


def run_from_transcript(transcript_path: Path, config: Config):
    """Generate notes from an existing transcript file."""
    config.validate()

    text = transcript_path.read_text()
    if not text.strip():
        print("Transcript file is empty.")
        sys.exit(1)

    print(f"Loaded transcript: {len(text.split())} words")

    notes = generate_notes(text, config.anthropic_api_key, config.claude_model)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    notes_path = config.output_dir / f"{timestamp}_meeting_notes.md"
    notes_path.write_text(notes)
    print(f"\nNotes saved to: {notes_path}")
    print("\n" + "=" * 60)
    print(notes)


def main():
    parser = argparse.ArgumentParser(
        description="Record conference calls and generate meeting notes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  meeting-notes                          # Interactive device selection
  meeting-notes --device 5               # Use device index 5
  meeting-notes --device "Monitor"       # Match device by name
  meeting-notes --from-transcript t.txt  # Generate notes from existing transcript
  meeting-notes --whisper-model medium   # Use more accurate Whisper model
        """,
    )
    parser.add_argument("--device", help="Audio device index or name substring")
    parser.add_argument("--whisper-model", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: base)")
    parser.add_argument("--output-dir", default="output",
                        help="Directory to save notes (default: output/)")
    parser.add_argument("--from-transcript",
                        help="Generate notes from an existing transcript file (skip recording)")
    parser.add_argument("--transcript-only", action="store_true",
                        help="Only transcribe, skip note generation")

    args = parser.parse_args()

    config = Config(
        output_dir=Path(args.output_dir),
        whisper_model=args.whisper_model,
    )

    # Mode: generate notes from existing transcript
    if args.from_transcript:
        run_from_transcript(Path(args.from_transcript), config)
        return

    # Mode: full pipeline (record -> transcribe -> notes)
    if not args.transcript_only:
        config.validate()  # Need API key for note generation

    # Step 1: Select audio device
    devices = print_devices()
    device = select_device(devices, args.device)
    print(f"\nUsing device: [{device['index']}] {device['name']}")

    # Step 2: Record audio
    wasapi = device.get("wasapi_loopback", False)
    audio = record(device["index"], config.sample_rate, wasapi_loopback=wasapi)

    if len(audio) == 0:
        print("No audio recorded. Exiting.")
        sys.exit(1)

    # Save raw audio as backup
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    wav_path = config.output_dir / f"{timestamp}_recording.wav"
    save_wav(audio, wav_path, config.sample_rate)

    # Step 3: Transcribe
    transcript = transcribe(
        audio, config.sample_rate, config.whisper_model,
        config.chunk_duration_secs, config.overlap_secs,
    )

    if not transcript.strip():
        print("No speech detected in the recording.")
        sys.exit(1)

    # Save transcript
    transcript_path = config.output_dir / f"{timestamp}_transcript.txt"
    transcript_path.write_text(transcript)
    print(f"Transcript saved to: {transcript_path}")

    if args.transcript_only:
        print("\n" + "=" * 60)
        print(transcript)
        return

    # Step 4: Generate meeting notes
    notes = generate_notes(transcript, config.anthropic_api_key, config.claude_model)

    notes_path = config.output_dir / f"{timestamp}_meeting_notes.md"
    notes_path.write_text(notes)
    print(f"Notes saved to: {notes_path}")

    # Display results
    print("\n" + "=" * 60)
    print(notes)
    print("=" * 60)
    print(f"\nFiles saved in: {config.output_dir}/")
    print(f"  - {wav_path.name} (audio backup)")
    print(f"  - {transcript_path.name} (raw transcript)")
    print(f"  - {notes_path.name} (meeting notes)")


if __name__ == "__main__":
    main()
