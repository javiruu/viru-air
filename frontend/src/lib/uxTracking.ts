import { hasToken } from "@/modules/shared/auth";
import { apiFetchBestEffort } from "@/modules/shared/api";

type UxMeta = Record<string, string | number | boolean | null | undefined>;

function compactMeta(input: UxMeta = {}): Record<string, string | number | boolean | null> {
  const out: Record<string, string | number | boolean | null> = {};
  for (const [key, value] of Object.entries(input)) {
    if (value === undefined) continue;
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean" || value === null) {
      out[key] = value;
    } else {
      out[key] = String(value);
    }
  }
  return out;
}

export async function trackUxEvent(eventName: string, metadata: UxMeta = {}): Promise<void> {
  if (typeof window === "undefined") return;
  if (!hasToken()) return;

  const payload = {
    event_name: eventName,
    duration_ms: typeof metadata.duration_ms === "number" ? Number(metadata.duration_ms) : undefined,
    metadata: compactMeta(metadata),
  };

  await apiFetchBestEffort("/ux/events", {
    method: "POST",
    body: JSON.stringify(payload),
    keepalive: true,
  });
}
