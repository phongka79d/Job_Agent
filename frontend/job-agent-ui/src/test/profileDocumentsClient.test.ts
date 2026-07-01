import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import {
  activateProfileDocumentVersion,
  deleteProfileDocument,
  getProfileDocumentDownloadUrl,
  getProfileDocumentFileUrl,
  listProfileDocumentVersions,
  listProfileDocuments,
  uploadProfileDocument,
} from "../api/profileDocumentsClient";

const getSpy = vi.spyOn(apiClient, "get");
const postSpy = vi.spyOn(apiClient, "post");
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
      "/api/role-profiles/profile-1/documents/doc-1/file"
    );
    expect(getProfileDocumentDownloadUrl("profile-1", "doc-1")).toBe(
      "/api/role-profiles/profile-1/documents/doc-1/download"
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
});
