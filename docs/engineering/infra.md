# Infra

**Estado:** vivo  
**Última revisión:** 2026-05-11  
**Fuente de verdad:** no  
**Área:** engineering

## Resumen

La documentación viva confirma una capa `infra/` con soporte para despliegue, workflows y manifiestos, pero no existe una sola doc consolidada que describa todo el stack operacional.

## Contenido principal

- La raíz del repo y `docs/overview/current-state.md` mencionan:
  - Docker local
  - CI/CD base
  - manifiestos Kubernetes
- Runbooks operativos detectados:
  - [Canary y rollback](../runbooks/runbook-canary-rollback.md)
  - [OOM](../runbooks/runbook-oom.md)

## Nota

> TODO: completar con una fuente consolidada si más adelante se documenta formalmente el flujo de despliegue y los entornos.

## Relacionado

- [Observabilidad](observability.md)
- [README raíz](../../README.md)
