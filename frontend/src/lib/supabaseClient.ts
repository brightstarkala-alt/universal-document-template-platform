import { createClient } from "@supabase/supabase-js";
import { env } from "@/config/env";

/**
 * Single Supabase client instance for the whole app. Feature code should
 * import `supabase` from here instead of calling `createClient` again —
 * multiple clients would each run their own auth-refresh timers and could
 * disagree on session state.
 */
export const supabase = createClient(env.supabaseUrl, env.supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
