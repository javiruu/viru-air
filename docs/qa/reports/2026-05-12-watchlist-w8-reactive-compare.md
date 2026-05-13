# Watchlist W8 Reactive Compare

**Estado:** vivo  
**Fecha:** 2026-05-13  
**Fuente de verdad:** si  
**Area:** QA / watchlist  
**Commit base:** `2656092fee2353655395b5200aa2143b634a096b`

## Problema resuelto

La comparativa multi-vuelo existia pero no guiaba bien el siguiente paso en estados de baja seleccion y no destacaba con suficiente claridad el valor comparativo cuando habia 2-4 rutas.

W8 refuerza la reactividad del bloque en `/watchlist` sin tocar backend ni scoring:

- estado 0 seleccionadas con instruccion clara;
- estado 1 seleccionada con accion siguiente explicita;
- estado 2-4 seleccionadas con comparativa inmediata desde `/prices/compare`;
- limite maximo de 4 rutas con copy consistente;
- aviso claro cuando `currency_mode = mixed`.

## Estados 0/1/2-4 y limite

- `0` seleccionadas:
  - `Selecciona entre 2 y 4 rutas para comparar precio, estabilidad y frescura.`
- `1` seleccionada:
  - `Selecciona una ruta m�s para activar la comparativa.`
- `2..4` seleccionadas:
  - se consulta y renderiza `GET /prices/compare?watch_ids=...`.
- `>4` intentadas:
  - se mantiene el guard existente y se muestra:
  - `Puedes comparar hasta 4 rutas.`

## Fuente de verdad y separaci�n de selecci�n

- La comparativa sigue usando `/prices/compare` como fuente de verdad para resultados y badges decisionales.
- `Mejor precio` y `M�s estable` se derivan de `compareResponse.watches`.
- `M�s fresca` se deriva de `compareResponse.points` (ultima fecha disponible por ruta).
- No se usa `historyRows` local para badges decisionales en `ComparePanels`.
- La selecci�n de comparativa (`compare_selection`) sigue separada de la selecci�n bulk (`selectedIds`) y no dispara toolbar destructiva por si sola.

## Moneda mixta

- Si `currency_mode = mixed`, se muestra:
  - `Hay monedas distintas; compara con cuidado.`
- No se implementa conversion FX ni promesas de equivalencia exacta.

## Archivos tocados

- `frontend/src/modules/watchlist/components/ComparePanels.tsx`
- `frontend/src/modules/watchlist/useWatchlistViewState.ts`
- `frontend/src/i18n/domains/watchlist.ts`
- `frontend/tests/watchlist-w8-reactive-compare.test.ts`
- `frontend/tests/watchlist-f3b-advanced-history.test.ts`
- `docs/qa/reports/2026-05-12-watchlist-w8-reactive-compare.md`
- `docs/DOCS_INVENTORY.md`

## Tests ejecutados

En `frontend`:

- `npm test`
- `npm run build`
- `npm run lint`

Resultado esperado de lint:

- warning preexistente de `react-hooks/exhaustive-deps` en `preferencias/busqueda/page.tsx` (sin cambios en W8).

## Pendiente fuera de W8

- W9: pulido visual final de la pantalla.