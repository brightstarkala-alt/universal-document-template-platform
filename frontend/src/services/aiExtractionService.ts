import { aiExtractionApi } from "@/services/aiExtractionApi";
import type { AIExtractionMetadata } from "@udtp/shared";

/**
 * Thin business-logic layer over `aiExtractionApi`. Foundation only — no
 * component calls this yet; no field-review UI, template generation, or
 * preview happens here or anywhere in this module. It exists so a future
 * module (Template Engine) has a single seam for triggering/reading an
 * extraction instead of calling `aiExtractionApi` (or `apiClient`) directly.
 */
export const aiExtractionService = {
  triggerExtraction(fileId: string, force = false): Promise<AIExtractionMetadata> {
    return aiExtractionApi.extract(fileId, force);
  },

  getLatestExtraction(fileId: string): Promise<AIExtractionMetadata> {
    return aiExtractionApi.getLatest(fileId);
  },

  listExtractionVersions(fileId: string): Promise<AIExtractionMetadata[]> {
    return aiExtractionApi.listVersions(fileId);
  },

  getExtractionVersion(fileId: string, version: number): Promise<AIExtractionMetadata> {
    return aiExtractionApi.getVersion(fileId, version);
  },
};
