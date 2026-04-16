Status: canonical
Scope: maintainer orientation and repo re-entry
Last reviewed: 2026-04-15
Canonical source: docs/overview/repo-map.md
Related: docs/INDICE_UNICO.md, README.md

---
# Repo Map

## Código

- `backend/`: API, dominio, infraestructura y tests del backend.
- `frontend/`: aplicación Next.js, módulos de producto, estilos y tests frontend.
- `infra/`: Docker, workflows y manifests.
- `scripts/`: utilidades de soporte del repo.
- `testsprite_tests/`: tests y artefactos del flujo Testsprite; los reportes documentales se han archivado en `docs/archive/tooling/`.

## Documentación viva

- `docs/overview/`: punto de reentrada.
- `docs/adr/`: decisiones arquitectónicas.
- `docs/reference/`: contratos, flags y referencias técnicas activas.
- `docs/specs/`: specs activas de producto, UI y contenido.
- `docs/ui/`: sistema visual, contrato UI y guía estética.
- `docs/runbooks/`: operación y respuesta ante incidentes.
- `docs/qa/`: checklists y referencias QA reutilizables.
- `docs/checks/`: comprobaciones manuales acotadas.
- `docs/plans/`: diseños y planes históricos todavía útiles como referencia.
- `docs/changelog/`: consolidado de cambios.

## Archivo histórico

- `docs/archive/fases/`: originales `.docx` y transcripciones de las fases 1-10.
- `docs/archive/qa/`: evidencia de QA por fecha y por iniciativa.
- `docs/archive/prompts/`: prompts operativos antiguos.
- `docs/archive/tooling/`: reportes de Testsprite y salidas visuales.
- `docs/archive/root-legacy/`: restos históricos que antes vivían en la raíz.

## Qué esperar en la raíz

La raíz debería quedar ligera: `README.md`, `AGENTS.md`, scripts de arranque y configuración del repo. Las specs y documentación de trabajo ya no deberían vivir ahí.




