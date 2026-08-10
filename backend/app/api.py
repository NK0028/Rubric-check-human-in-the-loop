from pathlib import Path
import csv
from io import StringIO
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_session
from .models import (
    Course,
    Evaluation,
    EvaluationCriterion,
    Exam,
    FinalEvaluation,
    FinalEvaluationCriterion,
    Question,
    RubricCriterion,
    Submission,
)
from .ocr import OCRUnavailableError, extract_text
from .schemas import (
    CourseCreate,
    CourseRead,
    EvaluationCriterionRead,
    EvaluationRead,
    ExamCreate,
    ExamRead,
    ExamProgressRead,
    QuestionCreate,
    QuestionRead,
    QuestionProgressRead,
    RubricCriterionRead,
    ExtractionUpdate,
    FinalEvaluationCreate,
    FinalEvaluationCriterionRead,
    FinalEvaluationRead,
    ExamResultRow,
    SubmissionRead,
)
from .storage import uploads_directory

router = APIRouter(prefix="/api", tags=["academic setup"])
allowed_upload_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
maximum_upload_size = 10 * 1024 * 1024


def question_response(question: Question, session: Session) -> QuestionRead:
    rubric = session.scalars(
        select(RubricCriterion).where(RubricCriterion.question_id == question.id).order_by(RubricCriterion.id)
    ).all()
    return QuestionRead(
        id=question.id,
        exam_id=question.exam_id,
        question_number=question.question_number,
        prompt=question.prompt,
        max_marks=question.max_marks,
        reference_answer=question.reference_answer,
        rubric=[RubricCriterionRead.model_validate(item) for item in rubric],
    )


def submission_response(submission: Submission) -> SubmissionRead:
    return SubmissionRead(
        id=submission.id,
        question_id=submission.question_id,
        student_name=submission.student_name,
        student_identifier=submission.student_identifier,
        original_filename=submission.original_filename,
        content_type=submission.content_type,
        status=submission.status,
        extracted_text=submission.extracted_text,
        file_url=f"/uploads/{submission.stored_filename}",
    )


def evaluation_response(evaluation: Evaluation, session: Session) -> EvaluationRead:
    criteria = session.scalars(
        select(EvaluationCriterion).where(EvaluationCriterion.evaluation_id == evaluation.id)
    ).all()
    return EvaluationRead(
        id=evaluation.id,
        submission_id=evaluation.submission_id,
        suggested_total=evaluation.suggested_total,
        maximum_marks=evaluation.maximum_marks,
        method=evaluation.method,
        status=evaluation.status,
        criteria=[EvaluationCriterionRead.model_validate(criterion) for criterion in criteria],
    )


def final_evaluation_response(final_evaluation: FinalEvaluation, session: Session) -> FinalEvaluationRead:
    criteria = session.scalars(
        select(FinalEvaluationCriterion)
        .where(FinalEvaluationCriterion.final_evaluation_id == final_evaluation.id)
        .order_by(FinalEvaluationCriterion.id)
    ).all()
    return FinalEvaluationRead(
        id=final_evaluation.id,
        evaluation_id=final_evaluation.evaluation_id,
        submission_id=final_evaluation.submission_id,
        awarded_total=final_evaluation.awarded_total,
        maximum_marks=final_evaluation.maximum_marks,
        teacher_feedback=final_evaluation.teacher_feedback,
        criteria=[FinalEvaluationCriterionRead.model_validate(criterion) for criterion in criteria],
    )


def exam_results(exam_id: int, session: Session) -> list[ExamResultRow]:
    if not session.get(Exam, exam_id):
        raise HTTPException(status_code=404, detail="Exam not found.")
    rows = session.execute(
        select(FinalEvaluation, Submission, Question)
        .join(Submission, Submission.id == FinalEvaluation.submission_id)
        .join(Question, Question.id == Submission.question_id)
        .where(Question.exam_id == exam_id)
        .order_by(Submission.student_name, Question.question_number)
    ).all()
    return [
        ExamResultRow(
            final_evaluation_id=final_evaluation.id,
            submission_id=submission.id,
            student_name=submission.student_name,
            student_identifier=submission.student_identifier,
            question_number=question.question_number,
            question_prompt=question.prompt,
            awarded_total=final_evaluation.awarded_total,
            maximum_marks=final_evaluation.maximum_marks,
            teacher_feedback=final_evaluation.teacher_feedback,
            finalized_at=final_evaluation.finalized_at,
        )
        for final_evaluation, submission, question in rows
    ]


