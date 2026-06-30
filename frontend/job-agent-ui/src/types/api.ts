export type JobStatus =
  | "pending_review"
  | "saved"
  | "applied"
  | "interview"
  | "rejected"
  | "offer"
  | "ignored";

export type JdStatus =
  | "full_jd"
  | "partial_jd"
  | "contact_for_jd"
  | "no_jd"
  | "unclear";

export type ParseStatus = "success" | "needs_manual_input" | "failed";
export type ExtractionStatus = "success" | "retried" | "failed";
export type SourcePlatform = "tavily" | "manual_url" | "manual_text" | "job_board";

export interface RoleProfile {
  id: string;
  target_role: string;
  level: string | null;
  location: string | null;
  accept_remote: boolean | null;
  resume_text: string | null;
  skills: string[];
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: string;
  batch_id: string;
  role_profile_id: string;
  title: string | null;
  company: string | null;
  location: string | null;
  work_mode: string | null;
  level: string | null;
  employment_type: string | null;
  salary: string | null;
  responsibilities: string | null;
  requirements: string | null;
  skills: string[];
  source_url: string | null;
  source_platform: SourcePlatform | null;
  parse_status: ParseStatus | null;
  jd_status: JdStatus | null;
  extraction_status: ExtractionStatus | null;
  error_reason: string | null;
  should_score_similarity: boolean;
  embedding_similarity: number | null;
  skill_overlap_score: number | null;
  location_match_score: number | null;
  level_match_score: number | null;
  base_score: number | null;
  jd_confidence_multiplier: number | null;
  final_score: number | null;
  final_score_percent: number | null;
  status: JobStatus;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_usd: number | null;
  extraction_time_ms: number | null;
  discovered_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface IngestionResponse {
  batch_id: string;
  inserted_jobs: number;
  skipped_exact_duplicates: number;
  skipped_dedup_key_duplicates: number;
  inserted_duplicate_metadata: number;
  qdrant_upserted: number;
  qdrant_synced: boolean;
  jobs: Job[];
  warnings: string[];
}

export interface BatchSummary {
  batch_id: string;
  total_parsed_jobs: number;
  scorable_jobs: number;
  failed_extractions: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  average_extraction_time_ms: number | null;
}

// Additional request/response interfaces for FastAPI client
export interface RoleProfileCreateRequest {
  target_role: string;
  level?: string | null;
  location?: string | null;
  accept_remote?: boolean | null;
  resume_text?: string | null;
  skills?: string[];
}

export interface RoleProfileListResponse {
  role_profiles: RoleProfile[];
}

export interface JobListResponse {
  jobs: Job[];
}

export interface SearchJobsRequest {
  role_profile_id: string;
  query: string;
  max_urls?: number;
}

export interface ParseJobTextRequest {
  role_profile_id: string;
  raw_text: string;
  source_url?: string | null;
}

export interface ParseJobUrlRequest {
  role_profile_id: string;
  source_url: string;
}

export interface StatusUpdateRequest {
  status: "applied" | "interview" | "rejected" | "offer";
}

export interface StatusMutationResponse extends Job {}

// Stable arrays and maps for runtime UI, tested against api-contract.json to avoid drift
export const JOB_STATUSES: JobStatus[] = [
  "pending_review",
  "saved",
  "applied",
  "interview",
  "rejected",
  "offer",
  "ignored"
];

export const JD_STATUSES: JdStatus[] = [
  "full_jd",
  "partial_jd",
  "contact_for_jd",
  "no_jd",
  "unclear"
];

export const PARSE_STATUSES: ParseStatus[] = ["success", "needs_manual_input", "failed"];

export const EXTRACTION_STATUSES: ExtractionStatus[] = ["success", "retried", "failed"];

export const SOURCE_PLATFORMS: SourcePlatform[] = [
  "tavily",
  "manual_url",
  "manual_text",
  "job_board"
];

export const TRACKED_JOB_STATUSES: JobStatus[] = [
  "saved",
  "applied",
  "interview",
  "rejected",
  "offer"
];

export const ALLOWED_STATUS_TRANSITIONS: Record<JobStatus, JobStatus[]> = {
  applied: ["interview", "rejected"],
  ignored: [],
  interview: ["rejected", "offer"],
  offer: [],
  pending_review: ["saved", "ignored"],
  rejected: [],
  saved: ["applied", "rejected"]
};
