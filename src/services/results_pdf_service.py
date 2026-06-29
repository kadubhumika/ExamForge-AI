import os
from typing import List, Dict, Any
from uuid import uuid4

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from src.config import settings


class ResultsPDFService:

    @staticmethod
    def generate_results_pdf(
        results: List[Dict[str, Any]],
        assignment_title: str,
        school_name: str,
        max_marks: int,
    ) -> str:
        """Generates a results PDF with per-question marks for each student.
        Returns file path."""

        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        filename = f"results_{uuid4()}.pdf"
        filepath = os.path.join(settings.STORAGE_DIR, filename)

        doc = SimpleDocTemplate(
            filepath, pagesize=landscape(A4),
            topMargin=15 * mm, bottomMargin=15 * mm,
            leftMargin=15 * mm, rightMargin=15 * mm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "Title", parent=styles["Heading1"],
            alignment=TA_CENTER, fontSize=16, spaceAfter=4
        )
        sub_style = ParagraphStyle(
            "Sub", parent=styles["Normal"],
            alignment=TA_CENTER, fontSize=10,
            textColor=colors.HexColor("#4B5563")
        )
        cell_style = ParagraphStyle(
            "Cell", parent=styles["Normal"],
            fontSize=8, alignment=TA_LEFT
        )

        story = []
        story.append(Paragraph(school_name, title_style))
        story.append(Paragraph(f"Results: {assignment_title}", sub_style))
        story.append(Paragraph(f"Maximum Marks: {max_marks}", sub_style))
        story.append(Spacer(1, 8))

        if not results:
            story.append(Paragraph("No results available yet.", sub_style))
            doc.build(story)
            return filepath

        # Find all unique question numbers across all students
        all_questions = set()
        for r in results:
            for key in r.get("scores_json", {}).keys():
                all_questions.add(key)
        question_cols = sorted(all_questions, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)

        # Build table header
        header = ["Rank", "Student Name"] + question_cols + ["Total", "Marks", "%"]
        table_data = [header]

        # Sort by total marks descending
        sorted_results = sorted(results, key=lambda x: x.get("total_marks", 0), reverse=True)

        for rank, r in enumerate(sorted_results, 1):
            scores = r.get("scores_json", {})
            row = [
                str(rank),
                r.get("student_name", "Unknown"),
            ]
            for q in question_cols:
                q_data = scores.get(q, {})
                awarded = q_data.get("awarded", "-")
                max_q = q_data.get("max", "-")
                row.append(f"{awarded}/{max_q}")

            row.append(str(r.get("total_marks", 0)))
            row.append(str(r.get("max_marks", max_marks)))
            pct = r.get("percentage", 0)
            row.append(f"{pct}%")
            table_data.append(row)

        # Add class average row
        if sorted_results:
            avg_pct = sum(r.get("percentage", 0) for r in sorted_results) / len(sorted_results)
            avg_total = sum(r.get("total_marks", 0) for r in sorted_results) / len(sorted_results)
            avg_row = ["", "CLASS AVERAGE"] + [""] * len(question_cols)
            avg_row += [f"{avg_total:.1f}", str(max_marks), f"{avg_pct:.1f}%"]
            table_data.append(avg_row)

        col_widths = [12 * mm, 45 * mm] + [18 * mm] * len(question_cols) + [18 * mm, 18 * mm, 15 * mm]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A1A1A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),

            # Data rows
            ("FONTSIZE", (0, 1), (-1, -2), 8),
            ("ALIGN", (0, 1), (-1, -1), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F9FAFB")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),

            # Average row
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FFF3EA")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 8),

            # Highlight top 3
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#D1FAE5")),
            ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#E0F2FE")),
            ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#FEF3C7")),
        ]))

        story.append(table)
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f"Total Students: {len(sorted_results)} | "
            f"Highest: {sorted_results[0].get('total_marks', 0) if sorted_results else 0}/{max_marks} | "
            f"Class Average: {avg_pct:.1f}%",
            sub_style
        ))

        doc.build(story)
        return filepath