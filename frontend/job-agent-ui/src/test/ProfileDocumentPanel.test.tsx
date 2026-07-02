import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiClientError } from "../api/client";
import {
  activateProfileDocumentVersion,
  exportCvDraftToPdf,
  getProfileCvTemplate,
  listCvDrafts,
  listCvSuggestions,
  listProfileDocumentVersions,
  listProfileDocuments,
  previewCvDraft,
  saveProfileCvTemplate,
  uploadProfileDocument,
} from "../api/profileDocumentsClient";
import ProfileDocumentPanel from "../components/profile/ProfileDocumentPanel";
import type { CvDraft, ProfileDocument, ProfileDocumentVersion } from "../types/profileDocuments";

vi.mock("../api/profileDocumentsClient", () => ({
  activateProfileDocumentVersion: vi.fn(),
  deleteProfileDocument: vi.fn(),
  exportCvDraftToPdf: vi.fn(),
  getProfileDocumentDownloadUrl: vi.fn(
    (profileId, documentId) => `/api/role-profiles/${profileId}/documents/${documentId}/download`
  ),
  getProfileDocumentFileUrl: vi.fn(
    (profileId, documentId) => `/api/role-profiles/${profileId}/documents/${documentId}/file`
  ),
  getProfileDocumentVersionDownloadUrl: vi.fn(
    (profileId, documentId, versionId) =>
      `/api/role-profiles/${profileId}/documents/${documentId}/versions/${versionId}/download`
  ),
  getProfileDocumentVersionFileUrl: vi.fn(
    (profileId, documentId, versionId) =>
      `/api/role-profiles/${profileId}/documents/${documentId}/versions/${versionId}/file`
  ),
  listCvDrafts: vi.fn(),
  listCvSuggestions: vi.fn(),
  listProfileDocumentVersions: vi.fn(),
  listProfileDocuments: vi.fn(),
  previewCvDraft: vi.fn(),
  getProfileCvTemplate: vi.fn(),
  saveProfileCvTemplate: vi.fn(),
  uploadProfileDocument: vi.fn(),
}));

