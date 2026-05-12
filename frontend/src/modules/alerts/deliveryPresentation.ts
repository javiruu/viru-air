type Translator = (key: string) => string;

export function getDeliveryStateCopy(status: string, t: Translator): string {
  const normalized = status.trim().toLowerCase();
  if (normalized === "queued") return t("alerts.history.pendingDelivery");
  if (normalized === "delivered") return t("alerts.history.deliveredDelivery");
  if (normalized === "sent") return t("alerts.history.sentDelivery");
  if (normalized === "failed" || normalized === "error") return t("alerts.history.failedDelivery");
  return status;
}

export function getNotificationChannelCopy(channel: string, t: Translator): string {
  const normalized = channel.trim().toLowerCase();
  if (normalized === "in_app") return t("alerts.history.channelInApp");
  if (normalized === "email") return t("alerts.history.channelEmail");
  return channel.replace("_", " ");
}
