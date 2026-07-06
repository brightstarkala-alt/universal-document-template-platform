import { previewApi } from "@/services/previewApi";
import type { SignedUrlResponse, TemplatePreviewResponse } from "@udtp/shared";

/**
 * Thin business-logic layer over `previewApi`. All interactive rendering
 * logic (marker detection, value overrides, hover/click handling) lives in
 * `@/lib/templatePreviewRenderer` and the `PreviewPage` component — this
 * service only fetches data, it never touches the DOM.
 */
export const previewService = {
  getLatestPreview(fileId: string): Promise<TemplatePreviewResponse> {
    return previewApi.getLatest(fileId);
  },

  getPreviewVersion(fileId: string, version: number): Promise<TemplatePreviewResponse> {
    return previewApi.getVersion(fileId, version);
  },

  refreshAssetUrl(fileId: string, assetId: string, version?: number): Promise<SignedUrlResponse> {
    return previewApi.refreshAssetUrl(fileId, assetId, version);
  },
};
