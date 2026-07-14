"use client";

import { MapPin, Plus, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  getAdditionalAirportFocusTarget,
  type QuickSearchAdditionalAirport,
} from "@/modules/quick-search/multiple-airports";
import type { AirportIataEntry } from "@/modules/quick-search/types";

type AirportSuggestion = {
  readonly iata: string;
  readonly name: string;
};

type Props = {
  readonly side: "origin" | "destination";
  readonly entries: readonly QuickSearchAdditionalAirport[];
  readonly focusEntryId: string | null;
  readonly airportsByIata: ReadonlyMap<string, AirportIataEntry>;
  readonly recentSuggestions: readonly AirportSuggestion[];
  readonly addLabel: string;
  readonly inputLabel: string;
  readonly removeLabel: string;
  readonly pickerLabel: string;
  readonly invalidLabel: string;
  readonly recentLabel: string;
  readonly maxEntries: number;
  readonly fetchSuggestions: (value: string) => Promise<AirportSuggestion[]>;
  readonly onAdd: () => void;
  readonly onChange: (id: string, value: string) => void;
  readonly onRemove: (id: string) => void;
  readonly onSelect: (id: string, iata: string) => void;
  readonly onOpenPicker: (id: string, trigger: HTMLButtonElement) => void;
};

export function QuickSearchAdditionalAirports(props: Props) {
  const { fetchSuggestions } = props;
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [suggestions, setSuggestions] = useState<AirportSuggestion[]>([]);
  const [touchedIds, setTouchedIds] = useState<ReadonlySet<string>>(new Set());
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const addButtonRef = useRef<HTMLButtonElement | null>(null);
  const activeEntry = props.entries.find((entry) => entry.id === activeId) ?? null;
  const activeValue = activeEntry?.value.trim() ?? "";
  const visibleSuggestions = useMemo(
    () => activeValue ? suggestions : props.recentSuggestions,
    [activeValue, props.recentSuggestions, suggestions],
  );

  useEffect(() => {
    const focusEntryId = props.focusEntryId;
    if (focusEntryId && typeof window !== "undefined") {
      window.requestAnimationFrame(() => inputRefs.current[focusEntryId]?.focus());
    }
  }, [props.focusEntryId]);

  useEffect(() => {
    if (!activeId || !activeValue) {
      setSuggestions([]);
      return;
    }
    let cancelled = false;
    const timeout = window.setTimeout(() => {
      fetchSuggestions(activeValue).then((next) => {
        if (!cancelled) setSuggestions(next);
      }).catch(() => {
        if (!cancelled) setSuggestions([]);
      });
    }, 120);
    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
    };
  }, [activeId, activeValue, fetchSuggestions]);

  const selectSuggestion = (id: string, iata: string) => {
    props.onSelect(id, iata);
    setTouchedIds((current) => new Set(current).add(id));
    setActiveId(null);
    setActiveIndex(-1);
  };

  return (
    <div className="qs-additional-airports" data-side={props.side}>
      {props.entries.map((entry, rowIndex) => {
        const code = entry.value.trim().toUpperCase();
        const isValid = code.length === 3 && props.airportsByIata.has(code);
        const showError = touchedIds.has(entry.id) && code.length > 0 && !isValid;
        const listboxId = `qs-${props.side}-additional-${entry.id}-suggestions`;
        const errorId = `qs-${props.side}-additional-${entry.id}-error`;

        return (
          <div className="qs-additional-airport" key={entry.id}>
            <div className="qs-input-wrap">
              <span className="qs-input-prefix" aria-hidden="true">
                <span className="qs-input-icon"><MapPin /></span>
              </span>
              <input
                ref={(node) => { inputRefs.current[entry.id] = node; }}
                className="qs-input qs-input-with-action"
                name={`${props.side}_iata_optional_${rowIndex + 1}`}
                role="combobox"
                autoComplete="off"
                aria-autocomplete="list"
                aria-label={`${props.inputLabel} ${rowIndex + 2}`}
                aria-expanded={activeId === entry.id && visibleSuggestions.length > 0}
                aria-controls={listboxId}
                aria-activedescendant={activeId === entry.id && activeIndex >= 0
                  ? `${listboxId}-${activeIndex}`
                  : undefined}
                aria-invalid={showError}
                aria-describedby={showError ? errorId : undefined}
                value={entry.value}
                placeholder={props.inputLabel}
                onFocus={() => {
                  setActiveId(entry.id);
                  setActiveIndex(-1);
                }}
                onBlur={() => {
                  setTouchedIds((current) => new Set(current).add(entry.id));
                  window.setTimeout(() => {
                    setActiveId((current) => current === entry.id ? null : current);
                    setActiveIndex(-1);
                  }, 120);
                }}
                onChange={(event) => {
                  props.onChange(entry.id, event.target.value.toUpperCase());
                  setActiveId(entry.id);
                  setActiveIndex(-1);
                }}
                onKeyDown={(event) => {
                  if (event.key === "ArrowDown" && visibleSuggestions.length > 0) {
                    event.preventDefault();
                    setActiveIndex((current) => (current + 1) % visibleSuggestions.length);
                  } else if (event.key === "ArrowUp" && visibleSuggestions.length > 0) {
                    event.preventDefault();
                    setActiveIndex((current) => current <= 0 ? visibleSuggestions.length - 1 : current - 1);
                  } else if (event.key === "Escape") {
                    setActiveId(null);
                    setActiveIndex(-1);
                  } else if (event.key === "Enter" && visibleSuggestions.length > 0) {
                    const selected = visibleSuggestions[activeIndex >= 0 ? activeIndex : 0];
                    if (selected) {
                      event.preventDefault();
                      selectSuggestion(entry.id, selected.iata);
                    }
                  }
                }}
              />
              <button
                type="button"
                className="qs-input-inline-action"
                onClick={(event) => props.onOpenPicker(entry.id, event.currentTarget)}
                aria-label={`${props.pickerLabel} ${rowIndex + 2}`}
              >
                <MapPin aria-hidden="true" />
              </button>
              {activeId === entry.id && visibleSuggestions.length > 0 ? (
                <ul
                  className={!activeValue ? "qs-autocomplete qs-autocomplete-recents" : "qs-autocomplete"}
                  id={listboxId}
                  role="listbox"
                >
                  {!activeValue ? <li className="qs-autocomplete-group-label">{props.recentLabel}</li> : null}
                  {visibleSuggestions.map((suggestion, index) => (
                    <li
                      key={suggestion.iata}
                      role="none"
                    >
                      <button
                        id={`${listboxId}-${index}`}
                        type="button"
                        role="option"
                        aria-selected={index === activeIndex}
                        className={index === activeIndex ? "qs-autocomplete-item active" : "qs-autocomplete-item"}
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => selectSuggestion(entry.id, suggestion.iata)}
                      >
                        <strong>{suggestion.iata}</strong>
                        <span>{suggestion.name}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
            <button
              type="button"
              className="qs-additional-airport__remove"
              onClick={() => {
                const focusTargetId = getAdditionalAirportFocusTarget(props.entries, rowIndex);
                props.onRemove(entry.id);
                window.requestAnimationFrame(() => {
                  if (focusTargetId) {
                    inputRefs.current[focusTargetId]?.focus();
                  } else {
                    addButtonRef.current?.focus();
                  }
                });
              }}
              aria-label={`${props.removeLabel} ${rowIndex + 2}`}
            >
              <X aria-hidden="true" />
            </button>
            {showError ? <small className="qs-error" id={errorId}>{props.invalidLabel}</small> : null}
          </div>
        );
      })}

      {props.entries.length < props.maxEntries ? (
        <button ref={addButtonRef} type="button" className="qs-additional-airports__add" onClick={props.onAdd}>
          <span>{props.addLabel}</span>
          <Plus aria-hidden="true" />
        </button>
      ) : null}
    </div>
  );
}
