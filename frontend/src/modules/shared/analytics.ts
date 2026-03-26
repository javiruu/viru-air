type AnalyticsValue = string | number | boolean | null | undefined;
type AnalyticsProps = Record<string, AnalyticsValue>;

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
    plausible?: (eventName: string, options?: { props?: Record<string, string | number | boolean> }) => void;
    posthog?: {
      capture?: (eventName: string, props?: Record<string, string | number | boolean>) => void;
    };
  }
}

function toPrimitiveProps(input: AnalyticsProps): Record<string, string | number | boolean> {
  const out: Record<string, string | number | boolean> = {};
  for (const [key, value] of Object.entries(input)) {
    if (value === null || value === undefined) continue;
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      out[key] = value;
    } else {
      out[key] = String(value);
    }
  }
  return out;
}

export function trackEvent(eventName: string, props: AnalyticsProps = {}): void {
  if (typeof window === "undefined") return;
  const payload = toPrimitiveProps(props);

  if (typeof window.gtag === "function") {
    window.gtag("event", eventName, payload);
  }
  if (typeof window.plausible === "function") {
    window.plausible(eventName, { props: payload });
  }
  if (typeof window.posthog?.capture === "function") {
    window.posthog.capture(eventName, payload);
  }
}
