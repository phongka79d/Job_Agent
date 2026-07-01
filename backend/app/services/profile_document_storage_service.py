"""Safe file storage helpers for profile CV PDFs."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from app.core.config import settings


class ProfileDocumentStorageService:
    def __init__(self, *, root_dir: Path | None = None) -> None:
        self.root_dir = (
            root_dir
            if root_dir is not None
            else Path(settings.SQLITE_DB_PATH).resolve().parent / "uploads" / "profile_documents"
        ).resolve()

    def copy_pdf(
        self,
        source_path: Path,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str,
        directory_name: str,
    ) -> Path:
        storage_dir = self.root_dir / role_profile_id / document_id / directory_name
        storage_dir.mkdir(parents=True, exist_ok=True)
        stored_path = storage_dir / f"{version_id}.pdf"
        shutil.copyfile(source_path, stored_path)
        return self.resolve_stored_pdf(stored_path)

    def resolve_stored_pdf(self, stored_path: str | Path) -> Path:
        resolved = Path(stored_path).resolve()
        if not resolved.is_file():
            raise FileNotFoundError("Stored PDF file was not found")
        if self.root_dir not in resolved.parents:
            raise ValueError("Stored PDF path is outside storage root")
        if resolved.suffix.lower() != ".pdf":
            raise ValueError("Stored file is not a PDF")
        return resolved

    def delete_document_files(self, *, role_profile_id: str, document_id: str) -> None:
        document_dir = (self.root_dir / role_profile_id / document_id).resolve()
        if self.root_dir not in document_dir.parents:
            raise ValueError("Document directory is outside storage root")
        if document_dir.exists():
            shutil.rmtree(document_dir)

    @staticmethod
    def safe_download_filename(profile_label: str, document_label: str, version_label: str) -> str:
        document_label = document_label.removesuffix(".pdf")
        raw = f"{profile_label}_{document_label}_{version_label}"
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._-")
        safe = re.sub(r"_+", "_", safe)
        if not safe:
            safe = "profile_cv"
        return f"{safe[:140]}.pdf"
