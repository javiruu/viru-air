# Watchlist W1 Layout Order

**Estado:** vivo  
**Fecha:** 2026-05-13  
**Fuente de verdad:** si  
**Area:** QA / watchlist  
**Commit base:** `df788d9165d3baa614c135052b5b8d9e903fc5f8` (`main`, sincronizado con `origin/main` al inicio)

## Objetivo W1

Reordenar la jerarquia principal de `/watchlist` sin agregar features, sin tocar backend y sin resolver todavia la duplicidad de filtros del historico (W2).

Orden objetivo aplicado:

1. Cabecera + estado operativo
2. Workspace principal: lista de rutas + detalle de ruta
3. Historico integrado
4. Comparativa multi-vuelo
5. Mesa de decisiones / mapa

## Cambios aplicados

- Se movio `HistoryIntegratedPanel` para que renderice despues del bloque `SmartWatchListPanel + WatchDetailPanel`.
- Se movio `WatchlistMapDecisionPanel` fuera del grid principal y al final, despues de `ComparePanels`.
- Se mantuvieron los mismos props, handlers y fuentes de datos en todos los bloques.
- No se tocaron endpoints, contratos API, backend ni logica de seleccion.

Archivos de implementacion:

- `frontend/src/app/(private)/watchlist/page.tsx`
- `frontend/tests/watchlist-w1-layout-order.test.ts`

## Criterios de aceptacion W1

- La lista de rutas y el detalle aparecen antes de historico en la composicion de pagina.
- Historico aparece antes de comparativa.
- Comparativa y mapa no desaparecen.
- Se mantiene guardia anti-regresion de copy EN bloqueado en `/watchlist`.

## Verificacion ejecutada

- `npm test`
- `npm run build`
- `npm run lint`

Resultado esperado para cierre W1:

- Todo en verde o, en lint, solo warning preexistente de `react-hooks/exhaustive-deps` en preferencias/busqueda si reaparece.

## Pendientes explicitamente fuera de W1

- W2: eliminar duplicidad de seleccion ruta vs filtros Origen/Destino/Fechas del historico.
- W7: resolver comportamiento de mapa vacio/colapsado.
