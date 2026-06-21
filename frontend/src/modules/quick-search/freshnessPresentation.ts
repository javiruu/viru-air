import { QuickSearchFreshness, QuickSearchFreshnessStatus } from "@/modules/quick-search/types";

type QuickSearchFreshnessPresentationTone = "fresh" | "warn" | "stale" | "neutral";

export type QuickSearchFreshnessPresentation = {
  status: QuickSearchFreshnessStatus | "unknown";
  label: string;
  shortLabel: string;
  tone: QuickSearchFreshnessPresentationTone;
  observedAt: string | null;
  isStaleLike: boolean;
  isUnavailable: boolean;
};

type QuickSearchFreshnessPresentationArgs = {
  freshness?: QuickSearchFreshness | null;
  freshnessTs?: string | null;
  staleData?: boolean;
  now?: number;
};

function formatRelativeMinutes(totalMinutes: number): string {
  if (totalMinutes < 60) return `${totalMinutes} min`;
  const hours = Math.round(totalMinutes / 60);
  return `${hours} h`;
}

export function formatQuickSearchFreshnessRelative(value?: string | null, now = Date.now()): string | null {
  if (!value) return null;
  const ts = new Date(value).getTime();
  if (Number.isNaN(ts)) return null;
  const diff = Math.max(0, now - ts);
  const mins = Math.round(diff / 60000);
  return formatRelativeMinutes(mins);
}

function resolvePresentationStatus({
  freshness,
  freshnessTs,
  staleData,
}: QuickSearchFreshnessPresentationArgs): QuickSearchFreshnessStatus | "unknown" {
  if (freshness?.status) return freshness.status;
  if (staleData) return "stale";
  if (freshnessTs || freshness?.observed_at) return "fresh";
  return "unknown";
}

export function getQuickSearchFreshnessPresentation({
  freshness,
  freshnessTs,
  staleData = false,
  now = Date.now(),
}: QuickSearchFreshnessPresentationArgs): QuickSearchFreshnessPresentation {
  const observedAt = freshness?.observed_at ?? freshnessTs ?? null;
  const relative = formatQuickSearchFreshnessRelative(observedAt, now);
  const status = resolvePresentationStatus({ freshness, freshnessTs, staleData });

  switch (status) {
    case "fresh":
      return {
        status,
        label: relative ? `Precio verificado hace ${relative}` : "Precio verificado hace poco",
        shortLabel: relative ? `Verificado ${relative}` : "Precio verificado",
        tone: "fresh",
        observedAt,
        isStaleLike: false,
        isUnavailable: false,
      };
    case "warm":
      return {
        status,
        label: relative ? `Comprobado hace ${relative}. Actualiza antes de decidir.` : "Actualiza antes de decidir.",
        shortLabel: relative ? `Comprobado ${relative}` : "Actualiza antes de decidir",
        tone: "warn",
        observedAt,
        isStaleLike: false,
        isUnavailable: false,
      };
    case "stale":
    case "expired":
      return {
        status,
        label: "Precio historico. Puede haber cambiado.",
        shortLabel: "Precio historico",
        tone: "stale",
        observedAt,
        isStaleLike: true,
        isUnavailable: false,
      };
    case "negative_fresh":
      return {
        status,
        label: "Sin resultados comprobados hace poco.",
        shortLabel: "Sin resultados reciente",
        tone: "neutral",
        observedAt,
        isStaleLike: false,
        isUnavailable: false,
      };
    case "negative_stale":
      return {
        status,
        label: "Sin resultados antiguo. Conviene repetir la busqueda.",
        shortLabel: "Sin resultados antiguo",
        tone: "stale",
        observedAt,
        isStaleLike: true,
        isUnavailable: false,
      };
    case "provider_error_fresh":
      return {
        status,
        label: "Proveedor sin respuesta. Conservamos la ultima senal.",
        shortLabel: "Ultima senal conservada",
        tone: "warn",
        observedAt,
        isStaleLike: false,
        isUnavailable: false,
      };
    case "provider_error_stale":
      return {
        status,
        label: "Proveedor sin respuesta. La ultima senal ya es antigua.",
        shortLabel: "Proveedor sin respuesta",
        tone: "stale",
        observedAt,
        isStaleLike: true,
        isUnavailable: false,
      };
    default:
      return {
        status: "unknown",
        label: "Ultima comprobacion no disponible",
        shortLabel: "Sin referencia reciente",
        tone: "neutral",
        observedAt,
        isStaleLike: false,
        isUnavailable: true,
      };
  }
}
