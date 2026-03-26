# Quick-Search Airport Modal Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the /quick-search airport selector modal scalable with two-panel layout, independent scroll, and sticky header/search using minimal class anchors and scoped CSS.

**Architecture:** Add class anchors in `page.tsx` for modal root/header/body/columns/search/recents and apply scoped CSS in `globals.css` for layout, overflow, sticky, and responsive stacking.

**Tech Stack:** Next.js (App Router), React, global CSS.

---

### Task 1: Add class anchors and minimal wrappers in quick-search modal

**Files:**
- Modify: `frontend/src/app/(private)/quick-search/page.tsx`

**Step 1: Add modal root class**
- On modal root node (`section.airport-modal`), append `qs-airport-modal` to existing className.

**Step 2: Add header wrapper class**
- Wrap the header row that contains title and clear action with a `div.qs-airport-modal__header` (if no wrapper exists).

**Step 3: Add body wrapper and column classes**
- Wrap the countries column in `div.qs-airport-modal__countries`.
- Wrap the airports column in `div.qs-airport-modal__airports`.
- Wrap both with `div.qs-airport-modal__body`.

**Step 4: Add search and recents wrappers**
- Wrap the search input section with `div.qs-airport-modal__search`.
- Wrap the recents block with `div.qs-airport-modal__recents`.

**Step 5: Commit**
```bash
git add frontend/src/app/(private)/quick-search/page.tsx
git commit -m "fix(ui): add airport modal layout anchors"
```

---

### Task 2: Add scoped modal layout CSS

**Files:**
- Modify: `frontend/src/styles/globals.css`

**Step 1: Append modal layout CSS**
Add the block at the end of file:
```css
/* /quick-search — Airport modal: escalable con listas largas, sin solapes */
.qs-airport-modal {
  max-height: 82vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.qs-airport-modal__header {
  position: sticky;
  top: 0;
  z-index: 3;
  background: #fff;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.qs-airport-modal__body {
  display: grid;
  grid-template-columns: minmax(260px, 1.1fr) minmax(320px, 0.9fr);
  gap: 16px;
  padding: 12px 12px;
  overflow: hidden;
  flex: 1 1 auto;
}

.qs-airport-modal__countries {
  overflow: auto;
  padding-right: 6px;
  border-right: 1px solid rgba(0, 0, 0, 0.06);
}

.qs-airport-modal__airports {
  overflow: auto;
  padding-left: 6px;
}

.qs-airport-modal__search {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #fff;
  padding-top: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.qs-airport-modal__recents {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

@media (max-width: 900px) {
  .qs-airport-modal__body {
    grid-template-columns: 1fr;
  }

  .qs-airport-modal__countries {
    border-right: none;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    padding-bottom: 10px;
  }
}

.qs-airport-modal__countries button,
.qs-airport-modal__countries a,
.qs-airport-modal__countries [role="button"] {
  padding-top: 6px;
  padding-bottom: 6px;
}
```

**Step 2: Commit**
```bash
git add frontend/src/styles/globals.css
git commit -m "fix(ui): make airport modal scalable with sticky header"
```

---

### Task 3: Manual QA (no automated tests)

**Step 1: Layout and scroll**
- Open the modal and confirm header remains visible while scrolling lists.
- Countries and airports columns scroll independently.

**Step 2: Search + recents**
- Search bar stays sticky in the airports column.
- Recents wrap without overflow.

**Step 3: Responsive**
- Resize to <900px and confirm columns stack with no overlap.

---

**Skills referenced:** @brainstorming, @writing-plans
