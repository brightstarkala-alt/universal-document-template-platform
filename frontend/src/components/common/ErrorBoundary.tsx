import { Component, type ErrorInfo, type ReactNode } from "react";
import { logger } from "@/lib/logger";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * Global React error boundary.
 * Catches render-time errors anywhere below it in the tree and shows a
 * graceful fallback instead of a blank white screen. Wrapped around the
 * whole app in `App.tsx`.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    logger.error("Unhandled error caught by ErrorBoundary", {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
    });
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="flex h-screen w-full flex-col items-center justify-center gap-2 bg-gray-50 px-4 text-center">
            <h1 className="text-xl font-semibold text-gray-900">Something went wrong</h1>
            <p className="max-w-md text-sm text-gray-500">
              An unexpected error occurred. Please refresh the page. If the problem persists,
              contact support.
            </p>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
