# RubriCheck AI — MVP scope

## Primary user

A teacher marking handwritten university exam answers, beginning with descriptive and algorithm-analysis questions.

## Core workflow

1. Create a course and an exam.
2. Add questions and a rubric for each question.
3. Upload a student's scanned answer sheet.
4. Extract text and associate it with an exam question.
5. Generate a criterion-by-criterion score recommendation.
6. Teacher reviews, edits, and finalizes marks.

## Out of scope for the first release

- Automatic final grading without a teacher review.
- Training a new handwriting-recognition model.
- Perfect support for every mathematical symbol, diagram, and scan quality.
- Student-facing accounts and payments.

## Suggested technical architecture

- Next.js and TypeScript for the teacher dashboard.
- FastAPI for the API and evaluation pipeline.
- SQLite locally, PostgreSQL in production.
- Object storage for scanned answer sheets.
- OCR plus a multimodal model for extraction and rubric matching.
