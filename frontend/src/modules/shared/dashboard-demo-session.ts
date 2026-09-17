/**
 * Dashboard demo auto-entry.
 *
 * NOTE (2026-09-16): the demo account depends on the legacy `/auth/login`
 * endpoint, which the Supabase Auth cutover decommissioned (HTTP 410). The
 * toggle remains wired for product continuity but is currently inert — the
 * login submit always fails and RequireAuth falls back to the normal redirect.
 * Re-enable by pointing `submitLogin` at Supabase Auth or a restored endpoint.
 */
import {
  DASHBOARD_DEMO_ACCOUNT,
  isDashboardLoginRequired,
  saveAuthTokens,
} from "@/modules/shared/auth";
import { submitLogin } from "@/modules/shared/login-submit";

export function isDashboardDemoAccessEnabled(): boolean {
  return !isDashboardLoginRequired();
}

export async function signInDashboardDemoAccount(): Promise<boolean> {
  if (!isDashboardDemoAccessEnabled()) return false;
  const result = await submitLogin(DASHBOARD_DEMO_ACCOUNT.email, DASHBOARD_DEMO_ACCOUNT.password);
  if (result.kind !== "success") return false;
  saveAuthTokens(result.data);
  return true;
}
