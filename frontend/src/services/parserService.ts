import { parserApi } from "@/services/parserApi";
import type { ParsedDocumentMetadata } from "@udtp/shared";

/**
 * Thin business-logic layer over `parserApi`. Foundation only — no
 * component calls this yet; no preview/rendering happens here or anywhere
 * in this module. It exists so a future module (AI Extraction, Template
 * Engine) has a single seam for triggering/reading a parse instead of
 * calling `parserApi` (or `apiClient`) directly.
 */
export const parserService = {
  triggerParse(fileId: string): Promise<ParsedDocumentMetadata> {
    return parserApi.parse(fileId);
  },

  getParsedDocument(fileId: string): Promise<ParsedDocumentMetadata> {
    return parserApi.getLatest(fileId);
  },
};
