"""Render editable CV draft previews into real PDF files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


class CvPdfExportService:
    """Writes a clean supported-template PDF from a draft preview."""

    def write_pdf(self, output_path: Path, preview: dict[str, Any]) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        styles = getSampleStyleSheet()
        title = str(preview.get("title") or "CV draft").strip() or "CV draft"
        story: list[Any] = [Paragraph(title, styles["Title"]), Spacer(1, 0.18 * inch)]

        recommendation = preview.get("recommendation")
        if recommendation:
            story.extend(
                [
                    Paragraph("Template recommendation", styles["Heading2"]),
                    Paragraph(str(recommendation), styles["BodyText"]),
                    Spacer(1, 0.12 * inch),
                ]
            )

        for section in preview.get("sections", []):
            if not isinstance(section, dict):
                continue
            heading = str(section.get("heading") or "Section").strip() or "Section"
            content = str(section.get("content") or "").strip()
            if not content:
                continue
            story.append(Paragraph(heading, styles["Heading2"]))
            for paragraph in content.splitlines():
                clean = paragraph.strip()
                if clean:
                    story.append(Paragraph(clean, styles["BodyText"]))
            story.append(Spacer(1, 0.12 * inch))

        edits = [edit for edit in preview.get("edits", []) if isinstance(edit, dict)]
        if edits:
            story.append(Paragraph("Applied edit plan", styles["Heading2"]))
            for edit in edits:
                requirement = str(edit.get("requirement") or "Requirement").strip()
                proposed_edit = str(edit.get("proposed_edit") or "").strip()
                if proposed_edit:
                    story.append(Paragraph(f"{requirement}: {proposed_edit}", styles["BodyText"]))

        document = SimpleDocTemplate(
            str(output_path),
            pagesize=LETTER,
            rightMargin=0.72 * inch,
            leftMargin=0.72 * inch,
            topMargin=0.72 * inch,
            bottomMargin=0.72 * inch,
        )
        document.build(story)
        return output_path
