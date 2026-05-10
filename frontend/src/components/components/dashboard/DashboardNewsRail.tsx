"use client";

import Link from "next/link";

import type { DashboardNewsItem } from "@/data/dashboardNews";

type DashboardNewsRailProps = {
  item: DashboardNewsItem;
  localeTag: string;
};

export function DashboardNewsRail({ item, localeTag }: DashboardNewsRailProps) {
  const publishedLabel = formatPublishedDate(item.publishedAt, localeTag);

  return (
    <aside className="dashboard-news-rail" aria-labelledby="dashboard-news-title">
      <article className="dashboard-news-card">
        <div className="dashboard-news-media-wrap">
          <div
            className="dashboard-news-media"
            style={{ backgroundImage: `linear-gradient(180deg, color-mix(in srgb, var(--color-overlay) 18%, transparent), color-mix(in srgb, var(--color-overlay) 82%, transparent)), url("${item.image}")` }}
          />
          <span className="dashboard-news-chip">{item.eyebrow}</span>
        </div>

        <div className="dashboard-news-body">
          <div className="dashboard-news-copy">
            <p className="dashboard-news-kicker">Dispatch</p>
            <h3 id="dashboard-news-title">{item.title}</h3>
            <p className="dashboard-news-excerpt">{item.excerpt}</p>
          </div>

          <div className="dashboard-news-meta">
            <div className="dashboard-news-author-mark" aria-hidden="true">
              {item.author.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <strong>{item.author}</strong>
              <p>
                <time dateTime={item.publishedAt}>{publishedLabel}</time>
                <span aria-hidden="true"> · </span>
                <span>{item.readTime}</span>
              </p>
            </div>
          </div>

          <Link className="dashboard-news-link" href={item.href}>
            <span>{item.ctaLabel}</span>
            <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </article>
    </aside>
  );
}

function formatPublishedDate(value: string, localeTag: string) {
  try {
    return new Intl.DateTimeFormat(localeTag, {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(value));
  } catch {
    return value;
  }
}
