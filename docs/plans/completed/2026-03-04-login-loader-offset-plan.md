# Login Loader Offset Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Shift the login marketing loader words block down by 3px using a CSS transform on `.login-words`.

**Architecture:** Make a minimal CSS-only change in the global stylesheet, scoped to the existing `.login-words` class to avoid layout changes elsewhere.

**Tech Stack:** Next.js app, global CSS in `frontend/src/styles/globals.css`.

---

### Task 1: Apply the CSS offset

**Files:**
- Modify: `frontend/src/styles/globals.css`

**Step 1: Add the visual offset**

Edit the `.login-words` rule to include:

```css
transform: translateY(3px);
```

**Step 2: Manual verification**

Run the app and open `/login` to confirm the loader words block is shifted down ~3px and no other layout changes are introduced.

Run: `npm run dev` (if not already running)
Expected: `/login` shows the marketing loader words slightly lower; other elements unchanged.

**Step 3: Commit**

```bash
git add frontend/src/styles/globals.css
git commit -m "ui: nudge login loader words down 3px"
```
