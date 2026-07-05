import { env } from "@/config/env";
import { logger } from "@/lib/logger";
import { supabase } from "@/lib/supabaseClient";
import type { ApiResponse } from "@udtp/shared";

/**
 * Thin fetch wrapper — the single place that knows how to talk to the
 * backend. Every feature module's API hooks should call `apiClient.*`
 * instead of calling `fetch` directly, so auth headers, error normalization,
 * and base URL handling stay consistent.
 *
 * Every request attaches the current Supabase session's access token (if
 * any) as a Bearer token, mirroring the backend's `get_current_user`
 * dependency which expects exactly that.
 */

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: Record<string, unknown> | null;

  constructor(
    message: string,
    code: string,
    status: number,
    details?: Record<string, unknown> | null,
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = `${env.apiBaseUrl}${path}`;
  const { body, headers, ...rest } = options;
  const isFormData = body instanceof FormData;

  try {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    const response = await fetch(url, {
      ...rest,
      headers: {
        // FormData sets its own multipart Content-Type (with boundary) —
        // letting fetch generate that header itself is required.
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(session ? { Authorization: `Bearer ${session.access_token}` } : {}),
        ...headers,
      },
      body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    });

    const payload = (await response.json()) as ApiResponse<T>;

    if (!response.ok || payload.success === false) {
      const errPayload = payload as Extract<ApiResponse<T>, { success: false }>;
      const message = errPayload.error?.message ?? "Unexpected error";
      const code = errPayload.error?.code ?? "UNKNOWN_ERROR";
      logger.error("API request failed", { url, status: response.status, code, message });
      throw new ApiError(message, code, response.status, errPayload.error?.details);
    }

    return (payload as Extract<ApiResponse<T>, { success: true }>).data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    logger.error("Network or parsing error calling API", {
      url,
      error: error instanceof Error ? error.message : String(error),
    });
    throw new ApiError("Could not reach the server. Please try again.", "NETWORK_ERROR", 0);
  }
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PATCH", body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "DELETE" }),
  upload: <T>(path: string, formData: FormData, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body: formData }),
};
