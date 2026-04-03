import os
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
from .library import add_meeting, get_all_meetings, rebuild_index, search_meetings
from .summarize import generate_notes
from .tasks import add_tasks_from_meeting, get_all_tasks, get_pending_tasks, update_task_status, delete_task
from .transcribe import transcribe


class MeetingNotesApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Meeting Notes")
        self.root.geometry("900x800")
        self.root.minsize(700, 600)

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
        # Rebuild index from any existing files on startup
        rebuild_index(self.config.output_dir)
        self._refresh_library()
        self._refresh_tasks()

    def _build_ui(self):
        # --- Header ---
        header = ttk.Frame(self.root, padding=(15, 10, 15, 0))
        header.pack(fill=tk.X)

        ttk.Label(header, text="Meeting Notes", font=("Helvetica", 20, "bold")).pack(side=tk.LEFT)

        # API key (compact, in header)
        key_frame = ttk.Frame(header)
        key_frame.pack(side=tk.RIGHT)
        ttk.Label(key_frame, text="API Key:").pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar()
        ttk.Entry(key_frame, textvariable=self.api_key_var, show="*", width=30).pack(side=tk.LEFT, padx=(5, 0))

        # Load saved API key
        self._key_file = Path(os.path.expanduser("~")) / ".meeting_notes_key"
        saved_key = ""
        if self._key_file.exists():
            saved_key = self._key_file.read_text().strip()
        env_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.api_key_var.set(saved_key or env_key)
        self.api_key_var.trace_add("write", self._save_api_key)

        # --- Notebook (tabs) ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Tab 1: Record
        self._build_record_tab()

        # Tab 2: Library
        self._build_library_tab()

        # Tab 3: Tasks
        self._build_tasks_tab()

    # ===== RECORD TAB =====

    def _build_record_tab(self):
        record_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(record_frame, text="  Record  ")

        # Audio devices
        device_frame = ttk.LabelFrame(record_frame, text="Audio Devices", padding=10)
        device_frame.pack(fill=tk.X, pady=(0, 8))

        row1 = ttk.Frame(device_frame)
        row1.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(row1, text="Call audio:").pack(side=tk.LEFT)
        self.system_device_var = tk.StringVar()
        self.system_device_dropdown = ttk.Combobox(row1, textvariable=self.system_device_var,
                                                   state="readonly", width=45)
        self.system_device_dropdown.pack(side=tk.LEFT, padx=(8, 0))

        row2 = ttk.Frame(device_frame)
        row2.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(row2, text="Microphone:").pack(side=tk.LEFT)
        self.mic_device_var = tk.StringVar()
        self.mic_device_dropdown = ttk.Combobox(row2, textvariable=self.mic_device_var,
                                                state="readonly", width=45)
        self.mic_device_dropdown.pack(side=tk.LEFT, padx=(8, 0))

        row3 = ttk.Frame(device_frame)
        row3.pack(fill=tk.X)
        ttk.Button(row3, text="Refresh", command=self._refresh_devices).pack(side=tk.LEFT)
        self.device_hint = ttk.Label(row3, text="", foreground="gray")
        self.device_hint.pack(side=tk.LEFT, padx=10)

        ttk.Label(row3, text="Quality:").pack(side=tk.RIGHT)
        self.model_var = tk.StringVar(value="base")
        model_combo = ttk.Combobox(row3, textvariable=self.model_var,
                                   values=["tiny (fastest)", "base (recommended)", "small (better)", "medium (best)"],
                                   state="readonly", width=18)
        model_combo.set("base (recommended)")
        model_combo.pack(side=tk.RIGHT, padx=(0, 5))

        # Controls
        ctrl_frame = ttk.Frame(record_frame)
        ctrl_frame.pack(fill=tk.X, pady=8)

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

        # Notes output
        notes_frame = ttk.LabelFrame(record_frame, text="Meeting Notes", padding=10)
        notes_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.notes_text = scrolledtext.ScrolledText(notes_frame, wrap=tk.WORD,
                                                    font=("Helvetica", 12), height=10)
        self.notes_text.pack(fill=tk.BOTH, expand=True)
        self.notes_text.insert(tk.END, "Ready to record.\n\n"
                               "1. Select your audio devices above\n"
                               "2. Start your video call\n"
                               "3. Click 'Start Recording'\n"
                               "4. Click 'Stop Recording' when done\n")

        # Bottom buttons
        bottom = ttk.Frame(record_frame)
        bottom.pack(fill=tk.X)
        ttk.Button(bottom, text="Save Notes...", command=self._save_notes).pack(side=tk.LEFT)
        ttk.Button(bottom, text="Clear", command=self._clear_notes).pack(side=tk.LEFT, padx=8)
        ttk.Button(bottom, text="Load Transcript...", command=self._load_transcript).pack(side=tk.RIGHT)

    # ===== LIBRARY TAB =====

    def _build_library_tab(self):
        lib_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(lib_frame, text="  Library  ")

        # Search bar
        search_frame = ttk.Frame(lib_frame)
        search_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(search_frame, text="Search:", font=("Helvetica", 12)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40,
                                      font=("Helvetica", 12))
        self.search_entry.pack(side=tk.LEFT, padx=(8, 8), fill=tk.X, expand=True)
        self.search_entry.bind("<Return>", lambda e: self._do_search())

        ttk.Button(search_frame, text="Search", command=self._do_search).pack(side=tk.LEFT)
        ttk.Button(search_frame, text="Show All", command=self._refresh_library).pack(side=tk.LEFT, padx=(5, 0))

        # Meeting list
        list_frame = ttk.Frame(lib_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Left: meeting list
        left = ttk.Frame(list_frame)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        self.meeting_listbox = tk.Listbox(left, width=40, font=("Helvetica", 11),
                                          selectmode=tk.SINGLE, activestyle="none")
        list_scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.meeting_listbox.yview)
        self.meeting_listbox.config(yscrollcommand=list_scroll.set)
        self.meeting_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.pack(side=tk.LEFT, fill=tk.Y)
        self.meeting_listbox.bind("<<ListboxSelect>>", self._on_meeting_select)

        # Meeting count label
        self.meeting_count_label = ttk.Label(lib_frame, text="", foreground="gray")
        self.meeting_count_label.pack(anchor=tk.W, pady=(4, 0))

        # Right: note viewer
        right = ttk.Frame(list_frame)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # Meeting detail header
        self.detail_title = ttk.Label(right, text="Select a meeting", font=("Helvetica", 14, "bold"))
        self.detail_title.pack(anchor=tk.W)
        self.detail_date = ttk.Label(right, text="", foreground="gray")
        self.detail_date.pack(anchor=tk.W, pady=(0, 5))

        self.detail_text = scrolledtext.ScrolledText(right, wrap=tk.WORD,
                                                     font=("Helvetica", 12), height=15)
        self.detail_text.pack(fill=tk.BOTH, expand=True)

        # Detail buttons
        detail_btns = ttk.Frame(right)
        detail_btns.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(detail_btns, text="View Transcript", command=self._view_transcript).pack(side=tk.LEFT)
        ttk.Button(detail_btns, text="Export Notes...", command=self._export_notes).pack(side=tk.LEFT, padx=8)
        ttk.Button(detail_btns, text="Rebuild Index", command=self._rebuild_index).pack(side=tk.RIGHT)

        # Store displayed meetings for selection lookup
        self._displayed_meetings = []
        self._selected_meeting = None

    def _refresh_library(self):
        """Reload the meeting list from the index."""
        meetings = get_all_meetings(self.config.output_dir)
        self._display_meetings(meetings)

    def _do_search(self):
        """Search meetings by keyword."""
        query = self.search_var.get().strip()
        if not query:
            self._refresh_library()
            return
        results = search_meetings(self.config.output_dir, query)
        self._display_meetings(results, query=query)

    def _display_meetings(self, meetings, query=""):
        """Update the meeting listbox with the given entries."""
        self._displayed_meetings = meetings
        self.meeting_listbox.delete(0, tk.END)

        for entry in meetings:
            # Show date and truncated title
            date_short = entry.get("date_display", "Unknown date")
            title = entry.get("title", "Untitled")
            if len(title) > 35:
                title = title[:32] + "..."
            self.meeting_listbox.insert(tk.END, f"{date_short}\n  {title}")

        count = len(meetings)
        if query:
            self.meeting_count_label.config(text=f"{count} meeting(s) matching '{query}'")
        else:
            self.meeting_count_label.config(text=f"{count} meeting(s) in library")

        # Clear detail view
        self._selected_meeting = None
        self.detail_title.config(text="Select a meeting")
        self.detail_date.config(text="")
        self.detail_text.delete("1.0", tk.END)

    def _on_meeting_select(self, event):
        """When a meeting is clicked in the list, show its notes."""
        selection = self.meeting_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        if idx >= len(self._displayed_meetings):
            return

        entry = self._displayed_meetings[idx]
        self._selected_meeting = entry

        self.detail_title.config(text=entry.get("title", "Untitled Meeting"))
        self.detail_date.config(text=f"{entry.get('date_display', '')}  •  {entry.get('word_count', 0)} words")

        # Load the notes file
        notes_path = self.config.output_dir / entry.get("notes_file", "")
        self.detail_text.delete("1.0", tk.END)

        if notes_path.exists():
            self.detail_text.insert(tk.END, notes_path.read_text())
        else:
            self.detail_text.insert(tk.END, f"Notes file not found: {notes_path}")

    def _view_transcript(self):
        """Show the transcript for the selected meeting."""
        if not self._selected_meeting:
            return

        transcript_path = self.config.output_dir / self._selected_meeting.get("transcript_file", "")
        self.detail_text.delete("1.0", tk.END)

        if transcript_path.exists():
            self.detail_text.insert(tk.END, f"--- Transcript ---\n\n{transcript_path.read_text()}")
        else:
            self.detail_text.insert(tk.END, "Transcript file not found.")

    def _export_notes(self):
        """Export the currently displayed notes to a file."""
        content = self.detail_text.get("1.0", tk.END).strip()
        if not content:
            return

        title = self._selected_meeting.get("title", "meeting_notes") if self._selected_meeting else "meeting_notes"
        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:50].strip()

        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")],
            initialfile=f"{safe_title}.md",
        )
        if path:
            Path(path).write_text(content)

    def _rebuild_index(self):
        """Rebuild the library index from files on disk."""
        count = rebuild_index(self.config.output_dir)
        self._refresh_library()
        messagebox.showinfo("Index Rebuilt", f"Found and indexed {count} meeting(s).")

    # ===== TASKS TAB =====

    def _build_tasks_tab(self):
        tasks_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tasks_frame, text="  Tasks  ")

        # Header
        header = ttk.Frame(tasks_frame)
        header.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(header, text="Action Items from Meetings",
                  font=("Helvetica", 14, "bold")).pack(side=tk.LEFT)

        self.task_filter_var = tk.StringVar(value="pending")
        filter_frame = ttk.Frame(header)
        filter_frame.pack(side=tk.RIGHT)
        ttk.Radiobutton(filter_frame, text="Pending", variable=self.task_filter_var,
                        value="pending", command=self._refresh_tasks).pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(filter_frame, text="All", variable=self.task_filter_var,
                        value="all", command=self._refresh_tasks).pack(side=tk.LEFT, padx=4)

        self.task_count_label = ttk.Label(tasks_frame, text="", foreground="gray")
        self.task_count_label.pack(anchor=tk.W, pady=(0, 5))

        # Task list with scrollbar
        list_container = ttk.Frame(tasks_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        # Use a canvas + frame for scrollable task cards
        self.tasks_canvas = tk.Canvas(list_container, highlightthickness=0)
        tasks_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL,
                                        command=self.tasks_canvas.yview)
        self.tasks_inner_frame = ttk.Frame(self.tasks_canvas)

        self.tasks_inner_frame.bind("<Configure>",
            lambda e: self.tasks_canvas.configure(scrollregion=self.tasks_canvas.bbox("all")))

        self.tasks_canvas.create_window((0, 0), window=self.tasks_inner_frame, anchor="nw")
        self.tasks_canvas.configure(yscrollcommand=tasks_scrollbar.set)

        self.tasks_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tasks_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mousewheel
        self.tasks_canvas.bind("<Enter>",
            lambda e: self.tasks_canvas.bind_all("<MouseWheel>",
                lambda ev: self.tasks_canvas.yview_scroll(-1 * (ev.delta // 120), "units")))
        self.tasks_canvas.bind("<Leave>",
            lambda e: self.tasks_canvas.unbind_all("<MouseWheel>"))

    def _refresh_tasks(self):
        """Reload and display tasks."""
        # Clear existing task widgets
        for widget in self.tasks_inner_frame.winfo_children():
            widget.destroy()

        filter_mode = self.task_filter_var.get()
        if filter_mode == "pending":
            tasks = get_pending_tasks(self.config.output_dir)
        else:
            tasks = get_all_tasks(self.config.output_dir)

        self.task_count_label.config(text=f"{len(tasks)} task(s)")

        if not tasks:
            ttk.Label(self.tasks_inner_frame,
                      text="No tasks yet. Record a meeting and action items will appear here.",
                      font=("Helvetica", 12), foreground="gray").pack(pady=20)
            return

        for task in tasks:
            self._create_task_card(task)

    def _create_task_card(self, task):
        """Create a visual card for a single task."""
        status = task.get("status", "pending")

        # Card frame
        card = ttk.Frame(self.tasks_inner_frame, relief=tk.GROOVE)
        card.pack(fill=tk.X, pady=3, padx=5)

        inner = ttk.Frame(card, padding=8)
        inner.pack(fill=tk.X)

        # Status indicator and checkbox
        top_row = ttk.Frame(inner)
        top_row.pack(fill=tk.X)

        if status == "completed":
            status_text = "Done"
            status_color = "green"
        elif status == "in_progress":
            status_text = "In Progress"
            status_color = "blue"
        else:
            status_text = "Pending"
            status_color = "orange"

        status_label = ttk.Label(top_row, text=status_text, foreground=status_color,
                                 font=("Helvetica", 10, "bold"))
        status_label.pack(side=tk.LEFT)

        # Owner badge
        owner = task.get("owner", "")
        if owner:
            ttk.Label(top_row, text=f"  [{owner}]", foreground="purple",
                      font=("Helvetica", 10)).pack(side=tk.LEFT)

        # Deadline
        deadline = task.get("deadline", "")
        if deadline:
            ttk.Label(top_row, text=f"  Due: {deadline}", foreground="red",
                      font=("Helvetica", 10)).pack(side=tk.LEFT)

        # Meeting date
        meeting_date = task.get("meeting_date", "")
        if meeting_date:
            ttk.Label(top_row, text=f"From: {meeting_date}", foreground="gray",
                      font=("Helvetica", 9)).pack(side=tk.RIGHT)

        # Task text
        task_text = task.get("text", "")
        ttk.Label(inner, text=task_text, wraplength=600,
                  font=("Helvetica", 12)).pack(anchor=tk.W, pady=(4, 4))

        # Action buttons
        btn_row = ttk.Frame(inner)
        btn_row.pack(anchor=tk.W)

        task_id = task["id"]

        if status != "completed":
            ttk.Button(btn_row, text="Complete",
                       command=lambda tid=task_id: self._complete_task(tid)).pack(side=tk.LEFT, padx=(0, 5))
        if status == "pending":
            ttk.Button(btn_row, text="Start",
                       command=lambda tid=task_id: self._start_task(tid)).pack(side=tk.LEFT, padx=(0, 5))
        if status == "completed":
            ttk.Button(btn_row, text="Reopen",
                       command=lambda tid=task_id: self._reopen_task(tid)).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(btn_row, text="Delete",
                   command=lambda tid=task_id: self._delete_task(tid)).pack(side=tk.LEFT)

    def _complete_task(self, task_id):
        update_task_status(self.config.output_dir, task_id, "completed")
        self._refresh_tasks()

    def _start_task(self, task_id):
        update_task_status(self.config.output_dir, task_id, "in_progress")
        self._refresh_tasks()

    def _reopen_task(self, task_id):
        update_task_status(self.config.output_dir, task_id, "pending")
        self._refresh_tasks()

    def _delete_task(self, task_id):
        delete_task(self.config.output_dir, task_id)
        self._refresh_tasks()

    # ===== API KEY =====

    def _save_api_key(self, *args):
        key = self.api_key_var.get().strip()
        if key:
            self._key_file.write_text(key)
            self._key_file.chmod(0o600)

    # ===== DEVICE MANAGEMENT =====

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
            if not system_selected and "blackhole" in name_lower:
                self.system_device_dropdown.current(i)
                system_selected = True
            elif not mic_selected and ("built-in" in name_lower or "macbook" in name_lower
                                       or "internal" in name_lower):
                self.mic_device_dropdown.current(i)
                mic_selected = True

        if not system_selected and names:
            self.system_device_dropdown.current(0)
        if not mic_selected and names:
            for i, dev in enumerate(devices):
                if "blackhole" not in dev["name"].lower():
                    self.mic_device_dropdown.current(i)
                    mic_selected = True
                    break
            if not mic_selected:
                self.mic_device_dropdown.current(0)

        if system_selected:
            self.device_hint.config(text="BlackHole detected", foreground="green")
        else:
            self.device_hint.config(text="BlackHole not detected", foreground="orange")

    def _get_model_name(self):
        val = self.model_var.get()
        return val.split(" ")[0]

    # ===== RECORDING =====

    def _toggle_recording(self):
        if not self.recording:
            self._start_recording()
        else:
            self._stop_recording_now()

    def _start_recording(self):
        if not self._devices:
            messagebox.showerror("Error", "No audio devices found.")
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
        self.notes_text.insert(tk.END, f"Recording...\n"
                               f"  System: {self._system_device['name']}\n"
                               f"  Mic: {self._mic_device['name']}\n\n"
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
        if orig_rate == target_rate:
            return audio
        duration = len(audio) / orig_rate
        target_len = int(duration * target_rate)
        indices = np.linspace(0, len(audio) - 1, target_len)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def _record_worker(self):
        system_chunks = []
        mic_chunks = []
        system_queue = queue.Queue()
        mic_queue = queue.Queue()

        def system_callback(indata, frames, time, status):
            system_queue.put(indata.copy())

        def mic_callback(indata, frames, time, status):
            mic_queue.put(indata.copy())

        sys_info = sd.query_devices(self._system_device["index"])
        mic_info = sd.query_devices(self._mic_device["index"])
        sys_rate = int(sys_info["default_samplerate"])
        mic_rate = int(mic_info["default_samplerate"])

        try:
            system_stream = sd.InputStream(
                device=self._system_device["index"],
                samplerate=sys_rate, channels=1, dtype="float32",
                callback=system_callback,
            )
            mic_stream = sd.InputStream(
                device=self._mic_device["index"],
                samplerate=mic_rate, channels=1, dtype="float32",
                callback=mic_callback,
            )

            with system_stream, mic_stream:
                while not self._stop_recording:
                    sd.sleep(100)
                    while not system_queue.empty():
                        try:
                            system_chunks.append(system_queue.get_nowait())
                        except queue.Empty:
                            break
                    while not mic_queue.empty():
                        try:
                            mic_chunks.append(mic_queue.get_nowait())
                        except queue.Empty:
                            break

        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self._on_record_error(err_msg))
            return

        target_rate = self.config.sample_rate

        if system_chunks or mic_chunks:
            system_audio = np.concatenate(system_chunks, axis=0) if system_chunks else np.array([], dtype=np.float32)
            mic_audio = np.concatenate(mic_chunks, axis=0) if mic_chunks else np.array([], dtype=np.float32)

            if system_audio.ndim > 1:
                system_audio = system_audio.mean(axis=1)
            if mic_audio.ndim > 1:
                mic_audio = mic_audio.mean(axis=1)

            if len(system_audio) > 0:
                system_audio = self._resample(system_audio, sys_rate, target_rate)
            if len(mic_audio) > 0:
                mic_audio = self._resample(mic_audio, mic_rate, target_rate)

            min_len = min(len(system_audio), len(mic_audio)) if len(system_audio) > 0 and len(mic_audio) > 0 else 0

            if min_len > 0:
                mixed = system_audio[:min_len] + mic_audio[:min_len]
                if len(system_audio) > min_len:
                    mixed = np.concatenate([mixed, system_audio[min_len:]])
                elif len(mic_audio) > min_len:
                    mixed = np.concatenate([mixed, mic_audio[min_len:]])
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
                                   "No API key provided — skipping note generation.\n\n"
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
        notes_file = f"{self._timestamp}_meeting_notes.md"
        notes_path = self.config.output_dir / notes_file
        notes_path.write_text(notes)

        # Add to library index
        add_meeting(
            self.config.output_dir,
            self._timestamp,
            notes_file,
            f"{self._timestamp}_transcript.txt",
            f"{self._timestamp}_recording.wav",
            notes,
        )

        # Extract action items into task list
        try:
            dt = datetime.strptime(self._timestamp, "%Y-%m-%d_%H%M%S")
            meeting_date = dt.strftime("%B %d, %Y")
        except ValueError:
            meeting_date = self._timestamp
        new_tasks = add_tasks_from_meeting(
            self.config.output_dir, notes, self._timestamp, meeting_date
        )

        self.status_label.config(text="Done!", foreground="green")
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert(tk.END, notes)
        self.notes_text.see("1.0")

        task_msg = f"\n\n---\nSaved to library and {self.config.output_dir}/\n"
        if new_tasks:
            task_msg += f"{len(new_tasks)} action item(s) added to Tasks tab.\n"
        self.notes_text.insert(tk.END, task_msg)

        # Refresh library and tasks tabs
        self._refresh_library()
        self._refresh_tasks()

    # ===== RECORD TAB BUTTONS =====

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
            initialdir=str(self.config.output_dir),
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
