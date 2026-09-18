import { createClient } from "@/lib/supabase/client";

type SupabaseAuthClient = ReturnType<typeof createClient>;

export async function submitForgotPassword(
  email: string,
  /** Injectable for tests; defaults to the Supabase browser client. */
  supabase: SupabaseAuthClient = createClient(),
): Promise<"success" | "error"> {
  try {
    const { error } = await supabase.auth.resetPasswordForEmail(email);
    return error ? "error" : "success";
  } catch {
    return "error";
  }
}
