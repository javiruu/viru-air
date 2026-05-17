export function formatDateTime(iso: string, locale = "es-ES"): string {
  return new Date(iso).toLocaleString(locale, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function safeDateTime(iso?: string | null, locale = "es-ES"): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return formatDateTime(iso, locale);
}

/** @deprecated Use getFreshnessPresentation from summary.ts instead. */
export function freshnessLabel(iso?: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const hours = (Date.now() - date.getTime()) / (1000 * 60 * 60);
  if (hours <= 6) return "Reciente";
  if (hours <= 24) return "En observación";
  return "Desactualizado";
}

export function buildSparklinePath(values: number[], width = 96, height = 28): string {
  if (values.length === 0) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return values
    .map((value, index) => {
      const x = values.length === 1 ? width / 2 : (index / (values.length - 1)) * width;
      const y = height - ((value - min) / span) * height;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}
