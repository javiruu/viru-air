import { createClient } from "@/lib/supabase/client";

export async function submitForgotPassword(email: string): Promise<"success" | "error"> {
  try {
    const supabase = createClient();
    const { error } = await supabase.auth.resetPasswordForEmail(email);
    return error ? "error" : "success";
  } catch {
    return "error";
  }
}
