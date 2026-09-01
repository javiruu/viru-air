"use client";

import Image from "next/image";
import { Check, ChevronDown } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";

import { LANGUAGES, persistLocale, useI18n, type Locale } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import { hasToken } from "@/modules/shared/auth";

type RegionPref = {
  language: string;
  region: string;
  time_format: string;
  decimal_separator: string;
  currency: string;
};

async function persistProfileLanguage(locale: Locale) {
  if (!hasToken()) return;

  try {
    const preference = await apiFetch<RegionPref>("/preferences/region");
    await apiFetch<{ status: string }>("/preferences/region", {
      method: "PUT",
      body: JSON.stringify({ ...preference, language: locale }),
    });
  } catch {
    // The active locale is already stored locally; a transient profile sync failure must not undo it.
  }
}

export default function LanguageSelector() {
  const { locale, t } = useI18n();
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const menuId = useId();
  const activeLanguage = LANGUAGES.find((language) => language.locale === locale) ?? LANGUAGES[0];
  const activeIndex = LANGUAGES.findIndex((language) => language.locale === activeLanguage.locale);

  const closeMenu = useCallback((restoreFocus = false) => {
    setIsOpen(false);
    if (restoreFocus) {
      window.requestAnimationFrame(() => triggerRef.current?.focus());
    }
  }, []);

  const openMenu = useCallback((focusIndex?: number) => {
    setIsOpen(true);
    if (typeof focusIndex === "number") {
      window.requestAnimationFrame(() => optionRefs.current[focusIndex]?.focus());
    }
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        closeMenu();
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeMenu(true);
      }
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [closeMenu, isOpen]);

  const selectLanguage = useCallback((nextLocale: Locale) => {
    persistLocale(nextLocale);
    closeMenu(true);
    void persistProfileLanguage(nextLocale);
  }, [closeMenu]);

  const moveFocus = (currentIndex: number, direction: 1 | -1) => {
    const nextIndex = (currentIndex + direction + LANGUAGES.length) % LANGUAGES.length;
    optionRefs.current[nextIndex]?.focus();
  };

  return (
    <div ref={rootRef} className="language-selector">
      <button
        ref={triggerRef}
        type="button"
        className="language-selector__trigger"
        aria-label={`${t("shared.a11y.changeLanguage")}: ${activeLanguage.label}`}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-controls={menuId}
        onClick={() => (isOpen ? closeMenu() : openMenu(activeIndex))}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            openMenu(activeIndex);
          }
          if (event.key === "ArrowUp") {
            event.preventDefault();
            openMenu((activeIndex - 1 + LANGUAGES.length) % LANGUAGES.length);
          }
        }}
      >
        <Image
          className="language-selector__flag"
          src={`/flags/${activeLanguage.countryCode}.svg`}
          alt=""
          width={24}
          height={16}
          unoptimized
          aria-hidden="true"
        />
        <span className="language-selector__short-label">{activeLanguage.shortLabel}</span>
        <ChevronDown className={`language-selector__chevron${isOpen ? " is-open" : ""}`} size={15} strokeWidth={2} aria-hidden="true" />
      </button>

      {isOpen ? (
        <div id={menuId} className="language-selector__menu" role="menu" aria-label={t("shared.a11y.languageMenu")}>
          {LANGUAGES.map((language, index) => {
            const selected = language.locale === locale;
            return (
              <button
                key={language.locale}
                ref={(element) => {
                  optionRefs.current[index] = element;
                }}
                type="button"
                className={`language-selector__option${selected ? " is-selected" : ""}`}
                role="menuitemradio"
                aria-checked={selected}
                onClick={() => selectLanguage(language.locale)}
                onKeyDown={(event) => {
                  if (event.key === "ArrowDown") {
                    event.preventDefault();
                    moveFocus(index, 1);
                  } else if (event.key === "ArrowUp") {
                    event.preventDefault();
                    moveFocus(index, -1);
                  } else if (event.key === "Home") {
                    event.preventDefault();
                    optionRefs.current[0]?.focus();
                  } else if (event.key === "End") {
                    event.preventDefault();
                    optionRefs.current[LANGUAGES.length - 1]?.focus();
                  } else if (event.key === "Tab") {
                    closeMenu();
                  }
                }}
              >
                <Image
                  className="language-selector__flag"
                  src={`/flags/${language.countryCode}.svg`}
                  alt=""
                  width={28}
                  height={19}
                  unoptimized
                  aria-hidden="true"
                />
                <span className="language-selector__option-copy">
                  <span>{language.label}</span>
                  <span className="language-selector__option-code">{language.shortLabel}</span>
                </span>
                {selected ? <Check className="language-selector__check" size={17} strokeWidth={2.2} aria-hidden="true" /> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
