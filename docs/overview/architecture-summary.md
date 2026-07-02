# Resumen de Arquitectura

**Estado:** vivo  
**Última revisión:** 2026-07-02
**Fuente de verdad:** sí  
**Área:** overview

## Resumen

Monorepo con backend (FastAPI), frontend (Next.js), infraestructura de túneles y documentación consolidada.

## Backend

- **Framework:** FastAPI + SQLAlchemy + Alembic
- **Entrada:** `backend/app/main.py` con prefijo `/api/v1`
- **Base de datos:** PostgreSQL (producción), SQLite (desarrollo local)
- **Arquitectura de providers:** `FlightSearchOrchestrator` ejecuta providers en paralelo via `ThreadPoolExecutor`. Cada provider (Ryanair, Vueling, Wizz Air, easyJet, Duffel) implementa `FlightProvider` interface. Wizz Air usa per-route locks para evitar serialización entre rutas distintas.
- **Caché de búsqueda:** Tres niveles → L1 (memoria local), L2 (DB compartida entre usuarios), Provider (API live). Anti-stampede con lock por firma de búsqueda.
- **Door-to-door:** Providers de transporte terrestre con datos GTFS + APIs REST (ORS, OpenTripPlanner). Perfiles de activación con blindaje anti-mock.

## Frontend

- **Framework:** Next.js + React + TypeScript
- **Rutas:** App Router con layout privado y auth
- **Estado:** Hooks locales con useReducer + useState, sin librería de estado global
- **SVGs corporativos:** Centralizados en `src/icons/` como componentes React (RyanairIcon, WizzAirIcon, GenericProviderIcon)
- **Estilos:** CSS modules + variables CSS con sistema dual dark/light (Aviation Dark-Luxe)
- **i18n:** Sistema propio con archivos por dominio y locale

## Infraestructura

- **Publicación principal:** Cloudflare Tunnel
- **Failover:** Tailscale Funnel
- **Panel unificado:** `VIRU_PANEL.bat` con estado y control de ambos túneles

## Documentación

- `docs/overview/` — reentrada y estado actual
- `docs/adr/` — 3 ADRs vigentes
- `docs/reference/` — contratos API activos
- `docs/specs/` — especificaciones vivas
- `docs/ui/` — sistema visual y contrato UI
- `docs/runbooks/` — operación y respuesta
- `docs/qa/` — checklists, reportes y evidencia
- `docs/plans/` — planes activos y completados

## Decisiones base

- [ADR-001](../adr/ADR-001-monolito-modular.md) — monolito modular
- [ADR-002](../adr/ADR-002-stack-base.md) — stack base (FastAPI, Next.js, SQLAlchemy)
- [ADR-003](../adr/ADR-003-provider-adapter.md) — patrón adapter para providers

## Relacionado

- [Overview del proyecto](project-overview.md)
- [Estado actual](current-state.md)
- [Backend engineering](../engineering/backend.md)
- [Reference](../reference/README.md)
