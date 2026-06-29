import json
from typing import Dict, Any, List

import google.generativeai as genai
from fastapi import HTTPException, status

from src.config import settings
from src.services.student_pdf_service import StudentPDFService

genai.configure(api_key=settings.GEMINI_API_KEY)

GRADING_SCHEMA = {
    "type": "object",
    "properties": {
        "student_name": {"type": "string"},
        "grades": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_number": {"type": "integer"},
                    "question_text": {"type": "string"},
                    "student_answer": {"type": "string"},
                    "correct_answer": {"type": "string"},
                    "marks_awarded": {"type": "integer"},
                    "max_marks": {"type": "integer"},
                    "reason": {"type": "string"}
                },
                "required": ["question_number", "marks_awarded", "max_marks", "reason"]
            }
        },
        "total_marks_awarded": {"type": "integer"},
        "total_max_marks": {"type": "integer"}
    },
    "required": ["grades", "total_marks_awarded", "total_max_marks"]
}


class EvaluationService:

    @staticmethod
    def grade_student_submission(
        student_pdf_path: str,
        student_name: str,
        assignment_structured_json: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Grades a student's answer sheet against the assignment's answer key.
        Uses Gemini multimodal — sends PDF pages as images so handwriting works too."""

        # Convert PDF pages to base64 images
        base64_images = StudentPDFService.pdf_to_base64_images(student_pdf_path)

        # Build the question + answer key summary for the prompt
        qa_summary = []
        q_num = 1
        for section in assignment_structured_json.get("sections", []):
            for q in section.get("questions", []):
                qa_summary.append(
                    f"Q{q_num} [{q.get('marks', 1)} marks]: {q.get('question_text', '')}\n"
                    f"Correct Answer: {q.get('answer', '')}"
                )
                q_num += 1

        qa_text = "\n\n".join(qa_summary)

        prompt = f"""You are a school examiner grading a student's answer sheet.

Student Name: {student_name}

QUESTION PAPER WITH ANSWER KEY:
{qa_text}

INSTRUCTIONS:
- The attached images show this student's answer sheet (may be handwritten or typed)
- Read each answer carefully from the images
- Award marks fairly based on conceptual understanding, not just exact wording
- For MCQs: full marks if correct, 0 if wrong
- For short/long answers: partial marks allowed based on how much of the answer is correct
- Return ONLY valid JSON matching the required schema, no extra text
"""

        # Build content parts: text prompt + all page images
        content_parts = [prompt]
        for b64_img in base64_images:
            content_parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": b64_img
                }
            })

        model = genai.GenerativeModel(settings.GEMINI_MODEL)

        try:
            response = model.generate_content(
                content_parts,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=GRADING_SCHEMA,
                    temperature=0.2,  # low temp for consistent grading
                ),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gemini grading failed: {str(e)}"
            )

        try:
            result = json.loads(response.text)
        except (json.JSONDecodeError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gemini returned malformed JSON: {str(e)}"
            )

        return result

    @staticmethod
    def build_scores_json(grading_result: Dict[str, Any]) -> Dict[str, Any]:
        """Converts Gemini grading output into our scores_json storage format."""
        scores = {}
        for grade in grading_result.get("grades", []):
            q_num = grade.get("question_number", 0)
            scores[f"Q{q_num}"] = {
                "awarded": grade.get("marks_awarded", 0),
                "max": grade.get("max_marks", 0),
                "reason": grade.get("reason", ""),
                "student_answer": grade.get("student_answer", ""),
                "correct_answer": grade.get("correct_answer", "")
            }
        return scores