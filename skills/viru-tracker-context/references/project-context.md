# Viru Tracker Project Context

## Product

- Viru Tracker is a flight-tracking product centered on watchlists, price history, alerts, and quick search.

## Stack

- Backend: Python >= 3.12, FastAPI, SQLAlchemy, Alembic.
- Frontend: Next.js 15.1, React 19, TypeScript.
- Local infra: docker-compose with backend, frontend, Postgres, and Redis.

## Repo shape

- `backend/`: API, domain, infrastructure, and tests.
- `frontend/`: app routes, product modules, shared code, styles, tests.
- `infra/`: Docker, workflows, manifests.
- `scripts/`: support utilities.
- `docs/`: the live documentation center.

## Main backend entrypoints

- App entry: `backend/app/main.py`
- API prefix: `/api/v1`
- Health endpoints: `/health`, `/ready`

## Main frontend routes

- Public: `/(public)/login`, `/(public)/register`, `/(public)/policies`, `/(public)/ayuda`
- Private: `/(private)/dashboard`, `watchlist`, `quick-search`, `alerts`, `history`, `recomendaciones`, `suggestions`, `admin`

## Documentation map

- `README.md`: repo entrypoint.
- `docs/overview/start-here.md`: fastest re-entry path.
- `docs/overview/current-state.md`: active stack and module map.
- `docs/overview/repo-map.md`: folder-level navigation.
- `docs/reference/codex-operating-contract.md`: adapted operating rules for Codex.
- `docs/reference/backend/`: active backend contracts and acceptance.
- `docs/specs/`: active product, UI, and policy specs.
- `docs/ui/`: visual system and UI contract.
- `docs/runbooks/`: operational playbooks.
- `docs/qa/`: evergreen QA artifacts.
- `docs/archive/`: historical material only.

## Architectural anchors

- Monolith-first modular architecture.
- FastAPI + SQLAlchemy + Alembic on backend.
- Next.js + TypeScript on frontend.
- Provider integration is intentionally adapter-based.

## Current doc discipline

- Prefer current docs over archived phases.
- Keep root-level repo guidance short and push long-form policy into docs.
- Update the matching canonical doc when a contract or stable rule changes.
