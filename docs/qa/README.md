# QA

**Estado:** vivo  
**�ltima revisi�n:** 2026-08-01
**Fuente de verdad:** s�  
**�rea:** QA

`docs/qa/` conserva solo material vivo o reutilizable. El hist�rico de ciclos cerrados est� en [archive/qa-reports](../archive/qa-reports/).

## Qu� vive aqu�

- `acceptance-checklists/`: checklists reutilizables.
- `visual/`: capturas y activos visuales activos.
- `reports/`: reportes ligeros y resultados activos que siguen siendo �tiles.
- `evidence/`: evidencia adicional referenciada.
- `traceability-matrix.md`: matriz base de trazabilidad.

## Lectura recomendada

- [Frontend PR checklist](acceptance-checklists/frontend-pr-checklist.md)
- [Matriz QA por �rea](qa-command-matrix.md)
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

## Qu� no debe quedarse aqu�

- actas de un ciclo cerrado;
- reportes fechados duplicados;
- prompts de herramientas;
- dumps o logs masivos no referenciados.

## Hist�rico

- ciclos cerrados y readiness: [../archive/qa-reports/](../archive/qa-reports/)
