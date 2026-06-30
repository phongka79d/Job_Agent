import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  apiClient,
  createRoleProfile,
  listRoleProfiles,
  searchJobs,
  parseJobUrl,
  parseJobText,
  loadMockJobs,
  getReviewJobs,
  approveJob,
  rejectJob,
  updateJobStatus,
  getJobs,
  getJobDetail,
  getBatchSummary,
  ApiClientError,
  normalizeError
} from "../api/client";
import axios from "axios";

// Spy on the Axios instance methods
const spyPost = vi.spyOn(apiClient, "post");
const spyGet = vi.spyOn(apiClient, "get");
const spyPatch = vi.spyOn(apiClient, "patch");

describe("API Client Functions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createRoleProfile", () => {
    it("should make a POST request with correct payload and return data", async () => {
      const mockRequest = {
        target_role: "Frontend Engineer",
        level: "Senior",
        location: "Hanoi",
        accept_remote: true,
        resume_text: "My Resume",
        skills: ["React", "TypeScript"]
      };
      const mockResponse = { id: "profile-123", ...mockRequest };
      
      spyPost.mockResolvedValueOnce({ data: mockResponse });

      const result = await createRoleProfile(mockRequest);

      expect(spyPost).toHaveBeenCalledWith("/api/role-profiles", mockRequest);
      expect(result).toEqual(mockResponse);
    });

    it("should surface API errors properly when they occur", async () => {
      const mockError = {
        isAxiosError: true,
        message: "Request failed",
        response: {
          status: 400,
          data: { detail: "Invalid request payload" }
        }
      };
      spyPost.mockRejectedValueOnce(mockError);

      await expect(createRoleProfile({ target_role: "" })).rejects.toThrow(ApiClientError);
    });
  });

  describe("listRoleProfiles", () => {
    it("should make a GET request and return the list of role profiles", async () => {
      const mockResponse = {
        role_profiles: [
          { id: "1", target_role: "SRE" },
          { id: "2", target_role: "DevOps" }
        ]
      };
      spyGet.mockResolvedValueOnce({ data: mockResponse });

      const result = await listRoleProfiles();

      expect(spyGet).toHaveBeenCalledWith("/api/role-profiles");
      expect(result).toEqual(mockResponse);
    });
  });

  describe("searchJobs", () => {
    it("should make a POST request to search jobs endpoint", async () => {
      const mockRequest = {
        role_profile_id: "profile-123",
        query: "React Engineer",
        max_urls: 5
      };
      const mockResponse = { batch_id: "batch-111", inserted_jobs: 3, jobs: [], warnings: [] };
      spyPost.mockResolvedValueOnce({ data: mockResponse });

      const result = await searchJobs(mockRequest);

      expect(spyPost).toHaveBeenCalledWith("/api/jobs/search", mockRequest);
      expect(result).toEqual(mockResponse);
    });
  });

  describe("parseJobUrl", () => {
    it("should make a POST request to parse-url endpoint", async () => {
      const mockRequest = {
        role_profile_id: "profile-123",
        source_url: "https://example.com/job"
      };
      const mockResponse = { batch_id: "batch-222", inserted_jobs: 1, jobs: [], warnings: [] };
      spyPost.mockResolvedValueOnce({ data: mockResponse });

      const result = await parseJobUrl(mockRequest);

      expect(spyPost).toHaveBeenCalledWith("/api/jobs/parse-url", mockRequest);
      expect(result).toEqual(mockResponse);
    });
  });

  describe("parseJobText", () => {
    it("should make a POST request to parse-text endpoint", async () => {
      const mockRequest = {
        role_profile_id: "profile-123",
        raw_text: "Seeking React dev...",
        source_url: "https://optional.url"
      };
      const mockResponse = { batch_id: "batch-333", inserted_jobs: 1, jobs: [], warnings: [] };
      spyPost.mockResolvedValueOnce({ data: mockResponse });

      const result = await parseJobText(mockRequest);

      expect(spyPost).toHaveBeenCalledWith("/api/jobs/parse-text", mockRequest);
      expect(result).toEqual(mockResponse);
    });
  });

  describe("loadMockJobs", () => {
    it("should make a POST request to mock-load endpoint", async () => {
      const mockRequest = {
        role_profile_id: "profile-123",
        reset_existing_demo: true
      };
      const mockResponse = { batch_id: "batch-mock", inserted_jobs: 5, jobs: [], warnings: [] };
      spyPost.mockResolvedValueOnce({ data: mockResponse });

      const result = await loadMockJobs(mockRequest);

      expect(spyPost).toHaveBeenCalledWith("/api/jobs/mock-load", mockRequest);
      expect(result).toEqual(mockResponse);
    });
  });

  describe("getReviewJobs", () => {
    it("should make a GET request to review endpoint with query params", async () => {
      const mockResponse = { jobs: [] };
      spyGet.mockResolvedValueOnce({ data: mockResponse });

      const result = await getReviewJobs("profile-123", 10);

      expect(spyGet).toHaveBeenCalledWith("/api/jobs/review", {
        params: {
          role_profile_id: "profile-123",
          limit: 10
        }
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe("approveJob", () => {
    it("should make a POST request to approve endpoint", async () => {
      const mockResponse = { id: "job-123", status: "saved" };
      spyPost.mockResolvedValueOnce({ data: mockResponse });

      const result = await approveJob("job-123");

      expect(spyPost).toHaveBeenCalledWith("/api/jobs/job-123/approve");
      expect(result).toEqual(mockResponse);
    });
  });

  describe("rejectJob", () => {
    it("should make a POST request to reject endpoint", async () => {
      const mockResponse = { id: "job-123", status: "ignored" };
      spyPost.mockResolvedValueOnce({ data: mockResponse });

      const result = await rejectJob("job-123");

      expect(spyPost).toHaveBeenCalledWith("/api/jobs/job-123/reject");
      expect(result).toEqual(mockResponse);
    });
  });

  describe("updateJobStatus", () => {
    it("should make a PATCH request to update job status manually", async () => {
      const mockRequest = { status: "applied" as const };
      const mockResponse = { id: "job-123", status: "applied" };
      spyPatch.mockResolvedValueOnce({ data: mockResponse });

      const result = await updateJobStatus("job-123", mockRequest);

      expect(spyPatch).toHaveBeenCalledWith("/api/jobs/job-123/status", mockRequest);
      expect(result).toEqual(mockResponse);
    });
  });

  describe("getJobs", () => {
    it("should request with proper query parameters for status and limit", async () => {
      const mockResponse = { jobs: [] };
      spyGet.mockResolvedValueOnce({ data: mockResponse });

      const result = await getJobs("profile-123", "tracked", 25);

      expect(spyGet).toHaveBeenCalledWith("/api/jobs", {
        params: {
          role_profile_id: "profile-123",
          status: "tracked",
          limit: 25
        }
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe("getJobDetail", () => {
    it("should request the single job details", async () => {
      const mockResponse = { id: "job-123", title: "Dev" };
      spyGet.mockResolvedValueOnce({ data: mockResponse });

      const result = await getJobDetail("job-123");

      expect(spyGet).toHaveBeenCalledWith("/api/jobs/job-123");
      expect(result).toEqual(mockResponse);
    });
  });

  describe("getBatchSummary", () => {
    it("should request batch summary", async () => {
      const mockResponse = { batch_id: "batch-123", total_parsed_jobs: 10 };
      spyGet.mockResolvedValueOnce({ data: mockResponse });

      const result = await getBatchSummary("batch-123");

      expect(spyGet).toHaveBeenCalledWith("/api/batches/batch-123/summary");
      expect(result).toEqual(mockResponse);
    });
  });
});

describe("Error Normalization and Surfacing", () => {
  it("should normalize string error detail from backend", () => {
    const mockAxiosError = {
      isAxiosError: true,
      message: "Request failed with status code 404",
      response: {
        status: 404,
        data: { detail: "Job post not found" }
      }
    };

    const normalized = normalizeError(mockAxiosError);
    expect(normalized).toBeInstanceOf(ApiClientError);
    expect(normalized.status).toBe(404);
    expect(normalized.message).toBe("Job post not found");
    expect(normalized.validationErrors).toBeUndefined();
  });

  it("should normalize array validation errors from FastAPI", () => {
    const mockAxiosError = {
      isAxiosError: true,
      message: "Request failed with status code 422",
      response: {
        status: 422,
        data: {
          detail: [
            { loc: ["body", "target_role"], msg: "field required", type: "value_error.missing" },
            { loc: ["query", "limit"], msg: "value is not a valid integer", type: "type_error.integer" }
          ]
        }
      }
    };

    const normalized = normalizeError(mockAxiosError);
    expect(normalized).toBeInstanceOf(ApiClientError);
    expect(normalized.status).toBe(422);
    expect(normalized.validationErrors).toEqual([
      { path: "body.target_role", message: "field required" },
      { path: "query.limit", message: "value is not a valid integer" }
    ]);
    expect(normalized.message).toContain("body.target_role: field required");
    expect(normalized.message).toContain("query.limit: value is not a valid integer");
  });

  it("should fall back gracefully if data.detail is absent or structured differently", () => {
    const mockAxiosError = {
      isAxiosError: true,
      message: "Request failed with status code 500",
      response: {
        status: 500,
        data: { message: "Internal server error details" }
      }
    };

    const normalized = normalizeError(mockAxiosError);
    expect(normalized.message).toBe("Internal server error details");
    expect(normalized.status).toBe(500);
  });

  it("should return raw error message for non-Axios error objects", () => {
    const genericError = new Error("Generic execution error");
    const normalized = normalizeError(genericError);
    
    expect(normalized).toBeInstanceOf(ApiClientError);
    expect(normalized.message).toBe("Generic execution error");
    expect(normalized.status).toBeUndefined();
  });
});
