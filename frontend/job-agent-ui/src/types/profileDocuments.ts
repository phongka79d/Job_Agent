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
