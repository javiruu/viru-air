# Hero CTA Quick Search Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Cambiar el CTA principal del Hero del dashboard para dirigir a Quick Search con copy orientado a acción.

**Architecture:** Actualizar el copy i18n del Hero y forzar el enlace del CTA principal a `/quick-search`. Sin cambios de backend.

**Tech Stack:** Next.js 15, React 19, i18n existente.

---

### Task 1: Actualizar CTA del Hero

**Files:**
- Modify: `frontend/src/app/(private)/dashboard/page.tsx`
- Modify: `frontend/src/i18n/domains/dashboard.ts`

**Step 1: Write the failing test**
- Skip (sin harness UI para texto/link).

**Step 2: Run test to verify it fails**
- Skip.

**Step 3: Write minimal implementation**
- Cambiar el copy del CTA principal del Hero a “Buscar nuevas rutas ahora”.
- Forzar el `href` del CTA a `/quick-search`.
- Ajustar strings i18n en ES/EN para el nuevo copy.

**Step 4: Run test to verify it passes**
- Run: `npm run lint` (desde `frontend`)
- Expected: `✔ No ESLint warnings or errors`

**Step 5: Commit**
```bash
git add frontend/src/app/(private)/dashboard/page.tsx frontend/src/i18n/domains/dashboard.ts
git commit -m "feat: point hero cta to quick search"
```