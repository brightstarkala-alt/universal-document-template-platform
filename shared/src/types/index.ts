/**
 * Shared domain types.
 *
 * IMPORTANT (Module 1 scope note):
 * This file intentionally contains no business/domain models yet
 * (no Template, Variable, Document, Tenant, etc.). Those are introduced
 * in their respective feature modules. For now we only define the
 * generic, cross-cutting contracts every module will build on top of.
 */

/** Standard shape returned by every backend error response. */
export interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown> | null;
    requestId?: string;
  };
}

/** Standard shape returned by every successful backend response. */
export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
}

export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;

/** Generic paginated list envelope, reused by future list endpoints. */
export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

/** Health check response contract (used by Module 1's health endpoint). */
export interface HealthCheckResponse {
  status: "ok" | "degraded" | "down";
  environment: string;
  version: string;
  timestamp: string;
}

/**
 * The authenticated user's company (Module 3: multi-tenant foundation).
 * Every user belongs to exactly one company — see
 * `backend/sql/002_company_members.sql`.
 */
export interface CurrentCompany {
  id: string;
  name: string;
  slug: string;
  role: "owner" | "admin" | "member";
}

/**
 * Metadata for a file stored in Supabase Storage (Module 4: storage
 * foundation; Module 5: upload engine). Mirrors
 * `backend/app/schemas/file.py::FileMetadata` and the `files` table
 * (`backend/sql/005_files.sql`, hardened by
 * `backend/sql/007_files_upload_hardening.sql`) — field names are
 * snake_case to match the JSON the backend actually sends over the wire.
 */
export interface FileMetadata {
  id: string;
  company_id: string;
  storage_bucket: string;
  storage_path: string;
  original_filename: string;
  extension: string;
  content_type: string;
  size_bytes: number;
  checksum_sha256: string;
  uploaded_by: string | null;
  uploaded_at: string;
}

/** A short-lived URL for downloading a stored file directly from storage. */
export interface SignedUrlResponse {
  url: string;
  expires_in: number;
}

/**
 * Metadata for one parse attempt (Module 6: parser engine). Mirrors
 * `backend/app/schemas/parsed_document.py::ParsedDocumentMetadata` and the
 * `parsed_documents` table (`backend/sql/008_parsed_documents.sql`). The
 * full Universal Document Model JSON itself is not modeled here — later
 * modules that consume it (AI Extraction, Template Engine) read it
 * server-side from `storage_path`, not through this frontend type.
 */
export interface ParsedDocumentMetadata {
  id: string;
  company_id: string;
  file_id: string;
  schema_version: string;
  parser_name: string;
  parser_version: string;
  status: "pending" | "processing" | "completed" | "completed_with_errors" | "failed";
  storage_path: string | null;
  unit_count: number | null;
  text_block_count: number | null;
  image_count: number | null;
  cell_grid_count: number | null;
  cell_count: number | null;
  character_count: number | null;
  duration_ms: number | null;
  error_message: string | null;
  created_at: string;
}

/**
 * Metadata for one AI field extraction attempt (Module 7: AI field
 * extraction). Mirrors `backend/app/schemas/ai_extraction_metadata.py::AIExtractionMetadata`
 * and the `ai_extractions` table (`backend/sql/009_ai_extractions.sql`).
 * Every extraction is versioned and append-only — a re-run of the same file
 * never overwrites a previous `version`. The full extracted fields/tables
 * JSON itself is not modeled here — later modules that consume it (Template
 * Engine) read it server-side from `storage_path`, not through this
 * frontend type. Deliberately excludes any calculated OpenAI dollar cost —
 * `model` + `prompt_tokens` + `completion_tokens` are stored instead.
 */
export interface AIExtractionMetadata {
  id: string;
  company_id: string;
  file_id: string;
  parsed_document_id: string;
  version: number;
  schema_version: string;
  source_checksum_sha256: string;
  model: string;
  prompt_version: string;
  status: "pending" | "processing" | "completed" | "completed_with_errors" | "failed";
  storage_path: string | null;
  field_count: number | null;
  table_count: number | null;
  low_confidence_count: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  duration_ms: number | null;
  error_message: string | null;
  created_at: string;
}

/**
 * Metadata for one template-generation attempt (Module 8: Template
 * Engine). Mirrors `backend/app/schemas/template_metadata.py::TemplateMetadata`
 * and the `templates` table (`backend/sql/010_templates.sql`). Every
 * template is versioned and append-only — a re-run never overwrites a
 * previous `version`. The full template artifact (`{ html, css, manifest }`
 * as one JSON object — see `backend/app/schemas/template.py::TemplateArtifact`)
 * is not modeled here — a later rendering module reads it server-side from
 * `storage_path`, not through this frontend type.
 */
