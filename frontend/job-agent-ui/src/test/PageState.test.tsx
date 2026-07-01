import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PageState from "../components/PageState";

describe("PageState", () => {
  it("renders the supplied empty message without adding domain values", () => {
    render(<PageState kind="empty">No tracked jobs found.</PageState>);
    expect(screen.getByText("No tracked jobs found.")).toBeInTheDocument();
    expect(screen.queryByText(/AI Engineer/i)).not.toBeInTheDocument();
  });
});
