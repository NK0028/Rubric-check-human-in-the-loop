from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CourseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=2, max_length=40)


class CourseRead(ORMModel):
    id: int
    title: str
    code: str


class StudentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    identifier: str = Field(min_length=2, max_length=80)


class StudentUpdate(StudentCreate):
    pass


class StudentRead(ORMModel):
    id: int
    course_id: int
    name: str
    identifier: str


class RosterImportRead(BaseModel):
    added: int
    updated: int
    total: int


class ExamCreate(BaseModel):
    course_id: int
    title: str = Field(min_length=2, max_length=160)
    description: str | None = None


class ExamRead(ORMModel):
    id: int
    course_id: int
    title: str
    description: str | None


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


class ExtractionUpdate(BaseModel):
    extracted_text: str = Field(min_length=2)


class EvaluationCriterionRead(ORMModel):
    id: int
    criterion_title: str
    maximum_marks: float
    awarded_marks: float
    evidence: str
    confidence: str


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