def csv_cell(value: object | None) -> object:
    """Prevent spreadsheet formula interpretation when teachers export student data."""
    if value is None:
        return ""
    text = str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def exam_progress(exam_id: int, session: Session) -> ExamProgressRead:
    if not session.get(Exam, exam_id):
        raise HTTPException(status_code=404, detail="Exam not found.")
    questions = session.scalars(select(Question).where(Question.exam_id == exam_id).order_by(Question.question_number)).all()
    submissions = session.execute(select(Submission.question_id, Submission.status).join(Question).where(Question.exam_id == exam_id)).all()
    counts: dict[int, dict[str, int]] = {question.id: {} for question in questions}
    for question_id, submission_status in submissions:
        counts[question_id][submission_status] = counts[question_id].get(submission_status, 0) + 1
    progress_questions = [
        QuestionProgressRead(question_id=question.id, question_number=question.question_number, prompt=question.prompt, maximum_marks=question.max_marks, uploaded_count=sum(counts[question.id].values()), ocr_ready_count=counts[question.id].get("ocr_complete", 0), reviewed_count=counts[question.id].get("transcribed", 0), suggested_count=counts[question.id].get("suggested", 0), finalized_count=counts[question.id].get("finalized", 0))
        for question in questions
    ]
    return ExamProgressRead(exam_id=exam_id, question_count=len(questions), uploaded_count=len(submissions), finalized_count=sum(item.finalized_count for item in progress_questions), questions=progress_questions)


def baseline_score(text: str, criterion: RubricCriterion) -> tuple[float, str, str]:
    """Temporary explainable baseline used until a handwriting/LLM provider is configured."""
    source = criterion.expected_evidence or criterion.description
    terms = {
        word.lower()
        for word in re.findall(r"[a-zA-Z]{4,}", source)
        if word.lower() not in {"that", "with", "this", "whether", "student", "answer", "shows", "checks", "uses", "valid"}
    }
    matched = sorted(term for term in terms if term in text.lower())
    ratio = len(matched) / len(terms) if terms else 0
    if ratio >= 0.5:
        return criterion.max_marks, f"Matched rubric terms: {', '.join(matched)}.", "low"
    if matched:
        return round(criterion.max_marks / 2, 2), f"Partial evidence found: {', '.join(matched)}.", "low"
    return 0, "No baseline keyword evidence found; teacher review is required.", "low"


@router.post("/courses", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, session: Session = Depends(get_session)) -> Course:
    course = Course(title=payload.title, code=payload.code.upper())
    session.add(course)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="A course with this code already exists.") from error
    session.refresh(course)
    return course


@router.get("/courses", response_model=list[CourseRead])
def list_courses(session: Session = Depends(get_session)) -> list[Course]:
    return list(session.scalars(select(Course).order_by(Course.created_at.desc())))


@router.post("/exams", response_model=ExamRead, status_code=status.HTTP_201_CREATED)
def create_exam(payload: ExamCreate, session: Session = Depends(get_session)) -> Exam:
    if not session.get(Course, payload.course_id):
        raise HTTPException(status_code=404, detail="Course not found.")
    exam = Exam(**payload.model_dump())
    session.add(exam)
    session.commit()
    session.refresh(exam)
    return exam


@router.get("/courses/{course_id}/exams", response_model=list[ExamRead])
def list_course_exams(course_id: int, session: Session = Depends(get_session)) -> list[Exam]:
    if not session.get(Course, course_id):
        raise HTTPException(status_code=404, detail="Course not found.")
    return list(session.scalars(select(Exam).where(Exam.course_id == course_id).order_by(Exam.created_at.desc())))


