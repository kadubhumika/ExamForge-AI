import json
from typing import List, Dict, Any
from fastapi import HTTPException, status


class AIService:
    @staticmethod
    def assemble_optimized_prompt(structure: List[Dict[str, Any]], extracted_text: str) -> str:

        if not structure:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Structure scheme context array empty")

        formatted_scheme = json.dumps(structure)

        # Enforce smart systemic text token bounds truncation
        truncated_text = extracted_text[:5000]

        compiled_prompt = (
            f"System Instruction: You are an expert AI Examiner. Create an assignment matching this structural template schema: {formatted_scheme}.\n"
            f"Source Text Context:\n\"\"\"\n{truncated_text}\n\"\"\"\n"
            f"Output requirements: Generate questions matching the marks distribution limits cleanly in structured JSON formatting."
        )
        return compiled_prompt
