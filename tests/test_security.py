"""Unit tests for SSRF and path safety."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.security import sanitize_filename, safe_join, validate_url, _is_blocked_ip


class TestBlockedIP:
    def test_loopback(self):
        assert _is_blocked_ip("127.0.0.1") is True
        assert _is_blocked_ip("::1") is True

    def test_private(self):
        assert _is_blocked_ip("10.0.0.1") is True
        assert _is_blocked_ip("192.168.1.1") is True
        assert _is_blocked_ip("172.16.0.5") is True

    def test_link_local(self):
        assert _is_blocked_ip("169.254.1.1") is True


class TestValidateURL:
    def test_rejects_empty(self):
        ok, _ = validate_url("")
        assert ok is False

    def test_rejects_ftp(self):
        ok, msg = validate_url("ftp://example.com/file")
        assert ok is False
        assert "HTTP" in msg or "HTTPS" in msg

    def test_rejects_localhost(self):
        ok, _ = validate_url("http://localhost/admin")
        assert ok is False

    def test_rejects_127(self):
        ok, _ = validate_url("http://127.0.0.1:8080/")
        assert ok is False

    def test_rejects_metadata(self):
        ok, _ = validate_url("http://metadata.google.internal/")
        assert ok is False

    def test_accepts_public(self):
        # May fail offline; skip if DNS fails
        ok, err = validate_url("https://example.com/")
        if "could not be resolved" in err.lower():
            pytest.skip("DNS unavailable")
        assert ok is True


class TestSafeJoin:
    def test_normal(self, tmp_path):
        p = safe_join(str(tmp_path), "file.mp4")
        assert p is not None
        assert p.name == "file.mp4"

    def test_traversal(self, tmp_path):
        p = safe_join(str(tmp_path), "..", "etc", "passwd")
        assert p is None

    def test_absolute_escape(self, tmp_path):
        p = safe_join(str(tmp_path), "/etc/passwd")
        # On POSIX absolute second part resets; safe_join should still confine
        if p is not None:
            assert str(tmp_path.resolve()) in str(p.resolve())


class TestSanitizeFilename:
    def test_strips_separators(self):
        assert "/" not in sanitize_filename("a/b\\c")
        assert "\\" not in sanitize_filename("a/b\\c")

    def test_empty(self):
        assert sanitize_filename("") == "download"
        assert sanitize_filename("...") == "download"

    def test_length(self):
        long = "a" * 300 + ".mp4"
        out = sanitize_filename(long, max_len=50)
        assert len(out) <= 50
        assert out.endswith(".mp4")
