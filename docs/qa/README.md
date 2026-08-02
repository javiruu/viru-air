# QA

**Estado:** vivo  
**Última revisión:** 2026-08-01
**Fuente de verdad:** sí  
**Área:** QA

`docs/qa/` conserva solo material vivo o reutilizable. El histórico de ciclos cerrados está en [archive/qa-reports](../archive/qa-reports/) y en las carpetas `docs/archive/qa-*`.

## Qué vive aquí

- `acceptance-checklists/`: checklists reutilizables.
- `visual/`: capturas y activos visuales activos.
- `reports/`: reportes ligeros y resultados activos que siguen siendo útiles.
- `evidence/`: evidencia adicional referenciada.
- `traceability-matrix.md`: matriz base de trazabilidad.

## Lectura recomendada

- [Frontend PR checklist](acceptance-checklists/frontend-pr-checklist.md)
- [Matriz QA por área](qa-command-matrix.md)
- [Traceability matrix](traceability-matrix.md)
- [Runbook UI captures](../runbooks/runbook-ui-captures.md)
- [Live flight tracking desde Watchlist - resultado browser](reports/2026-07-21-watchlist-live-flight-tracking.json)
- [Inteligencia comunitaria de rutas - QA full-stack](reports/2026-08-01-community-route-intelligence.md)

## Politica de validacion visual

- Para cambios visuales/UI, la validacion final depende de revision manual del usuario en navegador real.
- La IA debe pedir siempre:
  - ruta/pagina a revisar;
  - interaccion exacta;
  - resultado esperado;
  - feedback observado.
- Build/tests/lint/typecheck de terminal siguen siendo responsabilidad de la IA.

## Qué no debe quedarse aquí

- actas de un ciclo cerrado;
- reportes fechados duplicados;
- prompts de herramientas;
- dumps o logs masivos no referenciados.

## Histórico

- ciclos cerrados y readiness: [../archive/qa-reports/](../archive/qa-reports/)
- evidencias historicas: [../archive/qa-evidence/](../archive/qa-evidence/)
