import { apiClient } from "@/lib/apiClient";
import type { FileMetadata, SignedUrlResponse } from "@udtp/shared";

/**
 * Storage API client — the only place that knows the `/files` endpoint
 * shapes. Feature modules (a future file browser, download button, etc.)
 * should call this instead of `apiClient` directly.
 */
export const fileApi = {
  list: () => apiClient.get<FileMetadata[]>("/files"),
  get: (fileId: string) => apiClient.get<FileMetadata>(`/files/${fileId}`),
  getSignedUrl: (fileId: string) => apiClient.get<SignedUrlResponse>(`/files/${fileId}/signed-url`),
  upload: (file: File) => {
    const formData = new FormData();
    // Field name must match the backend's `UploadFile` parameter name
    // (`upload`) in app/api/v1/files.py.
    formData.append("upload", file);
    return apiClient.upload<FileMetadata>("/files", formData);
  },
};
