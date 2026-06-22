import os
from typing import Dict, Any
from uuid import uuid4

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib import colors

from src.config import settings


class PDFGeneratorService:
    @staticmethod
    def generate_question_paper_pdf(
        structured_data: Dict[str, Any],
        school_name: str,
        assignment_title: str,
        due_date_str: str = "",
    ) -> str:
        """Renders the Gemini-generated structured JSON into a styled PDF with
        a question paper section followed by an answer key section.
        Returns the local file path of the generated PDF."""

        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        filename = f"assignment_output_{uuid4()}.pdf"
        filepath = os.path.join(settings.STORAGE_DIR, filename)

        doc = SimpleDocTemplate(
            filepath, pagesize=A4,
            topMargin=18 * mm, bottomMargin=18 * mm,
            leftMargin=18 * mm, rightMargin=18 * mm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "PaperTitle", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=16, spaceAfter=2
        )
        subtitle_style = ParagraphStyle(
            "PaperSubtitle", parent=styles["Normal"], alignment=TA_CENTER, fontSize=11, textColor=colors.HexColor("#4B5563")
        )
        meta_style = ParagraphStyle(
            "Meta", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#374151")
        )
        section_style = ParagraphStyle(
            "Section", parent=styles["Heading2"], alignment=TA_CENTER, fontSize=13, spaceBefore=14, spaceAfter=6
        )
        question_style = ParagraphStyle(
            "Question", parent=styles["Normal"], fontSize=10, spaceAfter=8, leading=14
        )
        answer_style = ParagraphStyle(
            "Answer", parent=styles["Normal"], fontSize=9.5, spaceAfter=8, leading=13, textColor=colors.HexColor("#1F2937")
        )

        story = []

        # --- Header ---
        story.append(Paragraph(school_name or "School Examination", title_style))
        story.append(Paragraph(f"Subject: {structured_data.get('subject', assignment_title)}", subtitle_style))
        if structured_data.get("class_level"):
            story.append(Paragraph(f"Class: {structured_data['class_level']}", subtitle_style))
        story.append(Spacer(1, 8))

        meta_table_data = [[
            Paragraph(f"<b>Time Allowed:</b> {structured_data.get('time_allowed_minutes', '—')} minutes", meta_style),
            Paragraph(f"<b>Maximum Marks:</b> {structured_data.get('total_marks', '—')}", meta_style),
        ]]
        meta_table = Table(meta_table_data, colWidths=[None, None])
        meta_table.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 6))

        story.append(Paragraph("Name: _______________________________   Roll No: ____________", meta_style))
        if due_date_str:
            story.append(Paragraph(f"Due Date: {due_date_str}", meta_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<i>All questions are compulsory unless stated otherwise.</i>", meta_style))

        # --- Question sections ---
        for section in structured_data.get("sections", []):
            story.append(Paragraph(section.get("section_name", "Section"), section_style))
            if section.get("section_instructions"):
                story.append(Paragraph(f"<i>{section['section_instructions']}</i>", meta_style))
                story.append(Spacer(1, 6))

            for q in section.get("questions", []):
                difficulty = q.get("difficulty", "")
                diff_tag = f"<b>[{difficulty}]</b> " if difficulty else ""
                q_line = (
                    f"{q.get('question_number', '')}. {diff_tag}"
                    f"{q.get('question_text', '')} "
                    f"<b>[{q.get('marks', '')} Marks]</b>"
                )
                story.append(Paragraph(q_line, question_style))

                options = q.get("options") or []
                if options:
                    opt_text = "&nbsp;&nbsp;&nbsp;".join(
                        f"({chr(97+i)}) {opt}" for i, opt in enumerate(options)
                    )
                    story.append(Paragraph(opt_text, meta_style))
                    story.append(Spacer(1, 6))

        story.append(Spacer(1, 10))
        story.append(Paragraph("— End of Question Paper —", subtitle_style))

        # --- Answer key (new page) ---
        story.append(PageBreak())
        story.append(Paragraph("Answer Key", title_style))
        story.append(Spacer(1, 10))

        for section in structured_data.get("sections", []):
            story.append(Paragraph(section.get("section_name", "Section"), section_style))
            for q in section.get("questions", []):
                ans_line = f"<b>{q.get('question_number', '')}.</b> {q.get('answer', 'N/A')}"
                story.append(Paragraph(ans_line, answer_style))

        doc.build(story)
        return filepath