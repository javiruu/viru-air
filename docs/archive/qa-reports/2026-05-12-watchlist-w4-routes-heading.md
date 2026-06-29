# Watchlist W4 Routes Heading

**Estado:** vivo  
**Fecha:** 2026-05-13  
**Fuente de verdad:** si  
**Area:** QA / watchlist  
**Commit base:** `d3f8d37bf45f4630b336e95f9d8bd6e2bd92f013`

## Problema resuelto

El encabezado de la lista en `/watchlist` usaba el copy largo `Lista inteligente de vuelos`, con riesgo de wrap visual poco pulido en cabecera.

W4 renombra el bloque a `Rutas vigiladas` y ajusta el copy asociado del contador para usar terminologia de rutas.

## Antes / despues

### Antes

- Titulo: `Lista inteligente de vuelos`.
- Meta de conteo: `Mostrando X de Y vuelos.`

### Despues

- Titulo: `Rutas vigiladas` (via i18n en `watchlist.smartList.heading`).
- Meta de conteo: `Mostrando X de Y rutas.` (via i18n en `watchlist.smartList.showingCount`).
- Se mantiene buscador, orden y contador, sin tocar logica de seleccion W2 ni acciones contextuales W3.

## Archivos tocados

- `frontend/src/modules/watchlist/components/SmartWatchListPanel.tsx`
- `frontend/src/i18n/domains/watchlist.ts`
- `frontend/tests/watchlist-w0-baseline.test.ts`
- `frontend/tests/watchlist-w4-routes-heading.test.ts`
- `docs/qa/reports/2026-05-12-watchlist-w4-routes-heading.md`
- `docs/DOCS_INVENTORY.md`

## Tests ejecutados

En `frontend`:

- `npm test` -> pass `107`, fail `0`, skipped `15`.
- `npm run build` -> OK.
- `npm run lint` -> OK con warning preexistente:
  - `src/app/(private)/preferencias/busqueda/page.tsx:60`
  - `react-hooks/exhaustive-deps`.

## Pendientes fuera de W4

- W5 confianza historica.
- W6 frescura accionable.
- W7 mapa plegado.
- W8 comparativa reactiva.
- W9 pulido visual final.
