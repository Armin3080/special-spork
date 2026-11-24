"""Download orchestration with progress, cancellation and history."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import yt_dlp
from flask import current_app

from app.utils.security import sanitize_filename, safe_join, validate_url

_lock = threading.Lock()
_downloads: dict[str, dict[str, Any]] = {}
_active_count = 0
_active_lock = threading.Lock()


def get_ffmpeg_path() -> str | None:
    """Locate system FFmpeg only. Never auto-download untrusted binaries."""
    # Prefer system binary
    system = shutil.which("ffmpeg")
    if system:
        return system

    # Optional local folder (user-provided)
    folder = current_app.config.get("FFMPEG_FOLDER", "ffmpeg")
    for name in ("ffmpeg", "ffmpeg.exe"):
        candidate = Path(folder) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _history_path() -> Path:
    return Path(current_app.config["HISTORY_FILE"])


def _load_history() -> list[dict]:
    path = _history_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_history(entries: list[dict]) -> None:
    path = _history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # keep last N
    limit = 100
    try:
        from app.services.settings import load_settings
        limit = int(load_settings().get("history_limit", 100))
    except Exception:
        pass
    path.write_text(json.dumps(entries[:limit], indent=2, ensure_ascii=False), encoding="utf-8")


def add_history(entry: dict) -> None:
    with _lock:
        hist = _load_history()
        hist.insert(0, entry)
        _save_history(hist)


def list_history() -> list[dict]:
    with _lock:
        return _load_history()


def clear_history() -> None:
    with _lock:
        _save_history([])


def get_status(download_id: str) -> dict:
    with _lock:
        return dict(_downloads.get(download_id, {"status": "not_found"}))


def list_active() -> list[dict]:
    with _lock:
        return [
            {"id": k, **{kk: vv for kk, vv in v.items() if kk != "cancel"}}
            for k, v in _downloads.items()
            if v.get("status") in ("queued", "downloading", "processing")
        ]


def cancel_download(download_id: str) -> bool:
    with _lock:
        d = _downloads.get(download_id)
        if not d:
            return False
        d["cancel"] = True
        if d.get("status") in ("queued", "downloading"):
            d["status"] = "cancelled"
        return True


def get_video_info(url: str) -> dict:
    ok, err = validate_url(url)
    if not ok:
        return {"error": err}

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "ignoreerrors": False,
        "socket_timeout": current_app.config.get("REQUEST_TIMEOUT", 20),
        "nocheckcertificate": False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return {"error": "No information found for this URL"}

            formats = []
            seen = set()
            for f in info.get("formats") or []:
                height = f.get("height") or 0
                ext = f.get("ext") or ""
                key = f"{height}_{ext}_{f.get('format_id')}"
                if key in seen:
                    continue
                seen.add(key)

                vcodec = f.get("vcodec") or "none"
                acodec = f.get("acodec") or "none"

                if vcodec != "none" and acodec != "none" and height:
                    formats.append({
                        "format_id": f["format_id"],
                        "resolution": f"{height}p",
                        "ext": ext,
                        "filesize": f.get("filesize") or f.get("filesize_approx") or 0,
                        "note": f.get("format_note") or "",
                        "type": "video",
                    })
                elif acodec != "none" and vcodec == "none":
                    formats.append({
                        "format_id": f["format_id"],
                        "resolution": "audio",
                        "ext": ext,
                        "filesize": f.get("filesize") or f.get("filesize_approx") or 0,
                        "note": "Audio only",
                        "type": "audio",
                    })

            # Prefer unique resolutions, higher first
            unique = []
            seen_res = set()
            for f in sorted(formats, key=lambda x: (x["resolution"] != "audio", x.get("filesize") or 0), reverse=True):
                if f["resolution"] not in seen_res:
                    seen_res.add(f["resolution"])
                    unique.append(f)

            return {
                "title": info.get("title") or "Unknown",
                "duration": info.get("duration") or 0,
                "thumbnail": info.get("thumbnail") or "",
                "uploader": info.get("uploader") or "",
                "webpage_url": info.get("webpage_url") or url,
                "formats": unique[:12],
            }
    except Exception as e:
        return {"error": str(e)[:300]}


def extract_page_links(url: str) -> list[dict]:
    ok, err = validate_url(url)
    if not ok:
        return []

    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    try:
        headers = {"User-Agent": "X-Downloader/1.0 (public content only)"}
        timeout = current_app.config.get("REQUEST_TIMEOUT", 20)
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        # Re-validate final URL after redirects
        final_ok, _ = validate_url(resp.url)
        if not final_ok:
            return []
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        video_ext = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".flv"}
        audio_ext = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".opus"}
        image_ext = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

        links = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = urljoin(resp.url, href)
            if full in seen:
                continue
            lower = full.lower().split("?")[0]
            typ = None
            for e in video_ext:
                if lower.endswith(e):
                    typ = "video"
                    break
            if not typ:
                for e in audio_ext:
                    if lower.endswith(e):
                        typ = "audio"
                        break
            if not typ:
                for e in image_ext:
                    if lower.endswith(e):
                        typ = "image"
                        break
            if typ:
                ok2, _ = validate_url(full)
                if not ok2:
                    continue
                title = (a.get("title") or a.get_text() or Path(full).name).strip()
                title = " ".join(title.split())[:80]
                links.append({"url": full, "title": title or Path(full).name, "type": typ})
                seen.add(full)
                if len(links) >= 30:
                    break
        return links
    except Exception:
        return []


def start_download(url: str, format_id: str | None = None) -> dict:
    ok, err = validate_url(url)
    if not ok:
        return {"error": err}

    with _active_lock:
        global _active_count
        max_c = current_app.config.get("MAX_CONCURRENT_DOWNLOADS", 3)
        try:
            from app.services.settings import load_settings
            max_c = int(load_settings().get("max_concurrent", max_c))
        except Exception:
            pass
        if _active_count >= max_c:
            return {"error": f"Maximum concurrent downloads ({max_c}) reached"}

    download_id = uuid.uuid4().hex
    with _lock:
        _downloads[download_id] = {
            "status": "queued",
            "progress": 0,
            "speed": "0 B/s",
            "eta": "?",
            "filename": "",
            "title": "",
            "size": 0,
            "error": None,
            "cancel": False,
            "url": url,
            "created": time.time(),
        }

    app = current_app._get_current_object()

    def worker():
        global _active_count
        with _active_lock:
            _active_count += 1
        try:
            with app.app_context():
                _run_download(app, download_id, url, format_id)
        finally:
            with _active_lock:
                _active_count = max(0, _active_count - 1)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return {"download_id": download_id}


def _run_download(app, download_id: str, url: str, format_id: str | None):
    download_folder = app.config["DOWNLOAD_FOLDER"]
    max_size = app.config.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024 * 1024)

    with _lock:
        if download_id not in _downloads:
            return
        _downloads[download_id]["status"] = "downloading"

    def progress_hook(d):
        with _lock:
            entry = _downloads.get(download_id)
            if not entry:
                return
            if entry.get("cancel"):
                raise yt_dlp.utils.DownloadError("Cancelled by user")
            if d["status"] == "downloading":
                pct = d.get("_percent_str", "0%").strip().replace("%", "")
                try:
                    entry["progress"] = float(pct)
                except ValueError:
                    entry["progress"] = 0
                entry["speed"] = (d.get("_speed_str") or "0 B/s").strip()
                entry["eta"] = (d.get("_eta_str") or "?").strip()
                entry["size"] = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            elif d["status"] == "finished":
                entry["status"] = "processing"
                entry["progress"] = 99

    outtmpl = str(Path(download_folder) / "%(title).180B.%(ext)s")
    ydl_opts: dict[str, Any] = {
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "progress_hooks": [progress_hook],
        "max_filesize": max_size,
        "socket_timeout": app.config.get("REQUEST_TIMEOUT", 20),
        "retries": 3,
        "fragment_retries": 3,
        "noprogress": True,
    }
    if format_id:
        ydl_opts["format"] = format_id
    else:
        ydl_opts["format"] = "bestvideo+bestaudio/best"

    ffmpeg = get_ffmpeg_path()
    if ffmpeg:
        ydl_opts["ffmpeg_location"] = os.path.dirname(ffmpeg) if os.path.isfile(ffmpeg) else ffmpeg

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Normalize to actual file (extension may change after merge)
            base = Path(filename)
            if not base.exists():
                # try common alternates
                for alt in base.parent.glob(base.stem + ".*"):
                    filename = str(alt)
                    break

            safe_name = sanitize_filename(Path(filename).name)
            final_path = safe_join(download_folder, safe_name)
            if final_path is None:
                raise RuntimeError("Unsafe output path")

            src = Path(filename)
            if src.exists() and src.resolve() != final_path:
                if final_path.exists():
                    final_path.unlink()
                src.rename(final_path)
            elif not final_path.exists() and src.exists():
                # already correct
                pass

            with _lock:
                entry = _downloads.get(download_id)
                if entry:
                    entry["status"] = "completed"
                    entry["progress"] = 100
                    entry["filename"] = final_path.name if final_path.exists() else safe_name
                    entry["title"] = info.get("title") or safe_name
                    entry["size"] = final_path.stat().st_size if final_path and final_path.exists() else 0

            add_history({
                "id": download_id,
                "title": info.get("title") or safe_name,
                "filename": final_path.name if final_path else safe_name,
                "url": url,
                "size": final_path.stat().st_size if final_path and final_path.exists() else 0,
                "completed_at": time.time(),
            })
    except Exception as e:
        msg = str(e)
        status = "cancelled" if "Cancelled" in msg else "error"
        with _lock:
            entry = _downloads.get(download_id)
            if entry:
                entry["status"] = status
                entry["error"] = msg[:300]
                entry["progress"] = 0


def list_files() -> list[dict]:
    folder = current_app.config["DOWNLOAD_FOLDER"]
    files = []
    try:
        for name in os.listdir(folder):
            path = safe_join(folder, name)
            if path is None or not path.is_file():
                continue
            size = path.stat().st_size
            if size > current_app.config.get("MAX_CONTENT_LENGTH", 2 * 1024 ** 3):
                continue
            files.append({
                "name": path.name,
                "size": size,
                "size_mb": round(size / (1024 * 1024), 2),
                "modified": path.stat().st_mtime,
            })
        files.sort(key=lambda x: x["modified"], reverse=True)
    except Exception:
        pass
    return files


def delete_file(filename: str) -> tuple[bool, str]:
    folder = current_app.config["DOWNLOAD_FOLDER"]
    path = safe_join(folder, filename)
    if path is None or not path.is_file():
        return False, "File not found or invalid path"
    try:
        path.unlink()
        return True, "Deleted"
    except Exception as e:
        return False, str(e)
