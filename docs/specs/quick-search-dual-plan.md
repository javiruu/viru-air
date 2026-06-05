# Quick-Search Dual (Ida + Vuelta lado a lado) — Plan de Implementación

> **Estado:** En progreso — Fase 1 completada ✅  
> **Inicio:** 2026-06-05  
> **Propietario:** AI agent (Codebuff)

---

## Resumen

Cuando el usuario activa "Vuelta también" (`isReturn=true` + `returnDate`), en lugar de una sola búsqueda, se disparan **dos búsquedas independientes** al mismo endpoint `/search/quick`:

1. **Ida**: `travel_date = fechaIda`, ruta `origin → destination`
2. **Vuelta**: `travel_date = fechaVuelta`, ruta `destination → origin` (invertida)

Cada lado (ida/vuelta) tiene su propio estado completo: resultados, paginación, filtros, loading, errores.

---

## Arquitectura final

```
QuickSearchView
├── useQuickSearchFormState()          ← estado del formulario (compartido)
├── useQuickSearchSide("outbound")     ← estado completo de ida
├── useQuickSearchSide("return")       ← estado completo de vuelta (condicional)
│
├── QuickSearchSearchForm              ← usa formState
├── QuickSearchFilterConsole           ← usa formState
│
└── QuickSearchDualWorkspace           ← layout grid
    ├── QuickSearchSidePanel("outbound")   ← panel izquierdo
    │   ├── QuickSearchLoadingProgress
    │   ├── QuickSearchStatePanels
    │   ├── QuickSearchResultsList
    │   └── QuickSearchPagination
    │
    ├── div.qs-dual-divider
    │
    └── QuickSearchSidePanel("return")     ← panel derecho
        ├── QuickSearchLoadingProgress
        ├── QuickSearchStatePanels
        ├── QuickSearchResultsList
        └── QuickSearchPagination
```

---

## Fases

### Fase 0: Auditoría y Planificación ✅
- Auditoría detallada de 110 variables de estado
- Clasificación en 6 categorías (formulario, resultados, interacción, global, loader, weather)
- Plan de archivos a crear/modificar

### Fase 1: Refactor del Estado ✅
- ✅ `state/useQuickSearchFormState.ts` — hook de formulario (~46 pares state/setter + 10 refs)
- ✅ `state/useQuickSearchController.ts` — wrapper compatible hacia atrás
- ✅ `state/useQuickSearchSide.ts` — hook por lado (~35 pares + 18 refs + `runSearch`, `goToPage`, `reset`)

### Fase 2: Layout Dual CSS y Componentes ✅
- ✅ i18n: 13 nuevas claves en `quickSearchCopy.ts` (es + en)
- ✅ CSS: `styles/quick-search-dual.css` — grid 1fr 1fr, divisor central, responsive
- ✅ `components/QuickSearchDualWorkspace.tsx` — contenedor grid
- ✅ `components/QuickSearchSidePanel.tsx` — panel individual con cabecera + resultados
- ✅ Import CSS en `styles/globals.css`

### Fase 3: Paginación Independiente ✅
- ✅ `components/QuickSearchPagination.tsx` — componente reutilizable con i18n, accesibilidad, y clases CSS existentes
- ✅ `QuickSearchSidePanel.tsx` — props opcionales de paginación con renderizado condicional en footer
- ✅ CSS: `.qs-dual-panel__footer` + `.qs-pagination-ellipsis` en `screens.css`

### Fase 4: Experiencia de Combinación ✅
- ✅ `components/QuickSearchCombinedBanner.tsx` — banner sticky con precio combinado gradiente + botón "Guardar combinación" + spinner
- ✅ `state/useSaveCombination.ts` — hook que guarda 2 entradas `/search/save-result` con `group_id` compartido vía `Promise.allSettled`
- ✅ i18n: `savingCombination`, `combinationSaved`, `combinationError`, `combinationPartial`, `combinationSelectBoth` (es + en)
- ✅ CSS: `.qs-dual-combined__save` (hover, active, disabled), `.qs-spinner` (animación), `.qs-dual-sync` (toggle futuro)
- ✅ Backend: `group_id` añadido a `QuickSearchSaveResultIn`, `FlightWatch` model, `save_result` endpoint, migración `0026`

### Fase 5: Edge Cases 📅
- [ ] Estados de carga dual (2 barras o 1 combinada)
- [ ] Empty/Error/Rate-limit independientes por panel
- [ ] Deep links duales

### Fase 6: Integración en QuickSearchView 📅
- [ ] Reemplazar `useQuickSearchMainState` por `useQuickSearchFormState` + 2× `useQuickSearchSide`
- [ ] `onSubmit` refactorizado para 1 o 2 llamadas API en paralelo
- [ ] Modo solo-ida: 100% regresión-free

### Fase 7: Polish Visual y QA 📅
- [ ] Animaciones staggered entrance
- [ ] Hover cards, transiciones
- [ ] Tests de integración y regresión

---

## Archivos creados hasta ahora

| Archivo | Propósito |
|---------|-----------|
| `state/useQuickSearchFormState.ts` | Estado de formulario extraído |
| `state/useQuickSearchSide.ts` | Estado completo de un lado de búsqueda |
| `state/useSaveCombination.ts` | Guarda 2 entradas watchlist con `group_id` compartido |
| `components/QuickSearchDualWorkspace.tsx` | Contenedor grid dual |
| `components/QuickSearchSidePanel.tsx` | Panel individual con cabecera + paginación |
| `components/QuickSearchPagination.tsx` | Paginación reutilizable independiente |
| `components/QuickSearchCombinedBanner.tsx` | Banner sticky de precio combinado + guardar |
| `styles/quick-search-dual.css` | CSS grid, paneles, divisor, banner, sync toggle |
| `alembic/versions/0026_add_group_id_to_flight_watch.py` | Migración `group_id` en `flight_watch` |

## Archivos modificados hasta ahora

| Archivo | Cambio |
|---------|--------|
| `state/useQuickSearchController.ts` | Delega a `useQuickSearchFormState` internamente |
| `shared/quickSearchCopy.ts` | +18 claves i18n para dual panel + combinación (es + en) |
| `styles/globals.css` | Importa `quick-search-dual.css` |
| `styles/screens.css` | Añade `.qs-pagination-ellipsis` |
| `backend/app/api/v1/search.py` | `group_id` en `QuickSearchSaveResultIn` + `save_result` |
| `backend/app/infrastructure/db/models.py` | `group_id` en `FlightWatch` model |

---

## Próximo paso

**Fase 5:** Edge Cases — estados de carga duales, errores/empty/rate-limit independientes por panel, deep links duales.
