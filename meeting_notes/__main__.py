# Fix SSL certificates on macOS before any other imports.
# Python 3.14 on macOS doesn't always find system certificates,
# which breaks Whisper's model download.
import ssl
try:
    import certifi
    ssl._create_default_https_context = lambda: ssl.create_default_context(
        cafile=certifi.where()
    )
except ImportError:
    pass

from meeting_notes.gui import main

if __name__ == "__main__":
    main()
