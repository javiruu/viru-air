export type AuthOut = { access_token: string; refresh_token?: string; token_type: string };

const TOKEN_KEY = "viru_token";
const REFRESH_TOKEN_KEY = "viru_refresh_token";
const DASHBOARD_LOGIN_REQUIRED_KEY = "viru_dashboard_login_required";

export const DASHBOARD_DEMO_ACCOUNT = {
  email: "user@viru.local",
  password: "ViruUser123",
} as const;

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(TOKEN_KEY);
  if (!raw) return null;
  if (raw === "null" || raw === "undefined") {
    window.localStorage.removeItem(TOKEN_KEY);
    return null;
  }
  return raw;
}

export function saveToken(token: string): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(TOKEN_KEY, token);
  }
}

export function saveRefreshToken(token: string | null | undefined): void {
  if (typeof window === "undefined") return;
  if (!token) {
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    return;
  }
  window.localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!raw || raw === "null" || raw === "undefined") {
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    return null;
  }
  return raw;
}

export function saveAuthTokens(tokens: AuthOut): void {
  saveToken(tokens.access_token);
  saveRefreshToken(tokens.refresh_token);
}

export function clearToken(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function hasToken(): boolean {
  return Boolean(getToken());
}

export function isDashboardLoginRequired(): boolean {
  if (typeof window === "undefined") return true;
  return window.localStorage.getItem(DASHBOARD_LOGIN_REQUIRED_KEY) !== "false";
}

export function saveDashboardLoginRequired(isRequired: boolean): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DASHBOARD_LOGIN_REQUIRED_KEY, isRequired ? "true" : "false");
}
