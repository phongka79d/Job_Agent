import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  activateProfileDocumentVersion,
  listCvDrafts,
  listCvSuggestions,
  listProfileDocuments,
  previewCvDraft,
  uploadProfileDocument,
} from "../api/profileDocumentsClient";
import ProfileDocumentPanel from "../components/profile/ProfileDocumentPanel";
import type { ProfileDocument } from "../types/profileDocuments";

vi.mock("../api/profileDocumentsClient", () => ({
  activateProfileDocumentVersion: vi.fn(),
  deleteProfileDocument: vi.fn(),
  getProfileDocumentDownloadUrl: vi.fn(
    (profileId, documentId) => `/api/role-profiles/${profileId}/documents/${documentId}/download`
  ),
  getProfileDocumentFileUrl: vi.fn(
    (profileId, documentId) => `/api/role-profiles/${profileId}/documents/${documentId}/file`
  ),
  listCvDrafts: vi.fn(),
  listCvSuggestions: vi.fn(),
  listProfileDocuments: vi.fn(),
  previewCvDraft: vi.fn(),
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

describe("ProfileDocumentPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    expect(screen.getByText("wording_only - low")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });
});
