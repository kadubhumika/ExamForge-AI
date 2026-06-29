from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import os

from src.database import get_db, SessionLocal
from src.services.auth_service import get_current_user
from src.services.student_pdf_service import StudentPDFService
from src.services.evaluation_service import EvaluationService
from src.services.results_pdf_service import ResultsPDFService
from src.models import (
    Assignment, AssignmentResult, StudentSubmission,
    EvaluationResult, User
)

router = APIRouter(prefix="/evaluations", tags=["Student Evaluations"])


def run_grading_pipeline(submission_id: str):
    """Background task: grades one student submission."""
    db: Session = SessionLocal()
    try:
        submission = db.query(StudentSubmission).filter(
            StudentSubmission.id == submission_id
        ).first()
        if not submission:
            return

        submission.status = "PROCESSING"
        db.commit()

        # Get assignment's answer key
        assignment = db.query(Assignment).filter(
            Assignment.id == submission.assignment_id
        ).first()
        result = db.query(AssignmentResult).filter(
            AssignmentResult.assignment_id == submission.assignment_id
        ).first()

        if not result:
            raise Exception("Assignment result/answer key not found")

        structured_json = result.structured_json

        # Grade using Gemini multimodal
        grading_result = EvaluationService.grade_student_submission(
            student_pdf_path=submission.pdf_url,
            student_name=submission.student_name,
            assignment_structured_json=structured_json,
        )

        scores_json = EvaluationService.build_scores_json(grading_result)
        total_awarded = grading_result.get("total_marks_awarded", 0)
        total_max = grading_result.get("total_max_marks", 1)
        percentage = round((total_awarded / total_max) * 100) if total_max > 0 else 0

        # Extract student name from Gemini if it found one in the image
        gemini_name = grading_result.get("student_name", "").strip()
        if gemini_name and gemini_name.lower() not in ["unknown", "student", ""]:
            submission.student_name = gemini_name

        db.add(EvaluationResult(
            submission_id=submission.id,
            student_name=submission.student_name,
            scores_json=scores_json,
            total_marks=total_awarded,
            max_marks=total_max,
            percentage=percentage,
        ))

        submission.status = "DONE"
        db.commit()

    except Exception as e:
        db.rollback()
        submission = db.query(StudentSubmission).filter(
            StudentSubmission.id == submission_id
        ).first()
        if submission:
            submission.status = "FAILED"
            submission.error_message = str(e)[:500]
            db.commit()
        print(f"[GRADING ERROR] {submission_id}: {str(e)}")
    finally:
        db.close()


@router.post("/submit/{assignment_id}", status_code=status.HTTP_202_ACCEPTED)
def submit_student_pdfs(
        assignment_id: UUID,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Upload multiple student answer sheet PDFs for an assignment.
    Each PDF filename becomes the student name (e.g. Ravi_Kumar.pdf → Ravi Kumar)."""

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    result = db.query(AssignmentResult).filter(
        AssignmentResult.assignment_id == assignment_id
    ).first()
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Assignment must be fully generated (DONE) before evaluating students"
        )

    created = []
    for file in files:
        file_path, student_name = StudentPDFService.save_student_pdf(file)

        submission = StudentSubmission(
            assignment_id=assignment_id,
            teacher_id=current_user.id,
            student_name=student_name,
            pdf_url=file_path,
            status="PENDING"
        )
        db.add(submission)
        db.flush()

        background_tasks.add_task(run_grading_pipeline, str(submission.id))
        created.append({
            "submission_id": str(submission.id),
            "student_name": student_name,
            "status": "PENDING"
        })

    db.commit()
    return {"submitted": len(created), "students": created}


@router.get("/{assignment_id}/status")
def get_evaluation_status(
        assignment_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Poll this to check how many students are done grading."""
    submissions = db.query(StudentSubmission).filter(
        StudentSubmission.assignment_id == assignment_id
    ).all()

    summary = {"PENDING": 0, "PROCESSING": 0, "DONE": 0, "FAILED": 0}
    for s in submissions:
        summary[s.status] = summary.get(s.status, 0) + 1

    return {
        "total": len(submissions),
        "summary": summary,
        "all_done": summary["PENDING"] == 0 and summary["PROCESSING"] == 0
    }


@router.get("/{assignment_id}/results")
def get_evaluation_results(
        assignment_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get all student results for an assignment."""
    submissions = db.query(StudentSubmission).filter(
        StudentSubmission.assignment_id == assignment_id,
        StudentSubmission.status == "DONE"
    ).all()

    submission_ids = [s.id for s in submissions]
    results = db.query(EvaluationResult).filter(
        EvaluationResult.submission_id.in_(submission_ids)
    ).all()

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()

    return {
        "assignment_id": str(assignment_id),
        "assignment_title": assignment.title if assignment else "",
        "total_students": len(results),
        "class_average": round(
            sum(r.percentage for r in results) / len(results), 1
        ) if results else 0,
        "results": [
            {
                "student_name": r.student_name,
                "scores_json": r.scores_json,
                "total_marks": r.total_marks,
                "max_marks": r.max_marks,
                "percentage": r.percentage,
            }
            for r in sorted(results, key=lambda x: x.total_marks, reverse=True)
        ]
    }


@router.get("/{assignment_id}/download-results")
def download_results_pdf(
        assignment_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Generate and download results PDF."""
    submissions = db.query(StudentSubmission).filter(
        StudentSubmission.assignment_id == assignment_id,
        StudentSubmission.status == "DONE"
    ).all()

    submission_ids = [s.id for s in submissions]
    results = db.query(EvaluationResult).filter(
        EvaluationResult.submission_id.in_(submission_ids)
    ).all()

    if not results:
        raise HTTPException(status_code=404, detail="No completed evaluations found")

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    assignment_result = db.query(AssignmentResult).filter(
        AssignmentResult.assignment_id == assignment_id
    ).first()

    max_marks = assignment_result.structured_json.get("total_marks", 100) if assignment_result else 100
    from src.models import School
    school = db.query(School).filter(School.id == current_user.school_id).first()

    results_data = [
        {
            "student_name": r.student_name,
            "scores_json": r.scores_json,
            "total_marks": r.total_marks,
            "max_marks": r.max_marks,
            "percentage": r.percentage,
        }
        for r in results
    ]

    pdf_path = ResultsPDFService.generate_results_pdf(
        results=results_data,
        assignment_title=assignment.title if assignment else "Assignment",
        school_name=school.name if school else "School",
        max_marks=max_marks,
    )

    safe_title = (assignment.title if assignment else "results").replace(" ", "_")
    return FileResponse(
        path=pdf_path,
        filename=f"{safe_title}_results.pdf",
        media_type="application/pdf"
    )