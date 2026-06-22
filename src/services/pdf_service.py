import os
from fastapi import UploadFile, HTTPException, status
from uuid import uuid4
from pypdf import PdfReader

from src.config import settings


class PDFService:
    @staticmethod
    def upload_document(file: UploadFile) -> str:
        """Validates boundaries and handles local multi-part streaming paths."""
        max_size = settings.MAX_UPLOAD_MB * 1024 * 1024
        content = file.file.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds {settings.MAX_UPLOAD_MB}MB limit"
            )

        file.file.seek(0)
        file_extension = os.path.splitext(file.filename)[1].lower() if file.filename else ".pdf"
        if file_extension not in [".pdf", ".png", ".jpg", ".jpeg"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Allowed: .pdf, .png, .jpg, .jpeg"
            )

        filename = f"{uuid4()}{file_extension}"

        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        local_path = os.path.join(settings.STORAGE_DIR, filename)
        with open(local_path, "wb") as f:
            f.write(content)

        return local_path

    @staticmethod
    def extract_text_tokens(file_path: str) -> str:
        """Reads document streams and pulls out clean text for the AI prompt.
        PDFs: real text extraction via pypdf.
        Images (.png/.jpg): no OCR pipeline wired up yet, so we return an empty
        string and let the caller fall back to relying on instructions/template alone."""
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source document not found on disk"
            )

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            try:
                reader = PdfReader(file_path)
                text_parts = []
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)
                full_text = "\n".join(text_parts)
                # Clean up excessive blank lines
                cleaned = "\n".join(line.strip() for line in full_text.splitlines() if line.strip())
                return cleaned
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not extract text from PDF: {str(e)}"
                )
        else:
            # Image upload — no OCR configured. Returning empty text means the
            # AI prompt will rely on the topic/title/instructions the teacher typed.
            return ""