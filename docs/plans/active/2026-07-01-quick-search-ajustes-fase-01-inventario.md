# Quick Search ajustes — Fase 1 inventario

**Estado:** vivo
**Ultima revision:** 2026-07-01
**Fuente de verdad:** no
**Area:** plan
**Plan relacionado:** `docs/plans/active/2026-07-01-plan-20-fases-quick-search-ajustes.md`

## Objetivo

Crear una base de verdad antes de tocar la pantalla `/quick-search`. Esta fase no modifica comportamiento, CSS, layout ni copy visible.

## Quick Search inventory

- Main component: `frontend/src/modules/quick-search/QuickSearchView.tsx`. Orquesta estado, URL params, submit, payload, resultados, chips/resumen, drawer de ajustes, empty state y modo ida/vuelta.
- Active settings component: `frontend/src/modules/quick-search/components/QuickSearchFilterConsole.tsx`. Es el bloque visible actual de "Ajustes activos"; contiene cards/resumen y un drawer con cobertura, reglas, filtros visibles y vuelos separados.
- Search payload builder: `frontend/src/modules/quick-search/api/buildQuickSearchRequest.ts`, especialmente `prepareQuickSearchRequest`, `toQuickSearchQuery` y `buildQuickSearchCanonicalPayload`.
- URL/query state: `frontend/src/modules/shared/useRouteState.ts`, con `readQuickSearchUrlState` y `buildQuickSearchSearchParams`.
- Form state: `frontend/src/modules/quick-search/state/useQuickSearchFormState.ts`, consumido por `useQuickSearchMainState`.
- Result filters: `frontend/src/modules/quick-search/state/quickSearchVisibleResults.ts` aplica `priceMin`, `priceMax`, `durationMax` y `sortBy` sobre resultados ya normalizados.
- Empty state: `frontend/src/modules/quick-search/state/useQuickSearchScreenState.ts` deriva causas y acciones de rescate; `frontend/src/modules/quick-search/components/QuickSearchStatePanels.tsx` renderiza los paneles de estado.
- Result rendering: `frontend/src/modules/quick-search/components/QuickSearchResultsList.tsx`, `QuickSearchResultsWorkspace.tsx`, `QuickSearchSidePanel.tsx`, `QuickSearchSideViewControls.tsx` y markup final en `QuickSearchView.tsx`.
- Tests: existen suites unitarias y e2e bajo `frontend/tests/*quick-search*`; el script visual existente es `frontend/scripts/qa_quick_search_visual.mjs`.

## Componentes y estados por area

| Area | Pieza actual | Estado/props principales | Observacion para fases posteriores |
|---|---|---|---|
| Origen/destino | Markup y autocomplete en `QuickSearchView.tsx` | `origin`, `destination`, `activePicker`, `activeAutocompleteField`, `originRecentAirports`, `destinationRecentAirports` | No hay componente pequeño dedicado solo al campo; el modal/picker y autocomplete viven en la vista principal. |
| Fecha | `QuickSearchDatePicker` + estado en `QuickSearchView.tsx` | `travelDate`, `returnDate`, `isReturn`, `daysBefore`, `daysAfter`, `applyFlexReturn` | Fecha y flex ya están separados en estado, pero el layout actual aún los trata como parte de la configuración amplia. |
| Pasajeros | Markup en `QuickSearchView.tsx` | `adults` | Estado simple, sin dependencia backend especial fuera del payload. |
| Ajustes activos | `QuickSearchFilterConsole` | `radiusKm`, `includeNearbyOrigins`, `includeNearbyDestinations`, `excludeOrigins`, `departAfter`, `departBefore`, `strictFilters`, `includeStops`, `maxStops`, `bufferMin`, `priceMin`, `priceMax`, `durationMax`, `sortBy` | Es componente propio, no markup inline. Mezcla datos de busqueda, ajustes avanzados y filtros de resultados. |
| Drawer/modal de ajustes | `QuickSearchFilterConsole` via `createPortal` | `isFiltersOpen`, `filtersCloseRef`, callbacks de reset/aplicar | Ya existe shell tipo drawer; fases posteriores pueden reutilizarlo antes de crear otro patrón. |
| Resultados | `QuickSearchResultsList`, `QuickSearchResultsWorkspace`, `QuickSearchSideViewControls` | `results`, `visibleResults`, `searchMeta`, `sortBy`, filtros por lado en ida/vuelta | En ida/vuelta ya hay controles por lado para filtros visibles. |
| Empty state | `useQuickSearchScreenState` + `QuickSearchStatePanels` | `zeroResultCauses`, `zeroResultActions`, `emptyCausesExpanded` | Ya existe rescate contextual parcial: relajar strict, duración, radio, fecha flex y exclusiones. |

## Mapa de estado actual

