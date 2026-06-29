# W9.2 — Rescate visual y funcional del Histórico integrado

- Fecha: 2026-05-13
- Commit base: `5623c953f75f822229d51dd5b2522c0faa60f082`
- Alcance: frontend (`/watchlist`) sin cambios backend/endpoints/migraciones

## Bugs corregidos

1. Frescura con duplicidad:
- Antes: `hace hace 9 h`
- Ahora: `En observación · hace 9 h` (se elimina la duplicidad en i18n ES).

2. Copy EN en comparativa:
- Antes: `Select up to 4 routes to compare price, stability, and freshness.`
- Ahora: `Selecciona hasta 4 rutas para comparar precio, estabilidad y frescura.`

3. Doble etiqueta de rango:
- Se elimina la repetición visual de `Rango temporal RANGO` dejando título único + `aria-label` en selector.

4. Mes incoherente en calendario integrado:
- Se corrige el anclaje de mes visible para priorizar `selectedDates`, `selectedPoint` y filas filtradas de la ruta seleccionada.
- Se elimina fallback a `historyRows` globales para evitar contaminar el mes con otras rutas.

5. Calendario con poco valor:
- Decisión aplicada: calendario degradado a estado compacto cuando no hay datos útiles del rango.
- Estado compacto:
  - `Calendario no disponible para este rango.`
  - `Usa el gráfico para revisar las capturas disponibles.`

6. Gráfico con poca legibilidad:
- Se refuerza la visibilidad de línea y puntos cuando hay pocos datos.
- Se mantiene resumen KPI bajo gráfico (media, mínimo, máximo, snapshots).
- Mensaje editorial para histórico corto:
  - `Histórico en construcción`
  - `Viru irá afinando la lectura conforme haya más capturas.`

## Decisiones de producto aplicadas

- Vista principal del histórico: gráfico.
- Vista calendario: secundaria y condicionada a datos útiles.
- Si calendario no aporta valor, no compite con el gráfico y se muestra compacto.

## Archivos tocados

- `frontend/src/app/(private)/watchlist/page.tsx`
- `frontend/src/modules/watchlist/components/HistoryIntegratedPanel.tsx`
- `frontend/src/modules/watchlist/useWatchlistDerived.ts`
- `frontend/src/i18n/domains/watchlist.ts`
- `frontend/src/styles/screens.css`
- `frontend/tests/watchlist-w9-2-history-rescue.test.ts`
- Actualizaciones de tests existentes de watchlist para reflejar i18n y estructura actual.

## Verificación ejecutada

- `npm test` (frontend): PASS (`146` pass, `0` fail, `15` skipped por entorno Quick Search no levantado)
- `npm run build` (frontend): PASS
- `npm run lint` (frontend): PASS con warning preexistente:
  - `src/app/(private)/preferencias/busqueda/page.tsx` `react-hooks/exhaustive-deps`

## Verificación Playwright login

- Script ejecutado: `frontend/scripts/qa_capture_notification_login.mjs`
- Evidencias generadas:
  - `docs/qa/notifications-login-desktop-full.png`
  - `docs/qa/notifications-login-desktop-component.png`
- Validación adicional de ruta post-login:
  - URL final: `http://127.0.0.1:3000/dashboard`

## Caveats

- Los `skipped` de `npm test` corresponden a pruebas E2E de Quick Search que dependen de servicios en ejecución durante ese momento; no son regresiones de W9.2.
