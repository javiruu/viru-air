"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { trackUxEvent } from "@/lib/uxTracking";
import { getDeliveryStateCopy, getNotificationChannelCopy } from "@/modules/alerts/deliveryPresentation";
import { apiFetch } from "@/modules/shared/api";
import { formatCurrency, formatRelativeTime } from "@/modules/shared/format";
import { getDeliveryStatusMeta, getWatchStatusMeta } from "@/modules/shared/statusCatalog";

type Watch = {
  id: string;
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
};

type AlertRule = {
  id: string;
  watch_id: string;
  rule_type: string;
  cooldown_minutes: number;
  enabled: boolean;
  threshold_value?: number | null;
  min_change_pct?: number | null;
  notify_on_every_change?: boolean;
};

type AlertEvent = {
  id: string;
  rule_id: string;
  watch_id: string;
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
  channel: string;
  delivery_status: string;
  attempts?: number;
  next_attempt_at?: string | null;
  last_error?: string | null;
  delivered_at?: string | null;
  is_digest?: boolean;
  grouped_count?: number;
  group_reason?: string | null;
  message: string;
  created_at: string;
};

type QuietHoursPreference = {
  quiet_hours_enabled: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  quiet_hours_timezone: string | null;
};

type AlertSegment = "all" | "security" | "price";

function formatEur(value: number, locale: string): string {
  return formatCurrency(value, "EUR", locale);
}

