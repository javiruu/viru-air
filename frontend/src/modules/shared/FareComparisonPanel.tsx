"use client";

import React, { type ChangeEvent, useId } from "react";

import {
  FARE_EXTRA_KINDS,
  type FareComparisonProfile,
  type FareExtraKind,
} from "@/modules/shared/fareComparison";

const LABELS: Record<"es" | "en", {
  readonly title: string;
  readonly subtitle: string;
  readonly travelers: string;
  readonly amount: string;
  readonly perPerson: string;
  readonly missing: string;
  readonly extras: Record<FareExtraKind, string>;
}> = {
  es: {
    title: "Precio comparable",
    subtitle: "Crea la misma cesta para todos los vuelos. Los importes son tuyos; Viru no inventa tarifas.",
    travelers: "Viajeros",
    amount: "Precio",
    perPerson: "por persona",
    missing: "Añade el importe para calcular el total real.",
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
    subtitle: "Use the same basket for every flight. Prices are yours; Viru never invents fees.",
    travelers: "Travelers",
    amount: "Price",
    perPerson: "per person",
    missing: "Add the amount to calculate the real total.",
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
  readonly currency: string;
  readonly onChange: (profile: FareComparisonProfile) => void;
};

export function FareComparisonPanel({
  profile,
  locale,
  currency,
  onChange,
}: FareComparisonPanelProps) {
  const copy = LABELS[locale];
  const titleId = useId();

  function updateTravelers(event: ChangeEvent<HTMLInputElement>): void {
    const travelers = Math.max(1, Math.min(9, Number(event.target.value) || 1));
    onChange({ ...profile, travelers });
  }

  function updateExtra(kind: FareExtraKind, selected: boolean, amount: number | null): void {
    const currentByKind = new Map(profile.extras.map((extra) => [extra.kind, extra]));
    onChange({
      ...profile,
      extras: FARE_EXTRA_KINDS.map((extraKind) => {
        const current = currentByKind.get(extraKind) ?? {
          kind: extraKind,
          selected: false,
          amount_per_person: null,
        };
        return extraKind === kind
          ? { ...current, selected, amount_per_person: amount }
          : current;
      }),
    });
  }

  return (
    <section className="fare-comparison" aria-labelledby={titleId}>
      <header className="fare-comparison-header">
        <div>
          <span className="fare-comparison-kicker" id={titleId}>{copy.title}</span>
          <p>{copy.subtitle}</p>
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
            amount_per_person: null,
          };
          return (
            <div className={`fare-extra ${extra.selected ? "fare-extra--selected" : ""}`} key={kind}>
              <label className="fare-extra-toggle">
                <input
                  type="checkbox"
                  checked={extra.selected}
                  onChange={(event) => updateExtra(kind, event.target.checked, extra.amount_per_person)}
                />
                <span>{copy.extras[kind]}</span>
              </label>
              {extra.selected ? (
                <label className="fare-extra-price">
                  <span>{copy.amount}</span>
                  <span className="fare-extra-price-control">
                    <input
                      type="number"
                      min={0}
                      step="0.01"
                      value={extra.amount_per_person ?? ""}
                      aria-label={`${copy.amount}: ${copy.extras[kind]} (${copy.perPerson})`}
                      onChange={(event) => {
                        const value = event.target.value === "" ? null : Number(event.target.value);
                        updateExtra(kind, true, value !== null && Number.isFinite(value) ? Math.max(0, value) : null);
                      }}
                    />
                    <span>{currency}</span>
                  </span>
                  {extra.amount_per_person === null ? <small>{copy.missing}</small> : null}
                </label>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
