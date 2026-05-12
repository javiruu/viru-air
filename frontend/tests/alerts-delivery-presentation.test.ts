import assert from "node:assert/strict";
import test from "node:test";

import { getDeliveryStateCopy, getNotificationChannelCopy } from "@/modules/alerts/deliveryPresentation";

const t = (key: string) => {
  const dict: Record<string, string> = {
    "alerts.history.pendingDelivery": "Pendiente de envío",
    "alerts.history.deliveredDelivery": "Entregada",
    "alerts.history.sentDelivery": "Enviado",
    "alerts.history.failedDelivery": "No se pudo enviar",
    "alerts.history.channelInApp": "in-app",
    "alerts.history.channelEmail": "email",
  };
  return dict[key] ?? key;
};

test("queued delivery renders pending copy", () => {
  assert.equal(getDeliveryStateCopy("queued", t), "Pendiente de envío");
});

test("delivered and sent delivery render expected copy", () => {
  assert.equal(getDeliveryStateCopy("delivered", t), "Entregada");
  assert.equal(getDeliveryStateCopy("sent", t), "Enviado");
});

test("failed delivery renders error copy", () => {
  assert.equal(getDeliveryStateCopy("failed", t), "No se pudo enviar");
});

test("channel copy renders in-app and email labels", () => {
  assert.equal(getNotificationChannelCopy("in_app", t), "in-app");
  assert.equal(getNotificationChannelCopy("email", t), "email");
});
