import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import StatusSelect from "../components/StatusSelect";
import { updateJobStatus } from "../api/client";
import { loadApiContract } from "./contract";
import type { JobStatus } from "../types/api";

// Mock the API client
vi.mock("../api/client", () => ({
  updateJobStatus: vi.fn(),
}));

describe("StatusSelect component", () => {
  const contract = loadApiContract();

  beforeEach(() => {
    vi.resetAllMocks();
  });

  const expectedOptionsFromContract = (status: JobStatus) => [
    status,
    ...contract.allowed_status_transitions[status],
  ];

  const renderedOptions = () => {
    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    return Array.from(select.options).map((opt) => opt.value);
  };

  it("should render correct allowed transitions for 'saved' status", () => {
    render(<StatusSelect jobId="job-1" currentStatus="saved" />);
    
    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(select.disabled).toBe(false);
    expect(select.value).toBe("saved");

    expect(renderedOptions()).toEqual(expectedOptionsFromContract("saved"));
  });

  it("should render correct allowed transitions for 'applied' status", () => {
    render(<StatusSelect jobId="job-1" currentStatus="applied" />);
    
    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(select.disabled).toBe(false);
    expect(select.value).toBe("applied");

    expect(renderedOptions()).toEqual(expectedOptionsFromContract("applied"));
  });

  it("should render correct allowed transitions for 'interview' status", () => {
    render(<StatusSelect jobId="job-1" currentStatus="interview" />);
    
    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    expect(select.disabled).toBe(false);
    expect(select.value).toBe("interview");

    expect(renderedOptions()).toEqual(expectedOptionsFromContract("interview"));
  });

  it("should disable select component for terminal states like 'offer'", () => {
    render(<StatusSelect jobId="job-1" currentStatus="offer" />);
    
    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    expect(select.disabled).toBe(true);
    
    expect(renderedOptions()).toEqual(expectedOptionsFromContract("offer"));
  });

  it("should disable select component for terminal states like 'rejected'", () => {
    render(<StatusSelect jobId="job-1" currentStatus="rejected" />);
    
    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    expect(select.disabled).toBe(true);
    expect(renderedOptions()).toEqual(expectedOptionsFromContract("rejected"));
  });

  it("should only expose backend-approved manual transition options", () => {
    for (const status of ["saved", "applied", "interview", "rejected", "offer"] as JobStatus[]) {
      const { unmount } = render(<StatusSelect jobId={`job-${status}`} currentStatus={status} />);
      const options = renderedOptions();

      expect(options).toEqual(expectedOptionsFromContract(status));
      expect(options).not.toContain("pending_review");
      expect(options).not.toContain("ignored");
      if (status !== "saved") {
        expect(options).not.toContain("saved");
      }

      unmount();
    }
  });

  it("should trigger updateJobStatus on selection change and invoke callback on success", async () => {
    const onStatusChangeSuccess = vi.fn();
    vi.mocked(updateJobStatus).mockResolvedValue({ id: "job-1", status: "applied" } as any);

    render(
      <StatusSelect
        jobId="job-1"
        currentStatus="saved"
        onStatusChangeSuccess={onStatusChangeSuccess}
      />
    );

    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    
    // Change value to "applied"
    fireEvent.change(select, { target: { value: "applied" } });

    expect(updateJobStatus).toHaveBeenCalledWith("job-1", { status: "applied" });
    
    await waitFor(() => {
      expect(onStatusChangeSuccess).toHaveBeenCalled();
      expect(select.value).toBe("applied");
    });
  });

  it("should revert selection and display error on API failure", async () => {
    const onStatusChangeSuccess = vi.fn();
    const errorMessage = "API error";
    vi.mocked(updateJobStatus).mockRejectedValue(new Error(errorMessage));

    render(
      <StatusSelect
        jobId="job-1"
        currentStatus="saved"
        onStatusChangeSuccess={onStatusChangeSuccess}
      />
    );

    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    
    // Change value to "applied"
    fireEvent.change(select, { target: { value: "applied" } });

    expect(updateJobStatus).toHaveBeenCalledWith("job-1", { status: "applied" });

    // Wait for the error handling to execute
    await waitFor(() => {
      // Reverts back to current status
      expect(select.value).toBe("saved");
      // Shows error message
      expect(screen.getByTestId("status-error")).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    expect(onStatusChangeSuccess).not.toHaveBeenCalled();
  });
});
