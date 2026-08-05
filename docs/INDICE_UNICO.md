# Índice Único de Documentación

**Estado:** vivo
**Última revisión:** 2026-08-04
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
- [Community Pricing contract](reference/backend/community-pricing-contract.md)
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
- [Community Pricing contract](reference/backend/community-pricing-contract.md)
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
- [Community Pricing contract](reference/backend/community-pricing-contract.md)
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
- [Plan maestro de `/hoteles` — tracker hotelero preferido](plans/2026-08-04-hoteles-master-roadmap.md)
- [Visión de producto H01 de `/hoteles`](product/hoteles-product-vision-h01.md)
- [Benchmark H02 de Travel Price Drops Hotels](benchmarks/2026-08-04-travelpricedrops-hotels-h02.md)
- [Arquitectura de información H03 de `/hoteles`](product/hoteles-information-architecture-h03.md)
- [Métricas y eventos H04 de `/hoteles`](product/hoteles-metrics-events-h04.md)
- [Freshness, procedencia y confidence H05 de hoteles](reference/backend/hoteles-freshness-provenance-confidence-h05.md)
- [Contrato provider-neutral H06 de hoteles](reference/backend/hoteles-provider-neutral-contract-h06.md)
- [Auditoría Makcorps H07 de hoteles](reference/backend/hoteles-makcorps-audit-h07.md)
- [Matriz y onboarding H08 de providers hoteleros](reference/backend/hoteles-provider-onboarding-h08.md)
- [Gateway y sweeps H09 de hoteles](reference/backend/hoteles-sweep-gateway-h09.md)
- [Modelo de estancia y oferta H10 de hoteles](reference/backend/hoteles-stay-offer-model-h10.md)
- [Migración de datos H11 de hoteles](reference/backend/hoteles-data-migration-h11.md)
- [Resolución de destino H12 de hoteles](reference/backend/hoteles-destination-resolution-h12.md)
- [Formulario y URL state H13 de hoteles](reference/backend/hoteles-search-form-h13.md)
- [Filtros y ranking H14 de hoteles](reference/backend/hoteles-filters-ranking-h14.md)
- [Resultados y paginación H15 de hoteles](reference/backend/hoteles-results-pagination-h15.md)
- [Result cards H16 de hoteles](reference/frontend/hoteles-result-cards-h16.md)
- [Ranking y explicabilidad H17 de hoteles](reference/backend/hoteles-ranking-explainability-h17.md)
- [Detalle y navegación H18 de hoteles](reference/frontend/hoteles-detail-navigation-h18.md)
- [Precio total, noches y fees H19 de hoteles](reference/backend/hoteles-price-total-fees-h19.md)
- [Comparación de providers y hoteles cercanos H20](reference/backend/hoteles-provider-comparison-nearby-h20.md)
- [Matriz de estados y recuperación H21 de hoteles](reference/frontend/hoteles-state-matrix-h21.md)
- [Favorito frente a tracking H22 de hoteles](reference/backend/hoteles-favorite-vs-tracking-h22.md)
- [Tracking desde oferta real H23 de hoteles](reference/backend/hoteles-real-offer-tracking-h23.md)
- [Histórico y curva de precio H24 de hoteles](reference/backend/hoteles-price-history-curve-h24.md)
- [Freshness, confidence y acciones H25 de hoteles](reference/backend/hoteles-freshness-confidence-actions-h25.md)
- [Reglas, baselines y dedupe H26 de hoteles](reference/backend/hoteles-alert-rules-dedupe-h26.md)
- [Inbox privado, ownership y deep links H27 de hoteles](reference/backend/hoteles-private-inbox-deeplinks-h27.md)
- [Delivery, reintentos y preferencias H28 de hoteles](reference/backend/hoteles-delivery-retries-preferences-h28.md)
- [Lifecycle H29 de seguimientos hoteleros](reference/backend/hoteles-lifecycle-pause-edit-expire-delete-h29.md)
- [Calendario y fechas flexibles H30 de hoteles](reference/backend/hoteles-flexible-dates-calendar-h30.md)
- [Dirección visual y estados H31 de hoteles](reference/frontend/hoteles-visual-direction-states-h31.md)
- [Responsive, overflow y CTAs accesibles H32 de hoteles](reference/frontend/hoteles-responsive-accessible-ctas-h32.md)
- [Auditoría WCAG 2.2 AA H33 de hoteles](reference/frontend/hoteles-wcag-accessibility-audit-h33.md)
- [Localización, fechas, monedas y timezones H34 de hoteles](reference/frontend/hoteles-localization-dates-currency-timezones-h34.md)
- [Legal, privacidad, disclosure y deeplinks H35 de hoteles](reference/backend/hoteles-legal-privacy-disclosure-deeplinks-h35.md)
- [Rendimiento frontend y Web Vitals H36 de hoteles](reference/frontend/hoteles-performance-web-vitals-h36.md)
- [Benchmark, rate limits, locks y coste máximo H37 de hoteles](reference/backend/hoteles-benchmark-rate-limits-locks-cost-h37.md)
- [Ownership, secretos, SSRF y abuso H38 de hoteles](reference/backend/hoteles-ownership-secrets-ssrf-abuse-h38.md)
- [Pirámide de tests y huecos H39 de hoteles](reference/backend/hoteles-test-pyramid-gaps-h39.md)
- [QA visual, manual y cross-browser H40 de hoteles](reference/frontend/hoteles-visual-manual-crossbrowser-qa-h40.md)
- [Observabilidad end-to-end H41 de hoteles](reference/backend/hoteles-observability-e2e-h41.md)
- [Incidentes y recovery H42 de hoteles](runbooks/hoteles-incidentes-recovery-h42.md)
- [Flags, canary y kill switches H43 de hoteles](reference/backend/hoteles-flags-canary-killswitch-h43.md)
- [Seed, demo y fallos reproducibles H44 de hoteles](reference/backend/hoteles-seed-demo-fallos-h44.md)
- [Release, smoke, canary y rollback H45 de hoteles](reference/backend/hoteles-release-canary-smoke-rollback-h45.md)
- [Primera victoria sin tutorial largo H46 de hoteles](reference/frontend/hoteles-primera-victoria-h46.md)
- [Re-engagement y “Mis hoteles” H47](reference/frontend/hoteles-mis-hoteles-reengagement-h47.md)
- [Búsquedas guardadas y compartibles H48](reference/backend/hoteles-busquedas-guardadas-compartibles-h48.md)
- [Personalización prudente H49 de hoteles](reference/frontend/hoteles-personalizacion-prudente-h49.md)
- [Monetización, afiliación y atribución H50 de hoteles](reference/backend/hoteles-monetizacion-afiliacion-atribucion-h50.md)
- [Experimentos con hipótesis y guardrails H51 de hoteles](reference/frontend/hoteles-experimentos-hipotesis-guardrails-h51.md)
- [Feedback y correcciones de confianza H52 de hoteles](reference/frontend/hoteles-feedback-correcciones-confianza-h52.md)
- [Calidad de catálogo, matching y deduplicación H53 de hoteles](reference/backend/hoteles-catalogo-matching-deduplicacion-h53.md)
- [Mercados hoteleros: criterios de entrada y salida H54](reference/backend/hoteles-mercados-entrada-salida-h54.md)
- [Continuidad, backup/restore y disaster recovery H55](reference/backend/hoteles-continuidad-disaster-recovery-h55.md)
- [Revisión anual, providers, costes y siguiente roadmap H56](reference/backend/hoteles-revision-anual-roadmap-h56.md)
- [Plantilla H56 de revisión anual](qa/hoteles-h56-annual-review-template.md)
- [Plantilla H56 de DecisionRecord](qa/hoteles-h56-decision-record-template.md)
- [Baseline local H56 2026-08-05](qa/hoteles-h56-annual-review-2026-08-05.md)
- [DecisionRecord inicial H56 2026-08-05](qa/hoteles-h56-decision-record-2026-08-05.md)
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
- [ADR-006](adr/ADR-006-zero-cost-operational-provider-fallback.md)

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
- [QA fallback operacional sin coste](qa/reports/2026-07-21-zero-cost-live-provider-fallback.md)
- [QA precio comparable en Quick Search y Watchlist](qa/reports/2026-07-28-fare-comparison-manual-qa.md)
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