export default function AlertsPage() {
  const router = useRouter();
  const { t, localeTag } = useI18n();
  const { notify } = useNotificationCenter();
  const formRef = useRef<HTMLFormElement | null>(null);

  const [watches, setWatches] = useState<Watch[]>([]);
  const [selectedWatchId, setSelectedWatchId] = useState("");
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [events, setEvents] = useState<AlertEvent[]>([]);
  const [ruleType, setRuleType] = useState("threshold_low");
  const [thresholdValue, setThresholdValue] = useState("");
  const [notifyEveryChange, setNotifyEveryChange] = useState(false);
  const [minChangePct, setMinChangePct] = useState("");
  const [cooldownMinutes, setCooldownMinutes] = useState(60);
  const [status, setStatus] = useState<"idle" | "sending" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [segmentFilter, setSegmentFilter] = useState<AlertSegment>("all");
  const [quietHoursEnabled, setQuietHoursEnabled] = useState(false);
  const [quietHoursStart, setQuietHoursStart] = useState("22:00");
  const [quietHoursEnd, setQuietHoursEnd] = useState("08:00");
  const [thresholdFieldError, setThresholdFieldError] = useState<string | null>(null);
  const [minChangeFieldError, setMinChangeFieldError] = useState<string | null>(null);

  useEffect(() => {
    if (!message || status === "idle" || status === "sending") return;
    notify({
      tone: status === "success" ? "success" : "error",
      title: message,
      durationMs: 3200,
    });
    setMessage("");
    setStatus("idle");
  }, [message, notify, status]);

  const ruleOptions = useMemo(
    () => [
      { value: "threshold_low", label: t("alerts.ruleNames.thresholdLow") },
      { value: "threshold_high", label: t("alerts.ruleNames.thresholdHigh") },
      { value: "every_change", label: t("alerts.ruleNames.everyChange") },
    ],
    [t],
  );

  const categoryOptions = useMemo(
    () => [
      { value: "all", label: t("alerts.categories.all") },
      { value: "security", label: t("alerts.categories.security") },
      { value: "price", label: t("alerts.categories.price") },
    ],
    [t],
  );

  const quickPresets = useMemo(
    () => [
      {
        id: "drop_10",
        label: t("alerts.presets.drop10"),
        apply: () => {
          setRuleType("threshold_low");
          setThresholdValue("40");
          setCooldownMinutes(60);
          setNotifyEveryChange(false);
        },
      },
      {
        id: "price_40",
        label: t("alerts.presets.price40"),
        apply: () => {
          setRuleType("threshold_low");
          setThresholdValue("40");
          setCooldownMinutes(30);
          setNotifyEveryChange(false);
        },
      },
      {
        id: "weekend",
        label: t("alerts.presets.weekend"),
        apply: () => {
          setRuleType("every_change");
          setThresholdValue("");
          setCooldownMinutes(120);
          setNotifyEveryChange(true);
        },
      },
    ],
    [t],
  );

  const ruleLabel = useCallback(
    (value: string) => ruleOptions.find((rule) => rule.value === value)?.label || value,
    [ruleOptions],
  );

  useEffect(() => {
    apiFetch<Watch[]>("/watchlist")
      .then((rows) => {
        setWatches(rows);
        if (rows.length > 0) {
          setSelectedWatchId(rows[0].id);
        }
      })
      .catch(() => {
        setStatus("error");
        setMessage(t("alerts.messages.watchlistLoadError"));
      });

    apiFetch<QuietHoursPreference>("/preferences")
      .then((prefs) => {
        setQuietHoursEnabled(Boolean(prefs.quiet_hours_enabled));
        setQuietHoursStart(prefs.quiet_hours_start || "22:00");
        setQuietHoursEnd(prefs.quiet_hours_end || "08:00");
      })
      .catch(() => undefined);
  }, [t]);

  useEffect(() => {
    if (!selectedWatchId) {
      setRules([]);
      setEvents([]);
      return;
    }

    Promise.all([
      apiFetch<AlertRule[]>(`/alerts/rules?watch_id=${selectedWatchId}`),
      apiFetch<AlertEvent[]>(`/alerts/events?watch_id=${selectedWatchId}&limit=50`),
    ])
      .then(([ruleRows, eventRows]) => {
        setRules(ruleRows);
        setEvents(eventRows);
      })
      .catch(() => {
        setStatus("error");
        setMessage(t("alerts.messages.rulesLoadError"));
      });
  }, [selectedWatchId, t]);

  const selectedWatch = useMemo(
    () => watches.find((w) => w.id === selectedWatchId) || null,
    [watches, selectedWatchId],
  );

  const summary = useMemo(() => {
    const active = rules.filter((rule) => rule.enabled).length;
    const paused = Math.max(0, rules.length - active);
    const queued = events.filter((eventItem) => (eventItem.delivery_status || "").toLowerCase() === "queued").length;
    const delivered = events.filter((eventItem) => {
      const normalized = (eventItem.delivery_status || "").toLowerCase();
      return normalized === "delivered" || normalized === "sent";
    }).length;
    const failed = events.filter((eventItem) => {
      const normalized = (eventItem.delivery_status || "").toLowerCase();
      return normalized === "failed" || normalized === "error";
    }).length;

    return {
      active,
      paused,
      queued,
      delivered,
      failed,
      hasSignal: events.length > 0 || rules.length > 0,
      lastEvaluation: events[0]?.created_at ?? null,
    };
  }, [events, rules]);

  const previewText = useMemo(() => {
    if (!selectedWatch) return t("alerts.form.previewSelectFlight");
    if (ruleType === "every_change") return t("alerts.form.previewEveryChange");
    if (!thresholdValue) return t("alerts.form.previewDefineThreshold");

    const amount = Number(thresholdValue);
    if (Number.isNaN(amount)) return t("alerts.form.previewInvalidThreshold");

    return ruleType === "threshold_low"
      ? t("alerts.form.previewThresholdLow", { value: formatEur(amount, localeTag) })
      : t("alerts.form.previewThresholdHigh", { value: formatEur(amount, localeTag) });
  }, [localeTag, ruleType, selectedWatch, t, thresholdValue]);

  const filteredRules = useMemo(() => {
    if (segmentFilter === "all") return rules;
    if (segmentFilter === "security") return rules.filter((rule) => rule.rule_type === "every_change");
    return rules.filter((rule) => rule.rule_type === "threshold_low" || rule.rule_type === "threshold_high");
  }, [rules, segmentFilter]);

  const deliveryCopy = useCallback((deliveryStatus: string) => getDeliveryStateCopy(deliveryStatus, t), [t]);
  const channelCopy = useCallback((channel: string) => getNotificationChannelCopy(channel, t), [t]);

  function focusRuleForm() {
    if (!formRef.current) return;
    formRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    const firstInput = formRef.current.querySelector("select, input");
    if (firstInput instanceof HTMLElement) firstInput.focus();
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setThresholdFieldError(null);
    setMinChangeFieldError(null);

    if (!selectedWatchId) {
      setStatus("error");
      setMessage(t("alerts.messages.selectFlight"));
      return;
    }

    if (ruleType !== "every_change" && !thresholdValue.trim()) {
      const text = t("alerts.messages.defineThreshold");
      setStatus("error");
      setMessage(text);
      setThresholdFieldError(text);
      return;
    }

    if (ruleType !== "every_change") {
      const thresholdNumber = Number(thresholdValue);
      if (Number.isNaN(thresholdNumber) || thresholdNumber <= 0) {
        const text = t("alerts.messages.invalidThreshold");
        setStatus("error");
        setMessage(text);
        setThresholdFieldError(text);
        return;
      }
    }

    if (minChangePct.trim()) {
      const minChangeNumber = Number(minChangePct);
      if (Number.isNaN(minChangeNumber) || minChangeNumber < 0) {
        const text = t("alerts.messages.invalidMinChange");
        setStatus("error");
        setMessage(text);
        setMinChangeFieldError(text);
        return;
      }
    }

    try {
      setStatus("sending");
      await apiFetch("/alerts/rules", {
        method: "POST",
        body: JSON.stringify({
          watch_id: selectedWatchId,
          rule_type: ruleType,
          threshold_value: ruleType === "every_change" ? null : Number(thresholdValue),
          min_change_pct: minChangePct ? Number(minChangePct) : null,
          notify_on_every_change: notifyEveryChange,
          cooldown_minutes: cooldownMinutes,
        }),
      });

      const [updatedRules, updatedEvents] = await Promise.all([
        apiFetch<AlertRule[]>(`/alerts/rules?watch_id=${selectedWatchId}`),
        apiFetch<AlertEvent[]>(`/alerts/events?watch_id=${selectedWatchId}&limit=50`),
      ]);
      setRules(updatedRules);
      setEvents(updatedEvents);
      void trackUxEvent("alert_created", { rule_type: ruleType });
      setStatus("success");
      setMessage(t("alerts.messages.ruleCreated"));
      setThresholdValue("");
      setMinChangePct("");
      setNotifyEveryChange(false);
    } catch {
      setStatus("error");
      setMessage(t("alerts.messages.ruleCreateError"));
    }
  }

  async function toggleRule(rule: AlertRule) {
    try {
      await apiFetch(`/alerts/rules/${rule.id}`, {
        method: "PUT",
        body: JSON.stringify({
          enabled: !rule.enabled,
          min_change_pct: rule.min_change_pct ?? null,
        }),
      });
      const updated = await apiFetch<AlertRule[]>(`/alerts/rules?watch_id=${selectedWatchId}`);
      setRules(updated);
    } catch {
      setStatus("error");
      setMessage(t("alerts.messages.ruleUpdateError"));
    }
  }

  async function removeRule(rule: AlertRule) {
    const confirmed = window.confirm(t("alerts.messages.confirmDelete"));
    if (!confirmed) return;

    try {
      await apiFetch(`/alerts/rules/${rule.id}`, { method: "DELETE" });
      const updated = await apiFetch<AlertRule[]>(`/alerts/rules?watch_id=${selectedWatchId}`);
      setRules(updated);
      setStatus("success");
      setMessage(t("alerts.messages.ruleDeleted"));
    } catch {
      setStatus("error");
      setMessage(t("alerts.messages.ruleDeleteError"));
    }
  }

  async function evaluateNow() {
    if (!selectedWatchId) return;

    try {
      setIsEvaluating(true);
      await apiFetch("/alerts/evaluate", {
        method: "POST",
        body: JSON.stringify({ watch_id: selectedWatchId }),
      });
      const previousEventCount = events.length;
      const updatedEvents = await apiFetch<AlertEvent[]>(`/alerts/events?watch_id=${selectedWatchId}&limit=50`);
      setEvents(updatedEvents);

      const triggeredCount = Math.max(0, updatedEvents.length - previousEventCount);
      if (triggeredCount > 0) {
        void trackUxEvent("alert_triggered", { count: triggeredCount });
      }

      setStatus("success");
      setMessage(t("alerts.messages.evaluationComplete"));
    } catch {
      setStatus("error");
      setMessage(t("alerts.messages.evaluationError"));
    } finally {
      setIsEvaluating(false);
    }
  }

  async function saveQuietHours() {
    try {
      const current = await apiFetch<Record<string, unknown>>("/preferences");
      await apiFetch("/preferences", {
        method: "PUT",
        body: JSON.stringify({
          ...current,
          quiet_hours_enabled: quietHoursEnabled,
          quiet_hours_start: quietHoursStart,
          quiet_hours_end: quietHoursEnd,
          quiet_hours_timezone: null,
        }),
      });
      setStatus("success");
      setMessage(t("alerts.messages.quietHoursSaved"));
    } catch {
      setStatus("error");
      setMessage(t("alerts.messages.ruleUpdateError"));
    }
  }

  return (
    <main className="shell" id="main-content">
      <div className="page-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
          {t("shared.actions.back")}
        </button>
        <div className="page-title">
          <h1>{t("alerts.pageTitle")}</h1>
          <p>{t("alerts.pageSubtitle")}</p>
        </div>
      </div>

      <section className="panel panel-soft stack alerts-hero">
        <div className="alerts-hero-top">
          <div>
            <span className="alerts-kicker">{t("alerts.hero.kicker")}</span>
            <h2 className="panel-title">{t("alerts.hero.title")}</h2>
            <p className="panel-note">{t("alerts.hero.subtitle")}</p>
          </div>
          <div className="alerts-hero-actions">
            <button className="btn-primary" type="button" onClick={evaluateNow} disabled={isEvaluating}>
              {isEvaluating ? t("alerts.form.buttonEvaluating") : t("alerts.form.buttonSimulate")}
            </button>
            <button className="btn-secondary" type="button" onClick={focusRuleForm}>
              {t("alerts.hero.createRule")}
            </button>
            <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
              {t("alerts.hero.backToDashboard")}
            </button>
          </div>
        </div>

        <div className="alerts-hero-grid">
          <article className="alerts-metric-card">
            <span>{t("alerts.hero.cards.activeRules")}</span>
            <strong>{summary.active}</strong>
            <small>{t("alerts.hero.cards.pausedRules", { count: summary.paused })}</small>
          </article>
          <article className="alerts-metric-card">
            <span>{t("alerts.hero.cards.deliveryHealth")}</span>
            <strong>{summary.delivered}</strong>
            <small>{t("alerts.hero.cards.pendingAndFailed", { pending: summary.queued, failed: summary.failed })}</small>
          </article>
          <article className="alerts-metric-card">
            <span>{t("alerts.hero.cards.lastEvaluation")}</span>
            <strong>
              {summary.lastEvaluation
                ? formatRelativeTime(summary.lastEvaluation, localeTag)
                : t("alerts.hero.cards.noData")}
            </strong>
            <small>{t("alerts.hero.cards.lastEvaluationHint")}</small>
          </article>
        </div>

        <div className="alerts-flow-links">
          {watches.length === 0 ? (
            <>
              <p className="panel-note">{t("alerts.flow.emptyWatchlistHint")}</p>
              <Link href="/watchlist" className="btn-ghost btn-compact">{t("alerts.flow.goWatchlist")}</Link>
              <Link href="/quick-search" className="btn-ghost btn-compact">{t("alerts.flow.goQuickSearch")}</Link>
            </>
          ) : !summary.hasSignal ? (
            <>
              <p className="panel-note">{t("alerts.flow.noSignalHint")}</p>
              <Link href="/watchlist" className="btn-ghost btn-compact">{t("alerts.flow.goWatchlist")}</Link>
              <Link href="/quick-search" className="btn-ghost btn-compact">{t("alerts.flow.goQuickSearch")}</Link>
            </>
          ) : (
            <>
              <p className="panel-note">{t("alerts.flow.hasSignalHint")}</p>
              <Link href="/dashboard" className="btn-ghost btn-compact">{t("alerts.flow.goDashboard")}</Link>
            </>
          )}
        </div>
      </section>

      <section className="panel panel-soft stack section-gap">
        <div className="row-between">
          <h2 className="panel-title">{t("alerts.form.quietHoursTitle")}</h2>
        </div>
        <label className="alert-check">
          <input
            type="checkbox"
            checked={quietHoursEnabled}
            onChange={(event) => setQuietHoursEnabled(event.target.checked)}
          />
          <span className="alert-check-ui" aria-hidden="true">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5.5 12.5 10 17l8.5-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          {t("alerts.form.quietHoursEnabled")}
        </label>
        <div className="row-actions">
          <label className="field">
            {t("alerts.form.quietHoursStart")}
            <input value={quietHoursStart} onChange={(event) => setQuietHoursStart(event.target.value)} />
          </label>
          <label className="field">
            {t("alerts.form.quietHoursEnd")}
            <input value={quietHoursEnd} onChange={(event) => setQuietHoursEnd(event.target.value)} />
          </label>
          <button className="btn-ghost" type="button" onClick={saveQuietHours}>
            {t("alerts.form.buttonSave")}
          </button>
        </div>
        <p className="panel-note">{t("alerts.form.quietHoursHelp")}</p>
      </section>

      <section className="panel panel-soft stack section-gap">
        <div className="row-between">
          <div>
            <h2 className="panel-title">{t("alerts.form.title")}</h2>
            <p className="panel-subtitle">{t("alerts.form.subtitle")}</p>
          </div>
          {selectedWatch ? (
            <span className="alert-chip">
              {selectedWatch.origin_iata} {" ? "} {selectedWatch.destination_iata} · {selectedWatch.travel_date_local}
            </span>
          ) : null}
        </div>

        <form ref={formRef} className="alert-form" onSubmit={onSubmit}>
          <div className="alert-preview">
            <strong>{t("alerts.presets.title")}</strong>
            <div className="alert-actions">
              {quickPresets.map((preset) => (
                <button key={preset.id} type="button" className="btn-ghost btn-compact" onClick={preset.apply}>
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          <label className="field">
            {t("alerts.form.flight")}
            <select
              name="watch_id"
              autoComplete="off"
              value={selectedWatchId}
              onChange={(e) => setSelectedWatchId(e.target.value)}
            >
              <option value="">{t("alerts.form.watchDefault")}</option>
              {watches.map((watch) => (
                <option key={watch.id} value={watch.id}>
                  {watch.origin_iata} {" ? "} {watch.destination_iata} ({watch.travel_date_local})
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            {t("alerts.form.ruleType")}
            <select name="rule_type" autoComplete="off" value={ruleType} onChange={(e) => setRuleType(e.target.value)}>
              {ruleOptions.map((rule) => (
                <option key={rule.value} value={rule.value}>
                  {rule.label}
                </option>
              ))}
            </select>
            <small className="panel-note">{t("alerts.form.ruleTypeHelp")}</small>
          </label>

          {ruleType !== "every_change" ? (
            <label className="field">
              {t("alerts.form.threshold")}
              <input
                name="threshold_value"
                autoComplete="off"
                value={thresholdValue}
                onChange={(e) => setThresholdValue(e.target.value)}
                placeholder={t("alerts.form.placeholder")}
              />
              {thresholdFieldError ? <small className="prefs-error">{thresholdFieldError}</small> : null}
            </label>
          ) : null}

          <label className="field">
            {t("alerts.form.cooldown")}
            <select
              name="cooldown_minutes"
              autoComplete="off"
              value={cooldownMinutes}
              onChange={(e) => setCooldownMinutes(Number(e.target.value))}
            >
              {[15, 30, 60, 120, 240].map((value) => (
                <option key={value} value={value}>
                  {value} min
                </option>
              ))}
            </select>
            <small className="panel-note">{t("alerts.form.cooldownHelp")}</small>
          </label>

          <label className="field">
            {t("alerts.form.minChangePct")}
            <input
              name="min_change_pct"
              autoComplete="off"
              value={minChangePct}
              onChange={(e) => setMinChangePct(e.target.value)}
              placeholder={t("alerts.form.minChangePctPlaceholder")}
            />
            {minChangeFieldError ? <small className="prefs-error">{minChangeFieldError}</small> : null}
            <small className="panel-note">{t("alerts.form.minChangePctHelp")}</small>
          </label>

          <label className="alert-check">
            <input
              name="notify_every_change"
              type="checkbox"
              checked={notifyEveryChange}
              onChange={(e) => setNotifyEveryChange(e.target.checked)}
            />
            <span className="alert-check-ui" aria-hidden="true">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M5.5 12.5 10 17l8.5-9"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            {t("alerts.form.notifyLabel")}
          </label>

          <div className="alert-preview">
            <strong>{t("alerts.form.previewLabel")}</strong> {previewText}
          </div>

          <div className="row-actions">
            <button className="btn-primary" type="submit" disabled={status === "sending"}>
              {status === "sending" ? t("alerts.form.buttonSaving") : t("alerts.form.buttonSave")}
            </button>
            <button className="btn-secondary" type="button" onClick={evaluateNow} disabled={isEvaluating}>
              {isEvaluating ? t("alerts.form.buttonEvaluating") : t("alerts.form.buttonSimulate")}
            </button>
            <span className="panel-note">{t("alerts.note.description")}</span>
          </div>
        </form>
      </section>

      <section className="panel panel-soft stack section-gap">
        <div className="row-between">
          <h2 className="panel-title">{t("alerts.list.title")}</h2>
          <span className="panel-note">{t("alerts.list.count", { count: filteredRules.length })}</span>
        </div>

        <div className="alerts-segment-toolbar" role="tablist" aria-label={t("alerts.form.category")}>
          {categoryOptions.map((option) => {
            const isActive = option.value === segmentFilter;
            return (
              <button
                key={option.value}
                type="button"
                className={`btn-ghost btn-compact alerts-segment-btn ${isActive ? "is-active" : ""}`}
                onClick={() => setSegmentFilter(option.value as AlertSegment)}
                aria-pressed={isActive}
              >
                {option.label}
              </button>
            );
          })}
        </div>

        {filteredRules.length === 0 ? (
          <p className="panel-note">
            {segmentFilter === "all" ? t("alerts.list.emptyAll") : t("alerts.list.emptySegment")}
          </p>
        ) : (
          filteredRules.map((rule) => {
            const watchStatus = getWatchStatusMeta(rule.enabled ? "active" : "paused", t);
            const thresholdText =
              rule.rule_type !== "every_change" && rule.threshold_value != null
                ? t("alerts.row.threshold", { value: formatEur(Number(rule.threshold_value), localeTag) })
                : "";
            const minChangeText =
              rule.min_change_pct != null
                ? t("alerts.row.minChange", { value: rule.min_change_pct })
                : "";

            return (
              <div className="list-row alert-row" key={rule.id}>
                <div>
                  <strong>{ruleLabel(rule.rule_type)}</strong>
                  <div className="panel-note alerts-rule-meta">
                    {thresholdText ? <span>{thresholdText}</span> : null}
                    {minChangeText ? <span>{minChangeText}</span> : null}
                    <span>{t("alerts.row.cooldown", { value: rule.cooldown_minutes })}</span>
                  </div>
                </div>
                <div className="alert-actions">
                  <button className="btn-secondary btn-compact" type="button" onClick={() => toggleRule(rule)}>
                    {rule.enabled ? t("alerts.row.actions.pause") : t("alerts.row.actions.activate")}
                  </button>
                  <button className="btn-danger btn-compact" type="button" onClick={() => removeRule(rule)}>
                    {t("alerts.row.actions.delete")}
                  </button>
                  <span className={`status-pill ${watchStatus.tone}`}>{watchStatus.label}</span>
                </div>
              </div>
            );
          })
        )}
      </section>

      <section className="panel panel-soft stack section-gap">
        <div className="row-between">
          <div>
            <h2 className="panel-title">{t("alerts.history.title")}</h2>
            <p className="panel-note">
              {t("alerts.history.lastEvaluation", {
                value: events[0]?.created_at
                  ? formatRelativeTime(events[0].created_at, localeTag)
                  : t("alerts.hero.cards.noData"),
              })}
            </p>
          </div>
          <span className="panel-note">{t("alerts.history.count", { count: events.length })}</span>
        </div>

        {events.length === 0 ? (
          <p className="panel-note">{t("alerts.history.empty")}</p>
        ) : (
          events.map((eventItem) => {
            const delivery = getDeliveryStatusMeta(eventItem.delivery_status, t);
            return (
              <div key={eventItem.id} className="list-row alert-event">
                <div className="alert-event-main">
                  <strong>{eventItem.origin_iata} {" ? "} {eventItem.destination_iata}</strong>
                  <div className="panel-note">
                    {t("alerts.history.timeLabel", {
                      date: eventItem.travel_date_local,
                      time: new Date(eventItem.created_at).toLocaleString(localeTag),
                    })}
                  </div>
                  <div className="alert-message">{eventItem.message}</div>
                </div>
                <div className="alert-event-side">
                  <time className="alert-timestamp" dateTime={eventItem.created_at}>
                    {new Date(eventItem.created_at).toLocaleTimeString(localeTag, { hour: "2-digit", minute: "2-digit" })}
                  </time>
                  <span className="alert-channel">{channelCopy(eventItem.channel)}</span>
                  <span className="panel-note">{deliveryCopy(eventItem.delivery_status)}</span>
                  {eventItem.is_digest || (eventItem.grouped_count ?? 1) > 1 ? (
                    <span className="panel-note">
                      {t("alerts.history.groupedLabel")} · {t("alerts.history.digestSummary", { count: eventItem.grouped_count ?? 1 })}
                    </span>
                  ) : null}
                  {eventItem.delivery_status === "queued" && eventItem.last_error === "quiet_hours_active" ? (
                    <span className="panel-note">{t("alerts.history.quietHoursPending")}</span>
                  ) : null}
                  <span className={`status-pill ${delivery.tone}`}>{delivery.label}</span>
                </div>
              </div>
            );
          })
        )}
      </section>
    </main>
  );
}

