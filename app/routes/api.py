"""JSON API endpoints."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, send_file

from app.services import download_manager as dm
from app.services import settings as settings_svc
from app.utils.security import safe_join, validate_url

api_bp = Blueprint("api", __name__)


@api_bp.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "ffmpeg": dm.get_ffmpeg_path() is not None,
    })


@api_bp.route("/video-info", methods=["POST"])
def video_info():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400
    info = dm.get_video_info(url)
    status = 400 if "error" in info else 200
    return jsonify(info), status


@api_bp.route("/extract-links", methods=["POST"])
def extract_links():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400
    ok, err = validate_url(url)
    if not ok:
        return jsonify({"error": err}), 400
    links = dm.extract_page_links(url)
    return jsonify({"links": links})


@api_bp.route("/download", methods=["POST"])
def start_download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    format_id = data.get("format_id")
    if not url:
        return jsonify({"error": "URL is required"}), 400
    result = dm.start_download(url, format_id)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@api_bp.route("/status/<download_id>")
def status(download_id: str):
    if not download_id or len(download_id) > 64:
        return jsonify({"status": "not_found"}), 404
    st = dm.get_status(download_id)
    return jsonify(st)


@api_bp.route("/cancel/<download_id>", methods=["POST"])
def cancel(download_id: str):
    if dm.cancel_download(download_id):
        return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404


@api_bp.route("/active")
def active():
    return jsonify(dm.list_active())


@api_bp.route("/files")
def list_files():
    return jsonify(dm.list_files())


@api_bp.route("/download-file/<path:filename>")
def download_file(filename: str):
    folder = current_app.config["DOWNLOAD_FOLDER"]
    path = safe_join(folder, filename)
    if path is None or not path.is_file():
        return jsonify({"error": "File not found"}), 404
    max_size = current_app.config.get("MAX_CONTENT_LENGTH", 2 * 1024 ** 3)
    if path.stat().st_size > max_size:
        return jsonify({"error": "File exceeds size limit"}), 400
    return send_file(path, as_attachment=True, download_name=path.name)


@api_bp.route("/delete-file", methods=["DELETE", "POST"])
def delete_file():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename") or request.args.get("filename")
    if not filename:
        return jsonify({"error": "filename required"}), 400
    ok, msg = dm.delete_file(filename)
    if ok:
        return jsonify({"success": True})
    return jsonify({"error": msg}), 404


@api_bp.route("/history")
def history():
    return jsonify(dm.list_history())


@api_bp.route("/history", methods=["DELETE"])
def clear_history():
    dm.clear_history()
    return jsonify({"success": True})


@api_bp.route("/settings", methods=["GET"])
def get_settings():
    return jsonify(settings_svc.load_settings())


@api_bp.route("/settings", methods=["POST"])
def update_settings():
    data = request.get_json(silent=True) or {}
    # Only allow known keys
    allowed = {
        "language", "theme", "default_quality", "preferred_format",
        "max_concurrent", "max_filesize_mb", "auto_cleanup", "history_limit",
    }
    updates = {k: v for k, v in data.items() if k in allowed}
    # Basic validation
    if "max_concurrent" in updates:
        try:
            v = int(updates["max_concurrent"])
            updates["max_concurrent"] = max(1, min(10, v))
        except (TypeError, ValueError):
            del updates["max_concurrent"]
    if "language" in updates and updates["language"] not in ("fa", "en"):
        del updates["language"]
    saved = settings_svc.save_settings(updates)
    return jsonify(saved)


@api_bp.route("/ffmpeg-status")
def ffmpeg_status():
    path = dm.get_ffmpeg_path()
    return jsonify({"available": path is not None, "path": path})
