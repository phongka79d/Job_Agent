from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api import routes_profile_documents
from app.api.routes_role_profiles import get_session
from app.core.config import settings
from app.db.models import RoleProfile
from app.main import app
from app.services.profile_document_service import ProfileDocumentService


class FakeExtractor:
    def extract_text(self, path):
        return "Python FastAPI internship experience. " * 120


class FakeEmbedder:
    async def embed_text(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]


class FakeVectorStore:
    async def upsert_profile_document_chunk(self, **kwargs) -> None:
        return None


@pytest_asyncio.fixture
async def role_profile(db_session):
    profile = RoleProfile(target_role="AI Engineer", skills="[]")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


@pytest_asyncio.fixture
async def client(db_session, monkeypatch, tmp_path):
    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(settings, "SQLITE_DB_PATH", str(tmp_path / "job_matching.db"))
    monkeypatch.setattr(
        routes_profile_documents,
        "profile_document_service",
        ProfileDocumentService(
            extractor=FakeExtractor(),
            embedder=FakeEmbedder(),
            vector_store=FakeVectorStore(),
        ),
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_profile_document_returns_sanitized_document(client, role_profile):
    response = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents",
        files={"file": ("cv.pdf", b"%PDF-test", "application/pdf")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["role_profile_id"] == role_profile.id
    assert data["original_filename"] == "cv.pdf"
    assert data["status"] == "ready"
    assert data["chunk_count"] >= 1
    assert "stored_path" not in data
    assert "content_hash" not in data


@pytest.mark.asyncio
async def test_list_profile_documents_filters_by_profile(client, role_profile):
    await client.post(
        f"/api/role-profiles/{role_profile.id}/documents",
        files={"file": ("cv.pdf", b"%PDF-test", "application/pdf")},
    )

    response = await client.get(f"/api/role-profiles/{role_profile.id}/documents")

    assert response.status_code == 200
    data = response.json()
    assert len(data["documents"]) == 1
    assert data["documents"][0]["role_profile_id"] == role_profile.id


@pytest.mark.asyncio
async def test_upload_profile_document_rejects_missing_profile(client):
    response = await client.post(
        f"/api/role-profiles/{uuid4()}/documents",
        files={"file": ("cv.pdf", b"%PDF-test", "application/pdf")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "role profile not found"


@pytest.mark.asyncio
async def test_upload_profile_document_rejects_non_pdf(client, role_profile):
    response = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents",
        files={"file": ("cv.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Only PDF uploads are supported"
