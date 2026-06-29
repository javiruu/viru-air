# Watchlist W7 Map Empty State

**Estado:** vivo  
**Fecha:** 2026-05-13  
**Fuente de verdad:** si  
**Area:** QA / watchlist  
**Commit base:** `eadf237d9387b71b24f94fcd4f793251f6b69842`

## Problema resuelto

El bloque de mapa podía mostrar copy contradictorio (`No hay rutas activas para mostrar en el mapa.`) incluso cuando sí había rutas en Watchlist, y mantenía demasiado protagonismo cuando no había geodatos útiles.

## Decisión W7 aplicada

- Estado A (sin rutas): copy de alta intención:
  - `Añade una ruta a tu Watchlist para verla aquí.`
- Estado B (hay rutas, sin geodatos útiles): copy no contradictorio y secundario:
  - `Mapa no disponible para estas rutas.`
  - `La decisión principal está en precio, frescura e histórico.`
- Estado C (hay geodatos útiles): el mapa sigue operativo con rutas/markers/popup.

Para A/B, el panel pasa a versión compacta (sin canvas de mapa), dejándolo al final y con menor protagonismo.

## Archivos tocados

- `frontend/src/app/(private)/watchlist/page.tsx`
- `frontend/src/modules/watchlist/components/WatchlistMapDecisionPanel.tsx`
- `frontend/src/modules/watchlist/useWatchlistDerived.ts`
- `frontend/src/i18n/domains/watchlist.ts`
- `frontend/tests/watchlist-w1-layout-order.test.ts`
- `frontend/tests/watchlist-w7-map-empty-state.test.ts`
- `docs/qa/reports/2026-05-12-watchlist-w7-map-empty-state.md`
- `docs/DOCS_INVENTORY.md`

## Tests ejecutados

En `frontend`:

- `npm test`
- `npm run build`
- `npm run lint`

## Pendientes fuera de W7

- W8 comparativa reactiva.
- W9 pulido visual final.
