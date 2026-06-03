"use client";

import { useMemo, useState, type FormEvent } from "react";

import { useI18n } from "@/i18n";

import type { HotelAlertEventOut, HotelAlertRuleOut, HotelAlertRuleType, HotelSearchOut } from "../types";

type AlertFormDraft = {
  ruleType: HotelAlertRuleType;
  thresholdAmount: string;
  thresholdPercent: string;
  isActive: boolean;
};

const DEFAULT_DRAFT: AlertFormDraft = {
  ruleType: "price_below",
  thresholdAmount: "",
  thresholdPercent: "",
  isActive: true,
};

function formatRuleSummary(rule: HotelAlertRuleOut, localeTag: string): string[] {
  const parts: string[] = [];
  if (rule.threshold_amount !== null) {
    parts.push(
      new Intl.NumberFormat(localeTag, {
        maximumFractionDigits: 2,
      }).format(rule.threshold_amount),
    );
  }
  if (rule.threshold_percent !== null) {
    parts.push(`${rule.threshold_percent}%`);
  }
  return parts;
}

function formatCreatedAt(value: string, localeTag: string): string {
  return new Intl.DateTimeFormat(localeTag, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function parseThreshold(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed.replace(",", "."));
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function validateAlertDraft(draft: AlertFormDraft, t: ReturnType<typeof useI18n>["t"]): string | null {
  const thresholdAmount = parseThreshold(draft.thresholdAmount);
  const thresholdPercent = parseThreshold(draft.thresholdPercent);

  if ((draft.thresholdAmount.trim() && thresholdAmount === null) || (draft.thresholdPercent.trim() && thresholdPercent === null)) {
    return t("hotels.alerts.validation.invalidNumber");
  }

  if ((draft.ruleType === "price_below" || draft.ruleType === "price_above") && thresholdAmount === null && thresholdPercent === null) {
    return t("hotels.alerts.validation.priceThresholdRequired");
  }

  if (draft.ruleType === "parity_break") {
    if (thresholdPercent === null) {
      return t("hotels.alerts.validation.parityThresholdRequired");
    }
    if (thresholdAmount !== null) {
      return t("hotels.alerts.validation.parityAmountNotAllowed");
    }
  }

  return null;
}

export function HotelAlertsPanel({
  selectedHotel,
  rules,
  rulesLoading,
  rulesError,
  events,
  eventsLoading,
  eventsError,
  createBusy,
  busyRuleIds,
  onCreateRule,
  onToggleRule,
  onDeleteRule,
}: {
  selectedHotel: HotelSearchOut | null;
  rules: HotelAlertRuleOut[];
  rulesLoading: boolean;
  rulesError: string | null;
  events: HotelAlertEventOut[];
  eventsLoading: boolean;
  eventsError: string | null;
  createBusy: boolean;
  busyRuleIds: string[];
  onCreateRule: (payload: {
    hotel_id: string;
    rule_type: HotelAlertRuleType;
    threshold_amount: number | null;
    threshold_percent: number | null;
    is_active: boolean;
  }) => Promise<boolean>;
  onToggleRule: (ruleId: string, isActive: boolean) => void;
  onDeleteRule: (ruleId: string) => void;
}) {
  const { t, localeTag } = useI18n();
  const [draft, setDraft] = useState<AlertFormDraft>(DEFAULT_DRAFT);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const selectedHotelName = selectedHotel?.canonical_name ?? null;
  const ruleTypeLabel = useMemo(
    () => ({
      price_below: t("hotels.alerts.ruleTypes.priceBelow"),
      price_above: t("hotels.alerts.ruleTypes.priceAbove"),
      parity_break: t("hotels.alerts.ruleTypes.parityBreak"),
    }),
    [t],
  );
  const shouldShowAmount = draft.ruleType !== "parity_break";

  function resetDraft(nextRuleType?: HotelAlertRuleType) {
    setDraft({
      ruleType: nextRuleType ?? DEFAULT_DRAFT.ruleType,
      thresholdAmount: "",
      thresholdPercent: "",
      isActive: true,
    });
    setValidationMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedHotel) return;

    const error = validateAlertDraft(draft, t);
    if (error) {
      setValidationMessage(error);
      return;
    }

    const payload = {
      hotel_id: selectedHotel.id,
      rule_type: draft.ruleType,
      threshold_amount: shouldShowAmount ? parseThreshold(draft.thresholdAmount) : null,
      threshold_percent: parseThreshold(draft.thresholdPercent),
      is_active: draft.isActive,
    };

    const created = await onCreateRule(payload);
    if (created) {
      resetDraft(draft.ruleType);
    }
  }

  return (
    <section className="panel panel-soft hotel-alerts-panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">{t("hotels.alerts.title")}</h2>
          <p className="panel-subtitle">{t("hotels.alerts.subtitle")}</p>
        </div>
        <span className="status-pill info">{rules.length}</span>
      </div>

      <section className="hotel-alerts-form-block section-gap-sm">
        <div className="hotel-alerts-block-head">
          <strong>{t("hotels.alerts.createTitle")}</strong>
          {selectedHotelName ? <p className="panel-note">{t("hotels.alerts.createHint", { hotel: selectedHotelName })}</p> : null}
        </div>

        {!selectedHotel ? <p className="panel-note">{t("hotels.alerts.noHotelSelected")}</p> : null}

        {selectedHotel ? (
          <form className="hotel-alerts-form" onSubmit={(event) => void handleSubmit(event)}>
            <label className="field qs-label">
              <span>{t("hotels.alerts.fields.ruleType")}</span>
              <select
                className="qs-input-neutral"
                value={draft.ruleType}
                onChange={(event) => {
                  const nextRuleType = event.target.value as HotelAlertRuleType;
                  setDraft((current) => ({
                    ...current,
                    ruleType: nextRuleType,
                    thresholdAmount: nextRuleType === "parity_break" ? "" : current.thresholdAmount,
                  }));
                  setValidationMessage(null);
                }}
              >
                <option value="price_below">{ruleTypeLabel.price_below}</option>
                <option value="price_above">{ruleTypeLabel.price_above}</option>
                <option value="parity_break">{ruleTypeLabel.parity_break}</option>
              </select>
            </label>

            <div className={`hotel-alerts-thresholds${shouldShowAmount ? "" : " is-parity-only"}`}>
              {shouldShowAmount ? (
                <label className="field qs-label">
                  <span>{t("hotels.alerts.fields.thresholdAmount")}</span>
                  <input
                    className="qs-input-neutral"
                    inputMode="decimal"
                    value={draft.thresholdAmount}
                    onChange={(event) => {
                      setDraft((current) => ({ ...current, thresholdAmount: event.target.value }));
                      setValidationMessage(null);
                    }}
                    placeholder={t("hotels.alerts.fields.thresholdAmountPlaceholder")}
                  />
                </label>
              ) : null}

              <label className="field qs-label">
                <span>{t("hotels.alerts.fields.thresholdPercent")}</span>
                <input
                  className="qs-input-neutral"
                  inputMode="decimal"
                  value={draft.thresholdPercent}
                  onChange={(event) => {
                    setDraft((current) => ({ ...current, thresholdPercent: event.target.value }));
                    setValidationMessage(null);
                  }}
                  placeholder={t("hotels.alerts.fields.thresholdPercentPlaceholder")}
                />
              </label>
            </div>

            <label className="hotel-alert-toggle">
              <input
                type="checkbox"
                checked={draft.isActive}
                onChange={(event) => setDraft((current) => ({ ...current, isActive: event.target.checked }))}
              />
              <span>{t("hotels.alerts.fields.isActive")}</span>
            </label>

            {validationMessage ? <p className="panel-note hotel-alerts-validation">{validationMessage}</p> : null}

            <div className="action-row">
              <button type="submit" className="btn-secondary btn-compact" disabled={createBusy}>
                {createBusy ? t("shared.states.loading") : t("hotels.alerts.createCta")}
              </button>
            </div>
          </form>
        ) : null}
      </section>

      <section className="hotel-alerts-rules section-gap-sm">
        <div className="hotel-alerts-block-head">
          <strong>{t("hotels.alerts.rulesTitle")}</strong>
          {selectedHotel ? <p className="panel-note">{t("hotels.alerts.rulesHint")}</p> : null}
        </div>

        {!selectedHotel ? <p className="panel-note">{t("hotels.alerts.rulesNoHotel")}</p> : null}
        {selectedHotel && rulesLoading ? <p className="panel-note">{t("hotels.alerts.loadingRules")}</p> : null}
        {selectedHotel && rulesError ? <p className="panel-note">{rulesError}</p> : null}
        {selectedHotel && !rulesLoading && !rulesError && rules.length === 0 ? <p className="panel-note">{t("hotels.alerts.emptyRules")}</p> : null}

        {selectedHotel && !rulesLoading && !rulesError && rules.length > 0 ? (
          <div className="hotel-alert-rule-list">
            {rules.map((rule) => {
              const busy = busyRuleIds.includes(rule.id);
              const summaryParts = formatRuleSummary(rule, localeTag);
              return (
                <article key={rule.id} className="list-row hotel-alert-rule-item">
                  <div className="hotel-alert-rule-copy">
                    <div className="hotel-alert-rule-meta">
                      <span className={`status-pill ${rule.is_active ? "success" : "warning"}`}>
                        {rule.is_active ? t("hotels.alerts.states.active") : t("hotels.alerts.states.inactive")}
                      </span>
                      <span className="status-pill info">{ruleTypeLabel[rule.rule_type]}</span>
                    </div>
                    <strong>{summaryParts.length > 0 ? summaryParts.join(" · ") : t("hotels.alerts.thresholdFallback")}</strong>
                  </div>
                  <div className="hotel-alert-rule-actions">
                    <button type="button" className="btn-ghost btn-compact" disabled={busy} onClick={() => onToggleRule(rule.id, !rule.is_active)}>
                      {busy ? t("shared.states.loading") : rule.is_active ? t("hotels.alerts.deactivateCta") : t("hotels.alerts.activateCta")}
                    </button>
                    <button type="button" className="btn-ghost btn-compact" disabled={busy} onClick={() => onDeleteRule(rule.id)}>
                      {busy ? t("shared.states.loading") : t("hotels.alerts.deleteCta")}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : null}
      </section>

      <section className="hotel-alerts-events section-gap-sm">
        <div className="hotel-alerts-block-head">
          <strong>{t("hotels.alerts.eventsTitle")}</strong>
          {selectedHotel ? <p className="panel-note">{t("hotels.alerts.eventsHint")}</p> : null}
        </div>

        {!selectedHotel ? <p className="panel-note">{t("hotels.alerts.eventsNoHotel")}</p> : null}
        {selectedHotel && eventsLoading ? <p className="panel-note">{t("hotels.alerts.loadingEvents")}</p> : null}
        {selectedHotel && eventsError ? <p className="panel-note">{eventsError}</p> : null}
        {selectedHotel && !eventsLoading && !eventsError && events.length === 0 ? <p className="panel-note">{t("hotels.alerts.emptyEvents")}</p> : null}

        {selectedHotel && !eventsLoading && !eventsError && events.length > 0 ? (
          <div className="hotel-alert-events-list">
            {events.map((event) => (
              <article key={event.id} className="hotel-alert-event-item">
                <strong>{event.message}</strong>
                <p className="panel-note">{formatCreatedAt(event.created_at, localeTag)}</p>
                {event.trigger_value !== null ? <p className="panel-note">{t("hotels.alerts.triggerValue", { value: event.trigger_value })}</p> : null}
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </section>
  );
}