- Ruta base: `origin`, `destination`, `travelDate`, `returnDate`, `isReturn`, `adults`.
- Flexibilidad: `daysBefore`, `daysAfter`, `applyFlexReturn`.
- Aeropuertos cercanos: `radiusKm` default `150`, `includeNearbyOrigins`, `includeNearbyDestinations`.
- Exclusiones: `excludeOrigins`, `excludeDestinations`, `excludeOriginInput`, `excludeDestinationInput`.
- Horarios: `departAfter` default `07:00`, `departBefore` default `22:00`.
- Vuelos separados: `includeStops` default `false`, `maxStops` default `1`, `bufferMin`.
- Modo estricto: `strictFilters` default `true`, `soft_filters_weight` fijo en el payload de submit.
- Filtros de resultados: `priceMin`, `priceMax`, `durationMax`, `sortBy` default `ranking`.
- Preferencias: `resolveQuickSearchPreferenceDefaults` aplica defaults de radio, strict, horarios, stops y cercanos cuando hay preferencias disponibles.

## Query params y payload

- URL persistente de `/quick-search`: `origin`, `destination`, `travelDate`, `returnDate`, `isReturn`, `adults`, `flexB`, `flexA`, `radius`, `strict`.
- Payload de busqueda: `origin_iata`, `destination_iata`, `travel_date/date`, `flex_days_before`, `flex_days_after`, `radius_km`, `include_stops`, `include_nearby_origins`, `include_nearby_destinations`, `depart_after`, `depart_before`, `max_stops`, `exclude_origins`, `exclude_destinations`, `strict_filters`, `soft_filters_weight`, paginacion.
- Acoplamiento relevante: `buildQuickSearchCanonicalPayload` convierte cercanos/flex en modo wide search y ajusta limites de ejecucion. Cambiar ubicacion visual de controles no debe cambiar nombres ni semantica del payload.
- Filtros locales: `priceMin`, `priceMax`, `durationMax` y `sortBy` se aplican en `deriveQuickSearchVisibleResults`, no en el payload canonico de busqueda.

## Tests y QA existentes

- Unitarios cercanos: `quick-search-form-contract`, `quick-search-visible-results`, `quick-search-screen-state`, `quick-search-copy`, `quick-search-request-signatures`, `quick-search-filter-utils`, `quick-search-recent-airports`.
- E2E/visual cercanos: `quick-search-relax-preview.e2e.test.ts`, `quick-search-airport-picker.e2e.test.ts`, `quick-search-network-guards.e2e.test.ts`, `qa_quick_search_visual.mjs`.
- QA documental previa: `docs/qa/reports/2026-06-05-watchlist-quick-search-stabilization.md`.

## Riesgos

- `QuickSearchView.tsx` concentra demasiada responsabilidad; fases posteriores deben evitar refactors globales mientras muevan bloques.
- `QuickSearchFilterConsole` ya mezcla busqueda, reglas avanzadas y filtros post-resultados; es el principal punto seguro para fases 2-7.
- Mover filtros de resultados requiere confirmar si el estado por lado de ida/vuelta (`QuickSearchSideViewControls`) debe conservarse como patrón.
- Hay cambios locales previos no pertenecientes a esta fase sobre recientes por origen/destino. No forman parte del inventario ni deben mezclarse con una fase que prohibe cambios funcionales.

## QA de Fase 1

- `git fetch origin --prune`: correcto; `HEAD...origin/main` estaba `0/0`.
- Lectura completa del plan de 20 fases: completada.
- Inspeccion de componentes y estado con CodeGraph/rg: completada.
- `npm run lint`: correcto con warning preexistente en `QuickSearchView.tsx` por dependencias de `useEffect` en la linea 3078.
- `npx tsc --noEmit`: correcto.
- `npm run test -- tests/quick-search-visible-results.test.ts tests/quick-search-screen-state.test.tsx tests/quick-search-form-contract.test.ts tests/quick-search-request-signatures.test.ts tests/quick-search-recent-airports.test.ts`: 28 tests pasan.
- `npm run build`: correcto; mantiene el mismo warning de lint de `QuickSearchView.tsx`.
- `npm run qa:visual:quick-search`: genero baseline light en `docs/qa/`, pero salio con `panel-dom-missing` en todos los viewports porque el script espera un selector `qs-filter-risk` que ya no existe en el drawer actual.
- Capturas baseline light generadas por script:
  - `docs/qa/snapshots_quick-search-desktop1440.png`
  - `docs/qa/snapshots_quick-search-mobile360.png`
  - `docs/qa/snapshots_quick-search-mobile390.png`
  - `docs/qa/snapshots_quick-search-tablet768.png`
  - `docs/qa/snapshots_quick-search-tablet1024.png`
  - capturas equivalentes del drawer `docs/qa/snapshots_quick-search-filters-*.png`
- Capturas baseline dark manuales tras reiniciar el dev server en `http://127.0.0.1:3000/quick-search`:
  - `docs/qa/snapshots_quick-search-desktop1440-dark.png`
  - `docs/qa/snapshots_quick-search-filters-desktop1440-dark.png`
  - `docs/qa/snapshots_quick-search-mobile360-dark.png`
  - `docs/qa/snapshots_quick-search-filters-mobile360-dark.png`
- Verificacion visual manual de capturas: desktop/mobile light y dark no estan en blanco y muestran `/quick-search` con el drawer de ajustes abierto.

## Criterios de aceptacion

- Existe un mapa claro de archivos tocables: cumplido.
- No se ha modificado comportamiento: cumplido en esta fase.
- Se sabe que piezas son seguras para tocar en fases posteriores: cumplido.
- Queda documentado el acoplamiento con backend/query params: cumplido.
