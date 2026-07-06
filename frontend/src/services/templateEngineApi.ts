import { apiClient } from "@/lib/apiClient";
import type { TemplateMetadata } from "@udtp/shared";

/**
 * Template Engine API client — the only place that knows the template
 * generation endpoint shapes. Feature modules should call this instead of
 * `apiClient` directly.
 */
export const templateEngineApi = {
  generate: (fileId: string, force = false) =>
    apiClient.post<TemplateMetadata>(`/files/${fileId}/template${force ? "?force=true" : ""}`),
  getLatest: (fileId: string) => apiClient.get<TemplateMetadata>(`/files/${fileId}/template`),
  listVersions: (fileId: string) =>
    apiClient.get<TemplateMetadata[]>(`/files/${fileId}/template/versions`),
  getVersion: (fileId: string, version: number) =>
    apiClient.get<TemplateMetadata>(`/files/${fileId}/template/${version}`),
};
