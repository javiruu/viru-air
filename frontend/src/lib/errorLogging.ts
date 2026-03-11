import { hasToken } from "@/modules/shared/auth";
import { apiFetchBestEffort } from "@/modules/shared/api";

export async function reportClientError(section: string, error: Error): Promise<void> {
  if (typeof window === "undefined") return;
  if (!hasToken()) return;

  await apiFetchBestEffort("/ux/errors", {
    method: "POST",
    body: JSON.stringify({
      section,
      message: error.message || "unknown_error",
      stack: error.stack || null,
    }),
    keepalive: true,
  });
}
