import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import {
  activateProfileDocumentVersion,
  createCvDraft,
  createCvSuggestion,
  deleteProfileDocument,
  exportCvDraftToPdf,
  getProfileDocumentDownloadUrl,
  getProfileDocumentFileUrl,
  getProfileDocumentVersionDownloadUrl,
  getProfileDocumentVersionFileUrl,
  getProfileCvTemplate,
  listCvDrafts,
  listCvSuggestions,
  listProfileDocumentVersions,
  listProfileDocuments,
  previewCvDraft,
  saveProfileCvTemplate,
  uploadProfileDocument,
} from "../api/profileDocumentsClient";

const getSpy = vi.spyOn(apiClient, "get");
const postSpy = vi.spyOn(apiClient, "post");
const putSpy = vi.spyOn(apiClient, "put");
const deleteSpy = vi.spyOn(apiClient, "delete");

describe("profileDocumentsClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists profile documents", async () => {
    getSpy.mockResolvedValueOnce({ data: { documents: [{ id: "doc-1" }] } });

    const result = await listProfileDocuments("profile-1");

    expect(getSpy).toHaveBeenCalledWith("/api/role-profiles/profile-1/documents");
    expect(result).toEqual([{ id: "doc-1" }]);
  });

  it("uploads a profile document as multipart form data", async () => {
    postSpy.mockResolvedValueOnce({ data: { id: "doc-1" } });
    const file = new File(["%PDF-test"], "cv.pdf", { type: "application/pdf" });

    const result = await uploadProfileDocument("profile-1", file);

    expect(postSpy).toHaveBeenCalledWith(
      "/api/role-profiles/profile-1/documents",
      expect.any(FormData),
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    expect(result).toEqual({ id: "doc-1" });
  });

  it("builds view and download URLs for real PDF files", () => {
    expect(getProfileDocumentFileUrl("profile-1", "doc-1")).toBe(
      "http://localhost:8000/api/role-profiles/profile-1/documents/doc-1/file"
    );
    expect(getProfileDocumentDownloadUrl("profile-1", "doc-1")).toBe(
      "http://localhost:8000/api/role-profiles/profile-1/documents/doc-1/download"
    );
  });

  it("lists profile document versions", async () => {
    getSpy.mockResolvedValueOnce({ data: { versions: [{ id: "version-1" }] } });

    const result = await listProfileDocumentVersions("profile-1", "doc-1");

    expect(getSpy).toHaveBeenCalledWith(
      "/api/role-profiles/profile-1/documents/doc-1/versions"
    );
    expect(result[0].id).toBe("version-1");
  });

  it("activates a profile document version with confirmation", async () => {
    postSpy.mockResolvedValueOnce({ data: { id: "version-1" } });

    await activateProfileDocumentVersion("profile-1", "doc-1", "version-1");

    expect(postSpy).toHaveBeenCalledWith(
      "/api/role-profiles/profile-1/documents/doc-1/versions/version-1/activate",
      { confirmed: true }
    );
  });

  it("deletes a profile document", async () => {
    deleteSpy.mockResolvedValueOnce({});

    await deleteProfileDocument("profile-1", "doc-1", { clearActive: true });

    expect(deleteSpy).toHaveBeenCalledWith(
      "/api/role-profiles/profile-1/documents/doc-1",
      { params: { clear_active: true } }
    );
  });

  it("creates CV suggestions and drafts through profile document routes", async () => {
    postSpy.mockResolvedValueOnce({
      data: {
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
    });
    postSpy.mockResolvedValueOnce({
      data: {
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
    });

    const suggestion = await createCvSuggestion("profile-1", "doc-1", "version-1", {
      requirement: "FastAPI",
      current_cv_evidence: "Evidence",
      missing_or_weak_evidence: "Weak wording",
      proposed_edit: "Improve wording",
      edit_kind: "wording_only",
      risk_level: "low",
      requires_confirmation: true,
    });
    const draft = await createCvDraft("profile-1", "doc-1", "version-1", {
      title: "Draft",
      suggestion_ids: [suggestion.id],
      confirmed: true,
    });

    expect(suggestion.id).toBe("suggestion-1");
    expect(draft.id).toBe("draft-1");
  });

  it("lists suggestions, drafts, and draft previews", async () => {
    getSpy.mockResolvedValueOnce({ data: { suggestions: [] } });
    getSpy.mockResolvedValueOnce({ data: { drafts: [] } });
    getSpy.mockResolvedValueOnce({
      data: {
        draft_id: "draft-1",
        title: "Draft",
        status: "draft",
        structure_status: "reliable",
        recommendation: null,
        sections: [],
        edits: [],
      },
    });

    await expect(listCvSuggestions("profile-1", "doc-1")).resolves.toEqual([]);
    await expect(listCvDrafts("profile-1", "doc-1")).resolves.toEqual([]);
    await expect(previewCvDraft("profile-1", "doc-1", "draft-1")).resolves.toMatchObject({
      draft_id: "draft-1",
    });
  });

  it("builds version file and download URLs", () => {
    expect(getProfileDocumentVersionFileUrl("profile-1", "doc-1", "version-2")).toBe(
      "http://localhost:8000/api/role-profiles/profile-1/documents/doc-1/versions/version-2/file"
    );
    expect(getProfileDocumentVersionDownloadUrl("profile-1", "doc-1", "version-2")).toBe(
      "http://localhost:8000/api/role-profiles/profile-1/documents/doc-1/versions/version-2/download"
    );
  });

  it("exports a CV draft as PDF with confirmation", async () => {
    postSpy.mockResolvedValueOnce({ data: {
      id: "version-2",
      document_id: "doc-1",
      role_profile_id: "profile-1",
      version_number: 2,
      source_type: "exported_draft",
      display_name: "Exported draft v2",
      filename: "cv-draft-v2.pdf",
      mime_type: "application/pdf",
      file_size_bytes: 1000,
      extracted_text_chars: 80,
      chunk_count: 1,
      extraction_status: "ready",
      structure_status: "reliable",
      structure_confidence: 0.9,
      error_reason: null,
      created_by: "ai",
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    } });

    const version = await exportCvDraftToPdf("profile-1", "doc-1", "draft-1", { confirmed: true });

    expect(postSpy).toHaveBeenCalledWith(
      "/api/role-profiles/profile-1/documents/doc-1/drafts/draft-1/export-pdf",
      { confirmed: true }
    );
    expect(version.id).toBe("version-2");
    expect(version.source_type).toBe("exported_draft");
  });

  it("gets and saves the active profile CV LaTeX template", async () => {
    getSpy.mockResolvedValueOnce({ data: { id: "template-1", name: "Harvard style" } });
    putSpy.mockResolvedValueOnce({ data: { id: "template-2", name: "Updated style" } });

    await expect(getProfileCvTemplate("profile-1")).resolves.toEqual({
      id: "template-1",
      name: "Harvard style",
    });
    await expect(
      saveProfileCvTemplate("profile-1", {
        name: "Updated style",
        template_source: "\\documentclass{article}\\begin{document}\\end{document}",
      })
    ).resolves.toEqual({ id: "template-2", name: "Updated style" });

    expect(getSpy).toHaveBeenCalledWith("/api/role-profiles/profile-1/cv-template");
    expect(putSpy).toHaveBeenCalledWith(
      "/api/role-profiles/profile-1/cv-template",
      {
        name: "Updated style",
        template_source: "\\documentclass{article}\\begin{document}\\end{document}",
      }
    );
  });
});
