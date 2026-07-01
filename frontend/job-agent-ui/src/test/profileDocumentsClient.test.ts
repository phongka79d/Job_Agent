import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import {
  listProfileDocuments,
  uploadProfileDocument,
} from "../api/profileDocumentsClient";

const getSpy = vi.spyOn(apiClient, "get");
const postSpy = vi.spyOn(apiClient, "post");

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
});
