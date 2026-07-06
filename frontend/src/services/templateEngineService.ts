import { templateEngineApi } from "@/services/templateEngineApi";
import type { TemplateMetadata } from "@udtp/shared";

/**
 * Thin business-logic layer over `templateEngineApi`. Foundation only — no
 * component calls this yet; no live preview, PDF generation, or value
 * filling happens here or anywhere in this module. It exists so a future
 * module (Live Preview, PDF Generation) has a single seam for
 * triggering/reading a template instead of calling `templateEngineApi` (or
 * `apiClient`) directly.
 */
export const templateEngineService = {
  triggerGeneration(fileId: string, force = false): Promise<TemplateMetadata> {
    return templateEngineApi.generate(fileId, force);
  },

  getLatestTemplate(fileId: string): Promise<TemplateMetadata> {
    return templateEngineApi.getLatest(fileId);
  },

  listTemplateVersions(fileId: string): Promise<TemplateMetadata[]> {
    return templateEngineApi.listVersions(fileId);
  },

  getTemplateVersion(fileId: string, version: number): Promise<TemplateMetadata> {
    return templateEngineApi.getVersion(fileId, version);
  },
};
