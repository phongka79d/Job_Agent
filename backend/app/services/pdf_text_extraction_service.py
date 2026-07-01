"""Text-only PDF extraction for profile documents."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


class PdfTextExtractionError(Exception):
    """Raised when a PDF cannot provide enough extractable text."""


class PdfTextExtractionService:
    def extract_text(self, path: Path) -> str:
        try:
            reader = PdfReader(str(path))
            parts = [(page.extract_text() or "").strip() for page in reader.pages]
        except Exception as exc:
            raise PdfTextExtractionError("Could not extract text from PDF") from exc

        text = "\n\n".join(part for part in parts if part)
        if len(text.strip()) < 200:
            raise PdfTextExtractionError("PDF does not contain enough extractable text")
        return text.strip()
