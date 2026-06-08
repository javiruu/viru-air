# Quick-Search Dual (Ida + Vuelta lado a lado) — Plan de Implementación

> **Estado:** ✅ COMPLETADO — Fases 0-10 cerradas  
> **Última revisión:** 2026-06-08 (cierre completo del ciclo dual)  
> **Propietario:** AI agent (Codebuff)

---

## Resumen

Cuando el usuario activa "Ida y vuelta" (`isReturn=true` + `returnDate`), en lugar de una sola búsqueda, se disparan **dos búsquedas independientes** al mismo endpoint `/search/quick`:

1. **Ida (outbound)**: `travel_date = travelDate`, ruta `origin → destination`
2. **Vuelta (return)**: `travel_date = returnDate`, ruta `destination → origin` (invertida)

Cada lado tiene su propio estado completo: resultados, paginación, filtros, loading, errores. Ambos se procesan en paralelo vía `Promise.all`.

---

## Arquitectura conservada (decisiones cerradas)

### Principios inamovibles

1. **Dos búsquedas independientes** al mismo endpoint `POST /search/quick`. No se crea endpoint round-trip nuevo.
2. **Formulario compartido**: `useQuickSearchMainState` (vía `useQuickSearchController`) gestiona `origin`, `destination`, `travelDate`, `returnDate`, `isReturn`, `adults`, filtros, etc.
3. **Estado por lado**: `useQuickSearchSide("outbound")` y `useQuickSearchSide("return")` gestionan resultados, paginación, loading, errores, degradación, y weather por cada lado de forma independiente.
4. **El cierre se hace sobre la ruta actual**, no sobre una reescritura futura de quick-search. Cambios quirúrgicos, no rewrites.

### Lo que SÍ se conserva

```
QuickSearchView (~5000 líneas, refactor progresivo, no rewrite)
├── useQuickSearchMainState()              ← estado del formulario (compartido)
├── useQuickSearchSide("outbound")         ← estado completo de ida ✅
├── useQuickSearchSide("return")           ← estado completo de vuelta ✅
├── useSaveCombination()                   ← guarda combinación con group_id ✅
│
├── QuickSearchSearchForm                  ← usa formState
├── QuickSearchFilterConsole               ← usa formState
│
└── QuickSearchDualWorkspace               ← layout grid CSS 1fr 1px 1fr
    ├── QuickSearchSidePanel("outbound")   ← panel izquierdo ✅
    │   └── (children: resultados, estados, etc.)
    ├── div.qs-dual-divider                ← ❌ FALTA en JSX — causa bug panel invisible
    ├── QuickSearchSidePanel("return")     ← panel derecho ✅
    │   └── (children: resultados, estados, etc.)
    └── QuickSearchCombinedBanner          ← banner sticky combinado ✅
```

### Lo que se DESCARTA en este ciclo

- ❌ Endpoint round-trip nuevo en backend
- ❌ Rediseño masivo de quick-search
- ❌ Soporte dual completo de country-only (si no queda sólido, se deja fuera con UX clara)
- ❌ Reescritura de `QuickSearchView.tsx` — se extraen helpers mínimos, no se reescribe

---

## Fases completadas (todas ✅)

### Fase 0: Auditoría y Planificación ✅

---

## Bugs resueltos (cerrados 2026-06-08)

### Bug 1: Panel de vuelta invisible/colapsado 🔴 → ✅ RESUELTO (Fase 7)
- **Fix:** `<div className="qs-dual-divider" />` añadido entre paneles en `QuickSearchView.tsx`
- **Verificación:** 17/17 tests frontend pasan, inspección visual en navegador

### Bug 2: Calendario de vuelta sin hints de precio 🔴 → ✅ RESUELTO (Fase 4)
- **Fix:** Estados `calendarVisibleMonthReturn`, `calendarHintsByKeyReturn`, `calendarHintsLoadingKeyReturn` + useEffect de fetch con IATA invertido
- **Verificación:** Tests source-code confirman wiring completo de props al datepicker de vuelta

### Bug 3: Checkbox "Ida y vuelta" desalineado 🟡 → ✅ RESUELTO (Fase 3)
- **Fix:** `.qs-date-grid` con `grid-template-columns: 1fr auto` + `.has-return: 1fr auto 1fr`
- **Verificación:** Tests CSS confirman columnas explícitas (no auto-fit)

---

## Gaps cerrados

### Gap 1: Calendar hints per-side → ✅ Fase 4
### Gap 2: Divider en DualWorkspace → ✅ Fase 7
### Gap 3: Date grid layout → ✅ Fase 3
### Gap 7: Limpieza de orquestación → ✅ Fase 6 (`utils-dual.ts`)
### Gap 8: Tests → ✅ Fase 8 (backend, 10 tests) + Fase 9 (frontend, 17 tests)

