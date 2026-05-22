import React from "react";

import { useI18n } from "@/i18n";

export function DoorToDoorErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { t } = useI18n();
  return (
    <section className="notice notice-error d2d-error-state" role="alert">
      <div>
        <strong>{t("doorToDoor.states.errorTitle")}</strong>
        <p>{message || t("doorToDoor.states.errorBody")}</p>
      </div>
      <button className="btn-secondary btn-compact" type="button" onClick={onRetry}>{t("doorToDoor.states.retry")}</button>
    </section>
  );
}