const readyDocument: ProfileDocument = {
  id: "doc-1",
  role_profile_id: "profile-1",
  original_filename: "cv.pdf",
  document_kind: "cv",
  active_version_id: "version-1",
  is_active: true,
  mime_type: "application/pdf",
  file_size_bytes: 1000,
  extracted_text_chars: 500,
  chunk_count: 2,
  status: "ready",
  error_reason: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const originalVersion: ProfileDocumentVersion = {
  id: "version-1",
  document_id: "doc-1",
  role_profile_id: "profile-1",
  version_number: 1,
  source_type: "original_upload",
  display_name: "Original upload",
  filename: "cv.pdf",
  mime_type: "application/pdf",
  file_size_bytes: 1000,
  extracted_text_chars: 500,
  chunk_count: 2,
  extraction_status: "ready",
  structure_status: "reliable",
  structure_confidence: 0.9,
  error_reason: null,
  created_by: "user",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const exportedVersion: ProfileDocumentVersion = {
  ...originalVersion,
  id: "version-2",
  version_number: 2,
  source_type: "exported_draft",
  display_name: "Exported draft v2",
  filename: "cv-draft-v2.pdf",
  created_by: "ai",
};

const draft: CvDraft = {
  id: "draft-1",
  role_profile_id: "profile-1",
  document_id: "doc-1",
  base_version_id: "version-1",
  status: "draft",
  title: "Draft",
  structure_status_at_creation: "reliable",
  created_by: "ai",
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};

describe("ProfileDocumentPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getProfileCvTemplate).mockRejectedValue(
      new ApiClientError("CV template not found", 404)
    );
  });

  it("loads documents for the active profile", async () => {
    vi.mocked(listProfileDocuments).mockResolvedValue([readyDocument]);

    render(<ProfileDocumentPanel activeProfileId="profile-1" />);

    await waitFor(() => {
      expect(listProfileDocuments).toHaveBeenCalledWith("profile-1");
      expect(screen.getByText("cv.pdf")).toBeInTheDocument();
      expect(screen.getByText("ready")).toBeInTheDocument();
    });
  });

  it("does not load documents without an active profile", () => {
    render(<ProfileDocumentPanel activeProfileId={null} />);

    expect(screen.getByText("Select a role profile to manage PDFs.")).toBeInTheDocument();
    expect(listProfileDocuments).not.toHaveBeenCalled();
  });

  it("uploads a pdf and refreshes the list", async () => {
    vi.mocked(listProfileDocuments)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([readyDocument]);
    vi.mocked(uploadProfileDocument).mockResolvedValue(readyDocument);
    const file = new File(["%PDF-test"], "cv.pdf", { type: "application/pdf" });

    render(<ProfileDocumentPanel activeProfileId="profile-1" />);

    await waitFor(() => {
      expect(listProfileDocuments).toHaveBeenCalledTimes(1);
    });
    fireEvent.change(screen.getByTestId("profile-document-file-input"), {
      target: { files: [file] },
    });

    await waitFor(() => {
      expect(uploadProfileDocument).toHaveBeenCalledWith("profile-1", file);
      expect(listProfileDocuments).toHaveBeenCalledTimes(2);
      expect(screen.getByText("cv.pdf")).toBeInTheDocument();
    });
  });

  it("shows upload errors without clearing existing documents", async () => {
    vi.mocked(listProfileDocuments).mockResolvedValue([readyDocument]);
    vi.mocked(uploadProfileDocument).mockRejectedValue(new Error("Only PDF uploads are supported"));
    const file = new File(["plain text"], "cv.txt", { type: "text/plain" });

    render(<ProfileDocumentPanel activeProfileId="profile-1" />);

    await waitFor(() => {
      expect(screen.getByText("cv.pdf")).toBeInTheDocument();
    });
    fireEvent.change(screen.getByTestId("profile-document-file-input"), {
      target: { files: [file] },
    });

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Only PDF uploads are supported");
      expect(screen.getByText("cv.pdf")).toBeInTheDocument();
    });
  });

  it("renders view download active and delete controls", async () => {
    vi.mocked(listProfileDocuments).mockResolvedValue([readyDocument]);

    render(<ProfileDocumentPanel activeProfileId="profile-1" />);

    await waitFor(() => {
      expect(screen.getByText("Active CV")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /view cv.pdf/i })).toHaveAttribute(
        "href",
        "/api/role-profiles/profile-1/documents/doc-1/file"
      );
      expect(screen.getByRole("link", { name: /download cv.pdf/i })).toHaveAttribute(
        "href",
        "/api/role-profiles/profile-1/documents/doc-1/download"
      );
      expect(screen.getByRole("button", { name: /delete cv.pdf/i })).toBeInTheDocument();
    });
  });

  it("activates a non-active ready cv", async () => {
    const inactiveDocument = { ...readyDocument, is_active: false };
    vi.mocked(listProfileDocuments)
      .mockResolvedValueOnce([inactiveDocument])
      .mockResolvedValueOnce([{ ...inactiveDocument, is_active: true }]);
    vi.mocked(activateProfileDocumentVersion).mockResolvedValue({
      id: "version-1",
    } as never);

    render(<ProfileDocumentPanel activeProfileId="profile-1" />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /set cv.pdf active/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /set cv.pdf active/i }));

    await waitFor(() => {
      expect(activateProfileDocumentVersion).toHaveBeenCalledWith("profile-1", "doc-1", "version-1");
      expect(listProfileDocuments).toHaveBeenCalledTimes(2);
    });
  });

  it("shows cv suggestions and drafts for the active document", async () => {
    vi.mocked(listProfileDocuments).mockResolvedValue([readyDocument]);
    vi.mocked(listCvSuggestions).mockResolvedValue([
      {
        id: "suggestion-1",
        role_profile_id: "profile-1",
        document_id: "doc-1",
        version_id: "version-1",
        job_id: null,
        requirement: "FastAPI",
        current_cv_evidence: "Evidence",
        missing_or_weak_evidence: "Weak wording",
        proposed_edit: "Improve wording",
        edit_kind: "wording_only",
        risk_level: "low",
        requires_confirmation: true,
        status: "suggested",
        created_at: "2026-07-01T00:00:00Z",
        updated_at: "2026-07-01T00:00:00Z",
      },
    ]);
    vi.mocked(listCvDrafts).mockResolvedValue([
      {
        id: "draft-1",
        role_profile_id: "profile-1",
        document_id: "doc-1",
        base_version_id: "version-1",
        status: "draft",
        title: "Draft",
        structure_status_at_creation: "reliable",
        created_by: "ai",
        created_at: "2026-07-01T00:00:00Z",
        updated_at: "2026-07-01T00:00:00Z",
      },
    ]);
    vi.mocked(previewCvDraft).mockResolvedValue({
      draft_id: "draft-1",
      title: "Draft preview",
      status: "draft",
      structure_status: "reliable",
      recommendation: null,
      sections: [],
      edits: [{ requirement: "FastAPI", proposed_edit: "Improve wording" }],
    });

    render(<ProfileDocumentPanel activeProfileId="profile-1" />);

    await waitFor(() => {
      expect(screen.getByText("FastAPI")).toBeInTheDocument();
    });
    expect(screen.getByRole("article", { name: /FastAPI suggestion/i })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: /CV suggestions/i })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: /CV drafts/i })).toBeInTheDocument();
    expect(screen.getByText("wording_only - low")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("renders version history with exported version controls", async () => {
    vi.mocked(listProfileDocuments).mockResolvedValue([readyDocument]);
    vi.mocked(listProfileDocumentVersions).mockResolvedValue([originalVersion, exportedVersion]);
    vi.mocked(listCvSuggestions).mockResolvedValue([]);
    vi.mocked(listCvDrafts).mockResolvedValue([]);

    render(<ProfileDocumentPanel activeProfileId="profile-1" />);

    expect(await screen.findByText("Version history")).toBeInTheDocument();
    expect(screen.getByText("Exported draft v2")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view exported draft v2/i })).toHaveAttribute(
      "href",
      expect.stringContaining("/versions/version-2/file")
    );
  });

  it("exports a draft and refreshes version history", async () => {
    window.confirm = vi.fn(() => true);
    vi.mocked(listProfileDocuments).mockResolvedValue([readyDocument]);
    vi.mocked(listProfileDocumentVersions).mockResolvedValue([originalVersion]);
    vi.mocked(listCvSuggestions).mockResolvedValue([]);
    vi.mocked(listCvDrafts).mockResolvedValue([draft]);
    vi.mocked(exportCvDraftToPdf).mockResolvedValue(exportedVersion);

    render(<ProfileDocumentPanel activeProfileId="profile-1" />);
    fireEvent.click(await screen.findByRole("button", { name: /export .* PDF/i }));

    expect(exportCvDraftToPdf).toHaveBeenCalledWith("profile-1", readyDocument.id, draft.id, { confirmed: true });
  });

  it("loads and saves a profile CV LaTeX template", async () => {
    vi.mocked(listProfileDocuments).mockResolvedValue([]);
    vi.mocked(listCvSuggestions).mockResolvedValue([]);
    vi.mocked(listCvDrafts).mockResolvedValue([]);
    vi.mocked(listProfileDocumentVersions).mockResolvedValue([]);
    vi.mocked(getProfileCvTemplate).mockResolvedValue({
      id: "template-1",
      role_profile_id: "profile-1",
      name: "Harvard style",
      template_format: "latex",
      template_source: "\\documentclass{article}\\begin{document}\\end{document}",
      is_active: true,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });
    vi.mocked(saveProfileCvTemplate).mockResolvedValue({
      id: "template-2",
      role_profile_id: "profile-1",
      name: "Updated style",
      template_format: "latex",
      template_source: "\\documentclass{article}\\begin{document}{{AI_TARGETED_EDITS}}\\end{document}",
      is_active: true,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    render(<ProfileDocumentPanel activeProfileId="profile-1" />);

    fireEvent.change(await screen.findByLabelText(/template name/i), {
      target: { value: "Updated style" },
    });
    fireEvent.change(screen.getByLabelText(/latex template source/i), {
      target: {
        value: "\\documentclass{article}\\begin{document}{{AI_TARGETED_EDITS}}\\end{document}",
      },
    });
    fireEvent.click(screen.getByRole("button", { name: /save template/i }));

    await waitFor(() => {
      expect(saveProfileCvTemplate).toHaveBeenCalledWith("profile-1", {
        name: "Updated style",
        template_source: "\\documentclass{article}\\begin{document}{{AI_TARGETED_EDITS}}\\end{document}",
      });
    });
  });
});