export interface TemplateMetadata {
  id: string;
  company_id: string;
  file_id: string;
  source_ai_extraction_id: string;
  source_parsed_document_id: string;
  version: number;
  schema_version: string;
  generator_version: string;
  status: "pending" | "processing" | "completed" | "completed_with_errors" | "failed";
  storage_path: string | null;
  field_count: number | null;
  section_count: number | null;
  asset_count: number | null;
  page_count: number | null;
  duration_ms: number | null;
  error_message: string | null;
  created_at: string;
}

/** Mirrors `backend/app/schemas/ai_extraction.py::FieldType`. */
export type FieldType =
  | "text"
  | "long_text"
  | "number"
  | "currency"
  | "date"
  | "boolean"
  | "email"
  | "phone"
  | "identifier"
  | "address"
  | "signature_image"
  | "percentage";

/** Mirrors `backend/app/schemas/ai_extraction.py::ConfidenceTier`. */
export type ConfidenceTier = "high" | "medium" | "low";

/**
 * One page/sheet entry in a template's manifest (Module 8). `unit_system`
 * records which physical-sizing rule applies: real points for PDF/DOCX,
 * pixels for a standalone image, or no physical size at all (row/col
 * extents only) for an XLSX sheet.
 */
export interface TemplateManifestPage {
  unit_index: number;
  unit_type: "page" | "sheet";
  unit_system: "pt" | "px" | "grid";
  width: number | null;
  height: number | null;
  row_count: number | null;
  col_count: number | null;
}

/**
 * One scalar field placed in a template's HTML as a
 * `<span data-field-id data-machine-key>` marker. `field_id` is immutable
 * and is the only key a renderer should bind against; `machine_key` is
 * editable and purely for legibility.
 */
export interface TemplateManifestField {
  field_id: string;
  machine_key: string;
  display_label: string;
  type: FieldType;
  sample_value: string;
  confidence: number;
  confidence_tier: ConfidenceTier;
  unit_index: number;
}

export interface TemplateManifestColumn {
  column_key: string;
  display_label: string;
  type: FieldType;
}

/**
 * One repeating section (a grid-based line-item table). `section_id` is
 * immutable (reused from Module 7's `table_id`); `section_key` is
 * editable. Marked in the HTML as `data-section-id`/`data-section-key` on
 * a `<tbody>` and its single templated `<tr>`, which also carries
 * `data-repeating-row="true"` and `data-row-template="true"`.
 */
export interface TemplateManifestSection {
  section_id: string;
  section_key: string;
  unit_index: number;
  columns: TemplateManifestColumn[];
  sample_row_count: number;
  confidence: number;
  confidence_tier: ConfidenceTier;
}

/**
 * One image asset. `asset_id` is immutable and identical to Module 6's
 * `ImageBlock.asset_id` — marked in the HTML as `<img data-asset-id>`.
 * `original_path` is a stable Storage path, never a signed URL (a signed
 * URL expires; a stored template must not contain anything that does) —
 * resolving it to a fetchable URL is the Preview Renderer's job (Module 9).
 */
export interface TemplateManifestAsset {
  asset_id: string;
  original_path: string;
  mime_type: string;
  width: number;
  height: number;
  role: "content_image" | "signature";
}

export interface TemplateManifestMetadata {
  source_format: string;
  page_count: number;
  sheet_count: number;
  field_count: number;
  section_count: number;
  asset_count: number;
  unmapped_field_count: number;
  unmapped_section_count: number;
  duration_ms: number;
  warnings: string[];
}

/**
 * Formal manifest describing everything in a template — fields, repeating
 * sections, assets, pages, and metadata — so a client never needs to parse
 * the HTML to know what's in it. Mirrors
 * `backend/app/schemas/template.py::TemplateManifest`.
 */
export interface TemplateManifest {
  pages: TemplateManifestPage[];
  fields: TemplateManifestField[];
  repeating_sections: TemplateManifestSection[];
  assets: TemplateManifestAsset[];
  metadata: TemplateManifestMetadata;
}

/**
 * The full, persisted template (Module 8). `html` is body-level markup
 * only (one `<section class="page">` per unit) with no templating syntax
 * of any kind — only plain `data-*` markers. Combining it with `css` into
 * a standalone document is a fixed, trivial concatenation:
 * `<html><head><style>{css}</style></head><body>{html}</body></html>`.
 * Mirrors `backend/app/schemas/template.py::TemplateArtifact` — a Preview
 * Renderer (Module 9) must render this exactly as generated, never modify
 * it.
 */
export interface TemplateArtifact {
  schema_version: string;
  generator_version: string;
  source_ai_extraction_id: string;
  source_parsed_document_id: string;
  version: number;
  generated_at: string;
  html: string;
  css: string;
  manifest: TemplateManifest;
}

/**
 * Response from a Preview Renderer endpoint (Module 9). `artifact` is
 * byte-for-byte what Module 8 persisted; `asset_urls` is a sibling map
 * (asset_id -> short-lived signed URL) resolved fresh on every request —
 * never baked into the artifact itself.
 */
export interface TemplatePreviewResponse {
  artifact: TemplateArtifact;
  asset_urls: Record<string, string>;
}
