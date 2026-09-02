import { ArrowRight, Check, Minus, Pause, Plane, Play, Trash2, TrendingDown, TrendingUp } from "lucide-react";

import { useI18n } from "@/i18n";
import { CommunityRouteSignal } from "@/modules/community-routes/CommunityRouteSignal";
import type { CommunityRouteInsight } from "@/modules/community-routes/communityRoutesTypes";
import { getAirportMeta } from "@/modules/shared/airports";
import { formatCurrency, formatSignedCurrency } from "@/modules/shared/format";
import { getWatchStatusMeta } from "@/modules/shared/statusCatalog";
import { CommunityHubButton } from "@/modules/watchlist/components/CommunityHubButton";
import type { Watch } from "@/modules/watchlist/types";

export type WatchMetaEntry = {
  readonly latest: {
    readonly capturedAt: string;
    readonly price: number;
    readonly currency: string;
    readonly provider: string | null;
  } | null;
  readonly previous: {
    readonly price: number;
    readonly currency: string;
  } | null;
  readonly min: number | null;
  readonly max: number | null;
};

type TicketCity = {
  readonly label: string;
  readonly art: string;
};

const TICKET_CITIES: Readonly<Record<string, TicketCity>> = {
  ALC: { label: "Alicante", art: "alicante" },
  BER: { label: "Berlín", art: "berlin" },
  BRU: { label: "Bruselas", art: "bruselas" },
  BUD: { label: "Budapest", art: "budapest" },
  CTA: { label: "Catania", art: "catania" },
  CGN: { label: "Colonia", art: "colonia" },
  DUB: { label: "Dublín", art: "dublin" },
  EIN: { label: "Eindhoven", art: "eindhoven" },
  FAO: { label: "Faro", art: "faro" },
  FRA: { label: "Frankfurt", art: "frankfurt" },
  FUE: { label: "Fuerteventura", art: "fuerteventura" },
  LPA: { label: "Gran Canaria", art: "gran canaria" },
  ACE: { label: "Lanzarote", art: "lanzarote" },
  LHR: { label: "Londres", art: "londres" },
  LGW: { label: "Londres", art: "londres" },
  LTN: { label: "Londres", art: "londres" },
  STN: { label: "Londres", art: "londres" },
  LCY: { label: "Londres", art: "londres" },
  AGP: { label: "Málaga", art: "malaga" },
  RAK: { label: "Marrakech", art: "marrakech" },
  MXP: { label: "Milán", art: "milan" },
  LIN: { label: "Milán", art: "milan" },
  BGY: { label: "Milán", art: "milan" },
  OPO: { label: "Oporto", art: "oporto" },
  PMO: { label: "Palermo", art: "palermo" },
  CDG: { label: "París", art: "paris" },
  ORY: { label: "París", art: "paris" },
  BVA: { label: "París", art: "paris" },
  PSA: { label: "Pisa", art: "pisa" },
  PRG: { label: "Praga", art: "praga" },
  FCO: { label: "Roma", art: "roma" },
  CIA: { label: "Roma", art: "roma" },
  SVQ: { label: "Sevilla", art: "sevilla" },
  TSF: { label: "Treviso", art: "" },
  TRS: { label: "Trieste", art: "" },
  VIE: { label: "Viena", art: "viena" },
};

function ticketCity(iata: string): TicketCity {
  const code = iata.toUpperCase();
  const configuredCity = TICKET_CITIES[code];
  if (configuredCity) return configuredCity;

  return { label: getAirportMeta(code)?.city ?? iata, art: "" };
}

function ticketDate(value: string, localeTag: string) {
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) {
    return { day: "--", month: "", year: "" };
  }

  return {
    day: new Intl.DateTimeFormat(localeTag, { day: "2-digit" }).format(date),
    month: new Intl.DateTimeFormat(localeTag, { month: "long" })
      .format(date)
      .toUpperCase(),
    year: new Intl.DateTimeFormat(localeTag, { year: "numeric" }).format(date),
  };
}

type WatchRowProps = {
  readonly watch: Watch;
  readonly meta: WatchMetaEntry | undefined;
  readonly communityInsight: CommunityRouteInsight | undefined;
  readonly isSelected: boolean;
  readonly onSelect: (watch: Watch) => void;
  readonly onOpenCommunity: (
    watch: Watch,
    trigger: HTMLButtonElement,
  ) => void;
  readonly onPause: (watchId: string) => void;
  readonly onResume: (watchId: string) => void;
  readonly onDelete: (watchId: string) => void;
};

