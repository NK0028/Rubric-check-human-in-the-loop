from pathlib import Path
import csv
from io import StringIO
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_session
from .auth import SESSION_COOKIE, get_current_user, hash_password, issue_session, verify_password
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
    Student,
    User,
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
    StudentCreate,
    StudentExamProgressRead,
    StudentRead,
    StudentUpdate,
    RosterImportRead,
    RosterProgressRead,
    LoginRequest,
    RegisterRequest,
    UserRead,
)
from .storage import uploads_directory

auth_router = APIRouter(prefix="/api/auth", tags=["authentication"])
router = APIRouter(prefix="/api", tags=["academic setup"], dependencies=[Depends(get_current_user)])
allowed_upload_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
maximum_upload_size = 10 * 1024 * 1024


@auth_router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, session: Session = Depends(get_session)) -> User:
    email = payload.email.strip().lower()
    if session.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    issue_session(response, user, session)
    return user


@auth_router.post("/login", response_model=UserRead)
def login(payload: LoginRequest, response: Response, session: Session = Depends(get_session)) -> User:
    user = session.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    issue_session(response, user, session)
    return user


@auth_router.get("/me", response_model=UserRead)
def current_user(user: User = Depends(get_current_user)) -> User:
    return user


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    response.delete_cookie(SESSION_COOKIE)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def owned_course(course_id: int, user: User, session: Session) -> Course:
    course = session.get(Course, course_id)
    if not course or course.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Course not found.")
    return course


def owned_exam(exam_id: int, user: User, session: Session) -> Exam:
    exam = session.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found.")
    owned_course(exam.course_id, user, session)
    return exam


def owned_question(question_id: int, user: User, session: Session) -> Question:
    question = session.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")
    owned_exam(question.exam_id, user, session)
    return question


def owned_submission(submission_id: int, user: User, session: Session) -> Submission:
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    owned_question(submission.question_id, user, session)
    return submission


@router.get("/uploads/{stored_filename}", tags=["submissions"])
def download_upload(stored_filename: str, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> FileResponse:
    submission = session.scalar(select(Submission).where(Submission.stored_filename == stored_filename))
    if not submission:
        raise HTTPException(status_code=404, detail="Answer sheet not found.")
    owned_question(submission.question_id, user, session)
    file_path = uploads_directory / submission.stored_filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="The stored answer sheet is unavailable.")
    return FileResponse(file_path, media_type=submission.content_type, filename=submission.original_filename)


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
        file_url=f"/api/uploads/{submission.stored_filename}",
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


def roster_progress(exam_id: int, session: Session) -> RosterProgressRead:
    exam = session.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found.")
    questions = session.scalars(select(Question).where(Question.exam_id == exam_id).order_by(Question.question_number)).all()
    students = session.scalars(select(Student).where(Student.course_id == exam.course_id).order_by(Student.name)).all()
    submissions = session.execute(select(Submission.student_identifier, Submission.question_id, Submission.status).join(Question).where(Question.exam_id == exam_id)).all()
    by_student: dict[str, list[tuple[int, str]]] = {}
    for identifier, question_id, submission_status in submissions:
        if identifier:
            by_student.setdefault(identifier, []).append((question_id, submission_status))
    rows = []
    for student in students:
        attempts = by_student.get(student.identifier, [])
        submitted_ids = {question_id for question_id, _ in attempts}
        finalized_ids = {question_id for question_id, submission_status in attempts if submission_status == "finalized"}
        rows.append(StudentExamProgressRead(student_id=student.id, name=student.name, identifier=student.identifier, submitted_questions=len(submitted_ids), finalized_questions=len(finalized_ids), missing_question_numbers=[question.question_number for question in questions if question.id not in submitted_ids]))
    return RosterProgressRead(exam_id=exam_id, total_students=len(rows), students_with_missing_submissions=sum(bool(row.missing_question_numbers) for row in rows), students=rows)


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
def create_course(payload: CourseCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> Course:
    course = Course(title=payload.title, code=payload.code.upper(), owner_id=user.id)
    session.add(course)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="A course with this code already exists.") from error
    session.refresh(course)
    return course


