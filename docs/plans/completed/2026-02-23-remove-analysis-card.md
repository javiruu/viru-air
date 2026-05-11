# Remove Analysis Card Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminar la card de "Análisis y comparativa" del dashboard y su copy asociado.

**Architecture:** Ajuste del JSX para quitar el módulo y limpieza de i18n. No hay cambios de backend.

**Tech Stack:** Next.js 15, React 19, i18n existente.

---

### Task 1: Quitar módulo de análisis en dashboard

**Files:**
- Modify: `frontend/src/app/(private)/dashboard/page.tsx`

**Step 1: Write the failing test**
- Skip (sin harness UI).

**Step 2: Run test to verify it fails**
- Skip.

**Step 3: Write minimal implementation**
- Eliminar el bloque JSX de la card “Análisis y comparativa”.
- Verificar que el grid sigue consistente con 2 cards.

**Step 4: Run test to verify it passes**
- Run: `npm run lint` (desde `frontend`)
- Expected: `✔ No ESLint warnings or errors`

**Step 5: Commit**
```bash
git add frontend/src/app/(private)/dashboard/page.tsx
git commit -m "feat: remove analysis card from dashboard"
```

---

### Task 2: Limpiar i18n del módulo de análisis

**Files:**
- Modify: `frontend/src/i18n/domains/dashboard.ts`

**Step 1: Write the failing test**
- Skip (sin tests i18n).

**Step 2: Run test to verify it fails**
- Skip.

**Step 3: Write minimal implementation**
- Eliminar claves de `modules.analysis` en ES/EN.

**Step 4: Run test to verify it passes**
- Run: `npm run lint` (desde `frontend`)
- Expected: `✔ No ESLint warnings or errors`

**Step 5: Commit**
```bash
git add frontend/src/i18n/domains/dashboard.ts
git commit -m "chore: remove analysis module copy"
```