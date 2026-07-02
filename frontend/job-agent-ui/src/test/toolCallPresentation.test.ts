import { describe, expect, it } from "vitest";
import { getToolCallPresentation } from "../utils/toolCallPresentation";

const registeredTools = [
  {
    name: "search_jobs",
    running: "Searching for jobs",
    success: "Job search completed",
    failed: "Job search failed",
  },
  {
    name: "extract_job_from_url",
    running: "Importing job link",
    success: "Job link imported",
    failed: "Job link import failed",
  },
  {
    name: "extract_job_from_text",
    running: "Importing job description",
    success: "Job description imported",
    failed: "Job description import failed",
  },
  {
    name: "update_job_status",
    running: "Updating job status",
    success: "Job status updated",
    failed: "Job status update failed",
  },
  {
    name: "list_profile_cvs",
    running: "Loading your CVs",
    success: "CV list loaded",
    failed: "CV list could not be loaded",
  },
  {
    name: "get_active_profile_cv",
    running: "Checking active CV",
    success: "Active CV checked",
    failed: "Active CV check failed",
  },
  {
    name: "view_profile_cv_metadata",
    running: "Loading CV details",
    success: "CV details loaded",
    failed: "CV details could not be loaded",
  },
  {
    name: "retrieve_profile_cv_chunks",
    running: "Reading your CV",
    success: "CV reading completed",
    failed: "CV reading failed",
  },
  {
    name: "analyze_cv_structure",
    running: "Analyzing CV structure",
    success: "CV structure analyzed",
    failed: "CV structure analysis failed",
  },
  {
    name: "retrieve_profile_documents",
    running: "Reading profile documents",
    success: "Profile documents loaded",
    failed: "Profile documents could not be loaded",
  },
  {
    name: "suggest_cv_improvements",
    running: "Preparing CV suggestions",
    success: "CV suggestions prepared",
    failed: "CV suggestions could not be prepared",
  },
  {
    name: "create_cv_edit_draft",
    running: "Creating CV draft",
    success: "CV draft created",
    failed: "CV draft creation failed",
  },
  {
    name: "preview_cv_edit_draft",
    running: "Preparing CV preview",
    success: "CV preview ready",
    failed: "CV preview could not be prepared",
  },
  {
    name: "export_cv_draft_to_pdf",
    running: "Exporting CV draft",
    success: "CV draft exported",
    failed: "CV draft export failed",
  },
  {
    name: "score_cv_against_job",
    running: "Comparing CV with job",
    success: "CV comparison completed",
    failed: "CV comparison failed",
  },
  {
    name: "set_active_cv_version",
    running: "Setting active CV",
    success: "Active CV updated",
    failed: "Active CV update failed",
  },
] as const;

describe("getToolCallPresentation", () => {
  it.each(registeredTools)(
    "returns readable lifecycle labels for $name",
    ({ name, running, success, failed }) => {
      expect(getToolCallPresentation(name, "pending")).toEqual({
        label: running,
        statusLabel: "In progress",
      });
      expect(getToolCallPresentation(name, "running")).toEqual({
        label: running,
        statusLabel: "In progress",
      });
      expect(getToolCallPresentation(name, "success")).toEqual({
        label: success,
        statusLabel: "Completed",
      });
      expect(getToolCallPresentation(name, "failed")).toEqual({
        label: failed,
        statusLabel: "Needs attention",
      });
    },
  );

  it.each([
    ["pending", "Generate custom report in progress", "In progress"],
    ["running", "Generate custom report in progress", "In progress"],
    ["success", "Generate custom report completed", "Completed"],
    ["failed", "Generate custom report failed", "Needs attention"],
  ] as const)(
    "falls back to a sentence-case label for an unknown %s tool",
    (status, label, statusLabel) => {
      const presentation = getToolCallPresentation("generate_custom_report", status);

      expect(presentation).toEqual({ label, statusLabel });
      expect(presentation.label).not.toContain("_");
    },
  );

  it.each([
    ["", "running", "Tool in progress", "In progress"],
    ["_", "success", "Tool completed", "Completed"],
    ["__generate__report", "failed", "Generate report failed", "Needs attention"],
  ] as const)(
    "normalizes boundary identifier %j",
    (toolName, status, label, statusLabel) => {
      expect(getToolCallPresentation(toolName, status)).toEqual({
        label,
        statusLabel,
      });
    },
  );
});