@router.post("/questions", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
def create_question(payload: QuestionCreate, session: Session = Depends(get_session)) -> QuestionRead:
    if not session.get(Exam, payload.exam_id):
        raise HTTPException(status_code=404, detail="Exam not found.")
    rubric_total = sum(item.max_marks for item in payload.rubric)
    if abs(rubric_total - payload.max_marks) > 0.001:
        raise HTTPException(status_code=422, detail="Rubric criterion marks must equal the question's maximum marks.")
    question_data = payload.model_dump(exclude={"rubric"})
    question = Question(**question_data)
    session.add(question)
    session.flush()
    session.add_all([RubricCriterion(question_id=question.id, **criterion.model_dump()) for criterion in payload.rubric])
    session.commit()
    session.refresh(question)
    return question_response(question, session)


@router.get("/exams/{exam_id}/questions", response_model=list[QuestionRead])
def list_exam_questions(exam_id: int, session: Session = Depends(get_session)) -> list[QuestionRead]:
    if not session.get(Exam, exam_id):
        raise HTTPException(status_code=404, detail="Exam not found.")
    questions = session.scalars(select(Question).where(Question.exam_id == exam_id).order_by(Question.question_number)).all()
    return [question_response(question, session) for question in questions]


@router.get("/exams/{exam_id}/results", response_model=list[ExamResultRow], tags=["results"])
def list_exam_results(exam_id: int, session: Session = Depends(get_session)) -> list[ExamResultRow]:
    """List every teacher-finalized question result for an exam."""
    return exam_results(exam_id, session)


@router.get("/exams/{exam_id}/results.csv", tags=["results"])
def export_exam_results(exam_id: int, session: Session = Depends(get_session)) -> Response:
    """Download finalized results in a gradebook-friendly CSV format."""
    results = exam_results(exam_id, session)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student name", "Student identifier", "Question", "Final marks", "Maximum marks", "Teacher feedback", "Finalized at"])
    for result in results:
        writer.writerow(
            [
                csv_cell(result.student_name),
                csv_cell(result.student_identifier),
                f"Q{result.question_number}",
                result.awarded_total,
                result.maximum_marks,
                csv_cell(result.teacher_feedback),
                result.finalized_at.isoformat() if result.finalized_at else "",
            ]
        )
    filename = f"rubricheck-exam-{exam_id}-results.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/exams/{exam_id}/progress", response_model=ExamProgressRead, tags=["review dashboard"])
def get_exam_progress(exam_id: int, session: Session = Depends(get_session)) -> ExamProgressRead:
    return exam_progress(exam_id, session)


