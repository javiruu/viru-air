# Quick Search Loading Checkpoints - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enriquecer el loading de `/quick-search` con checkpoints macro + sub-checkpoints por vuelo (`X/Y/Z`) sin tocar lógica de negocio, endpoints ni contratos.

**Architecture:** Mantener el pipeline actual de progreso real (`targetProgress/displayProgress/loadingPhase`) y añadir una capa de presentación derivada de estado local (`loadingSubchecks`) sincronizada por hitos reales. La búsqueda principal y weather permanecen desacoplados como hoy.

**Tech Stack:** Next.js App Router, React/TypeScript, CSS global `qs-*`, i18n local `quickSearchCopy.ts`, analytics `trackEvent`.

---

### Task 1: Baseline y guardrails de flujo

**Files:**
- Modify: `frontend/src/app/(private)/quick-search/page.tsx`

**Step 1: Añadir comentario de guardrail junto al bloque `onSubmit`**
- Documentar explícitamente que no se modifican endpoints/contratos ni hitos 30/80/95/100.

**Step 2: Añadir helper local para construir sub-checkpoints (máx 3)**
- Inputs: `origin`, `destination`, `originCountryOnly`, `destinationCountryOnly`, toggles de cercanía.
- Output: array de labels seguros para UI.

**Step 3: No tocar payload ni `apiFetchWithStatus`**
- Verificar que `/search/quick` y weather siguen igual.

**Step 4: Validación rápida**
Run: `npm run build`
Expected: build OK sin cambios de contrato.

**Step 5: Commit**
```bash
git add frontend/src/app/(private)/quick-search/page.tsx
git commit -m "feat(quick-search): add safe sub-checkpoint derivation for loading"
```

### Task 2: Render de sub-checkpoints en loader

**Files:**
- Modify: `frontend/src/app/(private)/quick-search/page.tsx`
- Modify: `frontend/src/styles/globals.css` (solo `qs-*`)

**Step 1: Renderizar bloque debajo de phase/progress actual**
- Añadir sección compacta con título y lista de 2-3 ítems.
- Estado visual por item: `active`, `done`, `pending`.

**Step 2: Mapear activación por hitos reales**
- `requesting`: avanza index 0 -> 1.
- `response_parsed`: marca 1 done, activa 2.
- `client_done`: marca 2 done.
- `committed`: todos done (solo success/empty).

**Step 3: Estilos `qs-*` mínimos**
- Reutilizar la estética actual del loader.
- Sin añadir animación pesada; mantener reduced motion.

**Step 4: Validación responsive**
- Desktop + `<=900px` + `<=390px`.
- Confirmar que no hay CLS en `.qs-state-loading`.

**Step 5: Commit**
```bash
git add frontend/src/app/(private)/quick-search/page.tsx frontend/src/styles/globals.css
git commit -m "feat(quick-search): show loading sub-checkpoints x/y/z in boarding state"
```

### Task 3: i18n de microcopy

**Files:**
- Modify: `frontend/src/modules/shared/quickSearchCopy.ts`
- Test: `frontend/tests/quick-search-copy.test.ts`

**Step 1: Añadir claves ES/EN para sub-checkpoints**
- `loadingSubcheckTitle`
- `loadingSubcheckFlight`
- `loadingSubcheckCombo`
- `loadingSubcheckActive`
- `loadingSubcheckDone`

**Step 2: Integrar `t(...)` en render loader**
- Sin hardcodes nuevos.

**Step 3: Ajustar tests de copy**
- Verificar presencia de nuevas claves en ES/EN.

**Step 4: Ejecutar test de copy**
Run: `npm run test -- quick-search-copy.test.ts`
Expected: PASS.

**Step 5: Commit**
```bash
git add frontend/src/modules/shared/quickSearchCopy.ts frontend/tests/quick-search-copy.test.ts frontend/src/app/(private)/quick-search/page.tsx
git commit -m "feat(i18n): add loading sub-checkpoint copy for quick-search"
```

### Task 4: Analytics sin spam

**Files:**
- Modify: `frontend/src/app/(private)/quick-search/page.tsx`

**Step 1: Evento once per search**
- `quicksearch_loading_subcheckpoints_shown` cuando se renderiza primera vez en cada submit.

**Step 2: Evento por cambio de índice activo**
- `quicksearch_loading_subcheckpoint_advanced` con `{ index, total }`.
- Guardar último índice enviado en ref para no duplicar.

**Step 3: Verificar no hay envío por frame**
- Revisar que no dependa de `displayProgress` frame-by-frame.

**Step 4: Build completo**
Run: `npm run build`
Expected: build OK.

**Step 5: Commit**
```bash
git add frontend/src/app/(private)/quick-search/page.tsx
git commit -m "feat(analytics): track loading sub-checkpoints without spam"
```

### Task 5: QA manual y evidencia

**Files:**
- Modify: `logs_ia/<nuevo-log>.md`
- Modify: `docs/INDICE_UNICO.md` (si aplica nuevo plan/log enlazable)

**Step 1: Smoke scenarios**
1. Loading corto (<300ms): no parpadeo ni ruido.
2. Loading medio (2-3s): se ven `X/Y/Z`.
3. Loading largo (5-10s): avance legible, sin loop loco.
4. Empty: llega a committed correctamente.
5. Error/rate: no mostrar cierre engañoso de checkpoints.

**Step 2: A11y**
- Tab/lector de pantalla básico en loader.
- `aria-live` no hiperactivo.

**Step 3: Responsive**
- Desktop, `<=900`, `<=390`.

**Step 4: Registrar evidencia**
- Capturas + resultado de build/test en log.

**Step 5: Commit**
```bash
git add logs_ia docs/INDICE_UNICO.md
git commit -m "docs(quick-search): log qa evidence for loading checkpoints rollout"
```

## Manual checklist de aceptación
- [ ] Se mantienen hitos reales 30/80/95/100.
- [ ] Se muestran 2-3 checkpoints tipo "Buscando vuelo X/Y/Z".
- [ ] No se tocan endpoints ni contratos.
- [ ] No se altera ranking/filtros.
- [ ] Build y test de copy pasan.
- [ ] No hay spam de analytics.
