# Índice Único de Documentación

**Estado:** vivo
**Última revisión:** 2026-07-14
**Fuente de verdad:** sí
**Área:** documentación

## Por rol

### Nuevo desarrollador

- [README raíz](../README.md)
- [Documentación de `docs/`](README.md)
- [Overview del proyecto](overview/project-overview.md)
- [Estado actual](overview/current-state.md)
- [Mapa del repo](overview/repo-map.md)

### Backend

- [Backend](engineering/backend.md)
- [Reference](reference/README.md)
- [Quick Search contract](reference/backend/quick-search-contract.md)
- [Live flight tracking contract](reference/backend/live-flight-tracking-contract.md)
- [Provider integration guide](reference/backend/provider-integration-guide.md)
- [Feature flags y activacion por entorno](reference/feature-flags.md)
- [Runbook live flight tracking](runbooks/runbook-live-flight-tracking.md)
- [Door-to-door API contract](reference/backend/door-to-door-contract.md)
- [Notifications contract](reference/backend/notifications-contract.md)
- [Quick Search acceptance checklist](reference/backend/quick-search-acceptance-checklist.md)
- [Quick Search legacy alias sunset](reference/quick-search-legacy-alias-sunset.md)

### Frontend

- [Frontend](engineering/frontend.md)
- [UI System](ui/UI_SYSTEM_V1.md)
- [UI Contract](ui/UI_CONTRACT_V1.md)
- [Guia de lenguaje visible humanizado](reference/ui-visible-language-guide.md)
- [Estética UI (dark + light)](ui/estetica.md)
- [Specs activas](specs/README.md)

### Producto

- [Dashboard](product/dashboard.md)
- [Quick Search](product/quick-search.md)
- [Watchlist](product/watchlist.md)
- [Puerta a puerta](product/door-to-door.md)
- [Centro de notificaciones persistente](product/notifications.md)
- [Product language map](reference/product-language-map.md)
- [Guia de lenguaje visible humanizado](reference/ui-visible-language-guide.md)
- [Policies Page](product/policies-page.md)

### QA

- [README QA](qa/README.md)
- [Frontend PR checklist](qa/acceptance-checklists/frontend-pr-checklist.md)
- [Matriz QA por area](qa/qa-command-matrix.md)
- [Fase 0 limpieza conceptual](qa/fase-0-limpieza-conceptual-checklist.md)
- [Cierre pendiente de `/hoteles`](qa/hotels-pending-closeout.md)
- [Traceability matrix](qa/traceability-matrix.md)
- [TestSprite catalog](qa/testsprite/testsprite-catalog.md)
- [Auditoría de paleta dual (archivada)](archive/qa-visual/color-palette-audit.md)

### DevOps

- [Infra](engineering/infra.md)
- [Observabilidad](engineering/observability.md)
- [Feature flags y activacion por entorno](reference/feature-flags.md)
- [Runbooks](runbooks/)
- [Archive QA reports](archive/qa-reports/)

### Agente IA / Codex

- [AGENTS.md](../AGENTS.md)
- [Design System para agentes](../DESIGN.md)
- [Codex operating contract](reference/codex-operating-contract.md)
- [Prompts y contexto IA](prompts/README.md)
- [Skill Viru Air UI](../.codex/skills/viru-air-ui/SKILL.md)
- [Skill Taste Frontend](../.codex/skills/taste-skill/SKILL.md)
- [Inventario documental](DOCS_INVENTORY.md)
- [HISTORY.md](../HISTORY.md)

## Por área

### Overview

- [Documentación de `docs/`](README.md)
- [Overview del proyecto](overview/project-overview.md)
- [Estado actual](overview/current-state.md)
- [Mapa del repo](overview/repo-map.md)
- [Resumen de arquitectura](overview/architecture-summary.md)

### Product

- [Dashboard](product/dashboard.md)
- [Quick Search](product/quick-search.md)
- [Watchlist](product/watchlist.md)
- [Puerta a puerta](product/door-to-door.md)
- [Centro de notificaciones persistente](product/notifications.md)
- [Policies Page](product/policies-page.md)

### Engineering

- [Backend](engineering/backend.md)
- [Frontend](engineering/frontend.md)
- [Base de datos](engineering/database.md)
- [Testing y QA](engineering/testing.md)
- [Infra](engineering/infra.md)
- [Seguridad](engineering/security.md)
- [Observabilidad](engineering/observability.md)

### Runbooks

- [Runbooks operativos](runbooks/)
- [Runbook de estabilización watchlist + quick-search](runbooks/runbook-watchlist-quick-search-stabilization.md)
- [Runbook live flight tracking desde Watchlist](runbooks/runbook-live-flight-tracking.md)
- [Runbook QA de puerta a puerta](runbooks/runbook-puerta-a-puerta-qa.md)
- [Publicacion web por tuneles](runbooks/runbook-public-tunnels.md)
- [Sweeps hoteleros](runbooks/hotels-sweeps.md)

### Plans

- [Planes de trabajo](plans/README.md)
- [Plan progresivo de 20 fases — Quick Search + Ajustes activos](plans/active/2026-07-01-plan-20-fases-quick-search-ajustes.md)
- [Quick Search ajustes — Fase 1 inventario](plans/active/2026-07-01-quick-search-ajustes-fase-01-inventario.md)
- [Live flight tracking a partir de Watchlist (completado)](archive/plans/2026-07-21-live-flight-tracking-watchlist.md)
- [Auditoria cache Fare Memory F21](plans/2026-06-14-fare-memory-cache-audit.md)

### ADRs

- [ADR-001](adr/ADR-001-monolito-modular.md)
- [ADR-002](adr/ADR-002-stack-base.md)
- [ADR-003](adr/ADR-003-provider-adapter.md)
- [ADR-004](adr/ADR-004-flight-tracking-hub.md)
- [ADR-005](adr/ADR-005-live-operational-flight-tracking.md)

### Specs

- [Specs activas](specs/README.md)
- [Phase 1 Codex MVP](specs/phase1-codex.md)
- [Hotels Intelligence MVP](specs/hotels-intelligence-mvp.md)
- [Viru Fare Memory](specs/viru-fare-memory.md)
- [Hoteles post-cierre Fases A-E](plans/2026-06-04-hoteles-correcciones-post-cierre.md)

### QA

- [README QA](qa/README.md)
- [Cierre pendiente de `/hoteles`](qa/hotels-pending-closeout.md)
- [Matriz QA por area](qa/qa-command-matrix.md)
- [Evidencia Live flight tracking desde Watchlist](qa/reports/2026-07-21-watchlist-live-flight-tracking.json)
- [Visual QA (archivado)](archive/qa-visual/)
- [Auditoría de paleta dual (archivada)](archive/qa-visual/color-palette-audit.md)
- [Reportes QA (archivados)](archive/qa-reports/)

### Prompts

- [Prompts y contexto IA](prompts/README.md)
- [Roadmap de viaje 50 fases](prompts/codex-travel-roadmap-50-fases.md)
- [Design System para agentes](../DESIGN.md)
- [Skill Viru Air UI](../.codex/skills/viru-air-ui/SKILL.md)
- [Skill Taste Frontend](../.codex/skills/taste-skill/SKILL.md)
- [Prompts legacy](prompts/legacy/)

### Archive

- [Archive](archive/)
- [Planes archivados](archive/plans/)
- [QA evidence archivada](archive/qa-evidence/)
- [QA reports archivados](archive/qa-reports/)
- [QA visual archivada](archive/qa-visual/)
- [Reportes historicos](archive/reports/)
