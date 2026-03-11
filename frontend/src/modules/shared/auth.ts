export type AuthOut = { access_token: string; token_type: string };

const TOKEN_KEY = "viru_token";

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

export function clearToken(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

export function hasToken(): boolean {
  return Boolean(getToken());
}
