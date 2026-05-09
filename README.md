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

## WAN (tunel publico)

- El tunel WAN publica solo el frontend (`127.0.0.1:3000`).
- Las llamadas browser a `/api/*` se enrutan desde Next.js hacia backend local `127.0.0.1:8000` mediante `rewrites`.
- Para evitar 404 en login WAN, usa `NEXT_PUBLIC_API_URL=/api/v1`.

## Calidad (ejecucion real)

```bash
cd backend
python -m pytest -q

cd ../frontend
npm run build
```

Para E2E frontend con autenticacion real:

```bash
cd frontend
npm run test:e2e:real
```

Notas E2E:
- Los tests arrancan backend y frontend automaticamente (`8000` y `3000`) si no estan levantados.
- Si no logra arrancar algun servicio dentro del timeout, el test falla con error de bootstrap.
- Variables opcionales:
  - `E2E_BASE_URL` (default `http://127.0.0.1:3000`)
  - `E2E_API_BASE_URL` (default `http://127.0.0.1:8000/api/v1`)
  - `E2E_BACKEND_PYTHON` (ruta al `python.exe` de backend si no usas `.venv` por defecto)
  - `E2E_BACKEND_START_TIMEOUT_MS` (default `45000`)
  - `E2E_FRONTEND_START_TIMEOUT_MS` (default `90000`)

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

## Publicacion segura (main) y guardrails

Repositorio canonico para publicar en esta maquina:
- `C:\Users\javiru\Desktop\viru-tracker\_publish_repo`

Checklist obligatoria de cierre:
- `docs/reference/done-checklist.md`

Plantilla obligatoria de reporte final:
- `docs/reference/final-report-template.md`

Instalacion unica del hook pre-push:

```powershell
cd C:\Users\javiru\Desktop\viru-tracker\_publish_repo
powershell -ExecutionPolicy Bypass -File .\scripts\install-git-hooks.ps1
```

Validacion rapida antes de commit/push:

```powershell
cd C:\Users\javiru\Desktop\viru-tracker\_publish_repo
powershell -ExecutionPolicy Bypass -File .\scripts\release_guard.ps1 -AllowDirtyWorktree
```

Validacion de staging acotado (ejemplo):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\release_guard.ps1 `
  -AllowDirtyWorktree `
  -ExpectedPaths README.md,frontend/src/styles/components.css
```

Auditoria de 30 segundos tras publicar:

```powershell
git log -1 --oneline
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git ls-remote origin main
```

## Fases implementadas en este montaje

Cada fase queda reflejada en:

1. codigo/configuracion/documentacion del repo
2. log dedicado en `logs_fases/fase_XX.log`

## Nota

Este repositorio prioriza una base enterprise modular y trazable para seguir iterando por sprints.
