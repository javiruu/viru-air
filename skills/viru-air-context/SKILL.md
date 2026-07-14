---
name: viru-air-context
description: Reusable operating and onboarding context for Viru Air. Use when Codex is working in the Viru Air repo and needs to re-onboard quickly, identify which docs are canonical, translate older Paperclip-style process rules into the current Codex workflow, or gather stable project context before editing, verifying, or publishing changes.
---

# Viru Air Context

## Overview

Use this skill to rebuild working context quickly in the Viru Air repo without re-reading the full documentation tree. Prefer live docs first, treat `docs/archive/` as historical intent only, and use the bundled references when you need a compact recap before opening repo files.

## Quick Start

1. Open `AGENTS.md`.
2. Open `README.md`, `docs/README.md`, `docs/overview/current-state.md`, and `docs/overview/repo-map.md`.
3. Open `docs/reference/codex-operating-contract.md` if you need the persistent operating policy.
4. Branch by area:
   - Backend or quick-search: `docs/reference/README.md` and `docs/reference/backend/`.
   - UI or UX: `docs/ui/UI_SYSTEM_V1.md`, `docs/ui/UI_CONTRACT_V1.md`, `docs/ui/UI_VISUAL_QA_CHECKLIST.md`, and `docs/specs/README.md`.
   - Ops or QA: `docs/runbooks/` and `docs/qa/README.md`.

## Working Rules

- Treat `docs/overview/`, `docs/reference/`, `docs/specs/`, `docs/ui/`, `docs/runbooks/`, and `docs/qa/` as live documentation.
- Treat `docs/plans/` as nearby historical reference and `docs/archive/` as deep history only.
- Keep one canonical source per rule or contract; prefer linking over copying.
- Do not propose broad product or visual redesigns without explicit direction.
- When behavior, contracts, auth, data, infra, or user-visible risk is involved, prepare summary, key files, risks, rollback, and manual validation notes before publication.
- Use the canonical repo workflow: verify locally, then commit directo a `main` y push solo cuando el usuario pida un cambio real completado.

## References

- Read `references/project-context.md` for the compact project map.
- Read `references/operating-rules.md` for the adapted Word -> Codex operating rules.

## Notes

- This skill is intentionally lightweight. Open repo docs for full detail instead of inflating the skill body.
- If the repo docs and the archived material disagree, trust the live docs unless the task is explicitly historical.