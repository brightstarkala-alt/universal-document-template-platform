import { apiClient } from "@/lib/apiClient";
import type { SignedUrlResponse, TemplatePreviewResponse } from "@udtp/shared";

/**
 * Preview Renderer API client — the only place that knows the preview
 * endpoint shapes. Feature modules should call this instead of `apiClient`
 * directly. Entirely read-only: no endpoint here ever writes anything.
 */
export const previewApi = {
  getLatest: (fileId: string) =>
    apiClient.get<TemplatePreviewResponse>(`/files/${fileId}/preview`),
  getVersion: (fileId: string, version: number) =>
    apiClient.get<TemplatePreviewResponse>(`/files/${fileId}/preview/${version}`),
  refreshAssetUrl: (fileId: string, assetId: string, version?: number) =>
    apiClient.get<SignedUrlResponse>(
      `/files/${fileId}/preview/assets/${assetId}/signed-url${
        version !== undefined ? `?version=${version}` : ""
      }`,
    ),
};
