from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import os

from src.database import get_db
from src.schemas import (
    PaperTemplateCreate, PaperTemplateResponse,
    AssignmentCreate, AssignmentResponse, AssignmentStatusResponse,
)
from src.services.assignment_service import AssignmentService
from src.services.pdf_service import PDFService
from src.services.cache_service import CacheService
from src.services.notification_service import NotificationService
from src.services.auth_service import get_current_user
from src.models import Assignment, MyLibrary, User, AssignmentResult

router = APIRouter(prefix="/assignments", tags=["Assignments Management"])


# --- 1. PAPER TEMPLATES ---
@router.post("/templates", response_model=PaperTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_structural_template(
        payload: PaperTemplateCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        template = AssignmentService.add_template(payload, db)
        return template
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not create template: {str(e)}")


# --- 2. UPLOAD & ASSIGNMENT FLOW ---
@router.post("/upload-and-create", response_model=AssignmentResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_pdf_and_create_assignment(
        background_tasks: BackgroundTasks,
        title: str = Form(...),
        class_id: Optional[UUID] = Form(None),
        due_date: str = Form(...),
        instructions: Optional[str] = Form(None),
        template_id: Optional[UUID] = Form(None),
        structure_scheme: Optional[str] = Form(None),  # JSON string of [{type,count,marks_per}] when no saved template
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    file_path = PDFService.upload_document(file)

    try:
        parsed_due_date = datetime.fromisoformat(due_date)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid ISO due_date format (expected YYYY-MM-DD or full ISO datetime)")

    payload = AssignmentCreate(
        teacher_id=current_user.id,
        class_id=class_id,
        template_id=template_id,
        title=title,
        file_url=file_path,
        instructions=instructions,
        due_date=parsed_due_date
    )

    try:
        assignment = AssignmentService.create_assignment_job(payload, file_path, db)

        # If the teacher built a one-off question structure on the create-assignment
        # screen (instead of picking a saved template), cache it under the assignment id
        # so the background pipeline can find it without needing a PaperTemplate row.
        if not template_id and structure_scheme:
            import json
            try:
                scheme = json.loads(structure_scheme)
                CacheService.cache_prompt_template(f"assignment:{assignment.id}", scheme)
            except (json.JSONDecodeError, TypeError):
                pass

        CacheService.index_assignment_for_search(
            school_id=str(current_user.school_id),
            assignment_id=str(assignment.id),
            title=title,
            topic=title,
        )

        background_tasks.add_task(AssignmentService.run_generation_pipeline, str(assignment.id))

        return AssignmentResponse.model_validate(assignment)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Could not start assignment generation: {str(e)}")


# --- 3. STATUS POLLING (replaces WebSocket — frontend polls this every ~2s) ---
@router.get("/{assignment_id}/status", response_model=AssignmentStatusResponse)
def get_assignment_status(
        assignment_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    result = db.query(AssignmentResult).filter(AssignmentResult.assignment_id == assignment_id).first()

    return AssignmentStatusResponse(
        id=assignment.id,
        status=assignment.status,
        error_message=assignment.error_message,
        pdf_url=f"/api/v1/assignments/{assignment.id}/download" if result else None,
    )


# --- 4. RESULT (structured JSON, for rendering the live HTML preview) ---
@router.get("/{assignment_id}/result")
def get_assignment_result(
        assignment_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    result = db.query(AssignmentResult).filter(AssignmentResult.assignment_id == assignment_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not ready yet")

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()

    return {
        "assignment_id": str(assignment_id),
        "title": assignment.title if assignment else "",
        "structured_json": result.structured_json,
    }


# --- 5. DOWNLOAD PDF ---
@router.get("/{assignment_id}/download")
def download_assignment_pdf(
        assignment_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    pdf_path = AssignmentService.download_assignment_pdf(str(assignment_id), db)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated file missing from storage")

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    safe_title = (assignment.title if assignment else "assignment").replace(" ", "_")

    return FileResponse(
        path=pdf_path,
        filename=f"{safe_title}.pdf",
        media_type="application/pdf",
    )


# --- 6. SEARCH ---
@router.get("/search", response_model=List[Dict[str, Any]])
def fast_search_assignments(
        school_id: UUID,
        query: str,
        current_user: User = Depends(get_current_user)
):
    return CacheService.search_assignments(str(school_id), query)


# --- 7. DASHBOARD GRID VIEW CARDS ---
@router.get("/dashboard/{teacher_id}", response_model=List[AssignmentResponse])
def get_teacher_dashboard_cards(
        teacher_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    cards = db.query(Assignment).filter(
        Assignment.teacher_id == teacher_id,
        Assignment.status != "DELETED"
    ).order_by(Assignment.created_at.desc()).all()

    return [AssignmentResponse.model_validate(c) for c in cards]


# --- 8. DELETE ---
@router.delete("/{assignment_id}", status_code=status.HTTP_200_OK)
def delete_assignment(
        assignment_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    assignment.status = "DELETED"
    db.commit()

    CacheService.remove_from_search(school_id=str(current_user.school_id), assignment_id=str(assignment_id))
    NotificationService.assignment_deleted(db, current_user.id, assignment.id, assignment.title)

    return {"status": "success", "message": "Assignment deleted successfully"}


# --- 9. MY LIBRARY STATUS TRACKING ---
@router.get("/my-library/{user_id}")
def view_my_library(
        user_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    items = (
        db.query(MyLibrary, Assignment)
        .join(Assignment, MyLibrary.assignment_id == Assignment.id)
        .filter(MyLibrary.user_id == user_id, Assignment.status != "DELETED")
        .order_by(Assignment.created_at.desc())
        .all()
    )

    library_items = []
    completed_count = 0
    pending_count = 0

    for lib, assignment in items:
        is_done = assignment.status == "DONE"
        if is_done:
            completed_count += 1
        else:
            pending_count += 1

        library_items.append({
            "assignment_id": str(assignment.id),
            "title": assignment.title,
            "status": assignment.status,
            "is_completed": is_done,
            "created_at": assignment.created_at.isoformat(),
            "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
        })

    return {
        "total_count": len(library_items),
        "completed_count": completed_count,
        "pending_count": pending_count,
        "items": library_items,
    }