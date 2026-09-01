"use client";

import HelpBase from "@/modules/shared/HelpBase";
import { useI18n } from "@/i18n/shell";

export default function AyudaPublicaPage() {
  const { t } = useI18n();

  return (
    <HelpBase
      endpoint="/public/help"
      context="public"
      title={t("public.help.publicTitle")}
      subtitle={t("public.help.publicSubtitle")}
      loadingLabel={t("public.help.publicLoading")}
      loadedSubtitle={t("public.help.publicIntro")}
      systemStatusLabel={t("support.help.systemStatus")}
      publicLoginLabel={t("public.help.publicLogin")}
      publicRegisterLabel={t("public.help.publicRegister")}
    />
  );
}