@router.get("/courses", response_model=list[CourseRead])
def list_courses(session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> list[Course]:
    return list(session.scalars(select(Course).where(Course.owner_id == user.id).order_by(Course.created_at.desc())))


@router.post("/courses/{course_id}/students", response_model=StudentRead, status_code=status.HTTP_201_CREATED, tags=["roster"])
def create_student(course_id: int, payload: StudentCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> Student:
    owned_course(course_id, user, session)
    student = Student(course_id=course_id, name=payload.name.strip(), identifier=payload.identifier.strip())
    session.add(student)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="This student identifier is already in the course roster.") from error
    session.refresh(student)
    return student


@router.get("/courses/{course_id}/students", response_model=list[StudentRead], tags=["roster"])
def list_students(course_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> list[Student]:
    owned_course(course_id, user, session)
    return list(session.scalars(select(Student).where(Student.course_id == course_id).order_by(Student.name)))


@router.put("/courses/{course_id}/students/{student_id}", response_model=StudentRead, tags=["roster"])
def update_student(course_id: int, student_id: int, payload: StudentUpdate, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> Student:
    owned_course(course_id, user, session)
    student = session.get(Student, student_id)
    if not student or student.course_id != course_id:
        raise HTTPException(status_code=404, detail="Student not found in this course roster.")
    identifier = payload.identifier.strip()
    if identifier != student.identifier:
        has_submissions = session.scalar(
            select(Submission.id)
            .join(Question, Question.id == Submission.question_id)
            .join(Exam, Exam.id == Question.exam_id)
            .where(Exam.course_id == course_id, Submission.student_identifier == student.identifier)
            .limit(1)
        )
        if has_submissions:
            raise HTTPException(
                status_code=409,
                detail="A student with uploaded answers cannot have their student ID changed.",
            )
    student.name = payload.name.strip()
    student.identifier = identifier
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="This student identifier is already in the course roster.") from error
    session.refresh(student)
    return student


@router.delete("/courses/{course_id}/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["roster"])
def delete_student(course_id: int, student_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> Response:
    owned_course(course_id, user, session)
    student = session.get(Student, student_id)
    if not student or student.course_id != course_id:
        raise HTTPException(status_code=404, detail="Student not found in this course roster.")
    has_submissions = session.scalar(
        select(Submission.id)
        .join(Question, Question.id == Submission.question_id)
        .join(Exam, Exam.id == Question.exam_id)
        .where(Exam.course_id == course_id, Submission.student_identifier == student.identifier)
        .limit(1)
    )
    if has_submissions:
        raise HTTPException(status_code=409, detail="This student has uploaded answers and cannot be removed from the roster.")
    session.delete(student)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/courses/{course_id}/students/import", response_model=RosterImportRead, tags=["roster"])
async def import_students(course_id: int, file: UploadFile = File(...), session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> RosterImportRead:
    """Import or update a roster from UTF-8 CSV columns named `name` and `identifier`."""
    owned_course(course_id, user, session)
    if Path(file.filename or "").suffix.lower() != ".csv":
        raise HTTPException(status_code=415, detail="Upload a CSV file with name and identifier columns.")
    content = await file.read()
    if not content or len(content) > 1_000_000:
        raise HTTPException(status_code=422, detail="Upload a non-empty roster CSV smaller than 1 MB.")
    try:
        rows = list(csv.DictReader(StringIO(content.decode("utf-8-sig"))))
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=422, detail="Roster CSV must use UTF-8 encoding.") from error
    if not rows or not rows[0] or {"name", "identifier"} - {key.strip().lower() for key in rows[0] if key}:
        raise HTTPException(status_code=422, detail="Roster CSV needs `name` and `identifier` column headers.")
    parsed: list[tuple[str, str]] = []
    seen_identifiers = set()
    for index, row in enumerate(rows, start=2):
        normalized = {(key or "").strip().lower(): (value or "").strip() for key, value in row.items()}
        name, identifier = normalized.get("name", ""), normalized.get("identifier", "")
        if not name or not identifier or len(name) > 160 or len(identifier) > 80:
            raise HTTPException(status_code=422, detail=f"Invalid name or identifier on CSV row {index}.")
        if identifier in seen_identifiers:
            raise HTTPException(status_code=422, detail=f"Duplicate identifier `{identifier}` in the CSV.")
        seen_identifiers.add(identifier)
        parsed.append((name, identifier))
    existing = {student.identifier: student for student in session.scalars(select(Student).where(Student.course_id == course_id))}
    added = updated = 0
    for name, identifier in parsed:
        if student := existing.get(identifier):
            if student.name != name:
                student.name = name
                updated += 1
        else:
            session.add(Student(course_id=course_id, name=name, identifier=identifier))
            added += 1
    session.commit()
    return RosterImportRead(added=added, updated=updated, total=len(parsed))


@router.post("/exams", response_model=ExamRead, status_code=status.HTTP_201_CREATED)
def create_exam(payload: ExamCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> Exam:
    owned_course(payload.course_id, user, session)
    exam = Exam(**payload.model_dump())
    session.add(exam)
    session.commit()
    session.refresh(exam)
    return exam


@router.get("/courses/{course_id}/exams", response_model=list[ExamRead])
def list_course_exams(course_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> list[Exam]:
    owned_course(course_id, user, session)
    return list(session.scalars(select(Exam).where(Exam.course_id == course_id).order_by(Exam.created_at.desc())))


@router.post("/questions", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
def create_question(payload: QuestionCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> QuestionRead:
    owned_exam(payload.exam_id, user, session)
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
def list_exam_questions(exam_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> list[QuestionRead]:
    owned_exam(exam_id, user, session)
    questions = session.scalars(select(Question).where(Question.exam_id == exam_id).order_by(Question.question_number)).all()
    return [question_response(question, session) for question in questions]


@router.get("/exams/{exam_id}/results", response_model=list[ExamResultRow], tags=["results"])
def list_exam_results(exam_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> list[ExamResultRow]:
    """List every teacher-finalized question result for an exam."""
    owned_exam(exam_id, user, session)
    return exam_results(exam_id, session)


@router.get("/exams/{exam_id}/results.csv", tags=["results"])
def export_exam_results(exam_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> Response:
    """Download finalized results in a gradebook-friendly CSV format."""
    owned_exam(exam_id, user, session)
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
def get_exam_progress(exam_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> ExamProgressRead:
    owned_exam(exam_id, user, session)
    return exam_progress(exam_id, session)


@router.get("/exams/{exam_id}/roster-progress", response_model=RosterProgressRead, tags=["roster"])
def get_roster_progress(exam_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> RosterProgressRead:
    owned_exam(exam_id, user, session)
    return roster_progress(exam_id, session)


@router.post("/submissions", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED, tags=["submissions"])
async def upload_submission(
    question_id: int = Form(...),
    student_name: str = Form(...),
    student_identifier: str | None = Form(None),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> SubmissionRead:
    """Store a scanned answer and immediately attempt local, on-device OCR."""
    owned_question(question_id, user, session)
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
def list_question_submissions(question_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> list[SubmissionRead]:
    owned_question(question_id, user, session)
    submissions = session.scalars(
        select(Submission).where(Submission.question_id == question_id).order_by(Submission.uploaded_at.desc())
    ).all()
    return [submission_response(submission) for submission in submissions]


@router.get("/submissions/{submission_id}", response_model=SubmissionRead, tags=["submissions"])
def get_submission(submission_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> SubmissionRead:
    submission = owned_submission(submission_id, user, session)
    return submission_response(submission)


@router.get("/submissions/{submission_id}/final-evaluation", response_model=FinalEvaluationRead, tags=["evaluation"])
def get_final_evaluation(submission_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> FinalEvaluationRead:
    """Retrieve the teacher-approved score and criterion breakdown for an answer sheet."""
    owned_submission(submission_id, user, session)
    final_evaluation = session.scalar(
        select(FinalEvaluation).where(FinalEvaluation.submission_id == submission_id).order_by(FinalEvaluation.id.desc())
    )
    if not final_evaluation:
        raise HTTPException(status_code=404, detail="No final marks have been recorded for this submission.")
    return final_evaluation_response(final_evaluation, session)


@router.post("/submissions/{submission_id}/ocr", response_model=SubmissionRead, tags=["submissions"])
async def rerun_submission_ocr(submission_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> SubmissionRead:
    """Retry local OCR for a scan that had no text or was uploaded before Tesseract was installed."""
    submission = owned_submission(submission_id, user, session)
    if submission.status in {"transcribed", "suggested", "finalized"}:
        raise HTTPException(status_code=409, detail="OCR cannot replace a teacher-reviewed transcript.")
    await run_submission_ocr(submission, session)
    return submission_response(submission)


@router.put("/submissions/{submission_id}/extraction", response_model=SubmissionRead, tags=["evaluation"])
def save_extraction(
    submission_id: int,
    payload: ExtractionUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> SubmissionRead:
    """Save the teacher-reviewed version of the locally extracted transcript."""
    submission = owned_submission(submission_id, user, session)
    if submission.status == "finalized":
        raise HTTPException(status_code=409, detail="A finalized transcript cannot be changed.")
    submission.extracted_text = payload.extracted_text.strip()
    submission.status = "transcribed"
    session.commit()
    session.refresh(submission)
    return submission_response(submission)


@router.post("/submissions/{submission_id}/evaluate", response_model=EvaluationRead, status_code=status.HTTP_201_CREATED, tags=["evaluation"])
def create_baseline_evaluation(submission_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)) -> EvaluationRead:
    submission = owned_submission(submission_id, user, session)
    latest_evaluation = session.scalar(
        select(Evaluation)
        .where(Evaluation.submission_id == submission_id)
        .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
    )
    if latest_evaluation:
        return evaluation_response(latest_evaluation, session)
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
    user: User = Depends(get_current_user),
) -> FinalEvaluationRead:
    """Persist the teacher-approved criterion marks for a score suggestion."""
    evaluation = session.get(Evaluation, evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Score suggestion not found.")
    owned_submission(evaluation.submission_id, user, session)
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
