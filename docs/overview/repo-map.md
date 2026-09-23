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
- `skills/`: skills reutilizables para agentes (viru-air-context, taste-skill; supabase* son symlinks a `.agents/skills/`).

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
- `DESIGN.md`: sistema visual, contrato creativo y guía estética (Aviation Warm-Luxe).
- `docs/product/`: resúmenes funcionales por área de producto.
- `docs/engineering/`: resúmenes técnicos por capa.
- `docs/runbooks/`: operación y respuesta ante incidentes.
- `docs/qa/`: checklists, reportes y referencias QA reutilizables (evidencia binaria solo de runs vigentes; los reruns históricos se purgaron el 2026-09-23).
- `docs/plans/`: planes activos y completados (los cerrados se archivan en `docs/archive/plans/`).

## Archivo histórico

- `docs/archive/qa-reports/`: reportes QA de ciclos cerrados.
- `docs/archive/plans/`, `docs/archive/reports/`, `docs/archive/migration-era/`: material histórico.
- Nota: las carpetas pesadas (`qa-visual`, `qa-evidence`, `qa-screenshots`, `qa-snapshots`, `duplicated`, `fases`, `prompts`, `old-reports`, `extracted-txt`) se purgaron el 2026-09-23 con aprobación del usuario.

## Qué esperar en la raíz

La raíz debería quedar ligera: `README.md`, `AGENTS.md`, scripts de arranque y configuración del repo. Las specs y documentación de trabajo ya no deberían vivir ahí.


