# backend

A project created with FastAPI CLI.

## Quick Start

### Start the development server

```bash
uv run fastapi dev
```

For local answer-sheet OCR, install Tesseract on the API host (for macOS,
`brew install tesseract`). The app uses the local executable only; no scans are
sent to an external OCR provider. Set `TESSERACT_CMD` if its executable is not
on PATH.

Visit http://localhost:8000

### Runtime configuration

Copy the names in `.env.example` into your hosting provider's environment
configuration. For production, set `APP_ENV=production`, explicit HTTPS values
for `CORS_ORIGINS` and `ALLOWED_HOSTS`, and `COOKIE_SECURE=true`. The API does
not load `.env` files itself, which prevents local development settings from
silently being used in production.

## Project Structure

- `main.py` - Your FastAPI application
- `pyproject.toml` - Project dependencies

## Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [FastAPI Cloud](https://fastapicloud.com)