### Gaps diferidos (fuera del alcance de este ciclo)

| Gap | Motivo |
|-----|--------|
| Gap 4: Deep links duales | `useQuickSearchSide.fetchDeepLink` existe pero no se usa en modo dual; baja prioridad |
| Gap 5: Weather per-side | Slots de weather existen en `useQuickSearchSide` pero no se alimentan; baja prioridad |
| Gap 6: Estados de carga dual | Mejora UX futura; el comportamiento actual es funcional |

---

## Archivos del sistema dual

### Creados (todos existen y están funcionales)
| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `state/useQuickSearchFormState.ts` | Estado de formulario extraído | ✅ |
| `state/useQuickSearchSide.ts` | Estado completo de un lado de búsqueda | ✅ |
| `state/useSaveCombination.ts` | Guarda 2 entradas con `group_id` | ✅ |
| `components/QuickSearchDualWorkspace.tsx` | Contenedor grid dual | ✅ |
| `components/QuickSearchSidePanel.tsx` | Panel individual con cabecera + paginación | ✅ |
| `components/QuickSearchPagination.tsx` | Paginación reutilizable | ✅ |
| `components/QuickSearchCombinedBanner.tsx` | Banner sticky combinado + guardar | ✅ |
| `styles/quick-search-dual.css` | CSS grid, paneles, divisor, banner | ✅ |
| `alembic/versions/0026_add_group_id_to_flight_watch.py` | Migración `group_id` | ✅ |
| `utils-dual.ts` | `buildDualSearchParams` + `findCombinationResult` | ✅ |
| `tests/quick-search-dual-regression.test.tsx` | 17 tests regresión frontend | ✅ |
| `backend/tests/integration/test_quick_search_dual_reverse_leg.py` | 10 tests backend reverse leg | ✅ |

### Modificados
| Archivo | Cambio | Estado |
|---------|--------|--------|
| `QuickSearchView.tsx` | Import y uso de dual hooks, rama dual en onSubmit, render dual workspace, divider, hints vuelta, date grid | ✅ |
| `state/useQuickSearchController.ts` | Delega a `useQuickSearchFormState` | ✅ |
| `shared/quickSearchCopy.ts` | +18 claves i18n dual panel + combinación | ✅ |
| `styles/globals.css` | Importa `quick-search-dual.css` | ✅ |
| `styles/screens.css` | `.qs-pagination-ellipsis`, `.qs-date-grid` explícito, `.has-return`, `.qs-check-inline` | ✅ |
| `backend/app/api/v1/search.py` | `group_id` en save_result | ✅ |
| `backend/app/infrastructure/db/models.py` | `group_id` en FlightWatch | ✅ |
| `types.ts` | `"return_date"` en `QuickSearchField` | ✅ |

---

## Ciclo completado (2026-06-08)

### Archivos creados en el ciclo de estabilización

| Archivo | Fase | Propósito |
|---------|------|-----------|
| `utils-dual.ts` | 6 | `buildDualSearchParams` + `findCombinationResult` |
| `tests/quick-search-dual-regression.test.tsx` | 9 | 17 tests de regresión frontend |
| `backend/tests/integration/test_quick_search_dual_reverse_leg.py` | 8 | 10 tests backend reverse leg + hints + deeplink + group_id |

### Archivos modificados en el ciclo

| Archivo | Fase | Cambio |
|---------|------|--------|
| `QuickSearchView.tsx` | 3,4,5,6,7 | Date grid condicional, hints vuelta, validación, divider, helpers |
| `screens.css` | 3 | `.qs-date-grid` explícito + `.has-return` + `.qs-check-inline` |
| `types.ts` | 5 | `"return_date"` en `QuickSearchField` |
| `quick-search-dual-plan.md` | 10 | Spec final actualizada |

### Verificación final
- ✅ 17/17 tests frontend dual regression
- ✅ 10/10 tests backend reverse leg
- ✅ TypeScript sin errores nuevos
- ✅ Divider visible entre paneles
- ✅ Hints de precio funcionales en ambos datepickers
- ✅ Date grid alineado con 3 columnas explícitas
- ✅ Paginación independiente por lado
- ✅ Banner combinado + guardado con `group_id`

---

## Referencias
- Plan QA completo: `docs/qa/idayvuelta08-06.txt`
- Backend contract: `docs/reference/backend/quick-search-contract.md`
- Runbook: `docs/runbooks/runbook-watchlist-quick-search-stabilization.md`
