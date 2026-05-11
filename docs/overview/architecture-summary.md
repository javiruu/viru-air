# Resumen de Arquitectura

**Estado:** vivo  
**Última revisión:** 2026-05-11  
**Fuente de verdad:** sí  
**Área:** overview

## Resumen

La arquitectura visible del repo es la de un monorepo con backend, frontend, infra y documentación consolidada. La fuente verificable para las decisiones base sigue estando en los ADRs y en la documentación técnica activa.

## Contenido principal

- Backend:
  - API bajo `backend/app/`
  - punto de entrada en `backend/app/main.py`
  - prefijo principal `/api/v1`
- Frontend:
  - aplicación Next.js en `frontend/`
  - contrato visual documentado en `docs/ui/`
- Infra:
  - composición local, workflows y manifiestos bajo `infra/`
- Operación:
  - runbooks en `docs/runbooks/`
- QA:
  - checklists y evidencia activa en `docs/qa/`

## Decisiones base

- [ADR-001](../adr/ADR-001-monolito-modular.md)
- [ADR-002](../adr/ADR-002-stack-base.md)
- [ADR-003](../adr/ADR-003-provider-adapter.md)

## Nota

> TODO: completar con más detalle si se consolida una fuente técnica única sobre base de datos, observabilidad e integraciones. Durante este saneamiento no se ha encontrado una sola fuente canónica suficiente para ampliar más sin deducir de más.

## Relacionado

- [Overview del proyecto](project-overview.md)
- [Estado actual](current-state.md)
- [Reference](../reference/README.md)
