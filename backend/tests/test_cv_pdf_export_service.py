from pathlib import Path

from pypdf import PdfReader

from app.services.cv_pdf_export_service import CvPdfExportService


def test_write_pdf_creates_real_pdf_with_preview_content(tmp_path: Path) -> None:
    output_path = tmp_path / "draft-export.pdf"
    preview = {
        "title": "AI Engineer CV Draft",
        "sections": [
            {
                "heading": "Summary",
                "content": "Python, FastAPI, retrieval augmented generation, and LangGraph.",
            },
            {
                "heading": "Projects",
                "content": "Built an AI job agent that ranks roles against a CV.",
            },
        ],
        "edits": [
            {
                "requirement": "RAG experience",
                "proposed_edit": "Emphasize retrieval augmented generation project evidence.",
                "edit_kind": "wording_only",
                "risk_level": "low",
            }
        ],
        "recommendation": None,
    }

    CvPdfExportService().write_pdf(output_path, preview)

    assert output_path.read_bytes().startswith(b"%PDF")
    reader = PdfReader(str(output_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "AI Engineer CV Draft" in text
    assert "FastAPI" in text
    assert "RAG experience" in text
