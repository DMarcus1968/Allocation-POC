import platform
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd

from .audio import list_devices, save_wav
from .config import Config
from .summarize import generate_notes
from .transcribe import transcribe


class MeetingNotesApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Meeting Notes")
        self.root.geometry("820x750")
        self.root.minsize(620, 550)

        # Force window to front on macOS
        if platform.system() == "Darwin":
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(100, lambda: self.root.attributes("-topmost", False))
            try:
                import subprocess
                subprocess.Popen([
                    "osascript", "-e",
                    'tell application "System Events" to set frontmost of '
                    'the first process whose unix id is (do shell script "echo $PPID") to true'
                ])
            except Exception:
                pass

        # State
        self.config = Config()
        self.recording = False
        self.audio_data = None
        self.record_thread = None
        self._stop_recording = False

        self._build_ui()
        self._refresh_devices()

    def _build_ui(self):
        # --- Top section ---
        top = ttk.Frame(self.root, padding=15)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Meeting Notes", font=("Helvetica", 20, "bold")).pack(anchor=tk.W)
        ttk.Label(top, text="Record your conference calls and get AI-generated notes",
                  font=("Helvetica", 12)).pack(anchor=tk.W, pady=(0, 10))

        # API key
        key_frame = ttk.LabelFrame(top, text="Setup", padding=10)
        key_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(key_frame, text="Anthropic API Key:").pack(anchor=tk.W)
        self.api_key_var = tk.StringVar()
        api_entry = ttk.Entry(key_frame, textvariable=self.api_key_var, show="*", width=50)
        api_entry.pack(fill=tk.X, pady=(2, 5))

        import os
        env_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if env_key:
            self.api_key_var.set(env_key)

        # Audio devices — TWO dropdowns
        device_frame = ttk.LabelFrame(top, text="Audio Devices", padding=10)
        device_frame.pack(fill=tk.X, pady=(0, 10))

        # System audio (BlackHole)
        ttk.Label(device_frame, text="Call audio (BlackHole / system audio):").pack(anchor=tk.W)
        sys_row = ttk.Frame(device_frame)
        sys_row.pack(fill=tk.X, pady=(2, 5))

        self.system_device_var = tk.StringVar()
        self.system_device_dropdown = ttk.Combobox(sys_row, textvariable=self.system_device_var,
                                                   state="readonly", width=55)
        self.system_device_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Microphone
        ttk.Label(device_frame, text="Your microphone (to capture your voice):").pack(anchor=tk.W)
        mic_row = ttk.Frame(device_frame)
        mic_row.pack(fill=tk.X, pady=(2, 5))

        self.mic_device_var = tk.StringVar()
        self.mic_device_dropdown = ttk.Combobox(mic_row, textvariable=self.mic_device_var,
                                                state="readonly", width=55)
        self.mic_device_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(device_frame, text="Refresh Devices", command=self._refresh_devices).pack(anchor=tk.W, pady=(5, 0))

        self.device_hint = ttk.Label(device_frame, text="", foreground="gray")
        self.device_hint.pack(anchor=tk.W, pady=(5, 0))

        # Whisper model
        model_frame = ttk.Frame(device_frame)
        model_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(model_frame, text="Transcription quality:").pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value="base")
        model_combo = ttk.Combobox(model_frame, textvariable=self.model_var,
                                   values=["tiny (fastest)", "base (recommended)", "small (better)", "medium (best)"],
                                   state="readonly", width=20)
        model_combo.set("base (recommended)")
        model_combo.pack(side=tk.LEFT, padx=(8, 0))

        # --- Controls ---
        ctrl_frame = ttk.Frame(top)
        ctrl_frame.pack(fill=tk.X, pady=(5, 0))

        self.record_btn = tk.Button(ctrl_frame, text="  Start Recording  ",
                                    command=self._toggle_recording,
                                    bg="#d32f2f", fg="white",
                                    font=("Helvetica", 14, "bold"),
                                    relief=tk.FLAT, padx=20, pady=8)
        self.record_btn.pack(side=tk.LEFT)

        self.status_label = ttk.Label(ctrl_frame, text="Ready", font=("Helvetica", 12))
        self.status_label.pack(side=tk.LEFT, padx=15)

        self.time_label = ttk.Label(ctrl_frame, text="", font=("Helvetica", 12, "bold"))
        self.time_label.pack(side=tk.LEFT)

        # --- Notes output ---
        notes_frame = ttk.LabelFrame(self.root, text="Meeting Notes", padding=10)
        notes_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 10))

        self.notes_text = scrolledtext.ScrolledText(notes_frame, wrap=tk.WORD,
                                                    font=("Helvetica", 12), height=12)
        self.notes_text.pack(fill=tk.BOTH, expand=True)
        self.notes_text.insert(tk.END, "Your meeting notes will appear here after recording.\n\n"
                               "Steps:\n"
                               "1. Paste your Anthropic API key above\n"
                               "2. Select BlackHole for call audio (others' voices)\n"
                               "3. Select your microphone (your voice)\n"
                               "4. Start your video call\n"
                               "5. Click 'Start Recording'\n"
                               "6. When the call ends, click 'Stop Recording'\n"
                               "7. Wait for transcription and note generation\n")

        # Bottom buttons
        bottom = ttk.Frame(self.root, padding=(15, 0, 15, 15))
        bottom.pack(fill=tk.X)

        ttk.Button(bottom, text="Save Notes...", command=self._save_notes).pack(side=tk.LEFT)
        ttk.Button(bottom, text="Clear", command=self._clear_notes).pack(side=tk.LEFT, padx=8)
        ttk.Button(bottom, text="Load Transcript...", command=self._load_transcript).pack(side=tk.RIGHT)

    def _refresh_devices(self):
        devices = list_devices()
        self._devices = devices
        names = [f"[{d['index']}] {d['name']}" for d in devices]

        self.system_device_dropdown["values"] = names
        self.mic_device_dropdown["values"] = names

        system_selected = False
        mic_selected = False

        for i, dev in enumerate(devices):
            name_lower = dev["name"].lower()
            # Auto-select BlackHole for system audio
            if not system_selected and "blackhole" in name_lower:
                self.system_device_dropdown.current(i)
                system_selected = True
            # Auto-select built-in microphone
            elif not mic_selected and ("built-in" in name_lower or "macbook" in name_lower
                                       or "internal" in name_lower):
                self.mic_device_dropdown.current(i)
                mic_selected = True

        # Fallbacks
        if not system_selected and names:
            self.system_device_dropdown.current(0)
        if not mic_selected and names:
            # Pick first device that isn't BlackHole
            for i, dev in enumerate(devices):
                if "blackhole" not in dev["name"].lower():
                    self.mic_device_dropdown.current(i)
                    mic_selected = True
                    break
            if not mic_selected:
                self.mic_device_dropdown.current(0)

        if system_selected:
            self.device_hint.config(text="BlackHole detected — call audio will be captured", foreground="green")
        else:
            self.device_hint.config(
                text="BlackHole not detected. Install it to capture call audio.",
                foreground="orange")

    def _get_model_name(self):
        val = self.model_var.get()
        return val.split(" ")[0]

    def _toggle_recording(self):
        if not self.recording:
            self._start_recording()
        else:
            self._stop_recording_now()

    def _start_recording(self):
        if not self._devices:
            messagebox.showerror("Error", "No audio devices found. Check your audio setup.")
            return

        sys_idx = self.system_device_dropdown.current()
        mic_idx = self.mic_device_dropdown.current()
        if sys_idx < 0 or mic_idx < 0:
            messagebox.showerror("Error", "Please select both audio devices.")
            return

        self._system_device = self._devices[sys_idx]
        self._mic_device = self._devices[mic_idx]
        self.recording = True
        self._stop_recording = False

        self.record_btn.config(text="  Stop Recording  ", bg="#1565c0")
        self.status_label.config(text="Recording...", foreground="red")
        self._recording_start_time = datetime.now()
        self._update_timer()

        self.notes_text.delete("1.0", tk.END)
        sources = f"System: {self._system_device['name']}\nMic: {self._mic_device['name']}"
        self.notes_text.insert(tk.END, f"Recording from two sources:\n{sources}\n\n"
                               "Click 'Stop Recording' when your call ends.\n")

        self.record_thread = threading.Thread(target=self._record_worker, daemon=True)
        self.record_thread.start()

    def _update_timer(self):
        if not self.recording:
            return
        elapsed = datetime.now() - self._recording_start_time
        mins, secs = divmod(int(elapsed.total_seconds()), 60)
        hours, mins = divmod(mins, 60)
        if hours:
            self.time_label.config(text=f"{hours}:{mins:02d}:{secs:02d}")
        else:
            self.time_label.config(text=f"{mins:02d}:{secs:02d}")
        self.root.after(1000, self._update_timer)

    @staticmethod
    def _resample(audio, orig_rate, target_rate):
        """Resample audio from orig_rate to target_rate using linear interpolation."""
        if orig_rate == target_rate:
            return audio
        duration = len(audio) / orig_rate
        target_len = int(duration * target_rate)
        indices = np.linspace(0, len(audio) - 1, target_len)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def _record_worker(self):
        """Record from both system audio and microphone simultaneously, then mix."""
        system_chunks = []
        mic_chunks = []
        system_queue = queue.Queue()
        mic_queue = queue.Queue()

        def system_callback(indata, frames, time, status):
            system_queue.put(indata.copy())

        def mic_callback(indata, frames, time, status):
            mic_queue.put(indata.copy())

        # Use each device's native sample rate to avoid silent failures
        sys_info = sd.query_devices(self._system_device["index"])
        mic_info = sd.query_devices(self._mic_device["index"])
        sys_rate = int(sys_info["default_samplerate"])
        mic_rate = int(mic_info["default_samplerate"])

        try:
            system_stream = sd.InputStream(
                device=self._system_device["index"],
                samplerate=sys_rate,
                channels=1,
                dtype="float32",
                callback=system_callback,
            )
            mic_stream = sd.InputStream(
                device=self._mic_device["index"],
                samplerate=mic_rate,
                channels=1,
                dtype="float32",
                callback=mic_callback,
            )

            with system_stream, mic_stream:
                while not self._stop_recording:
                    try:
                        chunk = system_queue.get(timeout=0.1)
                        system_chunks.append(chunk)
                    except queue.Empty:
                        pass
                    try:
                        chunk = mic_queue.get(timeout=0.1)
                        mic_chunks.append(chunk)
                    except queue.Empty:
                        pass

        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self._on_record_error(err_msg))
            return

        # Mix both audio sources together
        target_rate = self.config.sample_rate  # 16000 for Whisper

        if system_chunks or mic_chunks:
            system_audio = np.concatenate(system_chunks, axis=0) if system_chunks else np.array([], dtype=np.float32)
            mic_audio = np.concatenate(mic_chunks, axis=0) if mic_chunks else np.array([], dtype=np.float32)

            # Flatten to 1D
            if system_audio.ndim > 1:
                system_audio = system_audio.mean(axis=1)
            if mic_audio.ndim > 1:
                mic_audio = mic_audio.mean(axis=1)

            # Resample both to 16kHz for Whisper
            if len(system_audio) > 0:
                system_audio = self._resample(system_audio, sys_rate, target_rate)
            if len(mic_audio) > 0:
                mic_audio = self._resample(mic_audio, mic_rate, target_rate)

            # Mix by summing (not averaging) so quiet sources don't dilute loud ones.
            # Then normalize to prevent clipping.
            min_len = min(len(system_audio), len(mic_audio)) if len(system_audio) > 0 and len(mic_audio) > 0 else 0

            if min_len > 0:
                # Sum the two sources
                mixed = system_audio[:min_len] + mic_audio[:min_len]
                # Append any remaining audio from the longer source
                if len(system_audio) > min_len:
                    mixed = np.concatenate([mixed, system_audio[min_len:]])
                elif len(mic_audio) > min_len:
                    mixed = np.concatenate([mixed, mic_audio[min_len:]])
                # Normalize to prevent clipping
                peak = np.abs(mixed).max()
                if peak > 1.0:
                    mixed = mixed / peak
            elif len(system_audio) > 0:
                mixed = system_audio
            elif len(mic_audio) > 0:
                mixed = mic_audio
            else:
                self.root.after(0, lambda: self._on_record_error("No audio captured"))
                return

            # Boost quiet audio so Whisper can detect speech
            peak = np.abs(mixed).max()
            if 0 < peak < 0.3:
                mixed = mixed * (0.8 / peak)
                mixed = np.clip(mixed, -1.0, 1.0)

            self.audio_data = mixed
            self.root.after(0, self._on_record_complete)
        else:
            self.root.after(0, lambda: self._on_record_error("No audio captured"))

    def _stop_recording_now(self):
        self._stop_recording = True
        self.recording = False
        self.record_btn.config(text="  Start Recording  ", bg="#d32f2f")
        self.status_label.config(text="Processing...", foreground="blue")
        self.time_label.config(text="")
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert(tk.END, "Recording stopped. Processing audio...\n")

    def _on_record_error(self, error_msg):
        self.recording = False
        self.record_btn.config(text="  Start Recording  ", bg="#d32f2f")
        self.status_label.config(text="Error", foreground="red")
        self.time_label.config(text="")
        messagebox.showerror("Recording Error",
                             f"Could not record audio:\n\n{error_msg}\n\n"
                             "Make sure you selected the correct audio devices.")

    def _on_record_complete(self):
        duration = len(self.audio_data) / self.config.sample_rate
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert(tk.END,
                               f"Recorded {duration:.0f} seconds ({duration/60:.1f} minutes)\n\n"
                               "Saving audio backup...\n")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self._timestamp = timestamp
        wav_path = self.config.output_dir / f"{timestamp}_recording.wav"
        save_wav(self.audio_data, wav_path, self.config.sample_rate)

        self.notes_text.insert(tk.END, f"Audio saved to: {wav_path}\n\n")
        self.notes_text.insert(tk.END, "Transcribing audio (this may take a few minutes)...\n")
        self.root.update()

        threading.Thread(target=self._transcribe_worker, daemon=True).start()

    def _transcribe_worker(self):
        try:
            model_name = self._get_model_name()
            transcript = transcribe(
                self.audio_data, self.config.sample_rate, model_name,
                self.config.chunk_duration_secs, self.config.overlap_secs,
            )
            self.root.after(0, lambda: self._on_transcribe_complete(transcript))
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self._on_transcribe_error(err_msg))

    def _on_transcribe_error(self, error_msg):
        self.status_label.config(text="Transcription failed", foreground="red")
        self.notes_text.insert(tk.END, f"\nTranscription error: {error_msg}\n"
                               "Your audio was saved — you can try again later.\n")

    def _on_transcribe_complete(self, transcript):
        if not transcript.strip():
            self.status_label.config(text="No speech detected", foreground="orange")
            self.notes_text.insert(tk.END, "\nNo speech was detected in the recording.\n")
            return

        transcript_path = self.config.output_dir / f"{self._timestamp}_transcript.txt"
        transcript_path.write_text(transcript)

        self.notes_text.insert(tk.END, f"\nTranscript saved ({len(transcript.split())} words)\n\n")

        api_key = self.api_key_var.get().strip()
        if not api_key:
            self.status_label.config(text="Done (no API key)", foreground="orange")
            self.notes_text.insert(tk.END,
                                   "No API key provided — skipping note generation.\n"
                                   "Paste your Anthropic API key and use 'Load Transcript' to generate notes later.\n\n"
                                   "--- Raw Transcript ---\n\n" + transcript)
            return

        self.notes_text.insert(tk.END, "Generating meeting notes with Claude...\n")
        self.root.update()

        threading.Thread(target=lambda: self._summarize_worker(transcript, api_key), daemon=True).start()

    def _summarize_worker(self, transcript, api_key):
        try:
            notes = generate_notes(transcript, api_key, self.config.claude_model)
            self.root.after(0, lambda: self._on_notes_complete(notes, transcript))
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self._on_notes_error(err_msg, transcript))

    def _on_notes_error(self, error_msg, transcript):
        self.status_label.config(text="Note generation failed", foreground="red")
        self.notes_text.insert(tk.END,
                               f"\nClaude API error: {error_msg}\n\n"
                               "Your transcript was saved. You can try again with 'Load Transcript'.\n\n"
                               "--- Raw Transcript ---\n\n" + transcript)

    def _on_notes_complete(self, notes, transcript):
        notes_path = self.config.output_dir / f"{self._timestamp}_meeting_notes.md"
        notes_path.write_text(notes)

        self.status_label.config(text="Done!", foreground="green")
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert(tk.END, notes)
        self.notes_text.see("1.0")

        self.notes_text.insert(tk.END, f"\n\n---\nFiles saved in: {self.config.output_dir}/\n")

    def _save_notes(self):
        content = self.notes_text.get("1.0", tk.END).strip()
        if not content:
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")],
            initialfile=f"meeting_notes_{datetime.now().strftime('%Y-%m-%d')}.md",
        )
        if path:
            Path(path).write_text(content)
            self.status_label.config(text="Saved!", foreground="green")

    def _clear_notes(self):
        self.notes_text.delete("1.0", tk.END)
        self.status_label.config(text="Ready", foreground="black")

    def _load_transcript(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter your Anthropic API key first.")
            return

        transcript = Path(path).read_text()
        if not transcript.strip():
            messagebox.showerror("Error", "The transcript file is empty.")
            return

        self.status_label.config(text="Generating notes...", foreground="blue")
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert(tk.END, f"Loaded transcript: {len(transcript.split())} words\n\n"
                               "Generating meeting notes with Claude...\n")
        self.root.update()

        self._timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        threading.Thread(target=lambda: self._summarize_worker(transcript, api_key), daemon=True).start()

    def run(self):
        self.root.mainloop()


def main():
    app = MeetingNotesApp()
    app.run()


if __name__ == "__main__":
    main()
