import { apiClient } from "@/lib/apiClient";
import type { ParsedDocumentMetadata } from "@udtp/shared";

/**
 * Parser Engine API client — the only place that knows the parsing
 * endpoint shapes. Feature modules should call this instead of
 * `apiClient` directly.
 */
export const parserApi = {
  parse: (fileId: string) => apiClient.post<ParsedDocumentMetadata>(`/files/${fileId}/parse`),
  getLatest: (fileId: string) => apiClient.get<ParsedDocumentMetadata>(`/files/${fileId}/parsed`),
};
