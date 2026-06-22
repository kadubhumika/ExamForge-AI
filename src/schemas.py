from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID


# ---------------------------
# USER SCHEMAS
# ---------------------------

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    school_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    school_id: UUID

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class GoogleLoginRequest(BaseModel):
    id_token: str


class ProfileUpdate(BaseModel):
    name: str
    theme: str  # "light" or "dark"


# ---------------------------
# TEMPLATE QUESTION ITEM (used both standalone and inline in assignment creation)
# ---------------------------

class TemplateItem(BaseModel):
    type: str  # e.g., "Multiple Choice Questions"
    count: int
    marks_per: int


class PaperTemplateCreate(BaseModel):
    school_id: UUID
    class_id: UUID
    topic_name: str
    structure_scheme: List[TemplateItem]


class PaperTemplateResponse(BaseModel):
    id: UUID
    topic_name: str
    structure_scheme: List[Dict]
    total_questions: int
    total_marks: int

    class Config:
        from_attributes = True


# ---------------------------
# ASSIGNMENT SCHEMAS
# ---------------------------

class AssignmentCreate(BaseModel):
    teacher_id: UUID
    class_id: Optional[UUID] = None
    template_id: Optional[UUID] = None

    title: str
    file_url: str
    instructions: Optional[str] = None
    due_date: datetime


class AssignmentResponse(BaseModel):
    id: UUID
    title: str
    status: str
    job_id: Optional[str] = None
    file_url: str
    error_message: Optional[str] = None
    assigned_on: datetime
    due_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class AssignmentStatusResponse(BaseModel):
    id: UUID
    status: str
    error_message: Optional[str] = None
    pdf_url: Optional[str] = None


# ---------------------------
# ASSIGNMENT RESULT
# ---------------------------

class AssignmentResultResponse(BaseModel):
    id: UUID
    assignment_id: UUID
    structured_json: Dict[str, Any]
    pdf_url: str
    ai_model_used: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------
# NOTIFICATIONS
# ---------------------------

class NotificationResponse(BaseModel):
    id: UUID
    type: str
    title: str
    message: Optional[str] = None
    related_id: Optional[UUID] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True