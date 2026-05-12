import { apiFetchWithStatus } from "@/modules/shared/api";

export async function submitForgotPassword(email: string): Promise<"success" | "error"> {
  try {
    const result = await apiFetchWithStatus<{ message: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
    return result.ok ? "success" : "error";
  } catch {
    return "error";
  }
}
