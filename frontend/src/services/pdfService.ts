import { pdfApi } from "@/services/pdfApi";
import type { PDFMetadata, SignedUrlResponse } from "@udtp/shared";

/**
 * Thin business-logic layer over `pdfApi`, mirroring `previewService`.
 */
export const pdfService = {
  generateLatest(fileId: string, force = false): Promise<PDFMetadata> {
    return pdfApi.generate(fileId, force);
  },

  getLatestPdf(fileId: string): Promise<PDFMetadata> {
    return pdfApi.getLatest(fileId);
  },

  getSignedUrl(fileId: string, version?: number): Promise<SignedUrlResponse> {
    return pdfApi.getSignedUrl(fileId, version);
  },
};
