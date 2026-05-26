# Runbook Proveedor Degradado

1. Detectar incremento de errores por provider (`provider_error_partial`, `provider_timeout_partial`, `provider_total_outage`).
2. Revisar `meta.provider_status.providers[]` para identificar provider degradado y nivel de impacto.
3. Abrir circuito del provider afectado y mantener servicio con providers restantes.
4. Si no hay providers sanos, servir último snapshot válido (`stale=true`) donde aplique.
5. Reducir frecuencia de consulta y aplicar reintentos controlados por provider.
6. Aplicar guardrail de ráfagas en refresh manual con `WATCH_REFRESH_COOLDOWN_SECONDS` (default: `60`).
   - Endpoint afectado: `POST /api/v1/watchlist/{watch_id}/refresh-now`
   - En cooldown activo devuelve `429 refresh_cooldown_active` + header `Retry-After`.
7. Observar ratio de bloqueos `429 refresh_cooldown_active` por `user_id/watch_id` en logs (`event=watch_refresh_denied_cooldown`).
8. Comunicar estado degradado en API/UI con foco multi-provider.
9. Recuperar gradualmente y reconciliar snapshots.
