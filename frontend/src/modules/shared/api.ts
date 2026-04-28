import { translate } from "@/i18n";
import { getToken, hasToken } from "@/modules/shared/auth";

const RAW_API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").trim();

function resolveApiBase(rawBase: string): string {
  if (typeof window === "undefined") return rawBase;
  if (rawBase.startsWith("/")) return rawBase.replace(/\/$/, "");
  try {
    const parsed = new URL(rawBase);
    const currentHost = window.location.hostname;
    const currentProtocol = window.location.protocol;
    const isHttpsPage = currentProtocol === "https:";
    const isLocalApi = parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1";
    let didMutate = false;

    if (isHttpsPage && parsed.protocol === "http:") {
      parsed.protocol = "https:";
      didMutate = true;
    }

    if (isLocalApi && parsed.hostname !== currentHost) {
      parsed.hostname = currentHost;
      didMutate = true;
    }

    if (isHttpsPage && parsed.hostname === currentHost && parsed.port === "8000") {
      // WAN deployments usually terminate TLS on 443 and proxy /api internally.
      parsed.port = "";
      didMutate = true;
    }

    if (isHttpsPage && parsed.hostname === currentHost && parsed.pathname.startsWith("/api/")) {
      return parsed.pathname.replace(/\/$/, "");
    }

    if (didMutate) {
      return parsed.toString().replace(/\/$/, "");
    }
  } catch {
    return rawBase;
  }
  return rawBase;
}

const API_BASE = resolveApiBase(RAW_API_BASE);

function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) {
    return {};
  }
  return { Authorization: `Bearer ${token}` };
}

function correlationId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function applyAuthHeaders(mergedHeaders: Headers) {
  const auth = authHeaders();
  if (auth instanceof Headers) {
    auth.forEach((value, key) => mergedHeaders.set(key, value));
  } else if (Array.isArray(auth)) {
    auth.forEach(([key, value]) => mergedHeaders.set(key, value));
  } else {
    Object.entries(auth).forEach(([key, value]) => {
      if (value) mergedHeaders.set(key, value);
    });
  }
}

function shouldSetJsonContentType(init?: RequestInit): boolean {
  if (!init || init.body == null) {
    return false;
  }
  const body = init.body;
  if (typeof FormData !== "undefined" && body instanceof FormData) {
    return false;
  }
  if (typeof URLSearchParams !== "undefined" && body instanceof URLSearchParams) {
    return false;
  }
  if (typeof Blob !== "undefined" && body instanceof Blob) {
    return false;
  }
  if (typeof ArrayBuffer !== "undefined" && (body instanceof ArrayBuffer || ArrayBuffer.isView(body as ArrayBufferView))) {
    return false;
  }
  return true;
}

function buildHeaders(init?: RequestInit): Headers {
  const mergedHeaders = new Headers(init?.headers || {});
  if (shouldSetJsonContentType(init) && !mergedHeaders.has("Content-Type")) {
    mergedHeaders.set("Content-Type", "application/json");
  }
  mergedHeaders.set("x-correlation-id", correlationId());
  applyAuthHeaders(mergedHeaders);
  return mergedHeaders;
}

function clearStoredToken() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem("viru_token");
  }
}

function parseDetailCode(rawText: string): string | null {
  if (!rawText) return null;
  try {
    const parsed = JSON.parse(rawText) as { detail?: unknown };
    if (typeof parsed?.detail === "string") {
      return parsed.detail;
    }
  } catch {
    if (!rawText.trim().startsWith("{")) {
      return rawText.trim();
    }
  }
  return null;
}

function isExpiredSessionCode(code: string | null): boolean {
  return code === "invalid_token" || code === "invalid_auth" || code === "session_expired";
}

function isAuthEntryPath(path: string): boolean {
  return path === "/auth/login" || path === "/auth/register";
}

function isNetworkFailure(error: unknown): boolean {
  return error instanceof TypeError;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  if (path === "/auth/me" && !hasToken()) {
    throw new Error(translate("shared.errors.sessionRequired"));
  }
  const mergedHeaders = buildHeaders(init);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: mergedHeaders,
    });
  } catch (error) {
    if (isNetworkFailure(error)) {
      throw new Error(translate("shared.errors.generic"));
    }
    throw error;
  }

  if (!response.ok) {
    const text = await response.text();
    const detailCode = parseDetailCode(text);
    if (response.status === 401 && isExpiredSessionCode(detailCode)) {
      clearStoredToken();
      throw new Error(translate("shared.errors.sessionExpired"));
    }
    if (response.status === 401) {
      if (isAuthEntryPath(path) && text.trim().length > 0) {
        throw new Error(text);
      }
      throw new Error(translate("shared.errors.sessionRequired"));
    }
    throw new Error(text || `HTTP ${response.status}`);
  }

  return (await response.json()) as T;
}

export { API_BASE };

