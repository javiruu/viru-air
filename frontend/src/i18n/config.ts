export const LANGUAGES = [
  {
    locale: "es",
    label: "Español",
    shortLabel: "ES",
    countryCode: "es",
    localeTag: "es-ES",
  },
  {
    locale: "en",
    label: "English",
    shortLabel: "EN",
    countryCode: "gb",
    localeTag: "en-US",
  },
] as const;

export type Locale = (typeof LANGUAGES)[number]["locale"];
export type LocaleTag = (typeof LANGUAGES)[number]["localeTag"];

export const DEFAULT_LOCALE: Locale = "es";

export function getLanguage(locale: Locale) {
  return LANGUAGES.find((language) => language.locale === locale) ?? LANGUAGES[0];
}