export function WatchRow({
  watch,
  meta,
  communityInsight,
  isSelected,
  onSelect,
  onOpenCommunity,
  onPause,
  onResume,
  onDelete,
}: WatchRowProps) {
  const { t, localeTag } = useI18n();
  const origin = ticketCity(watch.origin_iata);
  const destination = ticketCity(watch.destination_iata);
  const ticketArt = origin.art || destination.art;
  const departureDate = ticketDate(watch.travel_date_local, localeTag);
  const watchStatus = getWatchStatusMeta(watch.status, t);
  const showWatchStatus = watch.status !== "active";
  const canManageTracking =
    !watch.community_pricing.eligible && watch.status !== "purchased";
  const trend =
    !meta?.latest || !meta.previous
      ? "flat"
      : meta.latest.price > meta.previous.price
        ? "up"
        : meta.latest.price < meta.previous.price
          ? "down"
          : "flat";
  const deltaLabel =
    !meta?.latest || !meta.previous
      ? t("watchlist.smartList.noTrend")
      : formatSignedCurrency(
          meta.latest.price - meta.previous.price,
          meta.latest.currency,
          localeTag,
        );
  const priceDropAmount =
    trend === "down" && meta?.latest && meta.previous
      ? meta.previous.price - meta.latest.price
      : null;
  const priceDropPercent =
    priceDropAmount !== null && meta?.previous && meta.previous.price > 0
      ? Math.round((priceDropAmount / meta.previous.price) * 100)
      : null;
  const percentDelta =
    meta?.previous && meta.previous.price > 0 && meta.latest
      ? Math.round(
          ((meta.latest.price - meta.previous.price) / meta.previous.price) *
            100,
        )
      : null;
  const trendPercentLabel =
    percentDelta !== null && percentDelta !== 0
      ? t("watchlist.smartList.trendPercentDelta", {
          value: `${percentDelta > 0 ? "+" : ""}${percentDelta}`,
        })
      : "";
  const hasMeaningfulDrop =
    priceDropAmount !== null &&
    priceDropPercent !== null &&
    priceDropPercent > 0;
  const isBestPrice = Boolean(
    meta?.latest &&
      meta.min !== null &&
      meta.latest.price <= meta.min &&
      meta.max !== null &&
      meta.max > meta.min,
  );
  const trendIcon =
    trend === "up" ? <TrendingUp aria-hidden="true" /> : trend === "down" ? <TrendingDown aria-hidden="true" /> : <Minus aria-hidden="true" />;
  return (
    <article
      className={`list-row watch-row watch-ticket-row ${isSelected ? "watch-selected" : ""}`}
      data-selected={isSelected ? "true" : "false"}
      data-has-art={ticketArt ? "true" : "false"}
    >
      <button
        className="watch-row-select-surface"
        type="button"
        aria-pressed={isSelected}
        aria-label={t("watchlist.smartList.selectRowAria", {
          origin: watch.origin_iata,
          destination: watch.destination_iata,
          date: watch.travel_date_local,
        })}
        onClick={() => onSelect(watch)}
      />
      <CommunityHubButton watch={watch} onOpen={onOpenCommunity} variant="ticket" />
      <div
        className="watch-ticket-art"
        aria-hidden="true"
        style={
          ticketArt
            ? { backgroundImage: `url("/illustraciones/${ticketArt}.webp")` }
            : undefined
        }
      />
      <div className="watch-ticket-main">
        <div className="watch-ticket-route">
          <div className="watch-ticket-airport">
            <span>{origin.label}</span>
            <strong className="watch-route-code">{watch.origin_iata}</strong>
          </div>
          <ArrowRight className="watch-ticket-route-plane" aria-hidden="true" />
          <div className="watch-ticket-airport">
            <span>{destination.label}</span>
            <strong>{watch.destination_iata}</strong>
          </div>
          <span className="sr-only">{watch.origin_iata} → {watch.destination_iata}</span>
        </div>
        <svg className="watch-ticket-path" viewBox="0 0 460 70" fill="none" aria-hidden="true">
          <circle cx="20" cy="35" r="5" />
          <path d="M31 35c68 42 113-31 188 1s114 38 220-4" />
          <circle cx="449" cy="32" r="5" />
        </svg>
        <div className="watch-ticket-status-line">
          {showWatchStatus ? <span className={`status-pill ${watchStatus.tone}`}>{watchStatus.label}</span> : null}
          <CommunityRouteSignal watchersCount={watch.watchers_count ?? 0} insight={communityInsight} />
        </div>
        <div className="watch-ticket-pricing">
          <div className="watch-price tabular-nums">
            <span className="watch-price-caption">{t("watchlist.smartList.currentPrice")}</span>
            <strong className="watch-ticket-price">
              {meta?.latest ? formatCurrency(meta.latest.price, meta.latest.currency, localeTag) : "--"}
            </strong>
          </div>
          <div className={`watch-ticket-trend trend-${trend}`}>
            <span className="watch-ticket-trend-icon">{trendIcon}</span>
            <strong>{meta && meta.previous ? (deltaLabel) : "--"}</strong>
            <span>
              <b className="trend-chip-percent">{trendPercentLabel || "--"}</b>
            </span>
          </div>
        </div>
        <div className="watch-ticket-actions">
          {watch.status === "purchased" ? (
            <div className="alert-actions watch-ticket-action-buttons watch-ticket-action-buttons--purchased">
              <span className="watch-ticket-purchased-action">
                <Check aria-hidden="true" />
                {watchStatus.label}
              </span>
              <button
                className="btn-danger btn-compact"
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onDelete(watch.id);
                }}
              >
                <Trash2 aria-hidden="true" />
                {t("watchlist.smartList.delete")}
              </button>
            </div>
          ) : (
            <>
              <span className={`watch-ticket-trend-action watch-ticket-trend-action--${trend}`}>
                {trendIcon}
                {trend === "up"
                  ? t("watchlist.smartList.trendUp")
                  : trend === "down"
                    ? t("watchlist.smartList.trendDown")
                    : t("watchlist.smartList.trendStable")}
              </span>
              {meta?.latest && (hasMeaningfulDrop || isBestPrice) ? (
                <div className="watch-price-badges">
                  {hasMeaningfulDrop && priceDropAmount !== null && priceDropPercent !== null ? (
                    <span className="price-drop-badge tabular-nums">{formatCurrency(priceDropAmount, meta.latest.currency, localeTag)} ({priceDropPercent}%)</span>
                  ) : null}
                  {isBestPrice ? <span className="best-price-badge">{t("watchlist.compare.bestPriceBadge")}</span> : null}
                </div>
              ) : null}
              <div className="alert-actions watch-ticket-action-buttons">
                {canManageTracking && watch.status === "paused" ? (
              <button
                className="btn-ghost btn-compact"
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onResume(watch.id);
                }}
              >
                  <Play aria-hidden="true" />
                {t("watchlist.smartList.resume")}
              </button>
                ) : canManageTracking ? (
              <button
                className="btn-ghost btn-compact"
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onPause(watch.id);
                }}
              >
                <Pause aria-hidden="true" />
                {t("watchlist.smartList.pause")}
              </button>
                ) : null}
                <button
                  className="btn-danger btn-compact"
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onDelete(watch.id);
                  }}
                >
                  <Trash2 aria-hidden="true" />
                  {t("watchlist.smartList.delete")}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
      <aside className="watch-ticket-stub" aria-label={watch.travel_date_local}>
        <div className="watch-ticket-date-zone">
          <div className="watch-ticket-date-caption"><span /><b>FECHA <Plane aria-hidden="true" /></b><span /></div>
          <strong className="watch-ticket-day tabular-nums">{departureDate.day}</strong>
          <span className="watch-ticket-month">{departureDate.month}</span>
          <span className="watch-ticket-year tabular-nums">{departureDate.year}</span>
        </div>
        <div className="watch-ticket-stub-lower">
          <div className="watch-ticket-stub-rule" />
          <div className="watch-ticket-postal-waves" aria-hidden="true" />
          <div className="watch-ticket-stamp" aria-hidden="true">
            <span>VIRU TRACKER</span>
            <Plane />
            <strong>BUEN VIAJE</strong>
            <small>EST. 2024</small>
          </div>
        </div>
      </aside>
    </article>
  );
}
