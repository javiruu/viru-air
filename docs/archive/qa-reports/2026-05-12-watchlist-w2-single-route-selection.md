# Watchlist W2 Single Route Selection

**Estado:** vivo  
**Fecha:** 2026-05-13  
**Fuente de verdad:** si  
**Area:** QA / watchlist  
**Commit base:** `fb23df2adc2a95b42bc51745b03264c0ccb9bf41`

## Problema resuelto

En `/watchlist` coexistian dos lugares que parecian selector de ruta: la lista principal y los filtros del historico (Origen, Destino, Fechas de vuelo). Esto generaba ambiguedad de flujo.

W2 establece una sola fuente visible de seleccion de ruta: la lista Watchlist.

## Archivos tocados

- `frontend/src/modules/watchlist/components/HistoryIntegratedPanel.tsx`
- `frontend/src/app/(private)/watchlist/page.tsx`
- `frontend/src/i18n/domains/watchlist.ts`
- `frontend/tests/watchlist-w2-single-route-selection.test.ts`
- `frontend/tests/watchlist-w0-baseline.test.ts`

## Antes / despues

### Antes

- El historico mostraba controles editables de `Origen`, `Destino` y `Fechas de vuelo`.
- El usuario podia interpretar esos campos como un segundo selector de ruta.

### Despues

- El historico muestra un bloque no editable `Ruta seleccionada` con valor derivado de `selectedWatch`.
- Se eliminaron del historico los controles editables de ruta (`Origen`, `Destino`, `Fechas de vuelo`).
- Se mantienen filtros historicos propios:
  - rango temporal;
  - punto (fecha de consulta);
  - alternancia grafico/calendario;
  - vista acotada;
  - reset zoom.
- Sin ruta seleccionada, el historico muestra el empty state:
  - `Selecciona una ruta de tu Watchlist para ver su histórico.`
- `WatchDetailPanel` y `HistoryIntegratedPanel` consumen la misma ruta seleccionada (`derived.selectedWatch`).

## Verificacion ejecutada

En `frontend`:

- `npm test` -> pass (`98`), fail (`0`), skipped (`15`).
- `npm run build` -> OK.
- `npm run lint` -> OK con warning preexistente:
  - `src/app/(private)/preferencias/busqueda/page.tsx:60`
  - `react-hooks/exhaustive-deps`.

## Pendientes fuera de W2

- W3: acciones contextuales.
- W4: renombre `Rutas vigiladas` (si aplica).
- W5: confianza historica.
- W6: frescura accionable.
- W7: mapa plegado.
- W8: comparativa reactiva.
- W9: pulido final.
