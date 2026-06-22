import json
from typing import List, Dict, Any

import google.generativeai as genai
from fastapi import HTTPException, status

from src.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

# JSON schema we force Gemini to follow, so the PDF generator can render it reliably.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "class_level": {"type": "string"},
        "time_allowed_minutes": {"type": "integer"},
        "total_marks": {"type": "integer"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section_name": {"type": "string"},
                    "section_instructions": {"type": "string"},
                    "questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question_number": {"type": "integer"},
                                "question_type": {"type": "string"},
                                "difficulty": {"type": "string"},
                                "question_text": {"type": "string"},
                                "marks": {"type": "integer"},
                                "options": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "answer": {"type": "string"}
                            },
                            "required": ["question_number", "question_type", "question_text", "marks", "answer"]
                        }
                    }
                },
                "required": ["section_name", "questions"]
            }
        }
    },
    "required": ["subject", "sections", "total_marks"]
}


class AIService:
    @staticmethod
    def assemble_optimized_prompt(
        structure: List[Dict[str, Any]],
        extracted_text: str,
        topic_name: str = "",
        instructions: str = "",
    ) -> str:
        if not structure:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Structure scheme context array empty")

        formatted_scheme = json.dumps(structure)
        # Bound the source text to keep prompt size and latency sane
        truncated_text = extracted_text[:12000] if extracted_text else ""

        source_block = (
            f'Source Chapter Text:\n"""\n{truncated_text}\n"""\n'
            if truncated_text
            else "No source chapter text was extractable from the uploaded file. "
                 "Generate questions based on the topic name and instructions below using your own subject knowledge.\n"
        )

        compiled_prompt = (
            "You are an expert school examiner creating a question paper.\n"
            f"Topic / Chapter: {topic_name or 'Not specified'}\n"
            f"Required structure (each item = question type, how many questions, marks per question): {formatted_scheme}\n"
            f"{source_block}"
            f"Additional instructions from the teacher: {instructions or 'None'}\n\n"
            "Generate a complete question paper matching the structure exactly "
            "(same question types, same counts per type, same marks per question). "
            "Vary difficulty across questions (Easy / Moderate / Challenging). "
            "For Multiple Choice Questions, include an 'options' array of 4 choices and put the correct option text in 'answer'. "
            "For all other types, leave 'options' as an empty array and put a model answer in 'answer'. "
            "Number questions sequentially within each section starting at 1. "
            "Respond ONLY with valid JSON matching the required schema — no markdown, no commentary."
        )
        return compiled_prompt

    @staticmethod
    def generate_paper(
        structure: List[Dict[str, Any]],
        extracted_text: str,
        topic_name: str = "",
        instructions: str = "",
    ) -> Dict[str, Any]:
        """Calls Gemini with JSON-mode enabled and returns parsed, validated structured data."""
        prompt = AIService.assemble_optimized_prompt(structure, extracted_text, topic_name, instructions)

        model = genai.GenerativeModel('gemini-2.5-flash')

        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                    temperature=0.7,
                ),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gemini generation request failed: {str(e)}"
            )

        raw_text = response.text
        try:
            parsed = json.loads(raw_text)
        except (json.JSONDecodeError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gemini returned malformed JSON: {str(e)}"
            )

        if not parsed.get("sections"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini response missing question sections"
            )

        return parsed