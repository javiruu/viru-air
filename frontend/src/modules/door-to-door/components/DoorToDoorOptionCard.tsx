import React from "react";
import type { DoorToDoorOption } from "@/modules/door-to-door/types";
import { DoorToDoorRiskPill } from "@/modules/door-to-door/components/DoorToDoorRiskPill";
import { DoorToDoorSourceBadge } from "@/modules/door-to-door/components/DoorToDoorSourceBadge";

function durationLabel(minutes: number) {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h${String(mins).padStart(2, "0")}`;
}

function priceLabel(option: DoorToDoorOption) {
  if (option.total_price_min == null || option.total_price_max == null) return "precio no disponible";
  if (option.total_price_min === option.total_price_max) return `desde ${option.total_price_min} ${option.currency}`;
  return `${option.total_price_min}-${option.total_price_max} ${option.currency} estimado`;
}

export function DoorToDoorOptionCard({
  option,
  selected,
  chosen,
  onSelect,
  onChoose,
}: {
  option: DoorToDoorOption;
  selected: boolean;
  chosen: boolean;
  onSelect: () => void;
  onChoose: () => void;
}) {
  return (
    <article className={`d2d-option-card ${selected ? "is-selected" : ""} ${option.is_recommended ? "is-recommended" : ""}`}>
      <button type="button" className="d2d-option-main" onClick={onSelect} aria-pressed={selected}>
        <div className="d2d-option-head">
          <div>
            <span className="d2d-option-kicker">{option.is_recommended ? "Recomendada" : option.is_extended ? "Alternativa" : "Opción"}</span>
            <h3>{option.label}</h3>
          </div>
          <DoorToDoorRiskPill risk={option.risk_level} />
        </div>
        <strong className="d2d-option-price">{priceLabel(option)} · {durationLabel(option.total_duration_minutes)}</strong>
        <p>{option.description}</p>
        <div className="d2d-option-meta">
          <span>{option.airport_buffer_minutes ?? "--"} min margen</span>
          <span>{option.transfer_count} cambios</span>
          <span>Score {option.score}</span>
          {option.price_per_person_min != null ? <span>{option.price_per_person_min}-{option.price_per_person_max} {option.currency}/persona</span> : null}
        </div>
        <div className="d2d-option-sources">
          {option.sources.slice(0, 2).map((source) => (
            <DoorToDoorSourceBadge key={`${option.id}-${source.provider}`} confidence={source.confidence} label={source.source_type === "mock" ? "Estimado mock" : undefined} />
          ))}
          {option.source_types.includes("scraper") ? <DoorToDoorSourceBadge confidence="cached" label="Scraper opt-in" /> : null}
        </div>
      </button>
      <div className="d2d-option-actions">
        {option.legs.some((leg) => leg.booking_url) ? (
          <a className="btn-secondary btn-compact" href={option.legs.find((leg) => leg.booking_url)?.booking_url || "#"} target="_blank" rel="noreferrer">Abrir reserva</a>
        ) : null}
        <button type="button" className="btn-ghost btn-compact" onClick={onChoose}>{chosen ? "Plan elegido" : "Marcar elegida"}</button>
      </div>
    </article>
  );
}
