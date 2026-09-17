import { createClient } from "@/lib/supabase/client";
import { createUxEventApiV1UxEventsPost } from "@/api/generated/ux/ux";

type UxMeta = Record<string, string | number | boolean | null | undefined>;

function compactMeta(input: UxMeta = {}): Record<string, string | number | boolean | null> {
  const out: Record<string, string | number | boolean | null> = {};
  for (const [key, value] of Object.entries(input)) {
    if (value === undefined) continue;
    if (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean" ||
      value === null
    ) {
      out[key] = value;
    } else {
      out[key] = String(value);
    }
  }
  return out;
}

export async function trackUxEvent(eventName: string, metadata: UxMeta = {}): Promise<void> {
  if (typeof window === "undefined") return;
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) return;

  const payload = {
    event_name: eventName,
    duration_ms:
      typeof metadata.duration_ms === "number" ? Number(metadata.duration_ms) : undefined,
    metadata: compactMeta(metadata),
  };

  try {
    await createUxEventApiV1UxEventsPost(payload);
  } catch {}
}
