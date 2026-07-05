/**
 * Shared framework-agnostic utility functions.
 * Keep this dependency-free (no React, no Node-only APIs) so it can be
 * safely imported from the frontend bundle.
 */

/** Type guard for narrowing an ApiResponse to its success variant. */
export function isApiSuccess<T>(
  response: { success: boolean },
): response is { success: true } & { data: T } {
  return response.success === true;
}
