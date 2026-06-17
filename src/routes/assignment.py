from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from src.database import get_db
from src.routes.auth import router as auth_router
from src.schemas import PaperTemplateCreate, PaperTemplateResponse, AssignmentCreate, AssignmentResponse
from src.services.assignment_service import AssignmentService
from src.services.pdf_service import PDFService
from src.services.cache_service import CacheService
from src.models import Assignment, MyLibrary


from fastapi import WebSocket, WebSocketDisconnect
from src.services.websocket_manager import ws_manager

# WebSocket endpoint that your Streamlit UI connects to
def get_current_user(token: str = "bearer mock-token") -> Dict[str, Any]:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization credentials")
    return {"user_id": "authenticated-teacher-uuid", "school_id": "7ec92b3a-f10a-42c2-b9e4-5ab12de349bb"}



router = APIRouter(prefix="/assignments", tags=["Assignments Management"])


# --- 1. PAPER TEMPLATES ---
@router.post("/templates", response_model=PaperTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_structural_template(
        payload: PaperTemplateCreate,
        db: Session = Depends(get_db),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        template = AssignmentService.add_template(payload, db)
        return template
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database execution crash: {str(e)}")


# --- 2. UPLOAD & ASSIGNMENT FLOW ---
@router.post("/upload-and-create", response_model=AssignmentResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_pdf_and_create_assignment(

        title: str = Form(...),
        teacher_id: UUID = Form(...),
        class_id: UUID = Form(...),
        due_date: str = Form(...),
        instructions: Optional[str] = Form(None),
        template_id: Optional[UUID] = Form(None),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    # 1. Handle file stream upload processing safely
    file_path = PDFService.upload_document(file)

    try:
        parsed_due_date = datetime.fromisoformat(due_date)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid ISO due_date syntax layout string.")

    payload = AssignmentCreate(
        teacher_id=teacher_id,
        class_id=class_id,
        template_id=template_id,
        title=title,
        file_url=file_path,
        instructions=instructions,
        due_date=parsed_due_date
    )

    try:
        assignment = AssignmentService.create_assignment_job(payload, file_path, db)


        CacheService.index_assignment_for_search(
            school_id=str(current_user["school_id"]),
            assignment_id=str(assignment.id),
            title=title,
            topic="Document Chapter Analysis"
        )


        return AssignmentResponse.model_validate(assignment)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Pipeline initiation aborted: {str(e)}")


# --- 3. SEARCH ENGINE ---
@router.websocket("/ws/status/{channel_id}")
async def websocket_status_endpoint(websocket: WebSocket, channel_id: str):
    await ws_manager.connect(channel_id, websocket)
    try:
        while True:
            # Keeps connection line persistent and active
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(channel_id, websocket)

# Internal router point used by Celery workers to pass message text payloads
@router.post("/ws-notify", include_in_schema=False)
async def accept_worker_notification_broadcast(payload: dict):
    await ws_manager.send_status_update(
        client_id=payload["channel_id"],
        message={"status": payload["status"], "progress": payload["progress"]}
    )
    return {"status": "ok"}


@router.get("/search", response_model=List[Dict[str, Any]])
def fast_search_assignments(
        school_id: UUID,
        query: str,
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    return CacheService.search_assignments(str(school_id), query)


# --- 4. DASHBOARD GRID VIEW CARDS ---
@router.get("/dashboard/{teacher_id}", response_model=List[AssignmentResponse])
def get_teacher_dashboard_cards(
        teacher_id: UUID,
        db: Session = Depends(get_db),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Fetch active cards excluding soft deleted statuses
    cards = db.query(Assignment).filter(
        Assignment.teacher_id == teacher_id,
        Assignment.status != "DELETED"
    ).order_by(Assignment.created_at.desc()).all()

    return [AssignmentResponse.model_validate(c) for c in cards]  # 🌟 FIX BUG 1: Consistent serialization arrays


@router.delete("/{assignment_id}", status_code=status.HTTP_200_OK)
def delete_assignment(
        assignment_id: UUID,
        db: Session = Depends(get_db),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target node reference mapping unavailable")


    assignment.status = "DELETED"

    CacheService.remove_from_search(school_id=str(current_user["school_id"]), assignment_id=str(assignment_id))
    db.commit()
    return {"status": "success", "message": "Assignment soft-deleted successfully"}


# --- 5. MY LIBRARY STATUS TRACKING ---
@router.get("/my-library/{user_id}")
def view_my_library(
        user_id: UUID,
        db: Session = Depends(get_db),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    completed = db.query(MyLibrary).filter(MyLibrary.user_id == user_id, MyLibrary.is_completed == True).all()
    pending = db.query(MyLibrary).filter(MyLibrary.user_id == user_id, MyLibrary.is_completed == False).all()


    return {
        "completed_count": len(completed),
        "pending_count": len(pending),
        "completed_assignments": [str(item.assignment_id) for item in completed],
        "pending_assignments": [str(item.assignment_id) for item in pending]
    }
