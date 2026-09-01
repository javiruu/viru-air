import { publicEn, publicEs } from "./domains/public";
import { createI18n } from "./runtime";
import { sharedEn, sharedEs } from "./shared";

export {
  DEFAULT_LOCALE,
  getLanguage,
  LANGUAGES,
  localeTag,
  normalizeLocale,
  persistLocale,
  resolveLocale,
  type Locale,
  type LocaleTag,
} from "./runtime";

export const { t, translate, useI18n } = createI18n({
  es: { shared: sharedEs, public: publicEs },
  en: { shared: sharedEn, public: publicEn },
});
