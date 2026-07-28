import { PlaneTakeoff, TicketCheck, UsersRound, X } from "lucide-react";
import { useEffect, useRef, type KeyboardEvent } from "react";

import { useI18n } from "@/i18n";
import type { Watch } from "@/modules/watchlist/types";

type CommunityPricingDrawerProps = {
  readonly watch: Watch | null;
  readonly pendingCount: number;
  readonly stage: "flight" | "price";
  readonly price: string;
  readonly isSaving: boolean;
  readonly error: string;
  readonly onPriceChange: (value: string) => void;
  readonly onClose: () => void;
  readonly onChooseFlew: () => void;
  readonly onSaveNoFlight: () => void;
  readonly onSavePrice: () => void;
  readonly onDeleteResponse: () => void;
};

export function CommunityPricingDrawer({
  watch,
  pendingCount,
  stage,
  price,
  isSaving,
  error,
  onPriceChange,
  onClose,
  onChooseFlew,
  onSaveNoFlight,
  onSavePrice,
  onDeleteResponse,
}: CommunityPricingDrawerProps) {
  const { t, localeTag } = useI18n();
  const drawerRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!watch) return;
    const previouslyFocused =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    closeButtonRef.current?.focus();
    return () => previouslyFocused?.focus();
  }, [watch]);

  if (!watch) return null;

  const aggregate = watch.community_pricing.aggregate;
  const publicRange =
    aggregate.is_public &&
    aggregate.min_price !== null &&
    aggregate.max_price !== null
      ? { min: aggregate.min_price, max: aggregate.max_price }
      : null;

  function handleKeyDown(event: KeyboardEvent<HTMLElement>): void {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== "Tab" || !drawerRef.current) return;
    const focusable = Array.from(
      drawerRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      ),
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (!first || !last) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="community-pricing-overlay">
      <button
        className="community-pricing-backdrop"
        type="button"
        tabIndex={-1}
        aria-hidden="true"
        onClick={onClose}
      />
      <section
        ref={drawerRef}
        className="community-pricing-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="community-pricing-title"
        onKeyDown={handleKeyDown}
      >
        <header className="community-pricing-header">
          <div>
            <span className="community-pricing-kicker">
              <UsersRound aria-hidden="true" />
              {t("watchlist.communityPricing.kicker")}
            </span>
            <h2 id="community-pricing-title">
              {watch.origin_iata} → {watch.destination_iata}
            </h2>
            <p>
              {t("watchlist.communityPricing.pendingCount", {
                count: pendingCount,
              })}
            </p>
          </div>
          <button
            ref={closeButtonRef}
            className="modal-close"
            type="button"
            aria-label={t("watchlist.communityPricing.close")}
            onClick={onClose}
          >
            <X aria-hidden="true" />
          </button>
        </header>

        <div className="community-pricing-route-card">
          <PlaneTakeoff aria-hidden="true" />
          <div>
            <strong>
              {watch.origin_iata} → {watch.destination_iata}
            </strong>
            <span>{watch.travel_date_local}</span>
          </div>
          <span className="status-pill info">
            {watch.community_pricing.trigger_reason === "expired"
              ? t("watchlist.communityPricing.expired")
              : t("watchlist.communityPricing.purchased")}
          </span>
        </div>

        {publicRange ? (
          <div className="community-pricing-proof" role="status">
            <TicketCheck aria-hidden="true" />
            <p>
              {t("watchlist.communityPricing.aggregatePublic", {
                count: aggregate.sample_size,
                min: new Intl.NumberFormat(localeTag, {
                  maximumFractionDigits: 2,
                }).format(publicRange.min),
                max: new Intl.NumberFormat(localeTag, {
                  maximumFractionDigits: 2,
                }).format(publicRange.max),
              })}
            </p>
          </div>
        ) : null}

        {stage === "flight" ? (
          <div className="community-pricing-step">
            <span className="community-pricing-step-label">
              {t("watchlist.communityPricing.stepFlight")}
            </span>
            <h3>{t("watchlist.communityPricing.didFly")}</h3>
            <p>{t("watchlist.communityPricing.didFlyBody")}</p>
            <div className="community-pricing-actions">
              <button
                className="btn-primary"
                type="button"
                onClick={onChooseFlew}
                disabled={isSaving}
              >
                {t("watchlist.communityPricing.yesFlew")}
              </button>
              <button
                className="btn-ghost"
                type="button"
                onClick={onSaveNoFlight}
                disabled={isSaving}
              >
                {t("watchlist.communityPricing.noFlight")}
              </button>
            </div>
          </div>
        ) : (
          <div className="community-pricing-step">
            <span className="community-pricing-step-label">
              {t("watchlist.communityPricing.stepPrice")}
            </span>
            <h3>{t("watchlist.communityPricing.priceTitle")}</h3>
            <p>{t("watchlist.communityPricing.priceBody")}</p>
            <label className="field" htmlFor="community-price-per-traveler">
              {t("watchlist.communityPricing.priceLabel")}
              <div className="community-pricing-price-input">
                <input
                  id="community-price-per-traveler"
                  name="community_price_per_traveler"
                  inputMode="decimal"
                  autoComplete="off"
                  value={price}
                  onChange={(event) => onPriceChange(event.target.value)}
                  placeholder="67,00"
                  disabled={isSaving}
                />
                <span>EUR</span>
              </div>
              <small className="hint">
                {t("watchlist.communityPricing.priceHint")}
              </small>
            </label>
            <button
              className="btn-primary community-pricing-save"
              type="button"
              onClick={onSavePrice}
              disabled={isSaving}
            >
              {isSaving
                ? t("watchlist.communityPricing.saving")
                : t("watchlist.communityPricing.save")}
            </button>
          </div>
        )}

        {error ? (
          <p className="community-pricing-error" role="alert">
            {error}
          </p>
        ) : null}

        <footer className="community-pricing-footer">
          <button
            className="btn-ghost btn-compact"
            type="button"
            onClick={onClose}
            disabled={isSaving}
          >
            {t("watchlist.communityPricing.later")}
          </button>
          {watch.community_pricing.response ? (
            <button
              className="btn-danger btn-compact"
              type="button"
              onClick={onDeleteResponse}
              disabled={isSaving}
            >
              {t("watchlist.communityPricing.deleteResponse")}
            </button>
          ) : null}
        </footer>
      </section>
    </div>
  );
}
