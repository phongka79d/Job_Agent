/**
 * Helper to derive the localStorage key for a specific role profile's active batch ID.
 */
export function getActiveBatchKey(roleProfileId: string): string {
  return `job-agent.activeBatchId.${roleProfileId}`;
}

/**
 * Loads the active batch ID for a specific role profile from localStorage.
 */
export function loadActiveBatchId(roleProfileId: string): string | null {
  const key = getActiveBatchKey(roleProfileId);
  return localStorage.getItem(key);
}

/**
 * Saves the active batch ID for a specific role profile to localStorage.
 */
export function saveActiveBatchId(roleProfileId: string, batchId: string): void {
  const key = getActiveBatchKey(roleProfileId);
  localStorage.setItem(key, batchId);
}

/**
 * Clears the active batch ID for a specific role profile from localStorage.
 */
export function clearActiveBatchId(roleProfileId: string): void {
  const key = getActiveBatchKey(roleProfileId);
  localStorage.removeItem(key);
}
