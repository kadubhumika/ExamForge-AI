import os
import base64
from typing import List, Tuple
from uuid import uuid4

from fastapi import UploadFile, HTTPException, status
from pdf2image import convert_from_bytes

from src.config import settings


class StudentPDFService:

    @staticmethod
    def save_student_pdf(file: UploadFile) -> Tuple[str, str]:
        """Saves uploaded student answer sheet PDF.
        Returns (file_path, student_name) where student_name is derived from filename."""
        content = file.file.read()

        if len(content) > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} exceeds {settings.MAX_UPLOAD_MB}MB limit"
            )

        # Derive student name from filename: "Ravi_Kumar.pdf" → "Ravi Kumar"
        raw_name = os.path.splitext(file.filename or "Unknown")[0]
        student_name = raw_name.replace("_", " ").replace("-", " ").strip()
        if not student_name:
            student_name = f"Student_{uuid4().hex[:6]}"

        filename = f"student_{uuid4()}.pdf"
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        file_path = os.path.join(settings.STORAGE_DIR, filename)

        with open(file_path, "wb") as f:
            f.write(content)

        return file_path, student_name

    @staticmethod
    def pdf_to_base64_images(file_path: str) -> List[str]:
        """Converts each PDF page to a base64-encoded JPEG.
        Gemini reads these as images — handles handwritten/scanned PDFs perfectly."""
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student PDF not found: {file_path}"
            )

        try:
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()

            # Convert each page to PIL Image at 150 DPI (good quality, reasonable size)
            pages = convert_from_bytes(pdf_bytes, dpi=150, fmt="jpeg")

            base64_images = []
            for page in pages:
                import io
                buffer = io.BytesIO()
                page.save(buffer, format="JPEG", quality=85)
                img_bytes = buffer.getvalue()
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                base64_images.append(b64)

            return base64_images

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not convert student PDF to images: {str(e)}"
            )