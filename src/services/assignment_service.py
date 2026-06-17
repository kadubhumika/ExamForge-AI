from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException, status
from src.models import Assignment, PaperTemplate, AssignmentResult, MyLibrary
from src.services.cache_service import CacheService
from src.services.ai_service import AIService
from src.schemas import AssignmentCreate, PaperTemplateCreate


class AssignmentService:
    @staticmethod
    def add_template(payload: PaperTemplateCreate, db: Session) -> PaperTemplate:
        scheme_data = [item.dict() for item in payload.structure_scheme]

        new_template = PaperTemplate(
            school_id=payload.school_id,
            class_id=payload.class_id,
            topic_name=payload.topic_name,
            structure_scheme=scheme_data
        )
        db.add(new_template)
        db.commit()
        db.refresh(new_template)

        CacheService.cache_prompt_template(str(new_template.id), scheme_data)
        return new_template

    @staticmethod
    def create_assignment_job(payload: AssignmentCreate, file_url: str, db: Session) -> Assignment:
        new_assignment = Assignment(
            teacher_id=payload.teacher_id,
            class_id=payload.class_id,
            template_id=payload.template_id,
            title=payload.title,
            file_url=file_url,
            instructions=payload.instructions,
            due_date=payload.due_date,
            status="PENDING"
        )
        db.add(new_assignment)
        db.flush()

        db.add(MyLibrary(user_id=payload.teacher_id, assignment_id=new_assignment.id, is_completed=False))
        db.commit()

        # 🌟 FIX BUG 6: Standardized placeholder to pass parameters safely to Celery via string lookups
        # celery_app.send_task("src.workers.celery_worker.generate_assignment_task", args=[str(new_assignment.id)])
        return new_assignment

    @staticmethod
    def construct_ai_generation_payload(assignment_id: str, extracted_text: str, db: Session) -> str:
        """🌟 FIX BUG 3 & Bug 9: Resolves runtime hazards by utilizing strict schema null checks."""
        # 🌟 Look up assignment records with defensive checks
        assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Requested Assignment context footprint not found")

        # 🌟 Try to read from cache layer first (Redis DB Failback loop)
        structure = CacheService.get_cached_template(str(assignment.template_id))

        if not structure and assignment.template_id:
            # 🌟 Cache miss fallback checking logic
            template = db.query(PaperTemplate).filter(PaperTemplate.id == assignment.template_id).first()
            if not template:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="Target Paper Template layout rules mapping missing")
            structure = template.structure_scheme
            # Heal cache topology dynamically
            CacheService.cache_prompt_template(str(template.id), structure)

        # Leverage the dedicated AI service to compile your prompt parameters cleanly
        return AIService.assemble_optimized_prompt(structure, extracted_text)

    @staticmethod
    def download_assignment_pdf(assignment_id: str, db: Session) -> str:
        # 🌟 FIX BUG 3: Explicit check to prevent unexpected None attribute failures
        result = db.query(AssignmentResult).filter(AssignmentResult.assignment_id == assignment_id).first()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Final downloadable asset sheet generation processing incomplete. Please try again shortly."
            )
        return result.pdf_url
