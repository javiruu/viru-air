import { formatCurrency, formatSignedCurrency } from "@/modules/shared/format";
import { formatDateTime, freshnessLabel } from "@/modules/watchlist/presentation";

type CompareLatest = {
  capturedAt: string;
  currency: string;
  price: number;
};

type CompareCard = {
  date: string;
  latest: CompareLatest;
  delta: number;
  min: number;
  max: number;
};

type CompareOption = {
  id: string;
  origin: string;
  destination: string;
  travelDate: string;
};

type CompareSelectionItem = {
  id: string;
  origin: string;
  destination: string;
  travelDate: string;
  latest: CompareLatest | null;
  delta: number;
  volatility: number | null;
  min: number | null;
  max: number | null;
};

type CompareBadges = {
  bestPriceId: string | null;
  freshestId: string | null;
  stableId: string | null;
};

type ComparePanelsProps = {
  compareCards: CompareCard[] | null;
  compareOptions: CompareOption[];
  compareSelection: CompareSelectionItem[];
  compareBadges: CompareBadges | null;
  compareIds: string[];
  compareNotice: string;
  onToggleCompare: (id: string) => void;
};

export function ComparePanels({
  compareCards,
  compareOptions,
  compareSelection,
  compareBadges,
  compareIds,
  compareNotice,
  onToggleCompare,
}: ComparePanelsProps) {
  return (
    <>
      {compareCards ? (
        <section className="panel compare-panel section-gap">
          <div className="panel-header">
            <h2 className="panel-title">Comparativa rapida</h2>
            <span className="muted">Dos fechas seleccionadas</span>
          </div>
          <div className="compare-grid">
            {compareCards.map((card) => {
              const trend = card.delta > 0 ? "up" : card.delta < 0 ? "down" : "flat";
              const deltaLabel = card.delta === 0 ? "Sin variación" : formatSignedCurrency(card.delta, card.latest.currency);
              return (
                <article key={`compare-${card.date}`} className="compare-card">
                  <div className="compare-head">
                    <strong>{card.date}</strong>
                    <span className={`trend-chip trend-${trend}`}>
                      <span className="trend-icon" aria-hidden="true">
                        <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                          <path
                            d="M6 15l6-6 6 6"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.8"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </span>
                      {deltaLabel}
                    </span>
                  </div>
                  <div className="compare-body">
                    <div>
                      <span className="compare-label">Actual</span>
                      <strong>{formatCurrency(card.latest.price, card.latest.currency)}</strong>
                    </div>
                    <div>
                      <span className="compare-label">Min</span>
                      <strong>{formatCurrency(card.min, card.latest.currency)}</strong>
                    </div>
                    <div>
                      <span className="compare-label">Max</span>
                      <strong>{formatCurrency(card.max, card.latest.currency)}</strong>
                    </div>
                  </div>
                  <div className="compare-meta">Última actualización: {formatDateTime(card.latest.capturedAt)}</div>
                </article>
              );
            })}
          </div>
        </section>
      ) : null}

      <section className="panel compare-multi-panel section-gap">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Comparativa multi-vuelo</h2>
            <p className="panel-subtitle">Selecciona hasta 4 vuelos para ver precio, estabilidad y frescura.</p>
          </div>
          <span className="compare-count">{compareSelection.length}/4 seleccionados</span>
        </div>
        {compareNotice ? (
          <div className="notice notice-error notice-compact">{compareNotice}</div>
        ) : null}
        <div className="compare-selector">
          {compareOptions.map((option) => {
            const isChecked = compareIds.includes(option.id);
            return (
              <label key={option.id} className={`compare-option ${isChecked ? "active" : ""}`}>
                <input
                  type="checkbox"
                  name="compare_selection"
                  value={option.id}
                  checked={isChecked}
                  onChange={() => onToggleCompare(option.id)}
                />
                <span className="compare-check" aria-hidden="true">
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <path
                      d="M5 12l4 4 10-10"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
                <span className="compare-route">
                  {option.origin} → {option.destination}
                </span>
                <span className="compare-date">{option.travelDate}</span>
              </label>
            );
          })}
        </div>
        {compareSelection.length === 0 ? (
          <p className="muted">Marca vuelos para comparar tendencias y volatilidad.</p>
        ) : (
          <div className="compare-grid compare-grid--multi">
            {compareSelection.map((card) => {
              const currency = card.latest?.currency ?? "EUR";
              const trend = card.delta > 0 ? "up" : card.delta < 0 ? "down" : "flat";
              const deltaLabel = card.delta === 0 ? "Sin variación" : formatSignedCurrency(card.delta, currency);
              const freshness = card.latest ? freshnessLabel(card.latest.capturedAt) : "Sin datos";
              return (
                <article key={`multi-${card.id}`} className="compare-card compare-card--multi">
                  <div className="compare-head">
                    <strong>{card.origin} → {card.destination}</strong>
                    <div className="compare-badges">
                      {compareBadges?.bestPriceId === card.id ? <span className="compare-badge">Mejor precio</span> : null}
                      {compareBadges?.freshestId === card.id ? <span className="compare-badge">Más reciente</span> : null}
                      {compareBadges?.stableId === card.id ? <span className="compare-badge">Más estable</span> : null}
                    </div>
                  </div>
                  <div className="compare-subtitle">{card.travelDate}</div>
                  <div className="compare-body">
                    <div>
                      <span className="compare-label">Actual</span>
                      <strong>{card.latest ? formatCurrency(card.latest.price, card.latest.currency) : "Sin datos"}</strong>
                    </div>
                    <div>
                      <span className="compare-label">Rango</span>
                      <strong>
                        {card.min != null && card.max != null
                          ? `${formatCurrency(card.min, currency)}-${formatCurrency(card.max, currency)}`
                          : "Sin datos"}
                      </strong>
                    </div>
                    <div>
                      <span className="compare-label">Volatilidad</span>
                      <strong>{card.volatility != null ? formatCurrency(card.volatility, currency) : "Sin datos"}</strong>
                    </div>
                  </div>
                  <div className="compare-meta">
                    <span className={`trend-chip trend-${trend}`}>
                      <span className="trend-icon" aria-hidden="true">
                        <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                          <path
                            d="M6 15l6-6 6 6"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.8"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </span>
                      {deltaLabel}
                    </span>
                    <span className="compare-fresh">{freshness}</span>
                    <span className="compare-updated">
                      {card.latest ? formatDateTime(card.latest.capturedAt) : "Sin actualización"}
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </>
  );
}

