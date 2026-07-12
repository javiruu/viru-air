"use client";

import type { ReactNode } from "react";

import type { QuickSearchLocale } from "@/modules/shared/quickSearchCopy";
import { QuickSearchPagination } from "@/modules/quick-search/components/QuickSearchPagination";

type Props = {
  side: "outbound" | "return";
  origin: string;
  destination: string;
  dateLabel: string;
  headerLabel: string;
  resultCount: number;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  children: ReactNode;

  // ── Optional pagination ──────────────────────────────────────────
  /** Current page (1‑based). */
  currentPage?: number;
  /** Total pages available. */
  totalPages?: number;
  /** Results per page. */
  pageSize?: number;
  /** Total results across all pages. */
  totalResults?: number;
  /** Called on page change. */
  onPageChange?: (page: number) => void;
  isPageChanging?: boolean;
  /** Locale for i18n. */
  locale?: QuickSearchLocale;
  onHoverStart?: () => void;
  onHoverEnd?: () => void;
};

/**
 * Individual panel inside {@link QuickSearchDualWorkspace}.
 *
 * Renders a header with side‑specific iconography, the route label,
 * and wraps children (results list, pagination, state panels).
 */
export function QuickSearchSidePanel({
  side,
  origin,
  destination,
  dateLabel,
  headerLabel,
  resultCount,
  collapsed,
  onToggleCollapse,
  children,
  currentPage,
  totalPages,
  pageSize,
  totalResults,
  onPageChange,
  isPageChanging,
  locale,
  onHoverStart,
  onHoverEnd,
}: Props) {
  const isOutbound = side === "outbound";

  return (
    <div
      className={`qs-dual-panel qs-dual-panel--${side}${collapsed ? " qs-dual-panel--collapsed" : ""}`}
      role="region"
      aria-label={headerLabel}
      onMouseEnter={onHoverStart}
      onMouseLeave={onHoverEnd}
    >
      {/* Header */}
      <header
        className="qs-dual-panel__header"
        onClick={onToggleCollapse}
        onKeyDown={
          onToggleCollapse
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onToggleCollapse();
                }
              }
            : undefined
        }
        {...(onToggleCollapse ? { role: "button", tabIndex: 0 } : {})}
      >
        <span className="qs-dual-panel__header-icon" aria-hidden="true">
          {isOutbound ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path
                d="M22 2L15 22L11 13L2 9L22 2Z"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path
                d="M2 22L9 2L13 11L22 15L2 22Z"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </span>
        <span className="qs-dual-panel__header-label">{headerLabel}</span>
        {resultCount > 0 ? (
          <span className="qs-dual-panel__header-count">{resultCount}</span>
        ) : null}
        <span className="qs-dual-panel__header-route">
          <span>{origin}</span>
          <svg
            className="qs-inline-icon"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M5 12h14M13 5l7 7-7 7"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span>{destination}</span>
        </span>
      </header>

      {/* Date badge */}
      <div className="qs-dual-panel__date">{dateLabel}</div>

      {/* Body */}
      <div className="qs-dual-panel__body">{children}</div>

      {/* Pagination */}
      {currentPage && totalPages && pageSize && totalResults != null && onPageChange ? (
        <div className="qs-dual-panel__footer">
          <QuickSearchPagination
            currentPage={currentPage}
            totalPages={totalPages}
            pageSize={pageSize}
            totalResults={totalResults}
            onPageChange={onPageChange}
            isPageChanging={isPageChanging}
            locale={locale}
          />
        </div>
      ) : null}

      {/* Collapse toggle for mobile */}
      {onToggleCollapse ? (
        <button
          type="button"
          className="qs-dual-panel__collapse-btn"
          aria-label={collapsed ? "Expandir" : "Colapsar"}
          onClick={(e) => {
            e.stopPropagation();
            onToggleCollapse();
          }}
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
            style={{ transform: collapsed ? "rotate(180deg)" : undefined, transition: "transform 200ms" }}
          >
            <path
              d="m6 9 6 6 6-6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      ) : null}
    </div>
  );
}
