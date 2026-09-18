/**
 * Custom fetch client mutator for Orval generated client.
 * Connects the OpenAPI generated calls to Viru Tracker authentication (Supabase Auth / Bearer tokens),
 * correlation tracking, and base URL resolution.
 */
import { createClient as createBrowserSupabaseClient } from "@/lib/supabase/client";

/**
 * Opaque per-request correlation id. Restores the observability contract of the
 * retired `apiFetch` helper: every request carries a unique `x-correlation-id`
 * so browser→API traces can be grouped without leaking PII.
 */
function generateCorrelationId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `corr-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
  }
}

export interface CustomClientConfig {
  url: string;
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH" | "HEAD" | "OPTIONS";
  params?: Record<string, unknown>;
  data?: unknown;
  headers?: HeadersInit;
  signal?: AbortSignal;
}

export async function customClient<T>(
  config: CustomClientConfig | string,
  options?: RequestInit,
): Promise<T> {
  let url: string;
  let init: RequestInit;

  if (typeof config === "string") {
    url = config;
    init = options || {};
  } else {
    url = config.url;
    const searchParams = new URLSearchParams();
    if (config.params) {
      for (const [key, value] of Object.entries(config.params)) {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      }
    }
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString;
    }

    const headers = new Headers(config.headers);
    if (config.data && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    init = {
      method: config.method,
      headers,
      body: config.data ? JSON.stringify(config.data) : undefined,
      signal: config.signal,
    };
  }

  const apiBase =
    typeof window !== "undefined"
      ? "/api/v1"
      : process.env.INTERNAL_API_URL || "http://127.0.0.1:8000/api/v1";

  const fullUrl = url.startsWith("http") ? url : apiBase + (url.startsWith("/") ? "" : "/") + url;

  const finalHeaders = new Headers(init.headers);
  if (!finalHeaders.has("x-correlation-id")) {
    finalHeaders.set("x-correlation-id", generateCorrelationId());
  }
  if (typeof window !== "undefined" && !finalHeaders.has("Authorization")) {
    try {
      const supabase = createBrowserSupabaseClient();
      const sessionResult = await supabase.auth.getSession();
      const token = sessionResult?.data?.session?.access_token;
      if (token) {
        finalHeaders.set("Authorization", `Bearer ${token}`);
      }
    } catch {
      // Offline or unconfigured in test fixture
    }
  }

  const response = await fetch(fullUrl, {
    ...init,
    headers: finalHeaders,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ message: response.statusText }));
    const error = new Error(
      errorBody.detail || errorBody.message || `Request failed with status ${response.status}`,
    ) as Error & {
      status?: number;
      correlation_id?: string;
      client_event_id?: string;
    };
    error.status = response.status;
    error.correlation_id =
      errorBody.correlation_id || response.headers.get("x-correlation-id") || undefined;
    error.client_event_id =
      errorBody.client_event_id || response.headers.get("x-client-event-id") || undefined;
    throw error;
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

export default customClient;