export async function apiFetchBestEffort(path: string, init?: RequestInit): Promise<void> {
  try {
    const mergedHeaders = buildHeaders(init);
    await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: mergedHeaders,
    });
  } catch {
    // best-effort by design
  }
}

export type ApiError = {
  status: number;
  code?: string;
  message: string;
  details?: unknown;
  retry_after_sec?: number;
  correlation_id?: string;
};

type ParsedErrorEnvelope = {
  code?: string;
  message?: string;
  details?: unknown;
  retry_after_sec?: number;
  correlation_id?: string;
};

function extractDetailMessage(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim().length > 0) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const first = detail[0];
    if (!first || typeof first !== "object") return null;
    const firstObj = first as Record<string, unknown>;
    const firstMsg = firstObj.msg;
    return typeof firstMsg === "string" && firstMsg.trim().length > 0 ? firstMsg : null;
  }
  return null;
}

function extractTopLevelErrorEnvelope(parsed: unknown): ParsedErrorEnvelope | null {
  if (!parsed || typeof parsed !== "object") return null;
  const candidate = parsed as Record<string, unknown>;
  const hasKnownKey = (
    "code" in candidate
    || "message" in candidate
    || "details" in candidate
    || "retry_after_sec" in candidate
    || "correlation_id" in candidate
  );
  if (!hasKnownKey) return null;
  return {
    code: typeof candidate.code === "string" ? candidate.code : undefined,
    message: typeof candidate.message === "string" ? candidate.message : undefined,
    details: candidate.details,
    retry_after_sec: typeof candidate.retry_after_sec === "number" ? candidate.retry_after_sec : undefined,
    correlation_id: typeof candidate.correlation_id === "string" ? candidate.correlation_id : undefined,
  };
}

export async function apiFetchWithStatus<T>(
  path: string,
  init?: RequestInit,
): Promise<
  | { ok: true; data: T; status: number; headers: Headers }
  | { ok: false; error: ApiError; status: number; headers: Headers }
> {
  if (path === "/auth/me" && !hasToken()) {
    return {
      ok: false,
      status: 401,
      headers: new Headers(),
      error: {
        status: 401,
        code: "UNAUTHORIZED",
        message: translate("shared.errors.sessionRequired"),
      },
    };
  }
  const mergedHeaders = buildHeaders(init);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: mergedHeaders,
    });
  } catch (error) {
    if (isNetworkFailure(error)) {
      return {
        ok: false,
        status: 0,
        headers: new Headers(),
        error: {
          status: 0,
          code: "NETWORK_ERROR",
          message: translate("shared.errors.generic"),
        },
      };
    }
    throw error;
  }

  if (!response.ok) {
    const rawText = await response.text();
    const detailCode = parseDetailCode(rawText);
    if (response.status === 401 && isExpiredSessionCode(detailCode)) {
      clearStoredToken();
      return {
        ok: false,
        status: response.status,
        headers: response.headers,
        error: {
          status: response.status,
          code: "INVALID_TOKEN",
          message: translate("shared.errors.sessionExpired"),
        },
      };
    }
    if (response.status === 401) {
      const authEntryMessage = isAuthEntryPath(path) && rawText.trim().length > 0 ? rawText : undefined;
      return {
        ok: false,
        status: response.status,
        headers: response.headers,
        error: {
          status: response.status,
          code: "UNAUTHORIZED",
          message: authEntryMessage || translate("shared.errors.sessionRequired"),
        },
      };
    }
    let parsed: unknown = null;
    try {
      parsed = rawText ? JSON.parse(rawText) : null;
    } catch {
      parsed = null;
    }
    const parsedObj = parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : null;
    const topLevelEnvelope = extractTopLevelErrorEnvelope(parsed);
    const errorObj =
      parsed && typeof parsed === "object" && "error" in (parsed as Record<string, unknown>)
        ? (parsed as { error?: Record<string, unknown> }).error || {}
        : null;
    const detail = parsedObj?.detail;
    const message =
      topLevelEnvelope?.message ||
      extractDetailMessage(detail) ||
      (errorObj?.message as string | undefined) ||
      (typeof rawText === "string" && rawText.trim().length > 0 ? rawText : `HTTP ${response.status}`);
    const retryAfter =
      topLevelEnvelope?.retry_after_sec ||
      (typeof errorObj?.retry_after_sec === "number"
        ? errorObj.retry_after_sec
        : Number(response.headers.get("retry-after")) || undefined);
    return {
      ok: false,
      status: response.status,
      headers: response.headers,
      error: {
        status: response.status,
        code: topLevelEnvelope?.code || (errorObj?.code as string | undefined) || undefined,
        message,
        details: topLevelEnvelope?.details ?? errorObj?.details ?? detail,
        retry_after_sec: retryAfter,
        correlation_id: topLevelEnvelope?.correlation_id || response.headers.get("x-correlation-id") || undefined,
      },
    };
  }

  const data = (await response.json()) as T;
  return { ok: true, data, status: response.status, headers: response.headers };
}
