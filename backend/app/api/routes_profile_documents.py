"""Profile document API routes."""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.routes_role_profiles import SessionDep
from app.api.schemas import ProfileDocumentListResponse, ProfileDocumentResponse
from app.db.models import RoleProfile
from app.services.profile_document_service import ProfileDocumentService


router = APIRouter(
    prefix="/role-profiles/{role_profile_id}/documents",
    tags=["profile-documents"],
)
profile_document_service = ProfileDocumentService()


async def _require_profile(session: SessionDep, role_profile_id: str) -> None:
    result = await session.execute(
        select(RoleProfile.id).where(RoleProfile.id == role_profile_id).limit(1)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="role profile not found",
        )


@router.post(
    "",
    response_model=ProfileDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_profile_document(
    role_profile_id: UUID,
    session: SessionDep,
    file: UploadFile = File(...),
) -> ProfileDocumentResponse:
    await _require_profile(session, str(role_profile_id))
    suffix = Path(file.filename or "").suffix or ".pdf"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)
        return await profile_document_service.create_document_from_pdf(
            session,
            role_profile_id=str(role_profile_id),
            source_path=tmp_path,
            original_filename=file.filename or "profile.pdf",
            mime_type=file.content_type or "",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    finally:
        if "tmp_path" in locals():
            tmp_path.unlink(missing_ok=True)


@router.get("", response_model=ProfileDocumentListResponse)
async def list_profile_documents(
    role_profile_id: UUID,
    session: SessionDep,
) -> ProfileDocumentListResponse:
    await _require_profile(session, str(role_profile_id))
    documents = await profile_document_service.list_documents(
        session,
        role_profile_id=str(role_profile_id),
    )
    return ProfileDocumentListResponse(documents=documents)
