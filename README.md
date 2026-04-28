# Viru Platform (Fases 1-10)

Viru Tracker es una plataforma enfocada en optimizar la compra de vuelos Ryanair mediante watchlists, historicos de precios y alertas inteligentes. Analiza tendencias reales y ayuda a decidir cuando comprar, priorizando claridad, simplicidad y decisiones basadas en datos.

Monorepo inicial de Viru (Ryanair Tracker) montado desde la carpeta `fases`, con trazabilidad fase a fase, arquitectura fullstack y base de operacion.

## Estructura

- `backend/`: API FastAPI (`/api/v1`), dominio, servicios, proveedor desacoplado y tests.
- `frontend/`: Next.js + TypeScript con rutas privadas/publicas y modulos de producto.
- `infra/`: Docker, CI/CD base, manifests k8s y soporte de despliegue.
- `docs/`: ADR, runbooks, QA, roadmap de escalabilidad e i18n.
- `logs_fases/`: bitacoras legibles por cada fase, con decisiones y acciones ejecutadas.

## Arquitectura base

- Backend: Python 3.12 + FastAPI + SQLAlchemy + Alembic.
- Frontend: Next.js 15 + React + TypeScript.
- Datos: PostgreSQL (objetivo) y SQLite para arranque local rapido.
- Asincronia: cola preparada para Redis/workers (MVP en modo sync + hooks).
- Observabilidad: logging JSON estructurado + `x-correlation-id`.

## Arranque rapido local

```bash
# backend
cd backend
pip install -e .[dev]
copy .env.example .env
uvicorn app.main:app --reload --port 8000

# frontend (otra terminal)
cd frontend
npm install
npm run dev
```

Variables recomendadas:
- `backend/.env.example`
- `frontend/.env.example`

Importante: `JWT_SECRET` es obligatorio y no puede ser `change-me`.

## Calidad (ejecucion real)

```bash
cd backend
python -m pytest -q

cd ../frontend
npm run build
```

## Capturas UI rapidas (flujo recomendado)

Cuando necesites evidencia visual rapida en frontend, usa este flujo minimo en lugar de improvisar:

1. Arranca servicios con `powershell -ExecutionPolicy Bypass -File .\iniciar_viru.ps1`.
2. Ejecuta el script de captura reutilizable:
   - `node frontend/scripts/qa_capture_notification_login.mjs`
3. Revisa los PNG generados en `docs/qa/`:
   - `notifications-login-desktop-full.png`
   - `notifications-login-desktop-component.png`

Notas:
- El script abre `/login`, inicia sesion con el usuario semilla local y captura el toast real.
- Para nuevos casos UI, crea o amplia scripts estables en `frontend/scripts/qa_capture_*.mjs` y guarda salidas en `docs/qa/`.
- Guia canonica completa: `docs/runbooks/runbook-ui-captures.md`.

## Hardening / Operacion

- Health: `GET /health`
- Readiness: `GET /ready`
- Runbook canary/rollback: `docs/runbooks/runbook-canary-rollback.md`
- Manifiestos base: `infra/k8s/*.yaml`

## Fases implementadas en este montaje

Cada fase queda reflejada en:

1. codigo/configuracion/documentacion del repo
2. log dedicado en `logs_fases/fase_XX.log`

## Nota

Este repositorio prioriza una base enterprise modular y trazable para seguir iterando por sprints.
