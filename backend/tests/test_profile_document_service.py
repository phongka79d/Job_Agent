import pytest

from app.db.models import Base, ProfileDocument, ProfileDocumentChunk
from app.services import pdf_text_extraction_service
from app.services.pdf_text_extraction_service import (
    PdfTextExtractionError,
    PdfTextExtractionService,
)


def test_profile_document_models_are_registered_with_metadata():
    assert "profile_documents" in Base.metadata.tables
    assert "profile_document_chunks" in Base.metadata.tables
    assert ProfileDocument.__tablename__ == "profile_documents"
    assert ProfileDocumentChunk.__tablename__ == "profile_document_chunks"


def test_pdf_text_extractor_returns_text_from_text_based_pdf(monkeypatch, tmp_path):
    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakeReader:
        def __init__(self, path: str) -> None:
            self.path = path
            self.pages = [
                FakePage("Python FastAPI internship experience. " * 5),
                FakePage("Portfolio projects and certificates. " * 4),
            ]

    monkeypatch.setattr(pdf_text_extraction_service, "PdfReader", FakeReader)
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-test")

    text = PdfTextExtractionService().extract_text(pdf_path)

    assert "Python FastAPI internship experience" in text
    assert "Portfolio projects and certificates" in text


def test_pdf_text_extractor_rejects_pdf_with_no_extractable_text(monkeypatch, tmp_path):
    class FakePage:
        def extract_text(self) -> str:
            return ""

    class FakeReader:
        def __init__(self, path: str) -> None:
            self.path = path
            self.pages = [FakePage()]

    monkeypatch.setattr(pdf_text_extraction_service, "PdfReader", FakeReader)
    pdf_path = tmp_path / "blank.pdf"
    pdf_path.write_bytes(b"%PDF-test")

    with pytest.raises(PdfTextExtractionError, match="enough extractable text"):
        PdfTextExtractionService().extract_text(pdf_path)


def test_pdf_text_extractor_wraps_reader_failures(monkeypatch, tmp_path):
    class FailingReader:
        def __init__(self, path: str) -> None:
            raise ValueError("invalid pdf")

    monkeypatch.setattr(pdf_text_extraction_service, "PdfReader", FailingReader)
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.write_bytes(b"not a pdf")

    with pytest.raises(PdfTextExtractionError, match="Could not extract text from PDF"):
        PdfTextExtractionService().extract_text(pdf_path)
