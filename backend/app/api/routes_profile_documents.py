"""Profile document API routes."""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.routes_role_profiles import SessionDep
from app.api.schemas import (
    ActivateCvVersionRequest,
    ActiveCvResponse,
    ProfileDocumentListResponse,
    ProfileDocumentResponse,
    ProfileDocumentVersionListResponse,
    ProfileDocumentVersionResponse,
)
from app.db.models import RoleProfile
from app.services.profile_document_service import ProfileDocumentFileInfo, ProfileDocumentService


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


def _pdf_file_response(file_info: ProfileDocumentFileInfo, *, as_attachment: bool) -> FileResponse:
    filename = file_info.download_filename if as_attachment else file_info.inline_filename
    disposition = "attachment" if as_attachment else "inline"
    return FileResponse(
        path=file_info.path,
        media_type=file_info.media_type,
        filename=filename,
        content_disposition_type=disposition,
    )


@router.get("/{document_id}/file")
async def view_profile_document(
    role_profile_id: UUID,
    document_id: UUID,
    session: SessionDep,
) -> FileResponse:
    await _require_profile(session, str(role_profile_id))
    try:
        file_info = await profile_document_service.get_document_file(
            session,
            role_profile_id=str(role_profile_id),
            document_id=str(document_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _pdf_file_response(file_info, as_attachment=False)


@router.get("/{document_id}/download")
async def download_profile_document(
    role_profile_id: UUID,
    document_id: UUID,
    session: SessionDep,
) -> FileResponse:
    await _require_profile(session, str(role_profile_id))
    try:
        file_info = await profile_document_service.get_document_file(
            session,
            role_profile_id=str(role_profile_id),
            document_id=str(document_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _pdf_file_response(file_info, as_attachment=True)


@router.get("/{document_id}/versions/{version_id}/file")
async def view_profile_document_version(
    role_profile_id: UUID,
    document_id: UUID,
    version_id: UUID,
    session: SessionDep,
) -> FileResponse:
    await _require_profile(session, str(role_profile_id))
    try:
        file_info = await profile_document_service.get_document_file(
            session,
            role_profile_id=str(role_profile_id),
            document_id=str(document_id),
            version_id=str(version_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _pdf_file_response(file_info, as_attachment=False)


@router.get("/{document_id}/versions/{version_id}/download")
async def download_profile_document_version(
    role_profile_id: UUID,
    document_id: UUID,
    version_id: UUID,
    session: SessionDep,
) -> FileResponse:
    await _require_profile(session, str(role_profile_id))
    try:
        file_info = await profile_document_service.get_document_file(
            session,
            role_profile_id=str(role_profile_id),
            document_id=str(document_id),
            version_id=str(version_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _pdf_file_response(file_info, as_attachment=True)


@router.get("/{document_id}/versions", response_model=ProfileDocumentVersionListResponse)
async def list_profile_document_versions(
    role_profile_id: UUID,
    document_id: UUID,
    session: SessionDep,
) -> ProfileDocumentVersionListResponse:
    await _require_profile(session, str(role_profile_id))
    versions = await profile_document_service.list_versions(
        session,
        role_profile_id=str(role_profile_id),
        document_id=str(document_id),
    )
    return ProfileDocumentVersionListResponse(versions=versions)


@router.post("/{document_id}/versions/{version_id}/activate", response_model=ProfileDocumentVersionResponse)
async def activate_profile_cv_version(
    role_profile_id: UUID,
    document_id: UUID,
    version_id: UUID,
    request: ActivateCvVersionRequest,
    session: SessionDep,
):
    await _require_profile(session, str(role_profile_id))
    if not request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setting the active CV requires confirmation",
        )
    try:
        return await profile_document_service.set_active_version(
            session,
            role_profile_id=str(role_profile_id),
            document_id=str(document_id),
            version_id=str(version_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile_document(
    role_profile_id: UUID,
    document_id: UUID,
    session: SessionDep,
    clear_active: bool = Query(False),
) -> None:
    await _require_profile(session, str(role_profile_id))
    try:
        await profile_document_service.delete_document(
            session,
            role_profile_id=str(role_profile_id),
            document_id=str(document_id),
            clear_active=clear_active,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


active_cv_router = APIRouter(
    prefix="/role-profiles/{role_profile_id}/active-cv",
    tags=["profile-documents"],
)


@active_cv_router.get("", response_model=ActiveCvResponse)
async def get_active_cv(
    role_profile_id: UUID,
    session: SessionDep,
) -> ActiveCvResponse:
    await _require_profile(session, str(role_profile_id))
    document, version = await profile_document_service.get_active_cv(
        session,
        role_profile_id=str(role_profile_id),
    )
    return ActiveCvResponse(document=document, version=version)


@active_cv_router.get("/file")
async def view_active_cv(
    role_profile_id: UUID,
    session: SessionDep,
) -> FileResponse:
    await _require_profile(session, str(role_profile_id))
    document, version = await profile_document_service.get_active_cv(
        session,
        role_profile_id=str(role_profile_id),
    )
    if document is None or version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="active CV not found")
    file_info = await profile_document_service.get_document_file(
        session,
        role_profile_id=str(role_profile_id),
        document_id=document.id,
        version_id=version.id,
    )
    return _pdf_file_response(file_info, as_attachment=False)


@active_cv_router.get("/download")
async def download_active_cv(
    role_profile_id: UUID,
    session: SessionDep,
) -> FileResponse:
    await _require_profile(session, str(role_profile_id))
    document, version = await profile_document_service.get_active_cv(
        session,
        role_profile_id=str(role_profile_id),
    )
    if document is None or version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="active CV not found")
    file_info = await profile_document_service.get_document_file(
        session,
        role_profile_id=str(role_profile_id),
        document_id=document.id,
        version_id=version.id,
    )
    return _pdf_file_response(file_info, as_attachment=True)
