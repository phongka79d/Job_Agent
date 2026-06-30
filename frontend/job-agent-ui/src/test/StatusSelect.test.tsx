import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import StatusSelect from "../components/StatusSelect";
import { updateJobStatus } from "../api/client";

// Mock the API client
vi.mock("../api/client", () => ({
  updateJobStatus: vi.fn(),
}));

describe("StatusSelect component", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("should render correct allowed transitions for 'saved' status", () => {
    render(<StatusSelect jobId="job-1" currentStatus="saved" />);
    
    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(select.disabled).toBe(false);
    expect(select.value).toBe("saved");

    const options = Array.from(select.options).map((opt) => opt.value);
    expect(options).toEqual(["saved", "applied", "rejected"]);
  });

  it("should render correct allowed transitions for 'applied' status", () => {
    render(<StatusSelect jobId="job-1" currentStatus="applied" />);
    
    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(select.disabled).toBe(false);
    expect(select.value).toBe("applied");

    const options = Array.from(select.options).map((opt) => opt.value);
    expect(options).toEqual(["applied", "interview", "rejected"]);
  });

  it("should render correct allowed transitions for 'interview' status", () => {
    render(<StatusSelect jobId="job-1" currentStatus="interview" />);
    
    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    expect(select.disabled).toBe(false);
    expect(select.value).toBe("interview");

    const options = Array.from(select.options).map((opt) => opt.value);
    expect(options).toEqual(["interview", "rejected", "offer"]);
  });

  it("should disable select component for terminal states like 'offer'", () => {
    render(<StatusSelect jobId="job-1" currentStatus="offer" />);
    
    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    expect(select.disabled).toBe(true);
    
    const options = Array.from(select.options).map((opt) => opt.value);
    expect(options).toEqual(["offer"]);
  });

  it("should disable select component for terminal states like 'rejected'", () => {
    render(<StatusSelect jobId="job-1" currentStatus="rejected" />);
    
    const select = screen.getByTestId("status-select") as HTMLSelectElement;
    expect(select.disabled).toBe(true);
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
