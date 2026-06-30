import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import {
  JOB_STATUSES,
  JD_STATUSES,
  PARSE_STATUSES,
  EXTRACTION_STATUSES,
  SOURCE_PLATFORMS,
  TRACKED_JOB_STATUSES,
  ALLOWED_STATUS_TRANSITIONS
} from "../types/api";

// Helper to load the shared contract file
const loadContract = () => {
  const contractPath = path.resolve(process.cwd(), "../../shared/api-contract.json");
  if (!fs.existsSync(contractPath)) {
    throw new Error(`Shared api-contract.json not found at: ${contractPath}`);
  }
  const fileContent = fs.readFileSync(contractPath, "utf-8");
  return JSON.parse(fileContent);
};

describe("API Contract Drift Tests", () => {
  const contract = loadContract();

  it("should match job status values", () => {
    const contractJobStatuses = contract.job_statuses;
    expect(contractJobStatuses).toBeDefined();
    expect(JOB_STATUSES.slice().sort()).toEqual(contractJobStatuses.slice().sort());
  });

  it("should match jd status values", () => {
    const contractJdStatuses = contract.jd_statuses;
    expect(contractJdStatuses).toBeDefined();
    expect(JD_STATUSES.slice().sort()).toEqual(contractJdStatuses.slice().sort());
  });

  it("should match parse status values", () => {
    const contractParseStatuses = contract.parse_statuses;
    expect(contractParseStatuses).toBeDefined();
    expect(PARSE_STATUSES.slice().sort()).toEqual(contractParseStatuses.slice().sort());
  });

  it("should match extraction status values", () => {
    const contractExtractionStatuses = contract.extraction_statuses;
    expect(contractExtractionStatuses).toBeDefined();
    expect(EXTRACTION_STATUSES.slice().sort()).toEqual(contractExtractionStatuses.slice().sort());
  });

  it("should match source platform values", () => {
    const contractSourcePlatforms = contract.source_platforms;
    expect(contractSourcePlatforms).toBeDefined();
    expect(SOURCE_PLATFORMS.slice().sort()).toEqual(contractSourcePlatforms.slice().sort());
  });

  it("should match tracked job status values", () => {
    const contractTrackedJobStatuses = contract.tracked_job_statuses;
    expect(contractTrackedJobStatuses).toBeDefined();
    expect(TRACKED_JOB_STATUSES.slice().sort()).toEqual(contractTrackedJobStatuses.slice().sort());
  });

  it("should match allowed status transitions exactly and not contain unsupported values like archived", () => {
    const contractTransitions = contract.allowed_status_transitions;
    expect(contractTransitions).toBeDefined();

    // Verify all keys match
    const contractKeys = Object.keys(contractTransitions).sort();
    const localKeys = Object.keys(ALLOWED_STATUS_TRANSITIONS).sort();
    expect(localKeys).toEqual(contractKeys);

    // Verify all transitions match
    for (const key of localKeys) {
      const contractTargets = contractTransitions[key].slice().sort();
      const localTargets = ALLOWED_STATUS_TRANSITIONS[key as keyof typeof ALLOWED_STATUS_TRANSITIONS].slice().sort();
      expect(localTargets).toEqual(contractTargets);
    }

    // Ensure unsupported values such as 'archived' are not present in any target transitions
    const allLocalTargets = Object.values(ALLOWED_STATUS_TRANSITIONS).flat();
    expect(allLocalTargets).not.toContain("archived");

    const allContractTargets = Object.values(contractTransitions).flat();
    expect(allContractTargets).not.toContain("archived");
  });

  it("should verify endpoint metadata (methods and paths) used by the client", () => {
    // Expected client endpoint definitions mapping
    const EXPECTED_ENDPOINTS = {
      approveJob: { method: "POST", path: "/api/jobs/{id}/approve" },
      createRoleProfile: { method: "POST", path: "/api/role-profiles" },
      getBatchSummary: { method: "GET", path: "/api/batches/{batch_id}/summary" },
      getJobDetail: { method: "GET", path: "/api/jobs/{id}" },
      getJobs: { method: "GET", path: "/api/jobs" },
      getReviewJobs: { method: "GET", path: "/api/jobs/review" },
      listRoleProfiles: { method: "GET", path: "/api/role-profiles" },
      loadMockJobs: { method: "POST", path: "/api/jobs/mock-load" },
      parseJobText: { method: "POST", path: "/api/jobs/parse-text" },
      parseJobUrl: { method: "POST", path: "/api/jobs/parse-url" },
      rejectJob: { method: "POST", path: "/api/jobs/{id}/reject" },
      searchJobs: { method: "POST", path: "/api/jobs/search" },
      updateJobStatus: { method: "PATCH", path: "/api/jobs/{id}/status" }
    };

    const contractEndpoints = contract.endpoints;
    expect(contractEndpoints).toBeDefined();

    // Verify all expected client endpoints exist and match methods/paths in backend contract
    for (const [name, expected] of Object.entries(EXPECTED_ENDPOINTS)) {
      const contractEndpoint = contractEndpoints[name];
      expect(contractEndpoint, `Endpoint '${name}' missing from backend contract`).toBeDefined();
      expect(contractEndpoint.method, `Endpoint '${name}' method mismatch`).toBe(expected.method);
      expect(contractEndpoint.path, `Endpoint '${name}' path mismatch`).toBe(expected.path);
    }
  });

  it("should match key schema names used in response/request typing", () => {
    const contractSchemas = contract.schemas;
    expect(contractSchemas).toBeDefined();

    const expectedSchemas = [
      "JobResponse",
      "JobListResponse",
      "RoleProfileCreateRequest",
      "RoleProfileResponse",
      "RoleProfileListResponse",
      "IngestionResponse",
      "BatchSummaryResponse",
      "SearchJobsRequest",
      "ParseJobTextRequest",
      "ParseJobUrlRequest",
      "MockLoadRequest",
      "StatusUpdateRequest",
      "StatusMutationResponse"
    ];

    for (const schemaName of expectedSchemas) {
      expect(contractSchemas[schemaName], `Schema '${schemaName}' is missing from backend contract`).toBeDefined();
    }
  });
});
