type StatusTone = "success" | "warning" | "error" | "info";
type Translator = (key: string, params?: Record<string, string | number>) => string;

type StatusMeta = {
  tone: StatusTone;
  labelKey: string;
};

const WATCH_STATUS_MAP: Record<string, StatusMeta> = {
  active: { tone: "success", labelKey: "shared.statusCatalog.watch.active" },
  paused: { tone: "warning", labelKey: "shared.statusCatalog.watch.paused" },
  deleted: { tone: "info", labelKey: "shared.statusCatalog.watch.deleted" },
};

const DELIVERY_STATUS_MAP: Record<string, StatusMeta> = {
  queued: { tone: "warning", labelKey: "shared.statusCatalog.delivery.queued" },
  sent: { tone: "success", labelKey: "shared.statusCatalog.delivery.sent" },
  delivered: { tone: "success", labelKey: "shared.statusCatalog.delivery.delivered" },
  failed: { tone: "error", labelKey: "shared.statusCatalog.delivery.failed" },
  error: { tone: "error", labelKey: "shared.statusCatalog.delivery.error" },
};

const SYSTEM_STATUS_MAP: Record<string, StatusMeta> = {
  ok: { tone: "success", labelKey: "shared.statusCatalog.system.ok" },
  degraded: { tone: "warning", labelKey: "shared.statusCatalog.system.degraded" },
  critical: { tone: "error", labelKey: "shared.statusCatalog.system.critical" },
};

function resolveStatusMeta(
  map: Record<string, StatusMeta>,
  rawStatus: string,
  t: Translator,
): { tone: StatusTone; label: string } {
  const normalized = rawStatus.trim().toLowerCase();
  const meta = map[normalized];
  if (!meta) {
    return { tone: "info", label: rawStatus };
  }
  return { tone: meta.tone, label: t(meta.labelKey) };
}

export function getWatchStatusMeta(status: string, t: Translator) {
  return resolveStatusMeta(WATCH_STATUS_MAP, status, t);
}

export function getDeliveryStatusMeta(status: string, t: Translator) {
  return resolveStatusMeta(DELIVERY_STATUS_MAP, status, t);
}

export function getSystemStatusMeta(status: string, t: Translator) {
  return resolveStatusMeta(SYSTEM_STATUS_MAP, status, t);
}
