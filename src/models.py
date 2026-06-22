import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, JSON, Integer, Boolean, event
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from src.database import Base


# --- 1. CORE SYSTEM MANAGEMENT MODELS ---

class School(Base):
    __tablename__ = "schools"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)  # Indexed for fast lookups
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="school")
    classes = relationship("Class", back_populates="school")


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    school = relationship("School", back_populates="users")
    settings = relationship("UserSetting", back_populates="user", uselist=False)
    assignments = relationship("Assignment", back_populates="teacher")
    notifications = relationship("Notification", back_populates="user")


class UserSetting(Base):
    __tablename__ = "user_settings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    theme = Column(String, default="light")  # "light" or "dark"
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="settings")


class Class(Base):
    __tablename__ = "classes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    name = Column(String, nullable=False)  # e.g., "10-A"
    grade = Column(String, nullable=False)  # e.g., "10th Class"

    school = relationship("School", back_populates="classes")
    assignments = relationship("Assignment", back_populates="assigned_class")


# --- 2. PAPER TEMPLATES & ASSIGNMENT MODELS ---


class PaperTemplate(Base):
    __tablename__ = "paper_templates"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False)
    topic_name = Column(String, nullable=False)

    structure_scheme = Column(JSON, nullable=False)

    # Automatically computed backend columns (prevents UI math tampering)
    total_questions = Column(Integer, nullable=False, default=0)
    total_marks = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


@event.listens_for(PaperTemplate, 'before_insert')
@event.listens_for(PaperTemplate, 'before_update')
def calculate_template_totals(mapper, connection, target):
    if target.structure_scheme and isinstance(target.structure_scheme, list):
        try:
            total_q = sum(int(item.get('count', 0)) for item in target.structure_scheme)
            total_m = sum(int(item.get('count', 0)) * int(item.get('marks_per', 0)) for item in target.structure_scheme)

            target.total_questions = total_q
            target.total_marks = total_m
        except (ValueError, TypeError):
            target.total_questions = 0
            target.total_marks = 0


class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("paper_templates.id"), nullable=True)

    title = Column(String, nullable=False, index=True)
    file_url = Column(String, nullable=False)  # Source uploaded PDF/image
    instructions = Column(String, nullable=True)
    status = Column(String, default="PENDING")  # PENDING, PROCESSING, DONE, FAILED, DELETED
    job_id = Column(String, nullable=True)
    error_message = Column(String, nullable=True)

    assigned_on = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    due_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    teacher = relationship("User", back_populates="assignments")
    assigned_class = relationship("Class", back_populates="assignments")
    results = relationship("AssignmentResult", back_populates="assignment", uselist=False)

    __table_args__ = (
        Index("idx_school_search", "class_id", "created_at"),
        Index("idx_teacher_dashboard", "teacher_id", "due_date"),
    )


class AssignmentResult(Base):
    __tablename__ = "assignment_results"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id"), unique=True, nullable=False)
    structured_json = Column(JSON, nullable=False)
    pdf_url = Column(String, nullable=False)  # Generated final test sheet path
    ai_model_used = Column(String, default="gemini-2.0-flash")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    assignment = relationship("Assignment", back_populates="results")


# --- 3. LIBRARIES & DASHBOARD TRACKING ---

class MyLibrary(Base):
    __tablename__ = "my_libraries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id"), nullable=False)
    is_completed = Column(Boolean, default=False)

    __table_args__ = (
        Index("idx_library_lookup", "user_id", "is_completed"),
    )


# --- 4. NOTIFICATIONS ---

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    type = Column(String, nullable=False)  # ASSIGNMENT_CREATED, ASSIGNMENT_DELETED, ASSIGNMENT_READY, ASSIGNMENT_FAILED, PROFILE_UPDATED, THEME_CHANGED
    title = Column(String, nullable=False)
    message = Column(String, nullable=True)
    related_id = Column(UUID(as_uuid=True), nullable=True)  # e.g. assignment_id
    is_read = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("idx_notif_user_unread", "user_id", "is_read", "created_at"),
    )