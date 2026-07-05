/**
 * Single source of truth for reading Vite environment variables.
 * Never read `import.meta.env` directly outside this file — that keeps
 * env-var validation and typing centralized as the app grows.
 */

function readEnv(key: keyof ImportMetaEnv, required = false): string {
  const value = import.meta.env[key];
  if (required && !value) {
    throw new Error(
      `Missing required environment variable: ${key}. Check your .env file against .env.example.`,
    );
  }
  return value ?? "";
}

export const env = {
  apiBaseUrl: readEnv("VITE_API_BASE_URL", true),
  supabaseUrl: readEnv("VITE_SUPABASE_URL"),
  supabaseAnonKey: readEnv("VITE_SUPABASE_ANON_KEY"),
  mode: import.meta.env.MODE,
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
};
