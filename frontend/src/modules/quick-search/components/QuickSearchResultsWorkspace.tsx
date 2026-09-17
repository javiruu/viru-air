import type { ReactNode } from "react";

export function QuickSearchResultsWorkspace({ children }: { children: ReactNode }) {
  return <section className="qs-results-workspace">{children}</section>;
}
