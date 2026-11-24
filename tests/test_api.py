"""API smoke tests with Flask test client."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


@pytest.fixture
def client(tmp_path):
    os.environ["DOWNLOAD_FOLDER"] = str(tmp_path / "dl")
    os.environ["TEMP_FOLDER"] = str(tmp_path / "tmp")
    os.environ["DATA_FOLDER"] = str(tmp_path / "data")
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "healthy"
    assert "ffmpeg" in data


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"X DOWNLOADER" in r.data


def test_video_info_requires_url(client):
    r = client.post("/api/video-info", json={})
    assert r.status_code == 400


def test_video_info_rejects_localhost(client):
    r = client.post("/api/video-info", json={"url": "http://127.0.0.1/"})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_download_rejects_bad_scheme(client):
    r = client.post("/api/download", json={"url": "file:///etc/passwd"})
    assert r.status_code == 400


def test_settings_get_post(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    s = r.get_json()
    assert "language" in s

    r2 = client.post("/api/settings", json={"language": "en", "max_concurrent": 2})
    assert r2.status_code == 200
    assert r2.get_json()["language"] == "en"
    assert r2.get_json()["max_concurrent"] == 2


def test_files_empty(client):
    r = client.get("/api/files")
    assert r.status_code == 200
    assert r.get_json() == []


def test_delete_missing(client):
    r = client.delete("/api/delete-file", json={"filename": "nope.mp4"})
    assert r.status_code == 404


def test_path_traversal_download(client):
    r = client.get("/api/download-file/../../etc/passwd")
    assert r.status_code in (404, 400)
