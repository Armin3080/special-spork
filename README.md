# X DOWNLOADER

**Aurora Crystal Glass** — a secure, bilingual (Persian / English) media downloader built with Flask and yt-dlp.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-black)
![License](https://img.shields.io/badge/License-MIT-green)

> Download **publicly available** video and audio. Respect copyright, terms of service, and local law. This tool does **not** bypass DRM, paywalls, or authentication.

## Features

- **URL analysis** with format / quality selection (video + audio)
- **Progress tracking** — percentage, speed, ETA
- **Concurrent downloads** with configurable limit and cancellation
- **Page link extraction** for direct media links on public pages
- **Download history** and file management (list / download / delete)
- **FFmpeg detection** (system binary only — no silent auto-download of untrusted binaries)
- **Settings persistence** (language, concurrency, defaults)
- **Full Persian RTL + English LTR** UI
- **SSRF protection**, path confinement, safe filenames
- **Premium Aurora Crystal Glass** UI (obsidian / cyan / aurora palette)

## Screenshots

Concept previews of the Aurora Crystal interface are stored under [`docs/screenshots/`](docs/screenshots/).  
Replace with real captures after running the app locally.

## Requirements

- Python **3.10+**
- `pip`
- Optional but recommended: system **FFmpeg** on `PATH` (for merging formats / audio extraction)

```bash
# Debian/Ubuntu
sudo apt install ffmpeg

# macOS (Homebrew)
brew install ffmpeg

# Windows: install from https://ffmpeg.org and add to PATH
```

## Quick start

```bash
# 1. Clone / extract
cd x_downloader

# 2. Virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install
pip install -r requirements.txt

# 4. Run
python run.py
# → http://127.0.0.1:5000
```

### Windows

```bat
run.bat
```

### Linux / macOS

```bash
chmod +x run.sh
./run.sh
```

## Configuration

Copy `.env.example` to `.env` (optional) or set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | HTTP port |
| `SECRET_KEY` | (dev default) | Flask secret — **change in production** |
| `DOWNLOAD_FOLDER` | `./downloads` | Where files are saved |
| `MAX_CONCURRENT_DOWNLOADS` | `3` | Server-side concurrency cap |
| `CORS_ORIGINS` | `http://localhost:5000,...` | Allowed browser origins |
| `FLASK_DEBUG` | `0` | Set `1` only for local debug |

Settings such as language and concurrency are also stored in `data/settings.json` and can be changed from the UI.

## Security notes

- Only **HTTP/HTTPS** URLs are accepted.
- Hostnames are resolved; **private, loopback, link-local, and reserved** addresses are blocked (SSRF mitigation).
- Final URL after redirects is validated again for link extraction.
- File operations are confined to the configured download directory (path traversal blocked).
- No automatic download of FFmpeg from the internet; use a system-trusted binary.
- CORS is restricted to configured origins.
- **Do not expose** an unauthenticated instance to the public internet without adding authentication and hardening (reverse proxy, rate limits, TLS).

## API (summary)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health + FFmpeg presence |
| `POST` | `/api/video-info` | `{ "url": "..." }` → metadata + formats |
| `POST` | `/api/download` | `{ "url", "format_id?" }` → `{ "download_id" }` |
| `GET` | `/api/status/<id>` | Progress / status |
| `POST` | `/api/cancel/<id>` | Cancel download |
| `GET` | `/api/active` | Active jobs |
| `GET` | `/api/files` | List downloaded files |
| `GET` | `/api/download-file/<name>` | Download a file |
| `DELETE` | `/api/delete-file` | `{ "filename" }` |
| `GET/POST` | `/api/settings` | Read / update settings |
| `POST` | `/api/extract-links` | Extract media links from a page |

## Project layout

```
x_downloader/
├── app/
│   ├── core/          # config
│   ├── routes/        # HTTP routes
│   ├── services/      # download manager, settings
│   └── utils/         # security helpers
├── static/css|js      # Aurora Crystal UI
├── templates/
├── tests/
├── docs/screenshots/
├── run.py             # dev server
├── wsgi.py            # production WSGI
├── requirements.txt
└── ...
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
python -m compileall app run.py wsgi.py
```

## Known limitations

- Resume is only available when yt-dlp and the site support it; not all sources do.
- Some sites require cookies or login — this app does **not** automate authenticated downloads.
- Thumbnail images are loaded from third-party CDNs when present in metadata.
- Designed for personal / trusted-network use; add auth before public deployment.

## Roadmap

- [ ] Optional basic auth / token for public deploy
- [ ] Playlist support with selective items
- [ ] Dark/light theme toggle beyond Aurora
- [ ] Docker Compose example with volume mounts

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please open issues for bugs and security reports via [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

You are responsible for ensuring you have the right to download content. The authors are not liable for misuse.
