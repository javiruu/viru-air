import { ReactNode } from "react";

export function QuickSearchSetupPanel({ children }: { children: ReactNode }) {
  return <section className="qs-setup-panel">{children}</section>;
}
