## ARCHIVED — Feature flags legacy

> Este documento ya no refleja la realidad del proyecto.
> Los flags `ff_prediction_enabled`, `ff_self_connect_enabled`, `ff_everywhere_enabled`,
> `ff_deeplink_hardened`, `ff_country_content`, `ff_full_i18n` y `ff_suggestions_pipeline`
> corresponden a milestones M7-M13 que ya no se utilizan como sistema de feature flags.
>
> El proyecto actualmente no tiene un sistema centralizado de feature flags.
> Las activaciones se manejan mediante:
> - Perfiles de activación por entorno en door-to-door (`docs/runbooks/runbook-activation-profiles.md`)
> - Variables de entorno en `.env`
> - Configuración directa en código para funcionalidades experimentales
>
> **Última revisión:** 2026-06-29
> **Estado:** archivado

# Feature Flags (histórico)

- `ff_prediction_enabled` (M7)
- `ff_self_connect_enabled` (M8)
- `ff_everywhere_enabled` (M9)
- `ff_deeplink_hardened` (M10)
- `ff_country_content` (M11)
- `ff_full_i18n` (M12)
- `ff_suggestions_pipeline` (M13)

Uso histórico: activación progresiva por cohortes, rollback sin redeploy.





