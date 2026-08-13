"use client";

import React, { type ChangeEvent, useId } from "react";

import {
  FARE_EXTRA_KINDS,
  normalizeFareTravelers,
  type FareComparisonProfile,
  type FareExtraKind,
} from "@/modules/shared/fareComparison";

const LABELS: Record<"es" | "en", {
  readonly title: string;
  readonly subtitle: string;
  readonly travelers: string;
  readonly automatic: string;
  readonly extras: Record<FareExtraKind, string>;
}> = {
  es: {
    title: "Precio comparable",
    subtitle: "Elige tu cesta y Viru aplicará los rangos publicados por cada aerolínea en cada resultado.",
    travelers: "Viajeros",
    automatic: "Estimación automática según la unidad publicada",
    extras: {
      cabin_bag_10kg: "Equipaje de cabina · 10 kg",
      checked_bag_20kg: "Maleta facturada · 20 kg",
      insurance: "Seguro de viaje",
      fast_track: "Fast Track",
      priority_boarding: "Embarque prioritario",
      seat_selection: "Selección de asiento",
      flexible_ticket: "Cambios flexibles",
    },
  },
  en: {
    title: "Comparable price",
    subtitle: "Choose your basket and Viru will apply each airline's published ranges to every result.",
    travelers: "Travelers",
    automatic: "Automatic estimate using the published billing unit",
    extras: {
      cabin_bag_10kg: "Cabin bag · 10 kg",
      checked_bag_20kg: "Checked bag · 20 kg",
      insurance: "Travel insurance",
      fast_track: "Fast Track",
      priority_boarding: "Priority boarding",
      seat_selection: "Seat selection",
      flexible_ticket: "Flexible changes",
    },
  },
};

type FareComparisonPanelProps = {
  readonly profile: FareComparisonProfile;
  readonly locale: "es" | "en";
  readonly onChange: (profile: FareComparisonProfile) => void;
  readonly mode?: "comparison" | "extras";
};

export function FareComparisonPanel({
  profile,
  locale,
  onChange,
  mode = "comparison",
}: FareComparisonPanelProps) {
  const copy = LABELS[locale];
  const titleId = useId();
  const isExtrasMode = mode === "extras";
  const title = isExtrasMode
    ? locale === "es" ? "Extras del viaje" : "Trip extras"
    : copy.title;
  const subtitle = isExtrasMode
    ? locale === "es"
      ? "Selecciona lo que quieres añadir. Watchlist suma solo los importes publicados verificables para esta aerolínea."
      : "Choose what to add. Watchlist sums only published, verifiable amounts for this airline."
    : copy.subtitle;
  const selectedNote = isExtrasMode
    ? locale === "es" ? "Añadido a tu cesta" : "Added to your basket"
    : copy.automatic;

  function updateTravelers(event: ChangeEvent<HTMLInputElement>): void {
    const travelers = normalizeFareTravelers(Number(event.target.value));
    onChange({ ...profile, travelers });
  }

  function updateExtra(kind: FareExtraKind, selected: boolean): void {
    const currentByKind = new Map(profile.extras.map((extra) => [extra.kind, extra]));
    onChange({
      ...profile,
      extras: FARE_EXTRA_KINDS.map((extraKind) => {
        const current = currentByKind.get(extraKind) ?? {
          kind: extraKind,
          selected: false,
        };
        return extraKind === kind
          ? { ...current, selected }
          : current;
      }),
    });
  }

  return (
    <section className="fare-comparison" aria-labelledby={titleId}>
      <header className="fare-comparison-header">
        <div>
          <span className="fare-comparison-kicker" id={titleId}>{title}</span>
          <p>{subtitle}</p>
        </div>
        <label className="fare-comparison-travelers">
          <span>{copy.travelers}</span>
          <input type="number" min={1} max={9} value={profile.travelers} onChange={updateTravelers} />
        </label>
      </header>
      <div className="fare-comparison-grid">
        {FARE_EXTRA_KINDS.map((kind) => {
          const extra = profile.extras.find((item) => item.kind === kind) ?? {
            kind,
            selected: false,
          };
          return (
            <div className={`fare-extra ${extra.selected ? "fare-extra--selected" : ""}`} key={kind}>
              <label className="fare-extra-toggle">
                <input
                  type="checkbox"
                  checked={extra.selected}
                  onChange={(event) => updateExtra(kind, event.target.checked)}
                />
                <span>{copy.extras[kind]}</span>
              </label>
              {extra.selected ? (
                <small className="fare-extra-estimate">{selectedNote}</small>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
