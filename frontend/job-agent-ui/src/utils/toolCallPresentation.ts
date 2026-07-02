import type { ToolCallStatus } from "../types/chat";

type LifecycleLabels = {
  running: string;
  success: string;
  failed: string;
};

const TOOL_LABELS: Record<string, LifecycleLabels> = {
  search_jobs: {
    running: "Searching for jobs",
    success: "Job search completed",
    failed: "Job search failed",
  },
  extract_job_from_url: {
    running: "Importing job link",
    success: "Job link imported",
    failed: "Job link import failed",
  },
  extract_job_from_text: {
    running: "Importing job description",
    success: "Job description imported",
    failed: "Job description import failed",
  },
  update_job_status: {
    running: "Updating job status",
    success: "Job status updated",
    failed: "Job status update failed",
  },
  list_profile_cvs: {
    running: "Loading your CVs",
    success: "CV list loaded",
    failed: "CV list could not be loaded",
  },
  get_active_profile_cv: {
    running: "Checking active CV",
    success: "Active CV checked",
    failed: "Active CV check failed",
  },
  view_profile_cv_metadata: {
    running: "Loading CV details",
    success: "CV details loaded",
    failed: "CV details could not be loaded",
  },
  retrieve_profile_cv_chunks: {
    running: "Reading your CV",
    success: "CV reading completed",
    failed: "CV reading failed",
  },
  analyze_cv_structure: {
    running: "Analyzing CV structure",
    success: "CV structure analyzed",
    failed: "CV structure analysis failed",
  },
  retrieve_profile_documents: {
    running: "Reading profile documents",
    success: "Profile documents loaded",
    failed: "Profile documents could not be loaded",
  },
  suggest_cv_improvements: {
    running: "Preparing CV suggestions",
    success: "CV suggestions prepared",
    failed: "CV suggestions could not be prepared",
  },
  create_cv_edit_draft: {
    running: "Creating CV draft",
    success: "CV draft created",
    failed: "CV draft creation failed",
  },
  preview_cv_edit_draft: {
    running: "Preparing CV preview",
    success: "CV preview ready",
    failed: "CV preview could not be prepared",
  },
  export_cv_draft_to_pdf: {
    running: "Exporting CV draft",
    success: "CV draft exported",
    failed: "CV draft export failed",
  },
  score_cv_against_job: {
    running: "Comparing CV with job",
    success: "CV comparison completed",
    failed: "CV comparison failed",
  },
  set_active_cv_version: {
    running: "Setting active CV",
    success: "Active CV updated",
    failed: "Active CV update failed",
  },
};

export function getToolCallPresentation(
  toolName: string,
  status: ToolCallStatus,
): { label: string; statusLabel: string } {
  const lifecycle = status === "pending" ? "running" : status;
  const statusLabel =
    lifecycle === "running"
      ? "In progress"
      : lifecycle === "success"
        ? "Completed"
        : "Needs attention";
  const labels = TOOL_LABELS[toolName];

  if (labels) {
    return { label: labels[lifecycle], statusLabel };
  }

  const readableName =
    toolName.split("_").filter(Boolean).join(" ") || "Tool";
  const sentenceCaseName =
    readableName.charAt(0).toUpperCase() + readableName.slice(1);
  const suffix =
    lifecycle === "running"
      ? "in progress"
      : lifecycle === "success"
        ? "completed"
        : "failed";

  return { label: `${sentenceCaseName} ${suffix}`, statusLabel };
}
