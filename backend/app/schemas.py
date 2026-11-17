from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=10, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class UserRead(ORMModel):
    id: int
    name: str
    email: str


class SessionRead(BaseModel):
    id: int
    created_at: datetime
    expires_at: datetime
    is_current: bool


class CourseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=2, max_length=40)


class CourseUpdate(CourseCreate):
    pass


class ArchiveUpdate(BaseModel):
    is_archived: bool


class CourseRead(ORMModel):
    id: int
    title: str
    code: str
    is_archived: bool


class CoursePortalRead(BaseModel):
    course_id: int
    portal_code: str


class AuditEventRead(BaseModel):
    id: int
    actor_name: str
    action: str
    details: str
    created_at: datetime


class StudentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    identifier: str = Field(min_length=2, max_length=80)
    section_id: int | None = None


class StudentUpdate(StudentCreate):
    pass


class StudentRead(ORMModel):
    id: int
    course_id: int
    name: str
    identifier: str
    section_id: int | None


class SectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class SectionRead(ORMModel):
    id: int
    course_id: int
    name: str


class CollaboratorCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    role: str = Field(pattern="^(editor|viewer)$")


class CollaboratorRead(BaseModel):
    user_id: int
    name: str
    email: str
    role: str


class RosterImportRead(BaseModel):
    added: int
    updated: int
    total: int


class ExamCreate(BaseModel):
    course_id: int
    title: str = Field(min_length=2, max_length=160)
    description: str | None = None


class ExamUpdate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str | None = None


class ExamRead(ORMModel):
    id: int
    course_id: int
    title: str
    description: str | None
    is_archived: bool


class RubricCriterionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=2)
    max_marks: float = Field(gt=0)
    expected_evidence: str | None = None


class RubricCriterionRead(ORMModel):
    id: int
    title: str
    description: str
    max_marks: float
    expected_evidence: str | None


class RubricTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2_000)
    rubric: list[RubricCriterionCreate] = Field(min_length=1)


class RubricTemplateRead(ORMModel):
    id: int
    name: str
    description: str | None
    rubric: list[RubricCriterionRead]


class QuestionBankItemCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    prompt: str = Field(min_length=5)
    max_marks: float = Field(gt=0)
    reference_answer: str | None = None
    rubric: list[RubricCriterionCreate] = Field(min_length=1)


class QuestionBankItemRead(ORMModel):
    id: int
    title: str
    prompt: str
    max_marks: float
    reference_answer: str | None
    rubric: list[RubricCriterionRead]


class QuestionCreate(BaseModel):
    exam_id: int
    question_number: int = Field(gt=0)
    prompt: str = Field(min_length=5)
    max_marks: float = Field(gt=0)
    reference_answer: str | None = None
    rubric: list[RubricCriterionCreate] = Field(min_length=1)


class QuestionRead(ORMModel):
    id: int
    exam_id: int
    question_number: int
    prompt: str
    max_marks: float
    reference_answer: str | None
    rubric: list[RubricCriterionRead]


class SubmissionRead(ORMModel):
    id: int
    question_id: int
    student_name: str
    student_identifier: str | None
    original_filename: str
    content_type: str | None
    status: str
    extracted_text: str | None
    file_url: str


class BatchUploadRead(BaseModel):
    uploaded: list[SubmissionRead]


class ExtractionUpdate(BaseModel):
    extracted_text: str = Field(min_length=2)


class EvaluationCriterionRead(ORMModel):
    id: int
    criterion_title: str
    maximum_marks: float
    awarded_marks: float
    evidence: str
    confidence: str
    feedback_suggestion: str


class EvaluationRead(ORMModel):
    id: int
    submission_id: int
    suggested_total: float
    maximum_marks: float
    method: str
    status: str
    criteria: list[EvaluationCriterionRead]


class FinalCriterionCreate(BaseModel):
    evaluation_criterion_id: int
    awarded_marks: float = Field(ge=0)
    teacher_note: str | None = Field(default=None, max_length=2_000)


class FinalEvaluationCreate(BaseModel):
    criteria: list[FinalCriterionCreate] = Field(min_length=1)
    teacher_feedback: str | None = Field(default=None, max_length=4_000)


class FinalEvaluationCriterionRead(ORMModel):
    criterion_title: str
    maximum_marks: float
    awarded_marks: float
    teacher_note: str | None


class FinalEvaluationRead(ORMModel):
    id: int
    evaluation_id: int
    submission_id: int
    awarded_total: float
    maximum_marks: float
    teacher_feedback: str | None
    criteria: list[FinalEvaluationCriterionRead]


class ExamResultRow(BaseModel):
    final_evaluation_id: int
    submission_id: int
    student_name: str
    student_identifier: str | None
    question_number: int
    question_prompt: str
    awarded_total: float
    maximum_marks: float
    teacher_feedback: str | None
    finalized_at: datetime | None


class StudentGradebookRow(BaseModel):
    student_id: int
    name: str
    identifier: str
    submitted_questions: int
    finalized_questions: int
    total_questions: int
    awarded_total: float
    maximum_marks: float


class StudentReportRead(BaseModel):
    exam_id: int
    exam_title: str
    student_id: int
    student_name: str
    student_identifier: str
    awarded_total: float
    maximum_marks: float
    finalized_questions: int
    total_questions: int
    results: list[ExamResultRow]


class StudentPortalRequest(BaseModel):
    course_code: str = Field(min_length=2, max_length=40)
    portal_code: str = Field(min_length=4, max_length=32)
    student_identifier: str = Field(min_length=2, max_length=80)


class StudentPortalRead(BaseModel):
    course_title: str
    student_name: str
    student_identifier: str
    reports: list[StudentReportRead]


class ExamAnalyticsRead(BaseModel):
    exam_id: int
    exam_title: str
    rostered_students: int
    students_with_final_marks: int
    completion_rate: float
    average_percentage: float
    highest_percentage: float
    lowest_percentage: float


class CourseAnalyticsRead(BaseModel):
    course_id: int
    course_title: str
    exams: list[ExamAnalyticsRead]


class QuestionProgressRead(BaseModel):
    question_id: int
    question_number: int
    prompt: str
    maximum_marks: float
    uploaded_count: int
    ocr_ready_count: int
    reviewed_count: int
    suggested_count: int
    finalized_count: int


class ExamProgressRead(BaseModel):
    exam_id: int
    question_count: int
    uploaded_count: int
    finalized_count: int
    questions: list[QuestionProgressRead]


class StudentExamProgressRead(BaseModel):
    student_id: int
    name: str
    identifier: str
    submitted_questions: int
    finalized_questions: int
    missing_question_numbers: list[int]


class RosterProgressRead(BaseModel):
    exam_id: int
    total_students: int
    students_with_missing_submissions: int
    students: list[StudentExamProgressRead]
