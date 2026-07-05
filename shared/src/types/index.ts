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
 * foundation). Mirrors `backend/app/schemas/file.py::FileMetadata` and the
 * `files` table (`backend/sql/005_files.sql`) — field names are snake_case
 * to match the JSON the backend actually sends over the wire.
 */
export interface FileMetadata {
  id: string;
  company_id: string;
  storage_bucket: string;
  storage_path: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  checksum_sha256: string | null;
  uploaded_by: string | null;
  created_at: string;
}

/** A short-lived URL for downloading a stored file directly from storage. */
export interface SignedUrlResponse {
  url: string;
  expires_in: number;
}
