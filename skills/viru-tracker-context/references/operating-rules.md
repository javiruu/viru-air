# Viru Tracker Operating Rules

## Purpose

Use this reference when you need the compact process model extracted from the Viru Tracker Studio master Word and adapted to Codex.

## Core rules

- Every meaningful task needs scope, affected surfaces, and a closing criterion.
- Avoid duplicate modules, duplicate contracts, and duplicate sources of truth.
- Stable knowledge must land in files or skills, not only in chat.
- Do not break routes, API contracts, data structures, or visual system rules without updating the canonical doc.
- Keep secrets out of markdown, commits, PR bodies, screenshots, and logs.
- Treat connectors, automation, and integrations as sensitive surfaces.

## Source-of-truth order

1. Active session instructions.
2. `AGENTS.md`
3. `docs/reference/codex-operating-contract.md`
4. `docs/overview/`
5. Domain docs in `reference/specs/ui/runbooks/qa`
6. `docs/plans/` and `docs/changelog/`
7. `docs/archive/`

## Review and publication model

1. Clarify scope from the request and the live docs.
2. Implement locally.
3. Prepare a compact review packet with summary, key files, risks, rollback, and manual validation notes.
4. Review for regressions and contract drift.
5. Record human validation when auth, data, infra, connectors, or user-visible risk is involved.
6. Publish through the GitHub flow rather than treating remote GitHub as a draft area.

## Word sections worth adopting

- Non-negotiable operating principles.
- Source-of-truth hierarchy.
- Review and publication gates.
- Skills should stay single-purpose.
- Connector and secret hygiene.

## Word sections to keep as reference only

- Literal Paperclip package tree.
- Paperclip org chart as repo structure.
- Import/bootstrap phases.
- Formal budget and heartbeat machinery.
- Separate `HISTORY.md` requirement.
