/**
 * Shared constants.
 *
 * Only cross-cutting, module-agnostic constants live here for now
 * (e.g. supported file types, from the product spec). Feature-specific
 * constants (template statuses, variable types, etc.) will be added in
 * their owning modules.
 */

export const SUPPORTED_DOCUMENT_TYPES = [
  "pdf-text",
  "pdf-scanned",
  "docx",
  "xls",
  "xlsx",
  "png",
  "jpg",
  "jpeg",
  "webp",
] as const;

export type SupportedDocumentType = (typeof SUPPORTED_DOCUMENT_TYPES)[number];

export const API_V1_PREFIX = "/api/v1";
