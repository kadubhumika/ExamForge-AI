from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from src.models import Assignment, PaperTemplate, AssignmentResult, MyLibrary, School
from src.services.cache_service import CacheService
from src.services.ai_service import AIService
from src.services.pdf_service import PDFService
from src.services.pdf_generator_service import PDFGeneratorService
from src.services.notification_service import NotificationService
from src.schemas import AssignmentCreate, PaperTemplateCreate
from src.database import SessionLocal


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
        db.refresh(new_assignment)

        NotificationService.assignment_created(db, payload.teacher_id, new_assignment.id, payload.title)

        return new_assignment

    @staticmethod
    def get_structure_for_assignment(assignment: Assignment, db: Session) -> List[Dict[str, Any]]:
        """Looks up the question structure:
        1. From a saved PaperTemplate (if template_id is set)
        2. From the inline structure_scheme cached at upload time under assignment:{id}
        3. Falls back to a sane default if neither exists."""
        if assignment.template_id:
            structure = CacheService.get_cached_template(str(assignment.template_id))
            if not structure:
                template = db.query(PaperTemplate).filter(PaperTemplate.id == assignment.template_id).first()
                if template:
                    structure = template.structure_scheme
                    CacheService.cache_prompt_template(str(template.id), structure)
            if structure:
                return structure

        # Check for inline structure cached during upload (no saved template)
        inline_structure = CacheService.get_cached_template(f"assignment:{assignment.id}")
        if inline_structure:
            return inline_structure

        # Fallback default structure if no template was attached
        return [{"type": "Short Answer Questions", "count": 10, "marks_per": 2}]

    @classmethod
    def run_generation_pipeline(cls, assignment_id: str):
        """The actual background job: extract text from the uploaded file, call Gemini,
        render the result into a PDF, save it, and notify the teacher.
        Runs in its own DB session since BackgroundTasks executes after the request's
        session may already be closed."""
        db: Session = SessionLocal()
        try:
            assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
            if not assignment:
                return

            assignment.status = "PROCESSING"
            db.commit()

            structure = cls.get_structure_for_assignment(assignment, db)

            extracted_text = PDFService.extract_text_tokens(assignment.file_url)

            structured_data = AIService.generate_paper(
                structure=structure,
                extracted_text=extracted_text,
                topic_name=assignment.title,
                instructions=assignment.instructions or "",
            )

            school = db.query(School).filter(School.id == assignment.teacher.school_id).first() if assignment.teacher else None

            pdf_path = PDFGeneratorService.generate_question_paper_pdf(
                structured_data=structured_data,
                school_name=school.name if school else "School",
                assignment_title=assignment.title,
                due_date_str=assignment.due_date.strftime("%d-%m-%Y") if assignment.due_date else "",
            )

            existing_result = db.query(AssignmentResult).filter(AssignmentResult.assignment_id == assignment.id).first()
            if existing_result:
                existing_result.structured_json = structured_data
                existing_result.pdf_url = pdf_path
            else:
                db.add(AssignmentResult(
                    assignment_id=assignment.id,
                    structured_json=structured_data,
                    pdf_url=pdf_path,
                ))

            assignment.status = "DONE"
            db.commit()

            NotificationService.assignment_ready(db, assignment.teacher_id, assignment.id, assignment.title)

        except Exception as e:
            db.rollback()
            assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
            if assignment:
                assignment.status = "FAILED"
                assignment.error_message = str(e)[:500]
                db.commit()
                NotificationService.assignment_failed(db, assignment.teacher_id, assignment.id, assignment.title, str(e)[:200])
            print(f"[GENERATION ERROR] Assignment {assignment_id} failed: {str(e)}")
        finally:
            db.close()

    @staticmethod
    def download_assignment_pdf(assignment_id: str, db: Session) -> str:
        result = db.query(AssignmentResult).filter(AssignmentResult.assignment_id == assignment_id).first()
        if not result:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Final downloadable asset is not ready yet. Please try again shortly."
            )
        return result.pdf_url