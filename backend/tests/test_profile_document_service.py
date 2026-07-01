import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.models import Base, ProfileDocument, ProfileDocumentChunk
from app.services import pdf_text_extraction_service
from app.services.pdf_text_extraction_service import (
    PdfTextExtractionError,
    PdfTextExtractionService,
)
from app.services.profile_document_service import ProfileDocumentService


class FakeExtractor:
    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.text = text or ("Python FastAPI internship experience. " * 120)
        self.error = error

    def extract_text(self, path):
        if self.error:
            raise self.error
        return self.text


class FakeEmbedder:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def embed_text(self, text: str) -> list[float]:
        self.calls.append(text)
        return [1.0, 0.0, 0.0]


class FakeVectorStore:
    def __init__(self) -> None:
        self.upserts: list[dict[str, object]] = []

    async def upsert_profile_document_chunk(self, **kwargs) -> None:
        self.upserts.append(kwargs)


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


@pytest.mark.asyncio
async def test_create_document_from_pdf_extracts_chunks_and_indexes_vectors(
    db_session,
    test_role_profile,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "SQLITE_DB_PATH", str(tmp_path / "job_matching.db"))
    source_path = tmp_path / "cv.pdf"
    source_path.write_bytes(b"%PDF-test")
    embedder = FakeEmbedder()
    vector_store = FakeVectorStore()
    service = ProfileDocumentService(
        extractor=FakeExtractor(),
        embedder=embedder,
        vector_store=vector_store,
    )

    document = await service.create_document_from_pdf(
        db_session,
        role_profile_id=test_role_profile.id,
        source_path=source_path,
        original_filename="cv.pdf",
        mime_type="application/pdf",
    )

    assert document.status == "ready"
    assert document.original_filename == "cv.pdf"
    assert document.stored_path.endswith(".pdf")
    assert document.chunk_count >= 1
    assert document.extracted_text_chars > 200
    chunks = (
        await db_session.execute(
            select(ProfileDocumentChunk)
            .where(ProfileDocumentChunk.document_id == document.id)
            .order_by(ProfileDocumentChunk.chunk_index)
        )
    ).scalars().all()
    assert len(chunks) == document.chunk_count
    assert len(embedder.calls) == document.chunk_count
    assert len(vector_store.upserts) == document.chunk_count
    assert vector_store.upserts[0]["role_profile_id"] == test_role_profile.id
    assert vector_store.upserts[0]["document_id"] == document.id
    assert vector_store.upserts[0]["chunk_id"] == chunks[0].id


@pytest.mark.asyncio
async def test_create_document_from_pdf_rejects_non_pdf(db_session, test_role_profile, tmp_path):
    source_path = tmp_path / "cv.txt"
    source_path.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(ValueError, match="Only PDF uploads are supported"):
        await ProfileDocumentService(
            extractor=FakeExtractor(),
            embedder=FakeEmbedder(),
            vector_store=FakeVectorStore(),
        ).create_document_from_pdf(
            db_session,
            role_profile_id=test_role_profile.id,
            source_path=source_path,
            original_filename="cv.txt",
            mime_type="text/plain",
        )


@pytest.mark.asyncio
async def test_create_document_from_pdf_marks_extraction_failure(
    db_session,
    test_role_profile,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "SQLITE_DB_PATH", str(tmp_path / "job_matching.db"))
    source_path = tmp_path / "blank.pdf"
    source_path.write_bytes(b"%PDF-test")
    service = ProfileDocumentService(
        extractor=FakeExtractor(error=PdfTextExtractionError("PDF does not contain enough extractable text")),
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
    )

    with pytest.raises(ValueError, match="enough extractable text"):
        await service.create_document_from_pdf(
            db_session,
            role_profile_id=test_role_profile.id,
            source_path=source_path,
            original_filename="blank.pdf",
            mime_type="application/pdf",
        )

    documents = (
        await db_session.execute(select(ProfileDocument).where(ProfileDocument.status == "failed"))
    ).scalars().all()
    assert len(documents) == 1
    assert "extractable text" in (documents[0].error_reason or "")
