import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/apiClient";

/**
 * Single shared TanStack Query client. Feature modules import this instead
 * of instantiating their own, so caching/retry behavior stays consistent
 * app-wide.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // Never retry 4xx client errors (bad request, not found, validation, etc.)
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});
