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