@router.post("/submissions", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED, tags=["submissions"])
async def upload_submission(
    question_id: int = Form(...),
    student_name: str = Form(...),
    student_identifier: str | None = Form(None),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> SubmissionRead:
    """Store a scanned answer and immediately attempt local, on-device OCR."""
    if not session.get(Question, question_id):
        raise HTTPException(status_code=404, detail="Question not found.")
    original_filename = file.filename or "answer-sheet"
    suffix = Path(original_filename).suffix.lower()
    if suffix not in allowed_upload_suffixes:
        raise HTTPException(status_code=415, detail="Upload a PDF, JPG, JPEG, PNG, or WEBP answer sheet.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    if len(content) > maximum_upload_size:
        raise HTTPException(status_code=413, detail="Answer sheets must be 10 MB or smaller.")
    stored_filename = f"{uuid4().hex}{suffix}"
    (uploads_directory / stored_filename).write_bytes(content)
    submission = Submission(
        question_id=question_id,
        student_name=student_name.strip(),
        student_identifier=student_identifier.strip() if student_identifier else None,
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=file.content_type,
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)
    await run_submission_ocr(submission, session)
    return submission_response(submission)


async def run_submission_ocr(submission: Submission, session: Session) -> None:
    """Run OCR without allowing a local OCR issue to discard an uploaded answer sheet."""
    try:
        extracted_text = await run_in_threadpool(extract_text, uploads_directory / submission.stored_filename)
    except OCRUnavailableError:
        submission.status = "ocr_unavailable"
    except Exception:  # OCR failures are non-fatal; the teacher can still transcribe the scan.
        submission.status = "ocr_failed"
    else:
        submission.extracted_text = extracted_text or None
        submission.status = "ocr_complete" if extracted_text else "ocr_no_text"
    session.commit()
    session.refresh(submission)


@router.get("/questions/{question_id}/submissions", response_model=list[SubmissionRead], tags=["submissions"])
def list_question_submissions(question_id: int, session: Session = Depends(get_session)) -> list[SubmissionRead]:
    if not session.get(Question, question_id):
        raise HTTPException(status_code=404, detail="Question not found.")
    submissions = session.scalars(
        select(Submission).where(Submission.question_id == question_id).order_by(Submission.uploaded_at.desc())
    ).all()
    return [submission_response(submission) for submission in submissions]


@router.get("/submissions/{submission_id}", response_model=SubmissionRead, tags=["submissions"])
def get_submission(submission_id: int, session: Session = Depends(get_session)) -> SubmissionRead:
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    return submission_response(submission)


@router.post("/submissions/{submission_id}/ocr", response_model=SubmissionRead, tags=["submissions"])
async def rerun_submission_ocr(submission_id: int, session: Session = Depends(get_session)) -> SubmissionRead:
    """Retry local OCR for a scan that had no text or was uploaded before Tesseract was installed."""
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if submission.status in {"transcribed", "suggested", "finalized"}:
        raise HTTPException(status_code=409, detail="OCR cannot replace a teacher-reviewed transcript.")
    await run_submission_ocr(submission, session)
    return submission_response(submission)


@router.put("/submissions/{submission_id}/extraction", response_model=SubmissionRead, tags=["evaluation"])
def save_extraction(
    submission_id: int,
    payload: ExtractionUpdate,
    session: Session = Depends(get_session),
) -> SubmissionRead:
    """Save the teacher-reviewed version of the locally extracted transcript."""
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if submission.status == "finalized":
        raise HTTPException(status_code=409, detail="A finalized transcript cannot be changed.")
    submission.extracted_text = payload.extracted_text.strip()
    submission.status = "transcribed"
    session.commit()
    session.refresh(submission)
    return submission_response(submission)


@router.post("/submissions/{submission_id}/evaluate", response_model=EvaluationRead, status_code=status.HTTP_201_CREATED, tags=["evaluation"])
def create_baseline_evaluation(submission_id: int, session: Session = Depends(get_session)) -> EvaluationRead:
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if not submission.extracted_text:
        raise HTTPException(status_code=422, detail="Save a reviewed transcript before requesting a score suggestion.")
    question = session.get(Question, submission.question_id)
    assert question is not None
    rubric = session.scalars(
        select(RubricCriterion).where(RubricCriterion.question_id == question.id).order_by(RubricCriterion.id)
    ).all()
    scored_criteria = [(criterion, *baseline_score(submission.extracted_text, criterion)) for criterion in rubric]
    evaluation = Evaluation(
        submission_id=submission.id,
        suggested_total=round(sum(item[1] for item in scored_criteria), 2),
        maximum_marks=question.max_marks,
        method="keyword_baseline",
    )
    session.add(evaluation)
    session.flush()
    session.add_all(
        [
            EvaluationCriterion(
                evaluation_id=evaluation.id,
                rubric_criterion_id=criterion.id,
                criterion_title=criterion.title,
                maximum_marks=criterion.max_marks,
                awarded_marks=score,
                evidence=evidence,
                confidence=confidence,
            )
            for criterion, score, evidence, confidence in scored_criteria
        ]
    )
    submission.status = "suggested"
    session.commit()
    session.refresh(evaluation)
    return evaluation_response(evaluation, session)


@router.post("/evaluations/{evaluation_id}/finalize", response_model=FinalEvaluationRead, status_code=status.HTTP_201_CREATED, tags=["evaluation"])
def finalize_evaluation(
    evaluation_id: int,
    payload: FinalEvaluationCreate,
    session: Session = Depends(get_session),
) -> FinalEvaluationRead:
    """Persist the teacher-approved criterion marks for a score suggestion."""
    evaluation = session.get(Evaluation, evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Score suggestion not found.")
    if session.scalar(select(FinalEvaluation).where(FinalEvaluation.evaluation_id == evaluation_id)):
        raise HTTPException(status_code=409, detail="This score suggestion has already been finalized.")

    suggested_criteria = session.scalars(
        select(EvaluationCriterion).where(EvaluationCriterion.evaluation_id == evaluation_id).order_by(EvaluationCriterion.id)
    ).all()
    submitted_criteria = {item.evaluation_criterion_id: item for item in payload.criteria}
    expected_ids = {criterion.id for criterion in suggested_criteria}
    if len(submitted_criteria) != len(payload.criteria) or set(submitted_criteria) != expected_ids:
        raise HTTPException(status_code=422, detail="Final marks must include each suggested criterion exactly once.")
    for criterion in suggested_criteria:
        if submitted_criteria[criterion.id].awarded_marks > criterion.maximum_marks:
            raise HTTPException(status_code=422, detail=f"{criterion.criterion_title} cannot exceed its maximum marks.")

    awarded_total = round(sum(item.awarded_marks for item in payload.criteria), 2)
    final_evaluation = FinalEvaluation(
        evaluation_id=evaluation.id,
        submission_id=evaluation.submission_id,
        awarded_total=awarded_total,
        maximum_marks=evaluation.maximum_marks,
        teacher_feedback=payload.teacher_feedback.strip() if payload.teacher_feedback else None,
    )
    session.add(final_evaluation)
    session.flush()
    session.add_all(
        [
            FinalEvaluationCriterion(
                final_evaluation_id=final_evaluation.id,
                evaluation_criterion_id=criterion.id,
                criterion_title=criterion.criterion_title,
                maximum_marks=criterion.maximum_marks,
                awarded_marks=submitted_criteria[criterion.id].awarded_marks,
                teacher_note=submitted_criteria[criterion.id].teacher_note.strip()
                if submitted_criteria[criterion.id].teacher_note
                else None,
            )
            for criterion in suggested_criteria
        ]
    )
    evaluation.status = "finalized"
    submission = session.get(Submission, evaluation.submission_id)
    assert submission is not None
    submission.status = "finalized"
    session.commit()
    session.refresh(final_evaluation)
    return final_evaluation_response(final_evaluation, session)
