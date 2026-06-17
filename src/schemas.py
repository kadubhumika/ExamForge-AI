from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List, Dict
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



# ---------------------------
# ASSIGNMENT SCHEMAS
# ---------------------------

class AssignmentCreate(BaseModel):
    teacher_id: UUID
    class_id: UUID
    template_id: Optional[UUID] = None

    title: str
    file_url: str
    instructions: Optional[str] = None
    due_date: datetime


class AssignmentResponse(BaseModel):
    id: UUID
    title: str
    status: str
    job_id: Optional[str]
    due_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------
# ASSIGNMENT RESULT
# ---------------------------

class AssignmentResultResponse(BaseModel):
    id: UUID
    assignment_id: UUID
    structured_json: Dict
    pdf_url: str
    ai_model_used: str
    created_at: datetime

    class Config:
        from_attributes = True




# ---------------------------
# PAPER TEMPLATE
# ---------------------------

class TemplateItem(BaseModel):
    type: str  # e.g., "Multiple Choice Questions"
    count: int
    marks_per: int

class PaperTemplateCreate(BaseModel):
    school_id: UUID
    class_id: UUID
    topic_name: str
    structure_scheme: List[TemplateItem]  # Enforces type, count, and marks rules


class PaperTemplateResponse(BaseModel):
    id: UUID
    topic_name: str
    structure_scheme: List[Dict]
    total_questions: int
    total_marks: int

    class Config:
        from_attributes = True