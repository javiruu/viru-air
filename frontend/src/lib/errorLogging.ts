import { hasToken } from "@/modules/shared/auth";
import { apiFetchBestEffort } from "@/modules/shared/api";

const MAX_SECTION_LEN = 64;
const MAX_MESSAGE_LEN = 500;
const MAX_STACK_LEN = 8000;

function truncate(value: string | null | undefined, limit: number): string | null {
  if (!value) return null;
  const cleaned = value.trim();
  if (!cleaned) return null;
  return cleaned.length > limit ? cleaned.slice(0, limit) : cleaned;
}

export async function reportClientError(section: string, error: Error): Promise<void> {
  if (typeof window === "undefined") return;
  if (!hasToken()) return;

  const safeSection = truncate(section, MAX_SECTION_LEN) || "unknown";
  const safeMessage = truncate(error.message || "unknown_error", MAX_MESSAGE_LEN) || "unknown_error";
  const safeStack = truncate(error.stack || null, MAX_STACK_LEN);

  await apiFetchBestEffort("/ux/errors", {
    method: "POST",
    body: JSON.stringify({
      section: safeSection,
      message: safeMessage,
      stack: safeStack,
    }),
    keepalive: true,
  });
}
