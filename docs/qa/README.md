# QA

**Estado:** vivo  
**Última revisión:** 2026-05-11  
**Fuente de verdad:** sí  
**Área:** QA

`docs/qa/` conserva solo material vivo o reutilizable. El histórico de ciclos cerrados está en [archive/qa](../archive/qa/README.md).

## Qué vive aquí

- `acceptance-checklists/`: checklists reutilizables.
- `visual/`: capturas y activos visuales activos.
- `reports/`: reportes ligeros y resultados activos que siguen siendo útiles.
- `evidence/`: evidencia adicional referenciada.
- `traceability-matrix.md`: matriz base de trazabilidad.

## Lectura recomendada

- [Frontend PR checklist](acceptance-checklists/frontend-pr-checklist.md)
- [Traceability matrix](traceability-matrix.md)
- [Runbook UI captures](../runbooks/runbook-ui-captures.md)

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

- ciclos cerrados y readiness: [../archive/qa/README.md](../archive/qa/README.md)
- reportes de tooling: [../archive/tooling/README.md](../archive/tooling/README.md)
