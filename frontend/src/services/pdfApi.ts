import { apiClient } from "@/lib/apiClient";
import type { PDFMetadata, SignedUrlResponse } from "@udtp/shared";

/**
 * PDF Generation API client (Module 10) — the only place that knows the
 * PDF endpoint shapes. Mirrors `previewApi`/`templateEngineApi`'s shape.
 */
export const pdfApi = {
  generate: (fileId: string, force = false) =>
    apiClient.post<PDFMetadata>(`/files/${fileId}/pdf${force ? "?force=true" : ""}`),
  getLatest: (fileId: string) => apiClient.get<PDFMetadata>(`/files/${fileId}/pdf`),
  getVersions: (fileId: string) => apiClient.get<PDFMetadata[]>(`/files/${fileId}/pdf/versions`),
  getVersion: (fileId: string, version: number) =>
    apiClient.get<PDFMetadata>(`/files/${fileId}/pdf/${version}`),
  getSignedUrl: (fileId: string, version?: number) =>
    apiClient.get<SignedUrlResponse>(
      `/files/${fileId}/pdf/signed-url${version !== undefined ? `?version=${version}` : ""}`,
    ),
};
