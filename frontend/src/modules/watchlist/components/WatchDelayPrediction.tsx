import { useI18n } from "@/i18n";
import { formatLiveTime } from "@/modules/watchlist/liveFlightPresentation";
import type { LiveDelayPrediction } from "@/modules/watchlist/liveFlightTypes";

type WatchDelayPredictionProps = {
  prediction: LiveDelayPrediction | null;
};

export function WatchDelayPrediction({ prediction }: WatchDelayPredictionProps) {
  const { t, localeTag } = useI18n();

  if (!prediction || prediction.status === "not_applicable") return null;

  if (prediction.status === "insufficient_data") {
    return (
      <aside className="watch-delay-prediction watch-delay-prediction--waiting" aria-live="polite">
        <span className="watch-delay-prediction-signal" aria-hidden="true" />
        <div>
          <strong>{t("watchlist.live.prediction.waitingTitle")}</strong>
          <span>{t(`watchlist.live.prediction.reasons.${prediction.reason}`)}</span>
        </div>
      </aside>
    );
  }

  const incomingAircraft = prediction.incoming_aircraft;
  const incomingFlight =
    incomingAircraft.flight_number
    ?? `${incomingAircraft.origin_iata} → ${incomingAircraft.destination_iata}`;
  const incomingArrival =
    incomingAircraft.actual_arrival_at
    ?? incomingAircraft.estimated_arrival_at
    ?? incomingAircraft.scheduled_arrival_at;

  return (
    <aside
      className={`watch-delay-prediction watch-delay-prediction--${prediction.risk}`}
      aria-label={t("watchlist.live.prediction.title")}
    >
      <header className="watch-delay-prediction-header">
        <div>
          <span>{t("watchlist.live.prediction.kicker")}</span>
          <strong>{t("watchlist.live.prediction.title")}</strong>
        </div>
        <small>{t("watchlist.live.prediction.model")}</small>
      </header>

      <div className="watch-delay-prediction-reading">
        <div>
          <span>{t("watchlist.live.prediction.forecast")}</span>
          <strong>
            {t("watchlist.live.prediction.delayRange", {
              min: prediction.predicted_delay_min_minutes,
              max: prediction.predicted_delay_max_minutes,
            })}
          </strong>
        </div>
        <div>
          <span>
            {t("watchlist.live.prediction.riskScore", {
              risk: t(`watchlist.live.prediction.risk.${prediction.risk}`),
              score: prediction.risk_score,
            })}
          </span>
          <small>
            {t("watchlist.live.prediction.confidence", {
              value: t(`watchlist.live.prediction.confidenceValues.${prediction.confidence}`),
            })}
          </small>
        </div>
      </div>

      <div className="watch-delay-prediction-incoming">
        <span className="watch-delay-prediction-route" aria-hidden="true" />
        <div>
          <span>{t("watchlist.live.prediction.incomingLabel")}</span>
          <strong>{incomingFlight} · {incomingAircraft.registration}</strong>
          <small>
            {incomingAircraft.origin_iata} → {incomingAircraft.destination_iata}
            {" · "}
            {formatLiveTime(incomingArrival, localeTag)}
          </small>
        </div>
        <small>
          {t("watchlist.live.prediction.turnaround", {
            minutes: prediction.turnaround_minutes,
          })}
        </small>
      </div>

      <div className="watch-delay-prediction-factors">
        <span>{t("watchlist.live.prediction.why")}</span>
        <div>
          {prediction.factor_codes.map((factor) => (
            <small key={factor}>{t(`watchlist.live.prediction.factors.${factor}`)}</small>
          ))}
        </div>
      </div>

      <footer>{t("watchlist.live.prediction.disclaimer")}</footer>
    </aside>
  );
}
