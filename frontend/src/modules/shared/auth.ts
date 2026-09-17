export type AuthOut = { access_token: string; refresh_token?: string; token_type: string };

const DASHBOARD_LOGIN_REQUIRED_KEY = "viru_dashboard_login_required";

export const DASHBOARD_DEMO_ACCOUNT = {
  email: "user@viru.local",
  password: "ViruUser123",
} as const;

export function isDashboardLoginRequired(): boolean {
  if (typeof window === "undefined") return true;
  return window.localStorage.getItem(DASHBOARD_LOGIN_REQUIRED_KEY) !== "false";
}

export function saveDashboardLoginRequired(isRequired: boolean): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DASHBOARD_LOGIN_REQUIRED_KEY, isRequired ? "true" : "false");
}
