# Watchlist W3 Contextual Actions

**Estado:** vivo  
**Fecha:** 2026-05-13  
**Fuente de verdad:** si  
**Area:** QA / watchlist  
**Commit base:** `599b52a1bfb1eafc6edec8dec6a708e0a6605caf`

## Problema resuelto

En `/watchlist` las acciones masivas competian visualmente con acciones por fila y con la seleccion de comparativa. W3 reduce ruido y deja las acciones bulk en una barra contextual solo cuando existe seleccion bulk explicita en la lista.

## Decision W3 aplicada

- Ruta activa: sigue siendo la ruta seleccionada que alimenta detalle e historico.
- Seleccion de comparativa: sigue en `ComparePanels` con controles propios (`compare_selection`).
- Seleccion bulk: se mantiene en `SmartWatchListPanel` con checkboxes de lista (`selectedIds`).

No se asume equivalencia entre comparativa y acciones destructivas. La barra bulk no aparece con 0 seleccionados.

## Antes / despues

### Antes

- Con seleccion de lista, se mostraban acciones bulk sin contexto de conteo.
- El CTA de refresh bulk era ambiguo (`Actualizar`).
- No habia region toolbar con identificador accesible estable.

### Despues

- La toolbar bulk solo renderiza bajo `hasSelection`.
- La toolbar incluye contador contextual (`{count} seleccionado(s)`).
- El CTA seguro queda explicito: `Actualizar seleccionados`.
- Se mantiene `Pausar`, `Reanudar`, `Eliminar` solo dentro de esa misma toolbar contextual.
- Se agrega `role="toolbar"`, `aria-label` y `data-testid="watchlist-bulk-toolbar"` para accesibilidad y testeo estable.

## Ambiguedad comparativa vs bulk

No se detecto mezcla de estado en codigo actual:

- `SmartWatchListPanel` usa `selectedIds` local para bulk.
- `ComparePanels` usa `compareIds` y `onToggleCompare` para comparativa.

Por tanto, no fue necesario introducir un nuevo modo de seleccion ni tocar payloads/endpoints.

## Archivos tocados

- `frontend/src/modules/watchlist/components/SmartWatchListPanel.tsx`
- `frontend/src/i18n/domains/watchlist.ts`
- `frontend/tests/watchlist-w3-contextual-actions.test.ts`
- `docs/qa/reports/2026-05-12-watchlist-w3-contextual-actions.md`
- `docs/DOCS_INVENTORY.md`

## Tests ejecutados

En `frontend`:

- `npm test`
- `npm run build`
- `npm run lint`

## Pendientes fuera de W3

- W4: renombre "Rutas vigiladas".
- W5: confianza historica.
- W6: frescura accionable.
- W7: mapa plegado.
- W8: comparativa reactiva.
- W9: pulido visual final.
