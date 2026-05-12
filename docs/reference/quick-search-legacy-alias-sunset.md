Status: reference
Scope: quick-search contract transition policy
Last reviewed: 2026-05-12
Canonical source: docs/reference/quick-search-legacy-alias-sunset.md
Related: docs/reference/backend/quick-search-contract.md, docs/reference/feature-flags.md, docs/runbooks/runbook-route-canonicalization.md

---
# Quick Search Legacy Alias Sunset

## Objetivo

Definir cómo retirar aliases legacy de quick search sin romper clientes activos.

## Reglas

1. Mantener compatibilidad temporal de aliases solo durante ventana de transición explícita.
2. Priorizar payload canónico (`origin`, `destination`, `travel`, `constraints`, `execution`) en backend y frontend.
3. Cualquier alias debe emitir señal operativa (warning estructurado + `query_trace_id`).
4. No eliminar aliases en un solo paso: usar rollout por cohortes con feature flags.

## Plan de transición

1. Fase A: medir uso de aliases en logs y dashboards de observabilidad.
2. Fase B: marcar aliases como deprecated en contrato y exponer warning estable.
3. Fase C: bloquear aliases en entornos internos/canary.
4. Fase D: retirar aliases en producción cuando el uso residual sea cero o aceptado formalmente.

## Criterio de retiro

1. Sin uso residual relevante durante una ventana mínima de observación acordada.
2. Pruebas de contrato y regresión en verde con payload canónico.
3. Documentación de contrato y checklist de aceptación actualizados.
