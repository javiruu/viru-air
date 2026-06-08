# Cierre de Ida y Vuelta en /quick-search — Reporte Final

> **Fecha:** 2026-06-08  
> **Estado:** ✅ COMPLETADO  
> **Propietario:** AI agent (Codebuff)

---

## Resumen ejecutivo

Se completó el ciclo completo de estabilización del flujo dual (ida + vuelta) en `/quick-search`. Los 3 bugs críticos que impedían el funcionamiento correcto fueron diagnosticados y resueltos quirúrgicamente, sin reescribir la vista principal ni introducir nuevos endpoints.

---

## Bugs resueltos

| # | Bug | Severidad | Causa raíz | Fix |
|---|-----|-----------|------------|-----|
| 1 | Panel de vuelta invisible tras búsqueda dual | 🔴 Crítica | CSS grid 1fr 1px 1fr sin `div.qs-dual-divider` → panel caía en columna de 1px | Añadir `<div className="qs-dual-divider" />` entre paneles |
| 2 | Calendario de vuelta sin hints de precio | 🔴 Crítica | Solo existía caché de hints compartida, sin estado por lado ni inversión IATA | Estados separados `calendarVisibleMonthReturn`, `calendarHintsByKeyReturn`, fetch con IATA invertido |
| 3 | Checkbox "Ida y vuelta" desalineado | 🟡 Media | `.qs-date-grid` usaba `repeat(auto-fit)` genérico | Grid explícito: `1fr auto` (solo ida) / `1fr auto 1fr` (dual) |

---

## Fases ejecutadas

| Fase | Descripción | Archivos |
|------|-------------|----------|
| 1 | Baseline y diagnóstico | Inspección de código |
| 2 | Alinear spec dual | `docs/specs/quick-search-dual-plan.md` |
| 3 | Rehacer `.qs-date-grid` | `screens.css`, `QuickSearchView.tsx` |
| 4 | Activar hints en calendario de vuelta | `QuickSearchView.tsx` |
| 5 | Endurecer `QuickSearchDatePicker` | `QuickSearchView.tsx`, `types.ts` |
| 6 | Consolidar orquestación dual | `utils-dual.ts` (nuevo), `QuickSearchView.tsx` |
| 7 | Corregir divider invisible | `QuickSearchView.tsx` |
| 8 | Backend: auditoría reverse leg | `test_quick_search_dual_reverse_leg.py` (nuevo) |
| 9 | Frontend: tests de regresión | `quick-search-dual-regression.test.tsx` (nuevo) |
| 10 | QA manual y documentación | Navegador, este documento |

---

## Archivos creados

| Archivo | Propósito |
|---------|-----------|
| `frontend/src/modules/quick-search/utils-dual.ts` | `buildDualSearchParams` + `findCombinationResult` |
| `frontend/tests/quick-search-dual-regression.test.tsx` | 17 tests de regresión frontend |
| `backend/tests/integration/test_quick_search_dual_reverse_leg.py` | 10 tests backend reverse leg |
| `docs/plans/2026-06-08-quick-search-roundtrip-stabilization.md` | Este documento |

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `frontend/src/modules/quick-search/QuickSearchView.tsx` | Date grid condicional, hints vuelta, validación, divider, helpers |
| `frontend/src/styles/screens.css` | `.qs-date-grid` explícito, `.has-return`, `.qs-check-inline` |
| `frontend/src/modules/quick-search/types.ts` | `"return_date"` en `QuickSearchField` |
| `docs/specs/quick-search-dual-plan.md` | Spec actualizada a estado final |

---

## Verificación

| Capa | Resultado |
|------|-----------|
| Frontend tests | 17/17 ✅ |
| Backend tests | 14/15 ✅ (1 fallo pre-existente no relacionado: fake provider price mismatch) |
| TypeScript | Sin errores nuevos |
| Browser QA | ✅ Ambos paneles visibles lado a lado, hints funcionales, date grid alineado |

---

## Gaps diferidos (fuera de alcance)

| Gap | Prioridad | Notas |
|-----|-----------|-------|
| Deep links duales | Baja | `useQuickSearchSide.fetchDeepLink` existe; no se usa en modo dual |
| Weather per-side | Baja | Slots existen en hook; no se alimentan |
| Estados de carga dual | Baja | UX futura; comportamiento actual funcional |
| Soporte country-only dual | Media | Scope complejo; diferido con UX clara |

---

## Definición de terminado

- ✅ La casilla "Ida y vuelta" ya no se ve desalineada
- ✅ El calendario de vuelta pinta buckets de precio
- ✅ El panel de vuelta es visible en modo dual
- ✅ Ida y vuelta muestran estados independientes
- ✅ La búsqueda dual queda cubierta con tests frontend + backend
- ✅ El reverse leg queda cubierto en backend
- ✅ El flujo está verificado en UI real
- ✅ Dark y light mantienen identidad
- ✅ Queda documentado para futuras sesiones
