Status: canonical
Scope: maintainer orientation and repo re-entry
Last reviewed: 2026-06-29
Canonical source: docs/overview/repo-map.md
Related: docs/INDICE_UNICO.md, README.md

---
# Repo Map

## Código

- `backend/`: API, dominio, infraestructura y tests del backend.
- `frontend/`: aplicación Next.js, módulos de producto, estilos y tests frontend.
- `infra/`: configuracion de despliegue (cloudflare-tunnel.example.yml), workflows y manifests.
- `scripts/`: utilidades de soporte del repo (túneles, publicación, sanitización).
- `testsprite_tests/`: tests y artefactos del flujo Testsprite; los reportes documentales se han archivado en `docs/archive/tooling/`.
- `skills/`: skills reutilizables para agentes (viru-tracker-context, taste-skill, remodex, phase1-mvp).

## Directorios clave del frontend

- `frontend/src/app/`: rutas App Router de Next.js.
- `frontend/src/modules/`: módulos de producto (quick-search, watchlist, door-to-door, hotels, dashboard, alerts, shared).
- `frontend/src/components/`: componentes UI compartidos.
- `frontend/src/icons/`: iconos SVG corporativos como componentes React (RyanairIcon, WizzAirIcon, GenericProviderIcon).
- `frontend/src/styles/`: estilos globales y CSS modules.
- `frontend/src/i18n/`: archivos de internacionalización por dominio.

## Documentación viva

- `docs/overview/`: punto de reentrada y estado actual.
- `docs/adr/`: decisiones arquitectónicas (3 ADRs vigentes).
- `docs/reference/`: contratos API, feature flags y referencias técnicas activas.
- `docs/specs/`: specs activas de producto, UI y contenido.
- `docs/ui/`: sistema visual, contrato UI y guía estética (Aviation Dark-Luxe).
- `docs/product/`: resúmenes funcionales por área de producto.
- `docs/engineering/`: resúmenes técnicos por capa.
- `docs/runbooks/`: operación y respuesta ante incidentes.
- `docs/qa/`: checklists, reportes y referencias QA reutilizables.
- `docs/plans/`: planes activos y completados.
- `HISTORY.md`: historial resumido de cambios relevantes.

## Archivo histórico

- `docs/archive/fases/`: originales `.docx` y transcripciones de las fases 1-10.
- `docs/archive/qa/`: evidencia de QA por fecha y por iniciativa.
- `docs/archive/prompts/`: prompts operativos antiguos.
- `docs/archive/tooling/`: reportes de Testsprite y salidas visuales.
- `docs/archive/root-legacy/`: restos históricos que antes vivían en la raíz.
- `docs/archive/duplicated/`: copias de seguridad de documentos reubicados.

## Qué esperar en la raíz

La raíz debería quedar ligera: `README.md`, `AGENTS.md`, scripts de arranque y configuración del repo. Las specs y documentación de trabajo ya no deberían vivir ahí.



