#!/usr/bin/env python3
"""Development entry point for X DOWNLOADER."""

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.download_manager import get_ffmpeg_path

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 56)
    print("  X DOWNLOADER  —  Aurora Crystal Glass")
    print("=" * 56)
    print(f"  Local:  http://127.0.0.1:{port}")
    print(f"  Bind:   0.0.0.0:{port}")
    ffmpeg = get_ffmpeg_path()
    if ffmpeg:
        print(f"  FFmpeg: {ffmpeg}")
    else:
        print("  FFmpeg: not found (install system ffmpeg for best results)")
    print("=" * 56)
    # threaded=True for concurrent downloads; debug off by default
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, threaded=True, debug=debug)
