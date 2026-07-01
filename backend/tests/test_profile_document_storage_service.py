from pathlib import Path

import pytest


def test_storage_service_copies_pdf_under_profile_document_version(tmp_path):
    from app.services.profile_document_storage_service import ProfileDocumentStorageService

    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-real")
    service = ProfileDocumentStorageService(root_dir=tmp_path / "storage")

    stored = service.copy_pdf(
        source,
        role_profile_id="profile-1",
        document_id="doc-1",
        version_id="ver-1",
        directory_name="original",
    )

    assert stored.read_bytes() == b"%PDF-real"
    assert stored.name == "ver-1.pdf"
    assert "profile-1" in str(stored)
    assert "doc-1" in str(stored)
    assert "original" in str(stored)


def test_storage_service_rejects_paths_outside_root(tmp_path):
    from app.services.profile_document_storage_service import ProfileDocumentStorageService

    service = ProfileDocumentStorageService(root_dir=tmp_path / "storage")
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-real")

    with pytest.raises(ValueError, match="Stored PDF path is outside storage root"):
        service.resolve_stored_pdf(outside)


def test_storage_service_builds_safe_download_filename(tmp_path):
    from app.services.profile_document_storage_service import ProfileDocumentStorageService

    service = ProfileDocumentStorageService(root_dir=tmp_path / "storage")

    assert (
        service.safe_download_filename("AI Engineer / Intern", "My CV (final).pdf", "v1")
        == "AI_Engineer_Intern_My_CV_final_v1.pdf"
    )
