"use client";

import { Clock3, Inbox, RadioTower } from "lucide-react";
import Link from "next/link";

import { useI18n } from "@/i18n";
import { formatRelativeTime } from "@/modules/shared/format";

type SignalCadenceScope = {
  routeLabel: string | null;
  activeRules: number;
  pausedRules: number;
  cooldownMinutes: number | null;
  lastEvaluation: string | null;
};

type QuietHoursControl = {
  enabled: boolean;
  start: string;
  end: string;
  onEnabledChange: (enabled: boolean) => void;
  onStartChange: (value: string) => void;
  onEndChange: (value: string) => void;
  onSave: () => void;
};

export function SignalCadencePanel({
  scope,
  quietHours,
}: {
  scope: SignalCadenceScope;
  quietHours: QuietHoursControl;
}) {
  const { t, localeTag } = useI18n();

  return (
    <section className="panel panel-soft section-gap signals-cadence">
      <div className="signals-cadence-intro">
        <span className="signals-cadence-icon" aria-hidden="true">
          <RadioTower size={19} />
        </span>
        <div>
          <p className="eyebrow">{t("alerts.cadence.kicker")}</p>
          <h2 className="panel-title">{t("alerts.cadence.title")}</h2>
          <p className="panel-subtitle">{t("alerts.cadence.subtitle")}</p>
        </div>
        <Link className="btn-secondary btn-compact" href="/notifications?filter=actionable">
          <Inbox size={15} aria-hidden="true" />
          {t("alerts.cadence.openPending")}
        </Link>
      </div>

      <div className="signals-cadence-grid">
        <article>
          <span>{t("alerts.cadence.scope")}</span>
          <strong>{scope.routeLabel ?? t("alerts.cadence.noRoute")}</strong>
          <small>
            {t("alerts.cadence.ruleState", { active: scope.activeRules, paused: scope.pausedRules })}
          </small>
        </article>
        <article>
          <span>{t("alerts.cadence.rhythm")}</span>
          <strong>
            {scope.cooldownMinutes
              ? t("alerts.cadence.every", { minutes: scope.cooldownMinutes })
              : t("alerts.cadence.noActiveRules")}
          </strong>
          <small>{t("alerts.cadence.rhythmHint")}</small>
        </article>
        <article>
          <span>{t("alerts.cadence.lastConnection")}</span>
          <strong>
            {scope.lastEvaluation
              ? formatRelativeTime(scope.lastEvaluation, localeTag)
              : t("alerts.cadence.noEvaluation")}
          </strong>
          <small>{t("alerts.cadence.connectionHint")}</small>
        </article>
      </div>

      <div className="signals-cadence-controls">
        <div>
          <h3>
            <Clock3 size={16} aria-hidden="true" />
            {t("alerts.form.quietHoursTitle")}
          </h3>
          <p>{t("alerts.form.quietHoursHelp")}</p>
        </div>
        <label className="alert-check">
          <input
            type="checkbox"
            checked={quietHours.enabled}
            onChange={(event) => quietHours.onEnabledChange(event.target.checked)}
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
          {t("alerts.form.quietHoursEnabled")}
        </label>
        <label className="field">
          {t("alerts.form.quietHoursStart")}
          <input
            type="time"
            value={quietHours.start}
            disabled={!quietHours.enabled}
            onChange={(event) => quietHours.onStartChange(event.target.value)}
          />
        </label>
        <label className="field">
          {t("alerts.form.quietHoursEnd")}
          <input
            type="time"
            value={quietHours.end}
            disabled={!quietHours.enabled}
            onChange={(event) => quietHours.onEndChange(event.target.value)}
          />
        </label>
        <button className="btn-secondary btn-compact" type="button" onClick={quietHours.onSave}>
          {t("alerts.cadence.saveQuietHours")}
        </button>
      </div>
    </section>
  );
}
