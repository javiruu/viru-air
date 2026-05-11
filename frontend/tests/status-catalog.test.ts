import assert from "node:assert/strict";
import test from "node:test";

import { getDeliveryStatusMeta, getSystemStatusMeta, getWatchStatusMeta } from "../src/modules/shared/statusCatalog";

const labels: Record<string, string> = {
  "shared.statusCatalog.watch.active": "Activo",
  "shared.statusCatalog.watch.paused": "Pausado",
  "shared.statusCatalog.watch.deleted": "Eliminado",
  "shared.statusCatalog.delivery.queued": "En espera",
  "shared.statusCatalog.delivery.sent": "Enviado",
  "shared.statusCatalog.delivery.delivered": "Enviado",
  "shared.statusCatalog.delivery.failed": "Error",
  "shared.statusCatalog.delivery.error": "Error",
  "shared.statusCatalog.system.ok": "Operativo",
  "shared.statusCatalog.system.degraded": "Degradado",
  "shared.statusCatalog.system.critical": "Incidencia",
};

function t(key: string): string {
  return labels[key] ?? key;
}

test("watch statuses map to canonical tones and labels", () => {
  assert.deepEqual(getWatchStatusMeta("active", t), { tone: "success", label: "Activo" });
  assert.deepEqual(getWatchStatusMeta("paused", t), { tone: "warning", label: "Pausado" });
  assert.deepEqual(getWatchStatusMeta("deleted", t), { tone: "info", label: "Eliminado" });
});

test("delivery statuses map to canonical tones and labels", () => {
  assert.deepEqual(getDeliveryStatusMeta("queued", t), { tone: "warning", label: "En espera" });
  assert.deepEqual(getDeliveryStatusMeta("sent", t), { tone: "success", label: "Enviado" });
  assert.deepEqual(getDeliveryStatusMeta("failed", t), { tone: "error", label: "Error" });
});

test("system statuses map to canonical tones and labels", () => {
  assert.deepEqual(getSystemStatusMeta("ok", t), { tone: "success", label: "Operativo" });
  assert.deepEqual(getSystemStatusMeta("degraded", t), { tone: "warning", label: "Degradado" });
  assert.deepEqual(getSystemStatusMeta("critical", t), { tone: "error", label: "Incidencia" });
});
