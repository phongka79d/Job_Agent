import { apiClient, normalizeError } from "./client";
import type { ProfileDocument } from "../types/profileDocuments";

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
