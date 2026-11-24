# Security Policy

## Supported versions

Security fixes are applied to the latest main branch.

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Email or privately message the maintainers with:

- Description of the issue
- Steps to reproduce
- Potential impact
- Any suggested fix

We will acknowledge receipt as soon as practical and work on a fix.

## Hardening recommendations for deployment

- Run behind a reverse proxy with TLS
- Restrict network access (VPN / firewall)
- Set a strong `SECRET_KEY`
- Configure tight `CORS_ORIGINS`
- Add authentication if the service is reachable beyond a trusted LAN
- Keep yt-dlp and system packages updated
- Mount `downloads/` as a dedicated volume with limited permissions
