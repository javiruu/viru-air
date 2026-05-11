"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { DashboardNewsRail } from "@/components/components/dashboard/DashboardNewsRail";
import { getDashboardFeaturedNews } from "@/data/dashboardNews";
import { useI18n } from "@/i18n";
import { useFtueHint } from "@/lib/ftue";
import { trackUxEvent } from "@/lib/uxTracking";
import { apiFetch } from "@/modules/shared/api";
import { trackEvent } from "@/modules/shared/analytics";

type Me = { id: string; email: string; locale: string; is_admin: boolean };
type Watch = { id: string; origin_iata: string; destination_iata: string; status: string };
type Note = { id: string; title: string; body: string; created_at: string; updated_at: string };

type BackendBanner = {
  severity: "warning" | "error";
  message: string;
};

type SuggestionBadgeType = "price" | "schedule" | "altAirport" | "risk";

type DashboardSuggestion = {
  id: string;
  title: string;
  detail: string;
  type: SuggestionBadgeType;
  origin: string;
  destination: string;
};

export default function DashboardPage() {
  const { t, localeTag } = useI18n();
  const [me, setMe] = useState<Me | null>(null);
  const [watches, setWatches] = useState<Watch[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [backendBanner, setBackendBanner] = useState<BackendBanner | null>(null);
  const dashboardHint = useFtueHint("dashboard");

  useEffect(() => {
    void trackUxEvent("dashboard_view");
  }, []);
  const [noteDraft, setNoteDraft] = useState({ title: "", body: "" });
  const [noteActiveId, setNoteActiveId] = useState<string | null>(null);
  const [noteStatus, setNoteStatus] = useState<string | null>(null);
  const [notesCollapsed, setNotesCollapsed] = useState(false);

  const loadDashboard = useCallback(async () => {
    try {
      const [meData, watchData, noteData] = await Promise.all([
        apiFetch<Me>("/auth/me"),
        apiFetch<Watch[]>("/watchlist"),
        apiFetch<Note[]>("/notes"),
      ]);
      setMe(meData);
      setWatches(watchData);
      setNotes(noteData);
      setBackendBanner(null);
    } catch {
      const fallback = t("dashboard.banner.warmMessage");
      setBackendBanner({
        severity: "warning",
        message: fallback,
      });
    }
  }, [t]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const formattedNoteDate = useCallback((value: string) => {
    if (!value) return "";
    try {
      return new Intl.DateTimeFormat(localeTag, {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(value));
    } catch (error) {
      return value;
    }
  }, [localeTag]);

  const formatRelative = useCallback(
    (value: string) => {
      if (!value) return t("dashboard.activity.noRecent");
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return t("dashboard.activity.noRecent");
      const diffMs = Date.now() - date.getTime();
      const hours = Math.max(0, Math.floor(diffMs / (1000 * 60 * 60)));
      if (hours < 1) return t("dashboard.activity.lastSearchLessHour");
      if (hours < 24) return t("dashboard.activity.lastSearchHours", { count: hours });
      const days = Math.floor(hours / 24);
      if (days < 7) return t("dashboard.activity.lastSearchDays", { count: days });
      const dateLabel = new Intl.DateTimeFormat(localeTag, { day: "2-digit", month: "short" }).format(date);
      return t("dashboard.activity.lastSearchDate", { date: dateLabel });
    },
    [localeTag, t]
  );

  const startNewNote = useCallback(() => {
    setNoteActiveId(null);
    setNoteDraft({ title: "", body: "" });
    setNoteStatus(null);
    setNotesCollapsed(false);
  }, []);

  const handleSelectNote = useCallback((note: Note) => {
    setNoteActiveId(note.id);
    setNoteDraft({ title: note.title ?? "", body: note.body ?? "" });
    setNoteStatus(null);
  }, []);

  const handleSaveNote = useCallback(async () => {
    const payload = {
      title: noteDraft.title.trim(),
      body: noteDraft.body.trim(),
    };
    if (!payload.title && !payload.body) {
      setNoteStatus(t("dashboard.notes.status.requireContent"));
      return;
    }
    try {
      if (noteActiveId) {
        const updated = await apiFetch<Note>(`/notes/${noteActiveId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        setNotes((prev) => prev.map((note) => (note.id === updated.id ? updated : note)));
        setNoteStatus(t("dashboard.notes.status.updated"));
      } else {
        const created = await apiFetch<Note>("/notes", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setNotes((prev) => [created, ...prev]);
        setNoteActiveId(created.id);
        setNoteStatus(t("dashboard.notes.status.created"));
      }
    } catch (error) {
      setNoteStatus(t("dashboard.notes.status.saveFail"));
    }
  }, [noteActiveId, noteDraft.body, noteDraft.title, t]);

  const handleDeleteNote = useCallback(
    async (noteId: string) => {
      try {
        await apiFetch(`/notes/${noteId}`, { method: "DELETE" });
        setNotes((prev) => prev.filter((note) => note.id !== noteId));
        if (noteActiveId === noteId) {
          startNewNote();
        }
        setNoteStatus(t("dashboard.notes.status.deleted"));
      } catch (error) {
        setNoteStatus(t("dashboard.notes.status.deleteFail"));
      }
    },
    [noteActiveId, startNewNote, t]
  );

  const userName = me?.email || me?.id || "Usuario";
  const userInitials = useMemo(() => {
    const clean = userName.trim();
    const [first, second] = clean.split(/[\s.@_-]+/).filter(Boolean);
    if (!first) return "US";
    if (!second) return first.slice(0, 2).toUpperCase();
    return `${first[0]}${second[0]}`.toUpperCase();
  }, [userName]);

  const sortedNotes = useMemo(
    () => [...notes].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()),
    [notes]
  );

  const activityLabel = useMemo(() => {
    const latestNote = sortedNotes[0];
    if (!latestNote) return t("dashboard.activity.noRecent");
    return formatRelative(latestNote.updated_at);
  }, [formatRelative, sortedNotes, t]);

  const topSuggestion = useMemo<DashboardSuggestion | null>(() => {
    if (watches.length === 0) return null;
    const first = watches[0];
    return {
      id: first.id,
      title: t("dashboard.suggestions.topTitle", {
        origin: first.origin_iata,
        destination: first.destination_iata,
      }),
      detail: t("dashboard.suggestions.topDetail"),
      type: "price",
      origin: first.origin_iata,
      destination: first.destination_iata,
    };
  }, [t, watches]);

  const recentActivity = useMemo(() => {
    const out: Array<{ id: string; text: string; when: string }> = [];
    if (sortedNotes[0]) {
      out.push({
        id: `note-${sortedNotes[0].id}`,
        text: t("dashboard.activity.noteUpdated", {
          title: sortedNotes[0].title || t("dashboard.activity.noteUntitled"),
        }),
        when: formattedNoteDate(sortedNotes[0].updated_at),
      });
    }
    watches.slice(0, 2).forEach((watch) => {
      out.push({
        id: `watch-${watch.id}`,
        text: t("dashboard.activity.watchActive", { origin: watch.origin_iata, destination: watch.destination_iata }),
        when: t("dashboard.activity.watchWhen"),
      });
    });
    if (out.length === 0) {
      out.push({
        id: "empty",
        text: t("dashboard.activity.emptyText"),
        when: t("dashboard.activity.now"),
      });
    }
    return out.slice(0, 3);
  }, [formattedNoteDate, sortedNotes, watches, t]);

  const hasPersonalSuggestions = watches.length > 0 || notes.length >= 2;
  const locale = me?.locale?.toUpperCase() || "ES";
  const hasOpportunity = Boolean(topSuggestion);
  const heroStatus = t("dashboard.hero.status", { count: watches.length, activity: activityLabel });
  const heroCtaHref = "/quick-search";
  const featuredNews = useMemo(() => getDashboardFeaturedNews(localeTag), [localeTag]);

  return (
    <main className="shell dashboard-shell" id="main-content">
      <section className="dashboard-top-stage">
        <div className="dashboard-top-main">
          <section className="dashboard-hero-state">
            <div className="dashboard-hero-content">
              <div className="dashboard-hero-title">
                <h2>{t("dashboard.hero.title")}</h2>
                <p className="dashboard-hero-status">{heroStatus}</p>
              </div>
              <div className="dashboard-hero-highlight">
                {watches.length === 0 ? (
                  <div className="hero-empty">
                    <strong>{t("dashboard.hero.onboardingTitle")}</strong>
                    <p>{t("dashboard.hero.onboardingBody")}</p>
                  </div>
                ) : hasOpportunity && topSuggestion ? (
                  <div className="hero-opportunity">
                    <div>
                      <span className="hero-label">{t("dashboard.hero.opportunityRouteLabel")}</span>
                      <strong>{topSuggestion.title}</strong>
                      <p>{topSuggestion.detail}</p>
                    </div>
                    <div className="hero-opportunity-metrics">
                      <div>
                        <span className="hero-label">{t("dashboard.hero.opportunityPriceLabel")}</span>
                        <strong>{t("dashboard.hero.opportunityValueUnknown")}</strong>
                      </div>
                      <div>
                        <span className="hero-label">{t("dashboard.hero.opportunityDeltaLabel")}</span>
                        <strong>{t("dashboard.hero.opportunityValueUnknown")}</strong>
                      </div>
                      <span className="status-pill success">{t("dashboard.hero.opportunityBadge")}</span>
                    </div>
                  </div>
                ) : (
                  <div className="hero-empty">
                    <strong>{t("dashboard.hero.noOpportunityTitle")}</strong>
                    <p>{t("dashboard.hero.noOpportunityBody")}</p>
                  </div>
                )}
              </div>
              <div className="dashboard-hero-actions">
                <Link
                  href={heroCtaHref}
                  className="btn-primary"
                  onClick={() => trackEvent("dashboard_click_hero_cta", { area: "dashboard", source: "hero" })}
                >
                  {t("dashboard.hero.ctaExplore")}
                </Link>
              </div>
            </div>
            <div className="dashboard-hero-side">
              <span className="lang-pill">{locale}</span>
            </div>
          </section>

          <section className="dashboard-section dashboard-section-manage">
            <div className="dashboard-section-head">
              <div>
                <h3>{t("dashboard.sections.manage")}</h3>
                <p>{t("dashboard.sections.manageHint")}</p>
              </div>
            </div>
            <div className="dashboard-primary-grid">
              <article className="module-card">
                <div className="module-head">
                  <h4 className="module-title">{t("dashboard.modules.watchlist.title")}</h4>
                  <span className="module-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M5 3h14v18l-7-4-7 4V3z" />
                    </svg>
                  </span>
                </div>
                <p className="module-desc">{t("dashboard.modules.watchlist.desc")}</p>
                <div className="module-actions">
                  <Link
                    href="/watchlist"
                    className="btn-secondary"
                    onClick={() => trackEvent("dashboard_click_watchlist", { area: "dashboard", source: "watchlist_card" })}
                  >
                    {t("dashboard.modules.watchlist.primary")}
                  </Link>
                  <Link href="/watchlist" className="link-subtle">
                    {t("dashboard.modules.watchlist.secondary")}
                  </Link>
                </div>
              </article>

              <article className="module-card">
                <div className="module-head">
                  <h4 className="module-title">{t("dashboard.modules.alerts.title")}</h4>
                  <span className="module-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 2a6 6 0 0 1 6 6v4l2 3H4l2-3V8a6 6 0 0 1 6-6z" />
                      <path d="M9 18a3 3 0 0 0 6 0" />
                    </svg>
                  </span>
                </div>
                <p className="module-desc">{t("dashboard.modules.alerts.desc")}</p>
                <div className="module-actions">
                  <Link
                    href="/alerts"
                    className="btn-secondary"
                    onClick={() => trackEvent("dashboard_alerts_open", { area: "dashboard", source: "alerts_card" })}
                  >
                    {t("dashboard.modules.alerts.primary")}
                  </Link>
                  <Link href="/alerts" className="link-subtle">
                    {t("dashboard.modules.alerts.secondary")}
                  </Link>
                </div>
              </article>
            </div>
          </section>
        </div>

        <DashboardNewsRail item={featuredNews} localeTag={localeTag} />
      </section>

      {dashboardHint.visible ? (
        <section className="notice notice-compact notice-info section-gap" role="status" aria-live="polite">
          <div>
            <strong>{t("dashboard.ftue.title")}</strong>
            <p>{t("dashboard.ftue.body")}</p>
          </div>
          <div className="notice-actions">
            <button type="button" className="btn-ghost btn-compact" onClick={dashboardHint.dismiss}>
              {t("dashboard.ftue.confirm")}
            </button>
          </div>
        </section>
      ) : null}

      {backendBanner ? (
        <section className={`notice notice-compact notice-${backendBanner.severity} section-gap`} role="status" aria-live="polite">
          <div>
            <strong>{t("dashboard.banner.title")}</strong>
            <p>{backendBanner.message}</p>
          </div>
          <div className="notice-actions">
            <button type="button" className="btn-secondary btn-compact" onClick={loadDashboard}>
              {t("dashboard.banner.retry")}
            </button>
          </div>
        </section>
      ) : null}

      <section className="dashboard-section">
        <div className="dashboard-section-head">
          <div>
            <h3>{t("dashboard.sections.opportunities")}</h3>
          </div>
        </div>
        <article className="module-card module-card-opportunity">
          <div className="module-head">
            <h4 className="module-title">{t("dashboard.opportunities.title")}</h4>
            <span className="module-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2l3 7 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z" />
              </svg>
            </span>
          </div>
          {hasPersonalSuggestions && topSuggestion ? (
            <div className="suggestions-card-content">
              <div className="suggestion-highlight">
                <strong>{topSuggestion.title}</strong>
                <p>{topSuggestion.detail}</p>
                <span className="suggestion-badge">
                  {t(`dashboard.suggestions.badgeType.${topSuggestion.type}` as const)}
                </span>
              </div>
            </div>
          ) : (
            <div className="suggestion-empty">
              <strong>{t("dashboard.opportunities.emptyTitle")}</strong>
              <p>{t("dashboard.opportunities.emptyBody")}</p>
            </div>
          )}
          <div className="module-actions">
            <Link
              href="/recomendaciones"
              className="btn-secondary"
              onClick={() => trackEvent("dashboard_click_suggestions", { area: "dashboard", source: "opportunities_card" })}
            >
              {t("dashboard.opportunities.cta")}
            </Link>
          </div>
        </article>
      </section>

      <section className="dashboard-section dashboard-secondary">
        <div className="dashboard-section-head dashboard-section-head-row">
          <h3>{t("dashboard.modules.activity.title")}</h3>
          <button type="button" className="link-subtle" onClick={loadDashboard}>
            {t("dashboard.modules.activity.button")}
          </button>
        </div>
        <ul className="activity-timeline">
          {recentActivity.map((item) => (
            <li key={item.id} className="activity-timeline-item">
              <span className="activity-dot" aria-hidden="true" />
              <div>
                <p>{item.text}</p>
                <span>{item.when}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className={`notes-board${notesCollapsed ? " is-collapsed" : ""}`} aria-label={t("dashboard.notes.boardLabel")}>
        <div className="notes-board-header">
          <div>
            <h3>{t("dashboard.notes.headerTitle")}</h3>
            <p>{t("dashboard.notes.headerBody")}</p>
          </div>
          <div className="notes-header-actions">
            <button className="btn-ghost btn-compact" type="button" onClick={startNewNote}>
              {t("dashboard.notes.newNote")}
            </button>
            <button className="btn-ghost btn-compact" type="button" onClick={() => setNotesCollapsed((prev) => !prev)}>
              {notesCollapsed ? t("dashboard.notes.expand") : t("dashboard.notes.collapse")}
            </button>
          </div>
        </div>
        {!notesCollapsed ? (
          <div className="notes-board-content">
            <div className="notes-panel">
              <div className="notes-form">
                <label className="notes-field">
                  <span>{t("dashboard.notes.fieldTitle")}</span>
                  <input
                    name="note_title"
                    autoComplete="off"
                    type="text"
                    value={noteDraft.title}
                    onChange={(event) => setNoteDraft((prev) => ({ ...prev, title: event.target.value }))}
                    placeholder={t("dashboard.notes.placeholderTitle")}
                  />
                </label>
                <label className="notes-field">
                  <span>{t("dashboard.notes.fieldContent")}</span>
                  <textarea
                    name="note_body"
                    autoComplete="off"
                    rows={6}
                    value={noteDraft.body}
                    onChange={(event) => setNoteDraft((prev) => ({ ...prev, body: event.target.value }))}
                    placeholder={t("dashboard.notes.placeholderContent")}
                  />
                </label>
                <div className="notes-actions">
                  <button className="btn-primary" type="button" onClick={handleSaveNote}>
                    {noteActiveId ? t("dashboard.notes.actions.saveChanges") : t("dashboard.notes.actions.save")}
                  </button>
                  {noteActiveId ? (
                    <button className="btn-ghost" type="button" onClick={() => handleDeleteNote(noteActiveId)}>
                      {t("dashboard.notes.actions.delete")}
                    </button>
                  ) : null}
                  {noteStatus ? (
                    <span className="notes-status" role="status" aria-live="polite">
                      {noteStatus}
                    </span>
                  ) : null}
                </div>
              </div>
            </div>
            <div className="notes-list">
              <div className="notes-list-header">
                <h4>{t("dashboard.notes.list.title")}</h4>
                <span>{t("dashboard.notes.list.count", { count: notes.length })}</span>
              </div>
              {notes.length === 0 ? (
                <div className="notes-empty">
                  <strong>{t("dashboard.notes.list.emptyTitle")}</strong>
                  <p>{t("dashboard.notes.list.emptyBody")}</p>
                </div>
              ) : (
                <div className="notes-cards">
                  {notes.map((note) => (
                    <button
                      key={note.id}
                      type="button"
                      className={`notes-card${noteActiveId === note.id ? " is-active" : ""}`}
                      onClick={() => handleSelectNote(note)}
                    >
                      <div className="notes-card-head">
                        <strong>{note.title || t("dashboard.notes.list.cardDefaultTitle")}</strong>
                        <span>{formattedNoteDate(note.updated_at)}</span>
                      </div>
                      <p>{note.body || t("dashboard.notes.list.cardDefaultBody")}</p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="notes-collapsed-hint">{t("dashboard.notes.collapsedHint")}</div>
        )}
      </section>
    </main>
  );
}


