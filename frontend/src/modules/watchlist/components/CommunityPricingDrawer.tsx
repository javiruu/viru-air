import { ArrowLeft, PlaneTakeoff, UsersRound, X } from "lucide-react";
import { useLayoutEffect, useRef, type KeyboardEvent } from "react";

import { useI18n } from "@/i18n";
import { RelatedCommunityRoutes } from "@/modules/community-routes/RelatedCommunityRoutes";
import { CommunityHubOverview } from "@/modules/watchlist/components/CommunityHubOverview";
import type { Watch } from "@/modules/watchlist/types";

type CommunityPricingDrawerProps = {
  readonly watch: Watch | null;
  readonly stage: "overview" | "flight" | "price";
  readonly price: string;
  readonly isSaving: boolean;
  readonly error: string;
  readonly onPriceChange: (value: string) => void;
  readonly onClose: () => void;
  readonly onMarkPurchased: () => void;
  readonly onBeginContribution: () => void;
  readonly onReturnToOverview: () => void;
  readonly onChooseFlew: () => void;
  readonly onSaveNoFlight: () => void;
  readonly onSavePrice: () => void;
  readonly onDeleteResponse: () => void;
};

export function CommunityPricingDrawer({
  watch,
  stage,
  price,
  isSaving,
  error,
  onPriceChange,
  onClose,
  onMarkPurchased,
  onBeginContribution,
  onReturnToOverview,
  onChooseFlew,
  onSaveNoFlight,
  onSavePrice,
  onDeleteResponse,
}: CommunityPricingDrawerProps) {
  const { t } = useI18n();
  const drawerRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const activeWatchId = watch?.id;

  useLayoutEffect(() => {
    if (!activeWatchId) return;
    closeButtonRef.current?.focus();
  }, [activeWatchId]);

  if (!watch) return null;

  function handleKeyDown(event: KeyboardEvent<HTMLElement>): void {
    if (event.key === "Escape" && !isSaving) {
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

  const routeState =
    watch.community_pricing.trigger_reason === "expired"
      ? t("watchlist.communityPricing.expired")
      : watch.community_pricing.trigger_reason === "purchased"
        ? t("watchlist.communityPricing.purchased")
        : t("watchlist.communityPricing.tracking");

  return (
    <div className="community-pricing-overlay">
      <button
        className="community-pricing-backdrop"
        type="button"
        tabIndex={-1}
        aria-hidden="true"
        disabled={isSaving}
        onClick={onClose}
      />
      <section
        ref={drawerRef}
        className="community-pricing-drawer community-hub-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="community-hub-title"
        onKeyDown={handleKeyDown}
      >
        <header className="community-pricing-header">
          <div>
            <span className="community-pricing-kicker">
              <UsersRound aria-hidden="true" />
              {t("watchlist.communityPricing.hubKicker")}
            </span>
            <h2 id="community-hub-title">
              {watch.origin_iata} → {watch.destination_iata}
            </h2>
            <p>{t("watchlist.communityPricing.hubSubtitle")}</p>
          </div>
          <button
            ref={closeButtonRef}
            className="modal-close"
            type="button"
            aria-label={t("watchlist.communityPricing.close")}
            disabled={isSaving}
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
          <span className="status-pill info">{routeState}</span>
        </div>

        {stage === "overview" ? (
          <>
            <CommunityHubOverview
              watch={watch}
              isSaving={isSaving}
              onMarkPurchased={onMarkPurchased}
              onBeginContribution={onBeginContribution}
              onDeleteResponse={onDeleteResponse}
            />
            <RelatedCommunityRoutes
              origin={watch.origin_iata}
              destination={watch.destination_iata}
            />
          </>
        ) : (
          <div className="community-pricing-step">
            <button
              className="btn-ghost btn-compact community-hub-back"
              type="button"
              onClick={onReturnToOverview}
              disabled={isSaving}
            >
              <ArrowLeft aria-hidden="true" />
              {t("watchlist.communityPricing.backToHub")}
            </button>
            {stage === "flight" ? (
              <>
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
              </>
            ) : (
              <>
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
              </>
            )}
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
        </footer>
      </section>
    </div>
  );
}
