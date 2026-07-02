import axios from "axios";
import type {
  GenerateJobCvImprovementsRequest,
  GenerateJobCvImprovementsResponse,
  RoleProfile,
  RoleProfileCreateRequest,
  RoleProfileListResponse,
  Job,
  JobListResponse,
  IngestionResponse,
  BatchSummary,
  SearchJobsRequest,
  ParseJobUrlRequest,
  ParseJobTextRequest,
  StatusUpdateRequest,
  JobStatus
} from "../types/api";

const DEFAULT_BASE_URL = "http://localhost:8000";

export class ApiClientError extends Error {
  status?: number;
  validationErrors?: Array<{ path: string; message: string }>;
  rawDetail?: any;

  constructor(
    message: string,
    status?: number,
    validationErrors?: Array<{ path: string; message: string }>,
    rawDetail?: any
  ) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.validationErrors = validationErrors;
    this.rawDetail = rawDetail;
  }
}

/**
 * Normalizes backend validation/service errors into a frontend-safe error shape.
 * Surfaces details without swallowing them.
 */
export function normalizeError(error: any): ApiClientError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const data = error.response?.data;
    
    let message = error.message;
    let validationErrors: Array<{ path: string; message: string }> | undefined;
    
    if (data && typeof data === "object") {
      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        // FastAPI validation error array mapping
        const mappedErrors: Array<{ path: string; message: string }> = data.detail.map((err: any) => {
          const path = Array.isArray(err.loc) ? err.loc.join(".") : String(err.loc || "");
          return {
            path,
            message: err.msg || "Validation error"
          };
        });
        validationErrors = mappedErrors;
        message = `Validation Error: ${mappedErrors.map((e: { path: string; message: string }) => `${e.path}: ${e.message}`).join("; ")}`;
      } else if (data.message) {
        message = data.message;
      }
    }
    
    return new ApiClientError(message, status, validationErrors, data?.detail);
  }
  
  return new ApiClientError(error instanceof Error ? error.message : String(error));
}

// Instantiate Axios with default base URL and standard configuration
export const apiClient = axios.create({
  baseURL: DEFAULT_BASE_URL,
  headers: {
    "Content-Type": "application/json"
  }
});

export function resolveApiUrl(path: string): string {
  return new URL(path, apiClient.defaults.baseURL).toString();
}

/**
 * Creates a new role profile.
 * POST /api/role-profiles
 */
export async function createRoleProfile(request: RoleProfileCreateRequest): Promise<RoleProfile> {
  try {
    const response = await apiClient.post<RoleProfile>("/api/role-profiles", request);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

/**
 * Lists all active role profiles in descending order.
 * GET /api/role-profiles
 */
export async function listRoleProfiles(): Promise<RoleProfileListResponse> {
  try {
    const response = await apiClient.get<RoleProfileListResponse>("/api/role-profiles");
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

/**
 * Triggers an ingestion batch by searching for jobs based on a query.
 * POST /api/jobs/search
 */
export async function searchJobs(request: SearchJobsRequest): Promise<IngestionResponse> {
  try {
    const response = await apiClient.post<IngestionResponse>("/api/jobs/search", request);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

/**
 * Triggers ingestion by parsing a single public job posting URL.
 * POST /api/jobs/parse-url
 */
export async function parseJobUrl(request: ParseJobUrlRequest): Promise<IngestionResponse> {
  try {
    const response = await apiClient.post<IngestionResponse>("/api/jobs/parse-url", request);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

/**
 * Triggers ingestion by parsing raw text input for a job posting.
 * POST /api/jobs/parse-text
 */
export async function parseJobText(request: ParseJobTextRequest): Promise<IngestionResponse> {
  try {
    const response = await apiClient.post<IngestionResponse>("/api/jobs/parse-text", request);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

/**
 * Fetches pending review jobs for a specific role profile.
 * GET /api/jobs/review
 */
export async function getReviewJobs(roleProfileId: string, limit?: number): Promise<JobListResponse> {
  try {
    const response = await apiClient.get<JobListResponse>("/api/jobs/review", {
      params: {
        role_profile_id: roleProfileId,
        ...(limit !== undefined ? { limit } : {})
      }
    });
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

/**
 * Approves a pending job, moving its status to 'saved'.
 * POST /api/jobs/{id}/approve
 */
export async function approveJob(id: string): Promise<Job> {
  try {
    const response = await apiClient.post<Job>(`/api/jobs/${id}/approve`);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

/**
 * Rejects a pending job, moving its status to 'ignored'.
 * POST /api/jobs/{id}/reject
 */
export async function rejectJob(id: string): Promise<Job> {
  try {
    const response = await apiClient.post<Job>(`/api/jobs/${id}/reject`);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

/**
 * Updates a job's application tracking status manually.
 * PATCH /api/jobs/{id}/status
 */
export async function updateJobStatus(id: string, request: StatusUpdateRequest): Promise<Job> {
  try {
    const response = await apiClient.patch<Job>(`/api/jobs/${id}/status`, request);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

/**
 * Lists jobs filtered by role profile and application/dashboard status.
 * GET /api/jobs
 */
export async function getJobs(
  roleProfileId: string,
  status?: "saved" | "tracked" | JobStatus,
  limit?: number
): Promise<JobListResponse> {
  try {
    const response = await apiClient.get<JobListResponse>("/api/jobs", {
      params: {
        role_profile_id: roleProfileId,
        ...(status !== undefined ? { status } : {}),
        ...(limit !== undefined ? { limit } : {})
      }
    });
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

/**
 * Fetches the detail of a single job.
 * GET /api/jobs/{id}
 */
export async function getJobDetail(id: string): Promise<Job> {
  try {
    const response = await apiClient.get<Job>(`/api/jobs/${id}`);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

/**
 * Fetches summary statistics for a specific ingestion batch.
 * GET /api/batches/{batch_id}/summary
 */
export async function getBatchSummary(batchId: string): Promise<BatchSummary> {
  try {
    const response = await apiClient.get<BatchSummary>(`/api/batches/${batchId}/summary`);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function generateJobCvImprovements(
  id: string,
  request: GenerateJobCvImprovementsRequest
): Promise<GenerateJobCvImprovementsResponse> {
  try {
    const response = await apiClient.post<GenerateJobCvImprovementsResponse>(
      `/api/jobs/${id}/cv-improvements`,
      request
    );
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}
