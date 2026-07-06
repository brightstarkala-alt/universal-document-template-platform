import { apiClient } from "@/lib/apiClient";
import type { AIExtractionMetadata } from "@udtp/shared";

/**
 * AI Field Extraction API client — the only place that knows the
 * extraction endpoint shapes. Feature modules should call this instead of
 * `apiClient` directly.
 */
export const aiExtractionApi = {
  extract: (fileId: string, force = false) =>
    apiClient.post<AIExtractionMetadata>(`/files/${fileId}/extract${force ? "?force=true" : ""}`),
  getLatest: (fileId: string) =>
    apiClient.get<AIExtractionMetadata>(`/files/${fileId}/extracted`),
  listVersions: (fileId: string) =>
    apiClient.get<AIExtractionMetadata[]>(`/files/${fileId}/extracted/versions`),
  getVersion: (fileId: string, version: number) =>
    apiClient.get<AIExtractionMetadata>(`/files/${fileId}/extracted/${version}`),
};
