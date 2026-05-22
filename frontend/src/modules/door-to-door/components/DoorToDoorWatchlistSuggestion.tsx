import React from "react";
import Link from "next/link";

import { useI18n } from "@/i18n";
import type { Watch } from "@/modules/watchlist/types";

export function DoorToDoorWatchlistSuggestion({ watch }: { watch: Watch }) {
  const { t } = useI18n();
  return (
    <section className="panel panel-soft d2d-watch-suggestion" aria-label={t("doorToDoor.watchSuggestion.aria")}>
      <div className="d2d-watch-suggestion-copy">
        <span className="d2d-mini-kicker">{t("doorToDoor.watchSuggestion.kicker")}</span>
        <strong>{t("doorToDoor.watchSuggestion.title", { origin: watch.origin_iata, destination: watch.destination_iata })}</strong>
        <p>{t("doorToDoor.watchSuggestion.body")}</p>
      </div>
      <Link className="btn-primary btn-compact" href={`/puerta-a-puerta?watchId=${encodeURIComponent(watch.id)}`}>
        {t("doorToDoor.watchSuggestion.cta")}
      </Link>
    </section>
  );
}