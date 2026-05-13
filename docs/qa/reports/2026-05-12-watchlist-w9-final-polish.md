# Watchlist W9 Final Polish

**Estado:** vivo  
**Fecha:** 2026-05-13  
**Fuente de verdad:** si  
**Area:** QA / watchlist  
**Commit base:** `bfc300c117f89eacb72fdbb6b181a080e74df73d`

## Resumen W0-W8 cerrado

- W0: baseline visual y guardas anti-regresion.
- W1: orden principal con lista+detalle antes de historico y mapa al final.
- W2: fuente unica de seleccion de ruta visible en Watchlist.
- W3: acciones bulk solo con seleccion bulk explicita.
- W4: encabezado `Rutas vigiladas` y contador por rutas.
- W5: confianza historica por `snapshot_count`.
- W6: frescura con tiempo/accion.
- W7: mapa no contradictorio y secundario cuando no aporta.
- W8: comparativa reactiva 0/1/2-4 + limite 4 + moneda mixta.

## Problemas visuales detectados en W9

- Sensacion de pila por separacion vertical irregular entre bloques principales.
- Wraps poco elegantes en badges/fechas/rutas en celdas compactas.
- KPIs con alturas dispares segun longitud de etiqueta.
- Toolbar bulk podia empujar controles con salto brusco.
- Detalle perdia continuidad en desktop durante scroll largo.

## Cambios aplicados (solo frontend /watchlist)

- Ajuste de respiracion y jerarquia visual con espaciado mas consistente en la pagina watchlist.
- Rebalanceo ligero del `watchlist-decision-grid` y copy del bloque mapa con ancho legible.
- Prevencion de wraps feos en ruta, badges y fecha de comparativa.
- Estabilizacion de toolbar bulk con clase dedicada y mejor acomodo en desktop/mobile.
- Grid KPI afinado (`minmax` + `min-height`) para alturas mas homogeneas sin romper responsive.
- `WatchDetailPanel` con sticky ligero solo en desktop (`min-width: 1121px`), sin activar en mobile.
- Se mantiene intacta la logica de seleccion, historico, comparativa, mapa y acciones.

## Archivos tocados

- `frontend/src/styles/screens.css`
- `frontend/src/modules/watchlist/components/WatchDetailPanel.tsx`
- `frontend/src/modules/watchlist/components/SmartWatchListPanel.tsx`
- `frontend/tests/watchlist-w9-final-polish.test.ts`
- `docs/qa/reports/2026-05-12-watchlist-w9-final-polish.md`
- `docs/qa/screenshots/watchlist-w9-final.png`
- `docs/DOCS_INVENTORY.md`

## No se toco

- Backend, endpoints, contratos API, migraciones, auth, alerts, worker, quick-search, prices backend.
- Orden funcional W1 y reglas de fases W2-W8.
- Copy funcional ya decidido (solo ajuste visual por CSS).

## Responsive / mobile check

- Se aplicaron reglas mobile para mantener orden y evitar saltos visuales:
  1. Rutas vigiladas
  2. Detalle de ruta
  3. Historico
  4. Comparativa
  5. Mapa secundario
- Sticky se limita a desktop y se desactiva en mobile por media query.

## Tests ejecutados

En `frontend`:

- `npm test`
- `npm run build`
- `npm run lint`

## Evidencia visual

- Captura final guardada: `docs/qa/screenshots/watchlist-w9-final.png`.
- Captura realizada por navegación automatizada a `/watchlist` en entorno local.

## Caveats aceptados

- Si la sesión autenticada no está activa, la captura refleja el estado de acceso disponible en entorno local y no fuerza hack de auth.

## Conclusion

`/watchlist polish complete with caveats`
