import { apiClient, normalizeError } from "./client";
import type { ProfileDocument, ProfileDocumentVersion } from "../types/profileDocuments";

export async function listProfileDocuments(roleProfileId: string): Promise<ProfileDocument[]> {
  try {
    const response = await apiClient.get<{ documents: ProfileDocument[] }>(
      `/api/role-profiles/${roleProfileId}/documents`
    );
    return response.data.documents;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function uploadProfileDocument(
  roleProfileId: string,
  file: File
): Promise<ProfileDocument> {
  const formData = new FormData();
  formData.append("file", file);
  try {
    const response = await apiClient.post<ProfileDocument>(
      `/api/role-profiles/${roleProfileId}/documents`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export function getProfileDocumentFileUrl(roleProfileId: string, documentId: string): string {
  return `/api/role-profiles/${roleProfileId}/documents/${documentId}/file`;
}

export function getProfileDocumentDownloadUrl(roleProfileId: string, documentId: string): string {
  return `/api/role-profiles/${roleProfileId}/documents/${documentId}/download`;
}

export async function listProfileDocumentVersions(
  roleProfileId: string,
  documentId: string
): Promise<ProfileDocumentVersion[]> {
  try {
    const response = await apiClient.get<{ versions: ProfileDocumentVersion[] }>(
      `/api/role-profiles/${roleProfileId}/documents/${documentId}/versions`
    );
    return response.data.versions;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function activateProfileDocumentVersion(
  roleProfileId: string,
  documentId: string,
  versionId: string
): Promise<ProfileDocumentVersion> {
  try {
    const response = await apiClient.post<ProfileDocumentVersion>(
      `/api/role-profiles/${roleProfileId}/documents/${documentId}/versions/${versionId}/activate`,
      { confirmed: true }
    );
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function deleteProfileDocument(
  roleProfileId: string,
  documentId: string,
  options: { clearActive?: boolean } = {}
): Promise<void> {
  try {
    await apiClient.delete(`/api/role-profiles/${roleProfileId}/documents/${documentId}`, {
      params: { clear_active: Boolean(options.clearActive) },
    });
  } catch (error) {
    throw normalizeError(error);
  }
}
