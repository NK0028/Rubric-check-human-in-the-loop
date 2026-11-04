# RubriCheck AI

RubriCheck AI is a human-in-the-loop tool for evaluating handwritten exam answers against teacher-defined, question-specific rubrics. It suggests criterion-level marks and evidence; the teacher always approves the final score.

## Project structure

- `frontend/` — Next.js teacher dashboard
- `backend/` — FastAPI API
- `docs/` — architecture and product documentation
- `scripts/` — local setup utilities

## Run locally

First make `uv` available in new terminals (needed once on this machine):

```zsh
zsh scripts/configure-uv-path.sh
```

Start the API:

```zsh
cd backend
uv sync
uv run fastapi dev
```

Install the free local OCR engine once before uploading answer sheets:

```zsh
brew install tesseract
```

RubriCheck runs Tesseract on the API machine; answer sheets are not sent to an
OCR service. If Tesseract is installed outside your shell PATH, set
`TESSERACT_CMD` to its executable before starting the API. PDFs are rasterized
locally page by page. OCR output is always a draft and must be teacher-reviewed.

In a second terminal, start the web app:

```zsh
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. API documentation is available at `http://localhost:8000/docs`.
To complete a marking cycle, create the rubric, upload a scan, review the OCR
draft, generate and finalize a score, then open **View results** to download the
exam's finalized marks as CSV.

## Production readiness

The project is intentionally provider-neutral: deploy the Next.js frontend and
FastAPI backend wherever you prefer, then set the backend environment variables
below through that provider's secret/environment configuration. Do not commit a
real `.env` file.

```bash
APP_ENV=production
CORS_ORIGINS=https://app.example.com
ALLOWED_HOSTS=api.example.com
COOKIE_SECURE=true
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/rubricheck
UPLOADS_DIR=/var/lib/rubricheck/uploads
TESSERACT_CMD=/usr/bin/tesseract
```

The frontend must be built with its backend URL:

```bash
cd frontend
NEXT_PUBLIC_API_URL=https://api.example.com npm run build
```

Use the API health endpoint (`/api/health`) after deployment. It reports the
service status and whether the host can find Tesseract. HTTPS is required when
`COOKIE_SECURE=true` so sign-in sessions can be stored safely.

### Backups

For the local SQLite setup, back up the database and uploaded scans together:

```bash
./scripts/backup-rubricheck.sh
```

The script writes a timestamped database snapshot plus an uploads archive under
`backups/`. Store that directory outside the deployment machine. To restore a
local backup, stop the API, replace `backend/rubricheck.db`, run
`tar -xzf uploads.tar.gz -C backend/`, then start the API again. Production
databases should use the managed backup process supplied by their provider.

## Product principles

1. Teachers define the rubric for every question.
2. AI provides a transparent recommendation, not an unreviewed final grade.
3. Every suggested score includes criterion-level evidence and confidence.
4. Teacher overrides are recorded to improve future evaluation quality.
