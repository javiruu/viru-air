type CurrencyKey = `${string}|${string}|${string}`;
type NumberKey = `${string}|${string}`;

const currencyFormatters = new Map<CurrencyKey, Intl.NumberFormat>();
const numberFormatters = new Map<NumberKey, Intl.NumberFormat>();

function currencyKey(locale: string, currency: string, signDisplay: Intl.NumberFormatOptions["signDisplay"]): CurrencyKey {
  return `${locale}|${currency}|${signDisplay || "auto"}`;
}

function numberKey(locale: string, maxFractionDigits: number | undefined, minFractionDigits: number | undefined): NumberKey {
  return `${locale}|${maxFractionDigits ?? "auto"}|${minFractionDigits ?? "auto"}`;
}

function getCurrencyFormatter(
  locale: string,
  currency: string,
  signDisplay: Intl.NumberFormatOptions["signDisplay"] = "auto",
): Intl.NumberFormat {
  const key = currencyKey(locale, currency, signDisplay);
  let formatter = currencyFormatters.get(key);
  if (!formatter) {
    formatter = new Intl.NumberFormat(locale, { style: "currency", currency, signDisplay });
    currencyFormatters.set(key, formatter);
  }
  return formatter;
}

export function formatCurrency(value: number, currency: string, locale = "es-ES"): string {
  return getCurrencyFormatter(locale, currency).format(value);
}

export function formatSignedCurrency(value: number, currency: string, locale = "es-ES"): string {
  return getCurrencyFormatter(locale, currency, "exceptZero").format(value);
}

export function formatNumber(
  value: number,
  options: { maximumFractionDigits?: number; minimumFractionDigits?: number } = {},
  locale = "es-ES",
): string {
  const key = numberKey(locale, options.maximumFractionDigits, options.minimumFractionDigits);
  let formatter = numberFormatters.get(key);
  if (!formatter) {
    formatter = new Intl.NumberFormat(locale, {
      maximumFractionDigits: options.maximumFractionDigits,
      minimumFractionDigits: options.minimumFractionDigits,
    });
    numberFormatters.set(key, formatter);
  }
  return formatter.format(value);
}

export function formatPercent(value: number, locale = "es-ES"): string {
  return `${formatNumber(value, { maximumFractionDigits: 2, minimumFractionDigits: 0 }, locale)}%`;
}

export function formatRelativeTime(input: string | Date | null | undefined): string {
  if (!input) return "sin datos";
  const date = input instanceof Date ? input : new Date(input);
  if (Number.isNaN(date.getTime())) return "sin datos";

  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.max(0, Math.floor(diffMs / 60000));
  if (diffMin < 1) return "hace menos de 1 min";
  if (diffMin < 60) return `hace ${diffMin} min`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `hace ${diffHours} h`;
  const diffDays = Math.floor(diffHours / 24);
  return `hace ${diffDays} d`;
}
