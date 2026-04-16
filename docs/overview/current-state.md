Status: canonical
Scope: maintainer orientation and repo re-entry
Last reviewed: 2026-04-16
Canonical source: docs/overview/current-state.md
Related: docs/INDICE_UNICO.md, README.md

---
# Current State

## Producto

Viru Tracker es una plataforma para seguimiento de vuelos centrada en watchlists, historico de precios, alertas y quick search.

## Backend

- Stack base: Python >=3.12, FastAPI, SQLAlchemy, Alembic.
- Entrada principal: `backend/app/main.py`.
- API principal bajo prefijo: `/api/v1`.
- Endpoints de salud visibles: `/health` y `/ready`.
- Estructura visible: `api`, `core`, `domain`, `infrastructure`, `services`.
- Tests: `backend/tests/unit` y `backend/tests/integration`.
- Referencias utiles: [../reference/backend/quick-search-contract.md](../reference/backend/quick-search-contract.md) y [../reference/backend/quick-search-acceptance-checklist.md](../reference/backend/quick-search-acceptance-checklist.md).

## Frontend

- Stack base: Next.js 15.1, React 19, TypeScript.
- Estructura visible en `frontend/src`: `app`, `modules`, `pages`, `styles`, `lib`, `data`, `i18n`.
- Rutas publicas visibles: `/(public)/login`, `/(public)/register`, `/(public)/policies`, `/(public)/ayuda`.
- Rutas privadas visibles: `/(private)/dashboard`, `watchlist`, `quick-search`, `alerts`, `history`, `recomendaciones`, `suggestions`, `admin`.
- Tests visibles en `frontend/tests/`: session routing, quick search, recommendations, watchlist y utilidades.
- Contrato visual: [../ui/UI_SYSTEM_V1.md](../ui/UI_SYSTEM_V1.md), [../ui/UI_CONTRACT_V1.md](../ui/UI_CONTRACT_V1.md), [../ui/UI_VISUAL_QA_CHECKLIST.md](../ui/UI_VISUAL_QA_CHECKLIST.md).

## Infra y operacion

- `infra/docker/`: Dockerfiles y entrypoint frontend.
- `infra/docker-compose*.yml`: arranque local y relanzamiento.
- `infra/github/workflows/`: CI y release.
- `infra/k8s/`: manifests base para backend, frontend y worker.
- Script de arranque local: `iniciar_viru.ps1` (levanta backend y frontend y valida `health`).
- Runbooks vivos: [../runbooks/](../runbooks/).

## Documentacion viva

- Navegacion: [../INDICE_UNICO.md](../INDICE_UNICO.md)
- Reentrada: esta carpeta `overview/`
- Arquitectura: `adr/`
- Referencias tecnicas: `reference/`
- Specs de producto/UI/policies: `specs/`
- QA reusable: `qa/`
- Historico: `archive/`

## Que ya no es ruta principal

- Los `.docx` y transcripciones de `fases/` son historico de archivo.
- Los reportes detallados de QA y capturas de ciclos quedan en `docs/archive/qa/`.
- Los prompts y reportes de tooling quedan en `docs/archive/prompts/` y `docs/archive/tooling/`.
