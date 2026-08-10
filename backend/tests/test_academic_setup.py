"""Run directly with: uv run python tests/test_academic_setup.py"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

with tempfile.TemporaryDirectory() as temporary_directory:
    database_path = Path(temporary_directory) / "rubricheck-test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
    os.environ["UPLOADS_DIR"] = str(Path(temporary_directory) / "uploads")

    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from app.ocr import OCRUnavailableError

    from main import app

    with TestClient(app) as client:
        course = client.post(
            "/api/courses",
            json={"title": "Design and Analysis of Algorithms", "code": "DAA-101"},
        )
        assert course.status_code == 201, course.text

        exam = client.post(
            "/api/exams",
            json={"course_id": course.json()["id"], "title": "Midterm Examination"},
        )
        assert exam.status_code == 201, exam.text

        question = client.post(
            "/api/questions",
            json={
                "exam_id": exam.json()["id"],
                "question_number": 1,
                "prompt": "Prove the greedy-choice property for activity selection.",
                "max_marks": 6,
                "rubric": [
                    {"title": "Proof / reasoning", "description": "Uses a valid proof idea.", "max_marks": 2},
                    {"title": "Derivation steps", "description": "Shows the required steps.", "max_marks": 2},
                    {"title": "Correct conclusion", "description": "Reaches the correct conclusion.", "max_marks": 2},
                ],
            },
        )
        assert question.status_code == 201, question.text
        assert question.json()["max_marks"] == 6
        assert len(question.json()["rubric"]) == 3

        with patch("app.api.extract_text", return_value="A locally extracted answer."):
            submission = client.post(
                "/api/submissions",
                data={
                    "question_id": question.json()["id"],
                    "student_name": "Ayesha Khan",
                    "student_identifier": "FA21-BAI-042",
                },
                files={"file": ("ayesha-answer.png", b"sample-scan-content", "image/png")},
            )
        assert submission.status_code == 201, submission.text
        assert submission.json()["status"] == "ocr_complete"
        assert submission.json()["extracted_text"] == "A locally extracted answer."
        assert submission.json()["file_url"].endswith(".png")

        with patch("app.api.extract_text", side_effect=OCRUnavailableError("Tesseract is unavailable")):
            unavailable_ocr = client.post(
                "/api/submissions",
                data={"question_id": question.json()["id"], "student_name": "Sara Ali"},
                files={"file": ("sara-answer.png", b"another-scan", "image/png")},
            )
        assert unavailable_ocr.status_code == 201, unavailable_ocr.text
        assert unavailable_ocr.json()["status"] == "ocr_unavailable"
        assert unavailable_ocr.json()["extracted_text"] is None

        with patch("app.api.extract_text", return_value="A refreshed local OCR draft."):
            retried_ocr = client.post(f"/api/submissions/{unavailable_ocr.json()['id']}/ocr")
        assert retried_ocr.status_code == 200, retried_ocr.text
        assert retried_ocr.json()["status"] == "ocr_complete"
        assert retried_ocr.json()["extracted_text"] == "A refreshed local OCR draft."

        transcription = client.put(
            f"/api/submissions/{submission.json()['id']}/extraction",
            json={"extracted_text": "The proof gives the derivation steps and reaches the correct conclusion."},
        )
        assert transcription.status_code == 200, transcription.text
        assert transcription.json()["status"] == "transcribed"

        evaluation = client.post(f"/api/submissions/{submission.json()['id']}/evaluate")
        assert evaluation.status_code == 201, evaluation.text
        assert evaluation.json()["method"] == "keyword_baseline"
        assert len(evaluation.json()["criteria"]) == 3

        finalization_payload = {
            "criteria": [
                {"evaluation_criterion_id": criterion["id"], "awarded_marks": criterion["awarded_marks"]}
                for criterion in evaluation.json()["criteria"]
            ],
            "teacher_feedback": "Approved after reviewing the scan.",
        }
        finalization = client.post(
            f"/api/evaluations/{evaluation.json()['id']}/finalize",
            json=finalization_payload,
        )
        assert finalization.status_code == 201, finalization.text
        assert finalization.json()["awarded_total"] == evaluation.json()["suggested_total"]
        assert len(finalization.json()["criteria"]) == 3

        duplicate_finalization = client.post(
            f"/api/evaluations/{evaluation.json()['id']}/finalize", json=finalization_payload
        )
        assert duplicate_finalization.status_code == 409, duplicate_finalization.text

        results = client.get(f"/api/exams/{exam.json()['id']}/results")
        assert results.status_code == 200, results.text
        assert len(results.json()) == 1
        assert results.json()[0]["student_name"] == "Ayesha Khan"
        assert results.json()[0]["awarded_total"] == finalization.json()["awarded_total"]

        csv_export = client.get(f"/api/exams/{exam.json()['id']}/results.csv")
        assert csv_export.status_code == 200, csv_export.text
        assert csv_export.headers["content-type"].startswith("text/csv")
        assert "Ayesha Khan" in csv_export.text

print("Academic setup, OCR, teacher-finalization, and results-export workflow verified.")
