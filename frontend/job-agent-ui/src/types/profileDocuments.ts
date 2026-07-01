export interface ProfileDocumentVersion {
  id: string;
  document_id: string;
  role_profile_id: string;
  version_number: number;
  source_type: "original_upload" | "exported_draft";
  display_name: string;
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  extracted_text_chars: number;
  chunk_count: number;
  extraction_status: "processing" | "ready" | "failed";
  structure_status: "not_extracted" | "reliable" | "partial" | "unreliable";
  structure_confidence: number | null;
  error_reason: string | null;
  created_by: "user" | "ai" | "system";
  created_at: string;
  updated_at: string;
}

export interface ProfileDocument {
  id: string;
  role_profile_id: string;
  original_filename: string;
  document_kind: "cv";
  active_version_id: string | null;
  is_active: boolean;
  mime_type: string;
  file_size_bytes: number;
  extracted_text_chars: number;
  chunk_count: number;
  status: "processing" | "ready" | "failed";
  error_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface CvImprovementSuggestion {
  id: string;
  role_profile_id: string;
  document_id: string;
  version_id: string;
  job_id: string | null;
  requirement: string;
  current_cv_evidence: string;
  missing_or_weak_evidence: string;
  proposed_edit: string;
  edit_kind: "wording_only" | "requires_user_fact";
  risk_level: "low" | "medium" | "high";
  requires_confirmation: boolean;
  status: "suggested" | "accepted" | "rejected" | "drafted";
  created_at: string;
  updated_at: string;
}

export interface CvDraft {
  id: string;
  role_profile_id: string;
  document_id: string;
  base_version_id: string;
  status: "draft" | "exported" | "discarded";
  title: string;
  structure_status_at_creation: "not_extracted" | "reliable" | "partial" | "unreliable";
  created_by: "user" | "ai";
  created_at: string;
  updated_at: string;
}

export interface CvDraftPreview {
  draft_id: string;
  title: string;
  status: string;
  structure_status: string;
  recommendation: string | null;
  sections: Array<{ heading: string; content: string }>;
  edits: Array<{
    requirement: string;
    current_cv_evidence?: string;
    proposed_edit: string;
    edit_kind?: string;
    risk_level?: string;
  }>;
}

export interface CreateCvSuggestionPayload {
  requirement: string;
  current_cv_evidence: string;
  missing_or_weak_evidence: string;
  proposed_edit: string;
  edit_kind: "wording_only" | "requires_user_fact";
  risk_level: "low" | "medium" | "high";
  requires_confirmation: boolean;
  job_id?: string | null;
}

export interface CreateCvDraftPayload {
  title: string;
  suggestion_ids: string[];
  confirmed: boolean;
}
