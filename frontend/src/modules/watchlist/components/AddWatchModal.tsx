import type { FormEventHandler } from "react";
import { useI18n } from "@/i18n";

type PickerField = "origin" | "destination";

type AddWatchModalProps = {
  isOpen: boolean;
  travelDate: string;
  origin: string;
  destination: string;
  targetPrice: string;
  onClose: () => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
  onTravelDateChange: (value: string) => void;
  onOriginChange: (value: string) => void;
  onDestinationChange: (value: string) => void;
  onTargetPriceChange: (value: string) => void;
  onOpenPicker: (field: PickerField) => void;
};

export function AddWatchModal({
  isOpen,
  travelDate,
  origin,
  destination,
  targetPrice,
  onClose,
  onSubmit,
  onTravelDateChange,
  onOriginChange,
  onDestinationChange,
  onTargetPriceChange,
  onOpenPicker,
}: AddWatchModalProps) {
  const { t } = useI18n();
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <section
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-label={t("watchlist.modal.title")}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <h2 className="panel-title">{t("watchlist.modal.title")}</h2>
            <p className="panel-subtitle">{t("watchlist.modal.subtitle")}</p>
          </div>
          <button className="modal-close" type="button" aria-label={t("watchlist.modal.close")} onClick={onClose}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <form className="form" onSubmit={onSubmit}>
          <label className="date-field field">
            {t("watchlist.modal.date")}
            <input
              type="date"
              name="travel_date"
              autoComplete="off"
              value={travelDate}
              onChange={(e) => onTravelDateChange(e.target.value)}
            />
          </label>

          <div className="airport-row">
            <label className="field">
              {t("watchlist.modal.origin")}
              <input
                name="origin_iata"
                autoComplete="off"
                value={origin}
                onChange={(e) => onOriginChange(e.target.value.toUpperCase())}
                placeholder="MAD"
                disabled={!travelDate}
              />
              <small className="hint">
                {travelDate ? t("watchlist.modal.hintEnabled") : t("watchlist.modal.hintDisabled")}
              </small>
            </label>
            <button type="button" className="btn-ghost" onClick={() => onOpenPicker("origin")} disabled={!travelDate}>
              {t("watchlist.modal.pickAirport")}
            </button>
          </div>

          <div className="airport-row">
            <label className="field">
              {t("watchlist.modal.destination")}
              <input
                name="destination_iata"
                autoComplete="off"
                value={destination}
                onChange={(e) => onDestinationChange(e.target.value.toUpperCase())}
                placeholder="DUB"
                disabled={!travelDate}
              />
              <small className="hint">
                {travelDate ? t("watchlist.modal.hintEnabled") : t("watchlist.modal.hintDisabled")}
              </small>
            </label>
            <button type="button" className="btn-ghost" onClick={() => onOpenPicker("destination")} disabled={!travelDate}>
              {t("watchlist.modal.pickAirport")}
            </button>
          </div>

          <label className="field">
            {t("watchlist.modal.targetPrice")}
            <input
              name="target_price"
              autoComplete="off"
              inputMode="decimal"
              value={targetPrice}
              onChange={(e) => onTargetPriceChange(e.target.value)}
              placeholder="39.99"
            />
          </label>

          <div className="cta-row">
            <button type="submit" className="btn-primary">
              {t("watchlist.modal.save")}
            </button>
            <button type="button" className="btn-ghost" onClick={onClose}>
              {t("shared.actions.cancel")}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

