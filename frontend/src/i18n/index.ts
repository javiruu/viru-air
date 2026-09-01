import { useEffect, useMemo, useState } from "react";

import es from "./es";
import en from "./en";
import { DEFAULT_LOCALE, getLanguage, LANGUAGES, type Locale, type LocaleTag } from "./config";

export { DEFAULT_LOCALE, LANGUAGES, getLanguage, type Locale, type LocaleTag } from "./config";

type Dictionary = typeof es;
type DictValue = string | { one: string; other: string };

const DICTS: Record<Locale, Dictionary> = { es, en };
const LOCALE_CHANGE_EVENT = "viru:locale-changed";

export function normalizeLocale(raw?: string | null): Locale {
  if (!raw) return DEFAULT_LOCALE;
  const lower = raw.trim().toLowerCase();
  const language = LANGUAGES.find(({ locale }) => lower === locale || lower.startsWith(`${locale}-`));
  return language?.locale ?? DEFAULT_LOCALE;
}

export function resolveLocale(raw?: string | null): Locale {
  if (raw) return normalizeLocale(raw);
  if (typeof window !== "undefined" && window.localStorage) {
    const stored = window.localStorage.getItem("viru_locale");
    if (stored) return normalizeLocale(stored);
  }
  if (typeof navigator !== "undefined" && navigator.language) {
    return normalizeLocale(navigator.language);
  }
  return DEFAULT_LOCALE;
}

export function localeTag(locale: Locale): LocaleTag {
  return getLanguage(locale).localeTag;
}

export function persistLocale(locale: Locale) {
  if (typeof window === "undefined") return;
  const normalizedLocale = normalizeLocale(locale);
  window.localStorage.setItem("viru_locale", normalizedLocale);
  if (document?.documentElement) {
    document.documentElement.lang = normalizedLocale;
  }
  window.dispatchEvent(new CustomEvent(LOCALE_CHANGE_EVENT, { detail: normalizedLocale }));
}

function getNestedValue(dict: Dictionary, key: string): DictValue | null {
  const parts = key.split(".");
  let current: unknown = dict;
  for (const part of parts) {
    if (!current || typeof current !== "object") return null;
    current = (current as Record<string, unknown>)[part];
  }
  if (typeof current === "string") return current;
  if (current && typeof current === "object" && "one" in (current as Record<string, unknown>)) {
    return current as { one: string; other: string };
  }
  return null;
}

function formatTemplate(value: string, params?: Record<string, string | number>) {
  if (!params) return value;
  return Object.entries(params).reduce((acc, [key, paramValue]) => {
    return acc.replaceAll(`{${key}}`, String(paramValue));
  }, value);
}

export function t(locale: Locale, key: string, params?: Record<string, string | number>): string {
  const dict = DICTS[locale] || DICTS[DEFAULT_LOCALE];
  const entry = getNestedValue(dict, key) ?? getNestedValue(DICTS[DEFAULT_LOCALE], key);
  if (!entry) {
    return key;
  }
  if (typeof entry === "string") {
    return formatTemplate(entry, params);
  }
  const countValue = typeof params?.count === "number" ? params?.count : Number(params?.count);
  const choice = Number.isFinite(countValue) && Number(countValue) === 1 ? entry.one : entry.other;
  return formatTemplate(choice, params);
}

export function translate(key: string, params?: Record<string, string | number>, rawLocale?: string | null): string {
  const locale = resolveLocale(rawLocale);
  return t(locale, key, params);
}

export function useI18n(rawLocale?: string | null) {
  const [locale, setLocale] = useState<Locale>(() => normalizeLocale(rawLocale));

  useEffect(() => {
    const syncLocale = (nextLocale: Locale) => {
      setLocale(nextLocale);
      document.documentElement.lang = nextLocale;
    };
    const initialLocale = rawLocale ? normalizeLocale(rawLocale) : resolveLocale();
    syncLocale(initialLocale);
    const onLocaleChange = (event: Event) => {
      const detail = (event as CustomEvent<Locale>).detail;
      syncLocale(detail ? normalizeLocale(detail) : resolveLocale());
    };
    window.addEventListener(LOCALE_CHANGE_EVENT, onLocaleChange);
    return () => window.removeEventListener(LOCALE_CHANGE_EVENT, onLocaleChange);
  }, [rawLocale]);

  const localeKey = localeTag(locale);
  const translator = useMemo(() => (key: string, params?: Record<string, string | number>) => t(locale, key, params), [locale]);
  return { locale, localeTag: localeKey, t: translator };
}
