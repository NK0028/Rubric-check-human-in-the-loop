from datetime import datetime
from secrets import token_urlsafe

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(160))
    code: Mapped[str] = mapped_column(String(40), unique=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    portal_code: Mapped[str] = mapped_column(String(32), default=lambda: token_urlsafe(8), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CourseCollaborator(Base):
    __tablename__ = "course_collaborators"
    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_course_collaborator"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="editor")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("course_id", "identifier", name="uq_student_course_identifier"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("class_sections.id"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    identifier: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClassSection(Base):
    __tablename__ = "class_sections"
    __table_args__ = (UniqueConstraint("course_id", "name", name="uq_course_section_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    question_number: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(Text)
    max_marks: Mapped[float] = mapped_column(Float)
    reference_answer: Mapped[str | None] = mapped_column(Text, default=None)


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    max_marks: Mapped[float] = mapped_column(Float)
    expected_evidence: Mapped[str | None] = mapped_column(Text, default=None)


class RubricTemplate(Base):
    __tablename__ = "rubric_templates"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_rubric_template_owner_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RubricTemplateCriterion(Base):
    __tablename__ = "rubric_template_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("rubric_templates.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    max_marks: Mapped[float] = mapped_column(Float)
    expected_evidence: Mapped[str | None] = mapped_column(Text, default=None)


class QuestionBankItem(Base):
    __tablename__ = "question_bank_items"
    __table_args__ = (UniqueConstraint("owner_id", "title", name="uq_question_bank_owner_title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    prompt: Mapped[str] = mapped_column(Text)
    max_marks: Mapped[float] = mapped_column(Float)
    reference_answer: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuestionBankCriterion(Base):
    __tablename__ = "question_bank_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("question_bank_items.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    max_marks: Mapped[float] = mapped_column(Float)
    expected_evidence: Mapped[str | None] = mapped_column(Text, default=None)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    student_name: Mapped[str] = mapped_column(String(160))
    student_identifier: Mapped[str | None] = mapped_column(String(80), default=None)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str | None] = mapped_column(String(100), default=None)
    status: Mapped[str] = mapped_column(String(40), default="uploaded")
    extracted_text: Mapped[str | None] = mapped_column(Text, default=None)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True)
    suggested_total: Mapped[float] = mapped_column(Float)
    maximum_marks: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="suggested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvaluationCriterion(Base):
    __tablename__ = "evaluation_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id"), index=True)
    rubric_criterion_id: Mapped[int] = mapped_column(ForeignKey("rubric_criteria.id"))
    criterion_title: Mapped[str] = mapped_column(String(160))
    maximum_marks: Mapped[float] = mapped_column(Float)
    awarded_marks: Mapped[float] = mapped_column(Float)
    evidence: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(20))
    feedback_suggestion: Mapped[str] = mapped_column(Text, default="")


class FinalEvaluation(Base):
    __tablename__ = "final_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id"), unique=True, index=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True)
    awarded_total: Mapped[float] = mapped_column(Float)
    maximum_marks: Mapped[float] = mapped_column(Float)
    teacher_feedback: Mapped[str | None] = mapped_column(Text, default=None)
    finalized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinalEvaluationCriterion(Base):
    __tablename__ = "final_evaluation_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    final_evaluation_id: Mapped[int] = mapped_column(ForeignKey("final_evaluations.id"), index=True)
    evaluation_criterion_id: Mapped[int] = mapped_column(ForeignKey("evaluation_criteria.id"))
    criterion_title: Mapped[str] = mapped_column(String(160))
    maximum_marks: Mapped[float] = mapped_column(Float)
    awarded_marks: Mapped[float] = mapped_column(Float)
    teacher_note: Mapped[str | None] = mapped_column(Text, default=None)
