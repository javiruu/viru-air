# Dashboard Redesign V2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reestructurar el dashboard para un Hero dominante, operativa clara, oportunidades unificadas, y secundarios compactos, sin nuevas funcionalidades complejas.

**Architecture:** Reorganizar el layout en zonas dentro del dashboard existente, reutilizando datos ya cargados y aplicando condicional UI. Añadir estado local solo para colapsar Notas. Ajustar estilos globales para jerarquía y espaciado.

**Tech Stack:** Next.js 15, React 19, CSS global del proyecto.

---

### Task 1: Reestructurar el layout del dashboard

**Files:**
- Modify: `frontend/src/app/(private)/dashboard/page.tsx`

**Step 1: Write the failing test**
- Skip (no test harness for UI layout). Document visual checks instead.

**Step 2: Run test to verify it fails**
- Skip.

**Step 3: Write minimal implementation**
- Reorganizar el JSX en 4 zonas:
  - Hero dominante `DashboardHeroState` con CTA único y estados sin oportunidades.
  - Sección “Gestionar tus vuelos” con 3 cards (Watchlist, Alertas, Análisis).
  - Sección “Oportunidades” fusionando recomendaciones + sugerencias con 1 highlight.
  - Sección secundaria debajo: Actividad timeline + Notas colapsables.
- Eliminar duplicidad de botones secundarios grandes (convertir a links pequeños).
- Añadir estado local `notesCollapsed` para colapsar panel de notas.
- Mantener tracking events existentes y rutas actuales.

**Step 4: Run test to verify it passes**
- Run: `npm run lint` (desde `frontend`)
- Expected: `✔ No ESLint warnings or errors`

**Step 5: Commit**
```bash
git add frontend/src/app/(private)/dashboard/page.tsx
git commit -m "feat: restructure dashboard layout for hero focus"
```

---

### Task 2: Actualizar i18n de textos del dashboard

**Files:**
- Modify: `frontend/src/i18n/domains/dashboard.ts`

**Step 1: Write the failing test**
- Skip (sin tests de i18n).

**Step 2: Run test to verify it fails**
- Skip.

**Step 3: Write minimal implementation**
- Ajustar microcopy de Hero (“Hoy en Viru”, subtextos y estados).
- Añadir labels para “Gestionar tus vuelos”, “Oportunidades”, timeline compacto y notas colapsables.
- Mantener compatibilidad con claves existentes o mapear nuevas donde sea necesario.

**Step 4: Run test to verify it passes**
- Run: `npm run lint` (desde `frontend`)
- Expected: `✔ No ESLint warnings or errors`

**Step 5: Commit**
```bash
git add frontend/src/i18n/domains/dashboard.ts
git commit -m "feat: update dashboard copy for redesign v2"
```

---

### Task 3: Ajustar estilos para jerarquía, espaciado y compactación

**Files:**
- Modify: `frontend/src/styles/globals.css`

**Step 1: Write the failing test**
- Skip (sin tests de CSS).

**Step 2: Run test to verify it fails**
- Skip.

**Step 3: Write minimal implementation**
- Actualizar estilos de:
  - Hero (shadow más fuerte, tipografía H2).
  - Secciones con H3 y cards H4.
  - Espaciado 8/16/24 consistente.
  - Cards secundarias más planas.
  - Timeline compacto de actividad.
  - Notas colapsables (transición simple, padding reducido).
- Añadir clases nuevas específicas si el JSX lo requiere.

**Step 4: Run test to verify it passes**
- Run: `npm run lint` (desde `frontend`)
- Expected: `✔ No ESLint warnings or errors`

**Step 5: Commit**
```bash
git add frontend/src/styles/globals.css
git commit -m "feat: refine dashboard visual hierarchy and spacing"
```

---

### Task 4: QA visual rápida

**Files:**
- No code changes required.

**Step 1: Manual check**
- Run: `npm run dev` (desde `frontend`)
- Verify:
  - Hero dominante visible.
  - 1 botón sólido por card.
  - Oportunidades unificada.
  - Actividad compacta.
  - Notas colapsables.
  - Responsive correcto en mobile.

**Step 2: Commit**
- Skip (no code changes).