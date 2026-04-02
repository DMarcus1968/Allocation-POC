import platform
import signal
import sys
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd


def list_devices():
    """List available audio input devices, highlighting loopback/monitor devices."""
    devices = sd.query_devices()
    input_devices = []
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            input_devices.append({"index": i, "name": dev["name"], "channels": dev["max_input_channels"]})

    # On Windows, also list output devices (usable via WASAPI loopback)
    if platform.system() == "Windows":
        for i, dev in enumerate(devices):
            if dev["max_output_channels"] > 0 and dev["max_input_channels"] == 0:
                input_devices.append({
                    "index": i,
                    "name": f"{dev['name']} (WASAPI Loopback)",
                    "channels": dev["max_output_channels"],
                    "wasapi_loopback": True,
                })

    return input_devices


def print_devices():
    """Print available devices for user selection."""
    devices = list_devices()
    if not devices:
        print("No audio input devices found.")
        return devices

    print("\nAvailable audio devices:")
    print("-" * 60)
    for dev in devices:
        marker = " <-- likely loopback" if "monitor" in dev["name"].lower() else ""
        print(f"  [{dev['index']}] {dev['name']}{marker}")
    print("-" * 60)

    # Platform-specific guidance
    system = platform.system()
    if system == "Darwin":
        print("\nmacOS: To capture system audio, install a virtual audio device")
        print("like BlackHole (https://github.com/ExistentialAudio/BlackHole).")
        print("Route your system audio through it, then select it here.")
    elif system == "Linux":
        print("\nLinux: Select the 'Monitor of ...' device to capture system audio.")
    elif system == "Windows":
        print("\nWindows: Select a WASAPI Loopback device to capture system audio.")

    return devices


def record(device_index: int, sample_rate: int = 16000, channels: int = 1,
           wasapi_loopback: bool = False) -> np.ndarray:
    """Record audio from the specified device until Ctrl+C is pressed.

    Returns the recorded audio as a numpy array (mono, float32).
    """
    chunks = []
    recording = True

    def callback(indata, frames, time, status):
        if status:
            print(f"  Audio status: {status}", file=sys.stderr)
        chunks.append(indata.copy())

    def stop_recording(signum, frame):
        nonlocal recording
        recording = False

    # Set up graceful stop on Ctrl+C
    original_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, stop_recording)

    extra_settings = None
    actual_device = device_index

    if wasapi_loopback and platform.system() == "Windows":
        extra_settings = sd.WasapiSettings(loopback=True)

    try:
        stream = sd.InputStream(
            device=actual_device,
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            callback=callback,
            extra_settings=extra_settings,
        )

        print("\n🎙  Recording... Press Ctrl+C to stop.\n")

        with stream:
            while recording:
                sd.sleep(500)

    finally:
        signal.signal(signal.SIGINT, original_handler)

    if not chunks:
        print("No audio was recorded.")
        return np.array([], dtype=np.float32)

    audio = np.concatenate(chunks, axis=0)

    # Convert to mono if stereo
    if audio.ndim > 1 and audio.shape[1] > 1:
        audio = audio.mean(axis=1)
    elif audio.ndim > 1:
        audio = audio[:, 0]

    duration = len(audio) / sample_rate
    print(f"\nRecording stopped. Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")

    return audio


def save_wav(audio: np.ndarray, path: Path, sample_rate: int = 16000):
    """Save audio array to a WAV file for backup/debugging."""
    audio_int16 = (audio * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    print(f"Audio saved to: {path}")
