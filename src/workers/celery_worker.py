import os
import json
import asyncio
import pdfplumber
from celery import Celery
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from google import genai
from google.genai import types

from src.config import settings
from src.database import SessionLocal
from src.models import Assignment, AssignmentResult

# 🌟 Core Celery Configurations optimized for unpredictable workloads
celery_app = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_ignore_result=True,  # Eliminates cache state overhead
    worker_prefetch_multiplier=1,  # Keeps processing lines balanced
    task_acks_late=True,  # Protects against server crashes
)


# Helper function to push asynchronous async websocket payloads from inside Celery
def broadcast_live_status(channel_id: str, status_text: str, progress_percent: int):
    import requests
    try:
        # Pushes message back to FastAPI gateway router port layout cleanly
        requests.post(
            f"http://localhost:8085/assignments/ws-notify",
            json={"channel_id": channel_id, "status": status_text, "progress": progress_percent}
        )
    except Exception:
        pass


@celery_app.task(name="src.workers.celery_worker.generate_assignment_task")
def generate_assignment_task(assignment_id: str, prompt_blueprint: str) -> str:
    db = SessionLocal()
    try:
        assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if not assignment:
            return "ERR_NOT_FOUND"

        # --- STEP 1: PARSE PDF DOCUMENT (pdfplumber) ---
        broadcast_live_status(str(assignment.id), "Extracting Chapter Content Text...", 25)
        extracted_raw_text = ""
        if os.path.exists(assignment.file_url):
            with pdfplumber.open(assignment.file_url) as pdf:
                for page in pdf.pages[:5]:  # Hard limit boundary checkpoint
                    extracted_raw_text += page.extract_text() or ""

        # --- STEP 2: RUN AI PIPELINE (Google Gemini API) ---
        broadcast_live_status(str(assignment.id), "Generating Custom Questions via Gemini...", 60)

        # Pull execution credentials dynamically from system context values
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "MOCK_KEY_FOR_COMPILING"))

        # Combine structural definitions directly with context extractions
        combined_context = f"{prompt_blueprint}\nSource Text: {extracted_raw_text[:3000]}"

        # Request strict schema json structure outputs back from the model engine
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=combined_context,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            ),
        )

        generated_json_str = response.text or "[]"
        parsed_questions = json.loads(generated_json_str)

        # --- STEP 3: GENERATE PDF SHEET ASSET (ReportLab) ---
        broadcast_live_status(str(assignment.id), "Compiling Downloadable PDF Exam Sheet...", 85)
        output_filename = f"compiled_{assignment.id}.pdf"
        output_dir = "storage/results"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)

        # Compile document canvas layout parameters
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [
            Paragraph(f"<b>Exam Title: {assignment.title}</b>", styles['Title']),
            Spacer(1, 20)
        ]

        # Iterate over generated json tokens and assemble structural text elements
        if isinstance(parsed_questions, list):
            for i, q in enumerate(parsed_questions, 1):
                q_text = f"Q{i}: {q.get('question', 'Template Question Text')} ({q.get('marks', 1)} Marks)"
                story.append(Paragraph(q_text, styles['Normal']))
                story.append(Spacer(1, 10))
        else:
            story.append(Paragraph("Structured Content generated below reference fields.", styles['Normal']))

        doc.build(story)

        # --- STEP 4: PERSIST TO POSTGRESQL & UPDATE STATUS ---
        assignment.status = "DONE"

        result_node = AssignmentResult(
            assignment_id=assignment.id,
            structured_json=parsed_questions,
            pdf_url=output_path,
            ai_model_used="gemini-2.5-flash"
        )
        db.add(result_node)
        db.commit()

        broadcast_live_status(str(assignment.id), "Assignment Complete! 🎉", 100)
        return "SUCCESS"

    except Exception as e:
        db.rollback()
        if assignment:
            assignment.status = "FAILED"
            db.commit()
        broadcast_live_status(assignment_id, f"Generation Failed: {str(e)}", -1)
        return f"FAILED: {str(e)}"
    finally:
        db.close()
