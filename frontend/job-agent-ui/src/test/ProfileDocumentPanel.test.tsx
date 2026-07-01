import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  listProfileDocuments,
  uploadProfileDocument,
} from "../api/profileDocumentsClient";
import ProfileDocumentPanel from "../components/profile/ProfileDocumentPanel";
import type { ProfileDocument } from "../types/profileDocuments";

vi.mock("../api/profileDocumentsClient", () => ({
  listProfileDocuments: vi.fn(),
  uploadProfileDocument: vi.fn(),
}));

const readyDocument: ProfileDocument = {
  id: "doc-1",
  role_profile_id: "profile-1",
  original_filename: "cv.pdf",
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
});
