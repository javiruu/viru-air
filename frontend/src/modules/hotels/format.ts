export function formatDate(iso: string | null, localeTag: string): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat(localeTag, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function formatDateShort(iso: string | null, localeTag: string): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat(localeTag, {
    day: "2-digit",
    month: "short",
  }).format(new Date(iso));
}

export function formatPrice(value: number | null, currency: string, localeTag: string): string {
  if (value === null) return "—";
  return new Intl.NumberFormat(localeTag, {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}
