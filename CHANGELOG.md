# Changelog

## [1.0.0] — 2026-11-24

### Added
- Aurora Crystal Glass UI (obsidian / cyan / aurora palette)
- Modular Flask app (`app/routes`, `services`, `utils`)
- SSRF protection with DNS resolution and private-range blocking
- Path confinement for all file operations
- Settings persistence (`data/settings.json`)
- Download history, cancel, concurrent limit
- Full Persian RTL + English LTR
- Health, settings, and FFmpeg status APIs
- GitHub-ready docs: README, CONTRIBUTING, SECURITY, LICENSE (MIT), CI

### Security
- Removed automatic download of FFmpeg from the internet
- Restricted CORS
- Safe join for download/delete paths
- URL scheme limited to HTTP/HTTPS

### Changed
- Replaced monolithic `app.py` with package structure
- Improved progress and error reporting

### Removed
- Unsafe archive extraction of third-party FFmpeg builds
- Open CORS default
