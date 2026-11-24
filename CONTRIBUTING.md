# Contributing to X DOWNLOADER

Thank you for your interest in improving this project.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python run.py
```

## Guidelines

1. **Security first** — never weaken SSRF checks, path confinement, or allow arbitrary file access.
2. Keep the UI bilingual (Persian RTL + English LTR). Use `data-i18n` keys and CSS logical properties.
3. Prefer small, focused PRs with a clear description.
4. Add or update tests for behavioral changes.
5. Do not commit downloads, cookies, API keys, or personal data.

## Code style

- Python: follow existing patterns; run `ruff check` / `black` if available.
- JS/CSS: match the Aurora Crystal design tokens in `static/css/style.css`.

## Reporting issues

Use GitHub Issues. For security vulnerabilities, follow [SECURITY.md](SECURITY.md).
