/**
 * Lightweight structured client-side logger.
 *
 * In development this pretty-prints to the console. In production it stays
 * silent for `debug`/`info` by default and is the single seam where we will
 * later wire up a remote logging/monitoring provider (e.g. Sentry) without
 * touching call sites throughout the app.
 */

type LogLevel = "debug" | "info" | "warn" | "error";

interface LogContext {
  [key: string]: unknown;
}

const isDev = import.meta.env.DEV;

function log(level: LogLevel, message: string, context?: LogContext): void {
  const timestamp = new Date().toISOString();
  const payload = { timestamp, level, message, ...context };

  if (!isDev && (level === "debug" || level === "info")) {
    return;
  }

  const consoleMethod =
    level === "debug"
      ? console.debug
      : level === "info"
        ? console.info
        : level === "warn"
          ? console.warn
          : console.error;

  if (isDev) {
    consoleMethod(`[${timestamp}] [${level.toUpperCase()}] ${message}`, context ?? "");
  } else {
    // Structured single-line output, easier to ship to a log aggregator later.
    consoleMethod(JSON.stringify(payload));
  }
}

export const logger = {
  debug: (message: string, context?: LogContext) => log("debug", message, context),
  info: (message: string, context?: LogContext) => log("info", message, context),
  warn: (message: string, context?: LogContext) => log("warn", message, context),
  error: (message: string, context?: LogContext) => log("error", message, context),
};
