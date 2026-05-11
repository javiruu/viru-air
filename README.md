# Viru Tracker

Viru Tracker es una plataforma de seguimiento de vuelos centrada en watchlists, histórico de precios, alertas y quick search. El repo es un monorepo con backend, frontend, infra y un sistema documental consolidado en `docs/`.

## Estructura del repo

- `backend/`: API FastAPI, dominio, infraestructura y tests.
- `frontend/`: aplicación Next.js + TypeScript.
- `infra/`: soporte de despliegue y manifiestos.
- `docs/`: fuente principal de documentación del proyecto.
- `scripts/`: utilidades operativas del repo.

## Arranque rápido local

Backend:

```bash
cd backend
pip install -e .[dev]
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Variables recomendadas:

- `backend/.env.example`
- `frontend/.env.example`

Importante:

- `JWT_SECRET` es obligatorio y no puede ser `change-me`.

## Documentación

Empieza por:

1. [Documentación de `docs/`](docs/README.md)
2. [Índice único](docs/INDICE_UNICO.md)
3. [Overview del proyecto](docs/overview/project-overview.md)
4. [Estado actual](docs/overview/current-state.md)

Regla clave:

- `docs/archive/` conserva histórico y trazabilidad, pero no es fuente de verdad activa.

## Runbooks y referencia útil

- [Runbook UI captures](docs/runbooks/runbook-ui-captures.md)
- [Runbook canary rollback](docs/runbooks/runbook-canary-rollback.md)
- [Done checklist](docs/reference/done-checklist.md)
- [Final report template](docs/reference/final-report-template.md)

## ADRs

- [ADR-001 monolito modular](docs/adr/ADR-001-monolito-modular.md)
- [ADR-002 stack base](docs/adr/ADR-002-stack-base.md)
- [ADR-003 provider adapter](docs/adr/ADR-003-provider-adapter.md)

## Publicación segura en esta máquina

Repositorio Git canónico para publicación:

- `C:\Users\javiru\Desktop\viru-tracker\_publish_repo`

Validación rápida antes de commit o push:

```powershell
cd C:\Users\javiru\Desktop\viru-tracker\_publish_repo
powershell -ExecutionPolicy Bypass -File .\scripts\release_guard.ps1 -AllowDirtyWorktree
```
