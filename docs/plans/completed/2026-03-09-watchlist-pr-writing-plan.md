# Writing Plan — PR hardening de /watchlist (2026-03-09)

## Objetivo
Reducir carga N+1 en histórico de watchlist y reforzar consistencia/rate control en refresh, tocando solo capas necesarias.

## Alcance (sí)
1. Backend: endpoint batch para histórico de precios.
2. Frontend: migrar carga de histórico de N+1 a batch único.
3. Backend: guardrail de cooldown en refresh-now.
4. DB: constraint único para evitar duplicados de watchlist por usuario+ruta+fecha.

## Fuera de alcance (no)
- Cambios de diseño visual.
- Reescritura completa del módulo watchlist.
- Introducción de Redis/colas en este PR.

## Paso a paso
1. **Schemas**: agregar `SnapshotBatchIn` y `SnapshotBatchOut`.
2. **API**: implementar `POST /api/v1/prices/history/batch`.
3. **Frontend**: adaptar `useWatchlistActions.load()` para una sola llamada batch.
4. **Refresh guardrail**: añadir `WATCH_REFRESH_COOLDOWN_SECONDS` en `refresh-now`.
5. **Migración**: añadir índice único `uq_flight_watch_user_route_date`.
6. **QA**: validar flujo watchlist y regresión básica.

## Riesgos y mitigaciones
- **Riesgo**: migración falle por duplicados previos.
  - **Mitigación**: limpieza previa en migración antes de crear índice único.
- **Riesgo**: comportamiento de refresh cambie para usuarios intensivos.
  - **Mitigación**: cooldown configurable por env (`WATCH_REFRESH_COOLDOWN_SECONDS`).

## Checklist de salida
- [ ] El listado watchlist carga histórico con una sola llamada batch.
- [ ] `refresh-now` responde 429 en cooldown activo.
- [ ] No se permiten duplicados de watchlist por usuario/ruta/fecha.
- [ ] Sin cambios colaterales en módulos no relacionados.
