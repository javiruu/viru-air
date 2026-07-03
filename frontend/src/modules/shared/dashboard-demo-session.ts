import { DASHBOARD_DEMO_ACCOUNT, isDashboardLoginRequired, saveAuthTokens } from "@/modules/shared/auth";
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
