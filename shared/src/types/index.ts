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
