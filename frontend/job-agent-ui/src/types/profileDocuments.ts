export interface ProfileDocument {
  id: string;
  role_profile_id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  extracted_text_chars: number;
  chunk_count: number;
  status: "processing" | "ready" | "failed";
  error_reason: string | null;
  created_at: string;
  updated_at: string;
}
