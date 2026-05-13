# Watchlist W5 History Confidence

**Estado:** vivo  
**Fecha:** 2026-05-13  
**Fuente de verdad:** si  
**Area:** QA / watchlist  
**Commit base:** `f483772cf94c9dacdc4cc858752087b623878cfe`

## Problema resuelto

En el resumen historico de `WatchDetailPanel`, los KPIs se mostraban correctamente pero con baja muestra (`snapshot_count` bajo) podian transmitir una certeza excesiva.

W5 agrega una capa de contexto de confianza sin ocultar KPIs, sin cambiar calculos y sin tocar backend/endpoints.

## Reglas de confianza por snapshot_count

- `0` snapshots:
  - se mantiene el empty state existente `Aún no hay histórico suficiente para resumir esta ruta.`
  - no se renderiza aviso de confianza adicional.
- `<= 1` snapshot:
  - titulo: `Histórico inicial`
  - mensaje: `Solo hay 1 captura. Todavía no hay suficiente tendencia para decidir.`
- `2..3` snapshots:
  - titulo: `Histórico limitado`
  - mensaje: `Hay pocas capturas. Interpreta la tendencia con cautela.`
- `>= 4` snapshots:
  - titulo: `Histórico suficiente`
  - mensaje: `Ya hay varias capturas para comparar la evolución.`

## Archivos tocados

- `frontend/src/modules/watchlist/summary.ts`
- `frontend/src/modules/watchlist/components/WatchDetailPanel.tsx`
- `frontend/src/i18n/domains/watchlist.ts`
- `frontend/tests/watchlist-w5-history-confidence.test.ts`
- `docs/qa/reports/2026-05-12-watchlist-w5-history-confidence.md`
- `docs/DOCS_INVENTORY.md`

## Tests ejecutados

En `frontend`:

- `npm test`
- `npm run build`
- `npm run lint`

## Pendientes fuera de W5

- W6 frescura accionable.
- W7 mapa plegado.
- W8 comparativa reactiva.
- W9 pulido visual final.
