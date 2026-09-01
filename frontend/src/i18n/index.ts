import es from "./es";
import en from "./en";
import { createI18n } from "./runtime";

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

export const { t, translate, useI18n } = createI18n({ es, en });
