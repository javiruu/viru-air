import type { AuthOut } from "@/modules/shared/auth";
import { apiFetchWithStatus } from "@/modules/shared/api";

export type LoginSubmitResult =
  | { kind: "success"; data: AuthOut }
  | { kind: "invalid_credentials" }
  | { kind: "server_error" }
  | { kind: "network_error" };

export async function submitLogin(email: string, password: string): Promise<LoginSubmitResult> {
  const result = await apiFetchWithStatus<AuthOut>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  if (result.ok) {
    return { kind: "success", data: result.data };
  }

  if (result.status === 0) {
    return { kind: "network_error" };
  }

  if (result.status === 401 && result.error.code === "invalid_auth") {
    return { kind: "invalid_credentials" };
  }

  if (result.status === 401) {
    return { kind: "invalid_credentials" };
  }

  return { kind: "server_error" };
}
