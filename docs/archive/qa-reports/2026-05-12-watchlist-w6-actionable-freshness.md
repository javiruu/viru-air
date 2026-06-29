# Watchlist W6 Actionable Freshness

**Estado:** vivo  
**Fecha:** 2026-05-13  
**Fuente de verdad:** si  
**Area:** QA / watchlist  
**Commit base:** `7e9f11b3116f5c9a4de5997fda7f5ec365764b49`

## Problema resuelto

La frescura mostraba `En observación` de forma aislada, sin contexto temporal ni acción implícita.  
W6 mantiene tono editorial y añade orientación operativa con tiempo relativo y fallback accionable cuando no hay snapshots.

## Reglas de presentación de frescura

- Sin timestamp/sin snapshot:
  - `Sin datos todavía · actualiza para crear el primer snapshot`
- Timestamp reciente (`<= 24h`):
  - `En observación · actualizado hace X`
- Timestamp antiguo (`> 24h`):
  - `Necesita revisión · última actualización hace X`
- Si existe timestamp, `En observación` no aparece aislado.

## Archivos tocados

- `frontend/src/modules/watchlist/summary.ts`
- `frontend/src/modules/watchlist/components/SmartWatchListPanel.tsx`
- `frontend/src/modules/watchlist/components/WatchDetailPanel.tsx`
- `frontend/src/i18n/domains/watchlist.ts`
- `frontend/tests/watchlist-w6-actionable-freshness.test.ts`
- `docs/qa/reports/2026-05-12-watchlist-w6-actionable-freshness.md`
- `docs/DOCS_INVENTORY.md`

## Tests ejecutados

En `frontend`:

- `npm test`
- `npm run build`
- `npm run lint`

## Pendientes fuera de W6

- W7 mapa plegado.
- W8 comparativa reactiva.
- W9 pulido visual final.
