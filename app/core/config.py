"""Application configuration with safe defaults."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production-use-env")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2 GB

    DOWNLOAD_FOLDER = os.environ.get("DOWNLOAD_FOLDER", str(BASE_DIR / "downloads"))
    TEMP_FOLDER = os.environ.get("TEMP_FOLDER", str(BASE_DIR / "temp"))
    DATA_FOLDER = os.environ.get("DATA_FOLDER", str(BASE_DIR / "data"))
    FFMPEG_FOLDER = os.environ.get("FFMPEG_FOLDER", str(BASE_DIR / "ffmpeg"))

    # Security
    ALLOWED_SCHEMES = ("http", "https")
    MAX_CONCURRENT_DOWNLOADS = int(os.environ.get("MAX_CONCURRENT_DOWNLOADS", "3"))
    REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "20"))
    MAX_FILENAME_LENGTH = 200

    # CORS (comma-separated origins in env)
    _cors = os.environ.get("CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000")
    CORS_ORIGINS = [o.strip() for o in _cors.split(",") if o.strip()]

    # Settings file
    SETTINGS_FILE = str(Path(DATA_FOLDER) / "settings.json")
    HISTORY_FILE = str(Path(DATA_FOLDER) / "history.json")
