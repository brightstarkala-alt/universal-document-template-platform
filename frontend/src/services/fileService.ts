import { fileApi } from "@/services/fileApi";
import type { FileMetadata } from "@udtp/shared";

/**
 * Thin business-logic layer over `fileApi`. Foundation only — no
 * component calls this yet; it exists so the future file browser /
 * document list modules have a single seam for file reads instead of
 * calling `fileApi` (or `apiClient`) directly.
 */
export const fileService = {
  listFiles(): Promise<FileMetadata[]> {
    return fileApi.list();
  },

  getFile(fileId: string): Promise<FileMetadata> {
    return fileApi.get(fileId);
  },
};
