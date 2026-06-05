"use client";

import { useMemo } from "react";
import type { QuickSearchLocale } from "@/modules/shared/quickSearchCopy";
import { getQuickSearchCopy } from "@/modules/shared/quickSearchCopy";

// ── Helpers ──────────────────────────────────────────────────────────

function getPageNumbers(current: number, total: number): (number | string)[] {
  const pages: (number | string)[] = [];
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i);
  } else {
    pages.push(1);
    if (current > 3) {
      pages.push("...");
    }
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    if (current < total - 2) {
      pages.push("...");
    }
    pages.push(total);
  }
  return pages;
}

// ── Types ────────────────────────────────────────────────────────────

type Props = {
  /** Current active page (1-based). */
  currentPage: number;
  /** Total number of pages available. */
  totalPages: number;
  /** Number of results per page. */
  pageSize: number;
  /** Total number of results across all pages. */
  totalResults: number;
  /** Called when the user navigates to a different page. */
  onPageChange: (page: number) => void;
  /** Current locale tag (e.g. "es" | "en") for i18n. */
  locale?: QuickSearchLocale;
  /** Optional className for the root element. */
  className?: string;
};

// ── Component ────────────────────────────────────────────────────────

/**
 * Reusable pagination for quick‑search result lists.
 *
 * Extracted from the inline pagination in {@link QuickSearchView}.  Shows
 * a range summary, previous/next buttons, and a page‑number strip with
 * ellipsis for long page sets.  Fully independent — no parent state coupling.
 */
export function QuickSearchPagination({
  currentPage,
  totalPages,
  pageSize,
  totalResults,
  onPageChange,
  locale = "es",
  className,
}: Props) {
  const { t } = getQuickSearchCopy(locale);
  const activePage = useMemo(
    () => Math.min(Math.max(1, currentPage), totalPages),
    [currentPage, totalPages],
  );

  if (totalPages <= 1) return null;

  const start = (activePage - 1) * pageSize + 1;
  const end = Math.min(activePage * pageSize, totalResults);

  return (
    <div
      className={`qs-pagination animate-fade-in${className ? ` ${className}` : ""}`}
      role="navigation"
      aria-label="Pagination"
    >
      <span className="qs-pagination-stats">
        {t("paginationShowing")
          .replace("{start}", String(start))
          .replace("{end}", String(end))
          .replace("{total}", String(totalResults))}
      </span>

      <div className="qs-pagination-nav">
        <button
          type="button"
          className="qs-pagination-btn"
          disabled={activePage === 1}
          aria-label={t("paginationPrev")}
          onClick={() => onPageChange(activePage - 1)}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="m15 6-6 6 6 6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

        <div className="qs-pagination-pages">
          {getPageNumbers(activePage, totalPages).map((num, idx) =>
            num === "..." ? (
              <span
                key={`ellipsis-${idx}`}
                className="qs-pagination-ellipsis"
                aria-hidden="true"
              >
                …
              </span>
            ) : (
              <button
                key={`page-${num}`}
                type="button"
                className={`qs-pagination-btn${num === activePage ? " active" : ""}`}
                aria-label={`Page ${num}`}
                aria-current={num === activePage ? "page" : undefined}
                onClick={() => onPageChange(Number(num))}
              >
                {num}
              </button>
            ),
          )}
        </div>

        <button
          type="button"
          className="qs-pagination-btn"
          disabled={activePage === totalPages}
          aria-label={t("paginationNext")}
          onClick={() => onPageChange(activePage + 1)}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="m9 6 6 6-6 6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
