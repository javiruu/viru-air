# QA Checklist - Account System Redesign

Date: 2026-02-19
Owner: Codex

## Goals
- Cada item del menu lleva a su ruta real.
- Paginas nuevas cargan datos y muestran copy correcto.
- Centro de ayuda publico disponible.
- Backend expone endpoints nuevos y responde sin error.

## Scope
- Frontend rutas privadas: cuenta, preferencias, soporte.
- Frontend ruta publica: ayuda.
- Backend endpoints: account, support, public, preferences split.

## Checks (static)
- [x] `AccountMenu` enlaza a `/cuenta/perfil`
- [x] `AccountMenu` enlaza a `/cuenta/seguridad`
- [x] `AccountMenu` enlaza a `/preferencias/busqueda`
- [x] `AccountMenu` enlaza a `/preferencias/apariencia`
- [x] `AccountMenu` enlaza a `/preferencias/region`
- [x] `AccountMenu` enlaza a `/soporte/ayuda`
- [x] `AccountMenu` enlaza a `/soporte/feedback`
- [x] Ruta publica `/ayuda` creada
- [x] Router backend incluye `account`, `support`, `public`

## Checks (runtime)
- [x] Migracion alembic upgrade head
- [x] `GET /health` 200
- [x] `GET /ready` 200
- [ ] Probar flujo autenticado en UI (pendiente navegador)
- [ ] Verificar envio de feedback autenticado (pendiente)
- [ ] Verificar preferencias region actualiza locale (pendiente)

## Notes
- Smoke test backend ok con `LOG_FILE=logs\\smoke.log`.
- Validacion visual pendiente por falta de navegador en este paso.
