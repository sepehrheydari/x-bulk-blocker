# X List Bulk Blocker

Block every tweet author from any public X (Twitter) list — no API keys or developer account needed. Just your browser cookies.

[![CI](https://github.com/sepehrheydari/x-bulk-blocker/actions/workflows/ci.yml/badge.svg)](https://github.com/sepehrheydari/x-bulk-blocker/actions/workflows/ci.yml)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sepehrheydari/x-bulk-blocker)

## Features

- 🚫 **Bulk block** all tweet authors from any public X list
- 👁 **Dry-run mode** — preview who would be blocked before committing
- ⚡ **Live progress** — real-time log streamed to your browser
- 🔒 **Zero storage** — your cookies never touch disk or logs
- 🆓 **Free to run** — deploys on Render, Railway, or any Docker host

## How It Works

1. Paste a public X list URL (e.g. `https://x.com/i/lists/1234567890`)
2. Paste your `auth_token` and `ct0` browser cookies from x.com
3. Choose **Preview only** or **Block everyone** and hit Start
4. Watch the live log as each author is processed

Your cookies are used only to call X on your behalf and are cleared from memory the moment your job finishes.

## One-Click Deploy

### Render (recommended — free tier)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sepehrheydari/x-bulk-blocker)

Click the button, sign in to Render, and hit **Deploy**. The [`render.yaml`](render.yaml) handles everything automatically.

### Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/sepehrheydari/x-bulk-blocker)

## Self-Hosting with Docker

```bash
git clone https://github.com/sepehrheydari/x-bulk-blocker.git
cd x-bulk-blocker
docker compose up
# Open http://localhost:7070
```

## Self-Hosting with Python

```bash
git clone https://github.com/sepehrheydari/x-bulk-blocker.git
cd x-bulk-blocker
pip install -r requirements.txt
python app.py
# Open http://localhost:7070
```

## CLI Usage

```bash
cp .env.example .env
# Edit .env — fill in X_COOKIES=auth_token=XXX; ct0=YYY

# Preview (no blocking)
python x_bulk_block.py --list https://x.com/i/lists/1234567890 --dry-run

# Block everyone
python x_bulk_block.py --list https://x.com/i/lists/1234567890
```

## How to Get Your Cookies

1. Open [x.com](https://x.com) in Chrome and make sure you are logged in
2. Press `F12` (Windows/Linux) or `⌘ ⌥ I` (Mac) to open DevTools
3. Click **Application** → **Cookies** → **https://x.com**
4. Copy the value of `auth_token` and the value of `ct0`

> ⚠️ Treat these cookies like a password — they grant full access to your X account. Use this tool only on servers you control, over HTTPS.

## Security

- TLS verified on all outbound requests (`verify=True`)
- Strict Content Security Policy — no `unsafe-inline`
- `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`
- Rate limiting: 5 requests/minute per IP on the `/start` endpoint
- POST body capped at 4 KB; all inputs length-validated
- UUID validation on the `/stream/<id>` endpoint (no ID probing)
- Runs as a non-root user inside Docker
- No credentials ever written to disk or server logs

## Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v
```

## License

MIT
