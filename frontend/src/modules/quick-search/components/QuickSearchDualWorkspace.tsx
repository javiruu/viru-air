"use client";

import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  /** i18n aria-label for the workspace. Defaults to "Round‑trip results" in English. */
  ariaLabel?: string;
};

/**
 * Dual‑panel workspace for quick‑search.
 *
 * On desktop (≥900px) renders a two‑column grid with a central divider.
 * On mobile (<900px) renders stacked, collapsible panels.
 */
export function QuickSearchDualWorkspace({ children, ariaLabel = "Round‑trip results" }: Props) {
  return (
    <section className="qs-dual-workspace" role="region" aria-label={ariaLabel}>
      {children}
    </section>
  );
}
