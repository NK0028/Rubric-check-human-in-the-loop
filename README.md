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

## Product principles

1. Teachers define the rubric for every question.
2. AI provides a transparent recommendation, not an unreviewed final grade.
3. Every suggested score includes criterion-level evidence and confidence.
4. Teacher overrides are recorded to improve future evaluation quality.
