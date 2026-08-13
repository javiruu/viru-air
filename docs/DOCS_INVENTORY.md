# Inventario documental

**Estado:** vivo
**Ultima revision:** 2026-08-04
**Fuente de verdad:** si
**Area:** documentacion

## Resumen

Inventario completo de documentos `.md` y `.txt` relevantes del repositorio tras el saneamiento documental. Excluye dependencias, cach?s, builds, entornos virtuales, `_publish_repo` y otras salidas generadas masivas.

## Actualización manual 2026-08-13 (retirada segura de legado)

Entrada viva agregada:

- `docs/plans/2026-08-13-dead-code-legacy-retirement.md`

Motivo:

- Define la limpieza interna inmediata, la telemetría agregada y la retirada a 30 días de compatibilidades públicas y datos hoteleros persistidos.

## Actualizacion manual 2026-08-13 (planes de cierre local de `/hoteles`)

Entradas vivas agregadas:

- `docs/plans/2026-08-08-h36-performance-baseline.md`
- `docs/plans/2026-08-08-hoteles-detail-intent-design.md`
- `docs/plans/2026-08-08-hoteles-detail-intent-implementation.md`
- `docs/plans/2026-08-09-hotel-demo-seed-plan.md`
- `docs/plans/2026-08-09-hotel-mock-canary-design.md`
- `docs/plans/2026-08-09-hotel-mock-canary-plan.md`
- `docs/plans/2026-08-09-hotel-provider-latency-contract-plan.md`
- `docs/plans/2026-08-09-hotel-provider-latency-persistence-design.md`
- `docs/plans/2026-08-09-hotel-provider-latency-persistence-plan.md`
- `docs/plans/2026-08-09-hoteles-delivery-design.md`
- `docs/plans/2026-08-09-hoteles-delivery-implementation.md`
- `docs/plans/2026-08-09-hoteles-observability-dashboard-plan.md`
- `docs/plans/2026-08-09-hoteles-observability-metrics-design.md`
- `docs/plans/2026-08-10-h44-fault-matrix-dry-run-design.md`
- `docs/plans/2026-08-10-h44-fault-matrix-dry-run-plan.md`
- `docs/plans/2026-08-10-h44-revalidation-fault-profiles-plan.md`
- `docs/plans/2026-08-10-h48-saved-hotel-searches.md`
- `docs/plans/2026-08-10-hoteles-auditoria-checklist-completa.md`
- `docs/plans/2026-08-10-hoteles-local-backlog-closeout-plan.md`
- `docs/plans/2026-08-10-hotels-local-closeout-implementation.md`

Motivo:

- Planes vivos de diseño, implementación y auditoría que acompañan los cierres locales de datos, tracking, observabilidad, delivery in-app, proveedores, rendimiento y QA de `/hoteles`.

## Actualizacion manual 2026-08-04 (cierre H00-H07 de `/hoteles`)

Entradas vivas agregadas:

- `docs/qa/reports/2026-08-04-hoteles-h00-baseline.md`
- `docs/product/hoteles-product-vision-h01.md`
- `docs/benchmarks/2026-08-04-travelpricedrops-hotels-h02.md`
- `docs/product/hoteles-information-architecture-h03.md`
- `docs/product/hoteles-metrics-events-h04.md`
- `docs/reference/backend/hoteles-freshness-provenance-confidence-h05.md`
- `docs/reference/backend/hoteles-provider-neutral-contract-h06.md`
- `docs/reference/backend/hoteles-makcorps-audit-h07.md`

Motivo:

- Cierre documental de H00-H07 del plan maestro: baseline reproducible, visión/personas/jobs/métricas, benchmark fechado, arquitectura de información/wireflows, contratos de medición, calidad de datos, frontera provider-neutral, auditoría Makcorps y decisión condicionada de continuidad.

## Actualizacion manual 2026-08-04 (plan maestro de `/hoteles`)

Entradas vivas agregadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`

Motivo:

- Mega plan de producto y ejecución para evolucionar `/hoteles` desde su base técnica actual hasta un tracker hotelero confiable, con fases separadas de datos, providers, búsqueda, tracking, alertas, UX, QA, operación, lanzamiento y crecimiento.

## Actualizacion manual 2026-08-05 (contrato H40 QA visual hotelero)

Entradas vivas agregadas:

- `docs/reference/frontend/hoteles-visual-manual-crossbrowser-qa-h40.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H40 de QA browser, visual/manual, responsive, dark/light, cross-browser, foco/teclado, consola/red, screenshots, evidencia histórica y aprobación humana.

## Actualizacion manual 2026-08-05 (contrato H39 tests hoteleros)

Entradas vivas agregadas:

- `docs/reference/backend/hoteles-test-pyramid-gaps-h39.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Estrategia H39 de pirámide de tests, cobertura real por capa, huecos P0/P1/P2, fixtures, provider contract/canary, browser, seguridad, rendimiento y gates U/I/C/B/S/P/R.

## Actualizacion manual 2026-08-05 (contrato H38 seguridad hotelera)

Entradas vivas agregadas:

- `docs/reference/backend/hoteles-ownership-secrets-ssrf-abuse-h38.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H38 de ownership relacional, BOLA/IDOR, secretos, redaction, SSRF, open redirect, deeplinks, egress, abuso, límites y gates de seguridad.

## Actualizacion manual 2026-08-05 (contrato H37 benchmark y costes hoteleros)

Entradas vivas agregadas:

- `docs/reference/backend/hoteles-benchmark-rate-limits-locks-cost-h37.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H37 de benchmark fixture/canary/field, rate limits, ledger de presupuesto, locks/leases, singleflight, retries, circuit breaker, coste desconocido, redaction y gates de capacidad.

## Actualizacion manual 2026-08-05 (contrato H36 rendimiento hotelero)

Entradas vivas agregadas:

- `docs/reference/frontend/hoteles-performance-web-vitals-h36.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H36 de presupuesto de rendimiento, Web Vitals, primer resultado útil, cancelación/latest-wins, estabilidad visual, assets, móvil, red degradada y gates lab/field.

## Actualizacion manual 2026-08-05 (contrato H34 localizacion hotelera)

Entradas vivas agregadas:

- `docs/reference/frontend/hoteles-localization-dates-currency-timezones-h34.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H34 de i18n ES/EN, placeholders, pluralización, fechas civiles, timestamps, monedas de origen, timezones, copy provider y gates de QA.

## Actualizacion manual 2026-08-05 (contrato H33 accesibilidad hotelera)

Entradas vivas agregadas:

- `docs/reference/frontend/hoteles-wcag-accessibility-audit-h33.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H33 de auditoría WCAG 2.2 AA para búsqueda, autocomplete, resultados, tracking, alertas, estados, foco, contraste, zoom, reduced motion, prioridades P0/P1/P2 y gate de evidencia.

## Actualizacion manual 2026-08-05 (contrato H32 responsive hotelero)

Entradas vivas agregadas:

- `docs/reference/frontend/hoteles-responsive-accessible-ctas-h32.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H32 de layouts por viewport, overflow, zoom, CTAs de 48 px, teclado, foco, estados móviles, reduced motion y evidencia browser.

## Actualizacion manual 2026-08-05 (contrato H31 visual hotelero)

Entradas vivas agregadas:

- `docs/reference/frontend/hoteles-visual-direction-states-h31.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H31 de dirección visual específica de hoteles, jerarquía de búsqueda y decisión, estados, responsive, motion, accesibilidad, i18n y handoff a implementación/QA.

## Actualizacion manual 2026-08-05 (contrato H30 de calendario hotelero)

Entradas vivas agregadas:

- `docs/reference/backend/hoteles-flexible-dates-calendar-h30.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H30 para búsqueda exacta y flexible, modos temporales, fechas efectivas, noches, capabilities, coste, cache, ranking, URL, tracking, rollout y gates de provider.

## Actualizacion manual 2026-08-05 (contrato H29 de lifecycle hotelero)

Entradas vivas agregadas:

- `docs/reference/backend/hoteles-lifecycle-pause-edit-expire-delete-h29.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato de lifecycle seguro para pausa, reanudación, edición, expiración por checkout/policy, archivado, eliminación, ownership, cascadas, retención, idempotencia y migración V1→V2.

## Actualizacion manual 2026-08-04 (persistencia de tendencias comunitarias e inbox)

Entradas vivas agregadas:

- `docs/plans/2026-08-04-community-trending-persistence-inbox.md`

Motivo:

- Mega plan implementado y verificado para persistir snapshots diarios de tendencias comunitarias, corregir ownership/read-state del inbox y verificar compatibilidad, retención, rollback y privacidad.

## Actualizacion manual 2026-07-28 (Community Pricing)

Entradas vivas agregadas:

- `docs/reference/backend/community-pricing-contract.md`

Entradas vivas actualizadas:

- `docs/product/watchlist.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`
- `HISTORY.md`

## Actualizacion manual 2026-07-12 (tokens de seleccion global)

Entradas vivas actualizadas:

- `docs/ui/UI_SYSTEM_V1.md`
- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-07-12 (reparacion enlaces centrales F60)

Entradas vivas actualizadas:

- `docs/README.md`
- `docs/INDICE_UNICO.md`
- `docs/qa/README.md`
- `docs/prompts/README.md`
- `docs/DOCS_INVENTORY.md`
- `HISTORY.md`

## Actualizacion manual 2026-07-11 (cierre Fare Memory F60)

Entradas vivas actualizadas:

- `docs/reference/feature-flags.md`
- `docs/reference/README.md`
- `docs/INDICE_UNICO.md`
- `docs/specs/viru-fare-memory.md`
- `docs/DOCS_INVENTORY.md`
- `HISTORY.md`

## Actualizacion manual 2026-07-09 (providers activos Quick Search)

Entradas vivas actualizadas:

- `docs/reference/backend/provider-integration-guide.md`
- `docs/DOCS_INVENTORY.md`
- `HISTORY.md`

## Actualizacion manual 2026-07-03 (centro de notificaciones persistente)

Entradas vivas agregadas:

- `docs/product/notifications.md`
- `docs/reference/backend/notifications-contract.md`

Entradas vivas actualizadas:

- `docs/product/notifications.md`
- `docs/reference/backend/notifications-contract.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`
- `HISTORY.md`

## Actualizacion manual 2026-07-01 (plan Quick Search ajustes activos)

Entradas vivas agregadas:

- `docs/plans/active/2026-07-01-plan-20-fases-quick-search-ajustes.md`
- `docs/plans/active/2026-07-01-quick-search-ajustes-fase-01-inventario.md`

Entradas vivas actualizadas:

- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-30 (Flight Tracking Hub)

Entradas vivas agregadas:

- `docs/adr/ADR-004-flight-tracking-hub.md`
- `docs/adr/ADR-005-live-operational-flight-tracking.md`

Entradas vivas actualizadas:

- `docs/INDICE_UNICO.md`
- `docs/engineering/backend.md`
- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-27 (saneamiento minimo para LazyCodex)

Entradas vivas actualizadas:

- `docs/reference/codex-operating-contract.md`
- `skills/viru-air-context/SKILL.md`
- `skills/viru-air-context/references/project-context.md`
- `docs/overview/repo-map.md`
- `frontend/AGENTS.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-13 (roadmap de viaje 50 fases)

Entradas vivas agregadas:

- `docs/prompts/codex-travel-roadmap-50-fases.md`

## Actualizacion manual 2026-06-14 (fare memory fases 21-25)

Entradas vivas agregadas:

- `docs/specs/viru-fare-memory.md`
- `docs/plans/2026-06-14-fare-memory-cache-audit.md`

Entradas vivas actualizadas:

- `docs/reference/backend/quick-search-contract.md`
- `docs/specs/README.md`
- `docs/INDICE_UNICO.md`

## Actualizacion manual 2026-06-23 (pivot de publicacion a tuneles)

Entradas vivas agregadas:

- `docs/runbooks/runbook-public-tunnels.md`
- `infra/cloudflare-tunnel.example.yml`
- `scripts/cloudflare-tunnel-start.ps1`
- `scripts/cloudflare-tunnel-status.ps1`
- `scripts/cloudflare-tunnel-stop.ps1`
- `scripts/cloudflare-tunnel-setup.ps1`
- `scripts/tailscale-funnel-start.ps1`
- `scripts/tailscale-funnel-status.ps1`
- `scripts/tailscale-funnel-stop.ps1`
- `scripts/tailscale-funnel-setup.ps1`
- `scripts/stable-tunnel-logs.ps1`

Entradas vivas actualizadas:

- `VIRU_PANEL.bat`
- `scripts/ops-common.ps1`
- `scripts/public-stable-start.ps1`
- `scripts/public-stable-status.ps1`
- `scripts/public-stable-stop.ps1`
- `docs/engineering/infra.md`
- `docs/overview/repo-map.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-23 (panel de publicacion unificado con dos URLs)

Entradas vivas actualizadas:

- `VIRU_PANEL.bat`
- `scripts/ops-common.ps1`
- `scripts/public-stable-start.ps1`
- `scripts/public-stable-status.ps1`
- `scripts/public-stable-stop.ps1`
- `scripts/stable-tunnel-logs.ps1`
- `docs/runbooks/runbook-public-tunnels.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Entradas vivas retiradas (sin referencia verificable activa):

- docs/runbooks/runbook-duckdns-public-domain.md
- `infra/Caddyfile`
- `infra/duckdns.env.example`
- infra/public-stable-network-profiles.json
- infra/public-stable-network-state.json
- `scripts/caddy-start.ps1`
- `scripts/caddy-status.ps1`
- `scripts/caddy-stop.ps1`
- `scripts/duckdns-disable.ps1`
- `scripts/duckdns-enable.ps1`
- `scripts/duckdns-status.ps1`
- `scripts/duckdns-update.ps1`
- `scripts/iniciar_viru_publico.ps1`
- `scripts/public-domain-preflight.ps1`
- `scripts/public-stable-profile-save.ps1`
- `scripts/public-stable-profiles.ps1`
- `scripts/public-stable-profiles-selftest.ps1`
- `scripts/public-temp-logs.ps1`
- `scripts/public-temp-start.ps1`
- `scripts/public-temp-status.ps1`
- `scripts/public-temp-stop.ps1`
- `scripts/setup-duckdns.ps1`

## Actualizacion manual 2026-06-15 (fare memory fase 26)

Entradas vivas actualizadas:

- `docs/specs/viru-fare-memory.md`

## Actualizacion manual 2026-06-15 (fare memory fase 27)

Entradas vivas actualizadas:

- `docs/reference/backend/quick-search-contract.md`

## Actualizacion manual 2026-06-15 (fare memory fase 28)

Entradas vivas actualizadas:

- `docs/reference/backend/quick-search-contract.md`
- `docs/specs/viru-fare-memory.md`

## Actualizacion manual 2026-06-22 (panel simplificado de publicacion)

Entradas vivas actualizadas:

- `docs/DOCS_INVENTORY.md`
- `docs/runbooks/runbook-public-tunnels.md`

## Actualizacion manual 2026-06-16 (humanizacion de lenguaje visible)

Entradas vivas agregadas:

- `docs/reference/ui-visible-language-guide.md`

Entradas vivas actualizadas:

- `docs/reference/product-language-map.md`
- `docs/ui/UI_CONTRACT_V1.md`
- `docs/INDICE_UNICO.md`
- `docs/specs/policies/policies-page-acceptance-checklist.md`
- `docs/specs/policies/policies-page-copy-deck-es.md`
- `docs/specs/policies/policies-page-rewrite.md`

## Actualizacion manual 2026-06-13 (fases 1-5 del roadmap)

Entradas vivas agregadas:

- `docs/qa/qa-command-matrix.md`

Entradas vivas actualizadas:

- `docs/prompts/codex-travel-roadmap-50-fases.md`
- `docs/reference/backend/quick-search-acceptance-checklist.md`
- `docs/specs/hotels-intelligence-mvp.md`
- `docs/qa/hotels-pending-closeout.md`
- `docs/reference/done-checklist.md`
- `docs/qa/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-05-11 (Fase 0)

Entradas vivas agregadas:

- `docs/overview/current-state.md`
- `docs/reference/product-language-map.md`
- `docs/qa/fase-0-limpieza-conceptual-checklist.md`

## Actualizacion manual 2026-05-12 (Fase 1)

Entradas vivas agregadas:

- `docs/specs/phase1-codex.md`
- `docs/reference/quick-search-legacy-alias-sunset.md`
- `skills/phase1-mvp/SKILL.md`
- `docs/archive/qa-reports/2026-05-12-fase1-cumplimiento.md`
- `backend/tests/unit/test_airports_endpoints.py`

## Actualizacion manual 2026-05-14 (design skill viru-air-ui)

Entradas vivas agregadas:

- `DESIGN.md`
- `.codex/skills/viru-air-ui/SKILL.md`
- `.codex/skills/viru-air-ui/references/product-context.md`
- `.codex/skills/viru-air-ui/references/visual-direction.md`
- `.codex/skills/viru-air-ui/references/qa-checklist.md`

## Actualizacion manual 2026-05-14 (install taste frontend skill)

Entradas vivas agregadas:

- `.codex/skills/taste-skill/SKILL.md`

## Actualizacion manual 2026-05-18 (aviation dual dark-light visual docs)

Entradas vivas actualizadas:

- `DESIGN.md`
- `docs/ui/estetica.md`
- `docs/ui/UI_SYSTEM_V1.md`
- `docs/ui/UI_CONTRACT_V1.md`
- `docs/archive/qa-visual/color-palette-audit.md`

## Actualizacion manual 2026-05-18 (warm identity rewrite for Viru)

Entradas vivas actualizadas:

- `AGENTS.md`
- `DESIGN.md`
- `docs/overview/project-overview.md`
- `docs/ui/estetica.md`
- `docs/ui/UI_SYSTEM_V1.md`
- `docs/ui/UI_CONTRACT_V1.md`
- `docs/archive/qa-visual/color-palette-audit.md`
- `.codex/skills/viru-air-ui/SKILL.md`
- `.codex/skills/viru-air-ui/references/product-context.md`
- `.codex/skills/viru-air-ui/references/visual-direction.md`
- `.codex/skills/viru-air-ui/references/qa-checklist.md`

## Actualizacion manual 2026-05-18 (warm cockpit direction hardening)

Entradas vivas actualizadas:

- `AGENTS.md`
- `DESIGN.md`
- `docs/ui/estetica.md`
- `docs/ui/UI_CONTRACT_V1.md`
- `docs/ui/UI_SYSTEM_V1.md`
- `docs/ui/UI_VISUAL_QA_CHECKLIST.md`
- `docs/archive/qa-visual/color-palette-audit.md`
- `.codex/skills/viru-air-ui/SKILL.md`
- `.codex/skills/viru-air-ui/references/visual-direction.md`
- `.codex/skills/viru-air-ui/references/qa-checklist.md`

## Actualizacion manual 2026-05-26 (provider-driven backend architecture)

Entradas vivas agregadas:

- `docs/reference/backend/provider-integration-guide.md`

Entradas vivas actualizadas:

- `docs/engineering/backend.md`
- `docs/reference/backend/quick-search-contract.md`
- `docs/runbooks/runbook-provider-degraded.md`
- `docs/adr/ADR-003-provider-adapter.md`
- `docs/INDICE_UNICO.md`

## Actualizacion manual 2026-06-01 (hotels intelligence mvp fase 0)

Entradas vivas agregadas:

- `docs/specs/hotels-intelligence-mvp.md`

Entradas vivas actualizadas:

- `docs/specs/README.md`
- `docs/INDICE_UNICO.md`

## Actualizacion manual 2026-06-03 (hotels closeout fase 0-2)

Entradas vivas agregadas:

- `docs/qa/hotels-pending-closeout.md`

Entradas vivas actualizadas:

- `docs/specs/hotels-intelligence-mvp.md`
- `docs/INDICE_UNICO.md`

## Actualizacion manual 2026-06-03 (hotels closeout fases 7 y 8)

Entradas vivas agregadas:

- `docs/runbooks/hotels-sweeps.md`

Entradas vivas actualizadas:

- `docs/INDICE_UNICO.md`
- `docs/qa/hotels-pending-closeout.md`
- `docs/specs/hotels-intelligence-mvp.md`

## Actualizacion manual 2026-06-04 (duckdns public domain rewrite)

Entradas historicas agregadas y retiradas posteriormente:

- docs/runbooks/runbook-duckdns-public-domain.md

Entradas vivas actualizadas:

- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`
- `VIRU_PANEL.bat`
- `infra/Caddyfile`
- infra/docker-compose.prod.yml

Entradas vivas retiradas (sin referencia verificable activa):

- docs/runbooks/runbook-free-domain-setup.md
- infra/cloudflared-config.yml
- `scripts/setup-cloudflared.ps1`

## Actualizacion manual 2026-06-05 (watchlist + quick-search stabilization)

Entradas vivas agregadas:

- `docs/runbooks/runbook-watchlist-quick-search-stabilization.md`
| docs/runbooks/runbook-puerta-a-puerta-qa.md | runbook | vivo | conservar | docs/runbooks/runbook-puerta-a-puerta-qa.md | Runbook QA especifico de /puerta-a-puerta con taxonomia de fuentes, checklist y comandos de test | docs/runbooks/runbook-puerta-a-puerta-qa.md |
- Reporte archivado no conservado: docs/archive/qa-reports/2026-06-05-watchlist-quick-search-stabilization.md

Entradas vivas actualizadas:

- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-08 (button hierarchy contract)

Entradas vivas actualizadas:

- `docs/ui/UI_CONTRACT_V1.md`
- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-08 (puerta-a-puerta plan aterrizado real)

Entradas vivas agregadas:

- `docs/plans/2026-06-08-puerta-a-puerta-plan-aterrizado-real.md`

Entradas vivas actualizadas:

- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-09 (perfiles de activacion Fase 1)

Entradas vivas agregadas:

- `docs/runbooks/runbook-activation-profiles.md`
- `docs/plans/2026-06-09-puerta-a-puerta-siguientes-10-fases.md`

Entradas vivas actualizadas:

- `docs/reference/backend/door-to-door-contract.md` (V1.6 — perfiles de activacion, blindaje anti-mock)
- `backend/.env.example` (perfil local_real rotulado, secciones comentadas para otros perfiles)
- `backend/app/door_to_door/providers/registry.py` (guard anti-mock en staging/prod)
- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-09 (puerta-a-puerta plan 10 fases activacion real)

Entradas vivas agregadas:

- `docs/plans/2026-06-09-puerta-a-puerta-plan-10-fases-activacion-real.md`

Entradas vivas actualizadas:

- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-09 (puerta-a-puerta siguientes 10 fases)

Entradas vivas agregadas:

- `docs/plans/2026-06-09-puerta-a-puerta-siguientes-10-fases.md`

Entradas vivas actualizadas:

- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-10 (sticky navbar scroll-state rollout)

Entradas vivas agregadas:

- `docs/plans/2026-06-10-sticky-navbar-scroll-state-rollout.md`

Entradas vivas actualizadas:

- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-10 (quick-search shared cache implementation plan)

Entradas vivas agregadas:

- `docs/plans/2026-06-10-quick-search-shared-cache-implementation.md`

Entradas vivas actualizadas:

- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-10 (Redis hot layer design plan)

Entradas vivas agregadas:

- `docs/plans/2026-06-10-redis-hot-layer-plan.md`

Entradas vivas actualizadas:

- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-10 (quick-search shared cache implementation complete)

Entradas vivas agregadas:

- `backend/app/services/quick_search_cache_service.py`
- `backend/alembic/versions/0030_add_quick_search_shared_cache.py`
- `backend/tests/unit/test_quick_search_cache_models.py`
- `backend/tests/unit/test_quick_search_shared_cache.py`

Entradas vivas actualizadas:

- `docs/reference/backend/quick-search-contract.md` (V2.1 — shared cache section + implementation status)
- `docs/engineering/backend.md` (shared cache mention)
- `backend/app/services/quick_search_execution.py` (canonicalization + L1→L2→provider cascade + anti-stampede)
- `backend/app/infrastructure/db/models.py` (QuickSearchCacheEntry model)
- `backend/app/api/v1/search.py` (L2 wiring + pruning + observability)
- `backend/app/api/v1/watchlist.py` (shared cache in _refresh_watch_now)
- `backend/.env.example` (5 QUICK_SEARCH_SHARED_CACHE_* env vars)
- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-10 (quick-search shared cache review plan)

Entradas vivas agregadas:

- `docs/plans/2026-06-10-quick-search-shared-cache-review-plan.md`

Entradas vivas actualizadas:

- `docs/DOCS_INVENTORY.md`

## Actualizacion manual 2026-06-08 (puerta-a-puerta F1-F10 cierre)

Entradas vivas agregadas:

- `docs/runbooks/runbook-puerta-a-puerta-qa.md`

Entradas vivas actualizadas:

- `docs/product/door-to-door.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`
- `HISTORY.md`

## Actualizacion manual 2026-06-05 (hoteles post-cierre Fases A-E)

Entradas vivas agregadas:

- `HISTORY.md`
- `docs/archive/plans/cabinalimpia.txt`
- `docs/plans/2026-06-04-hoteles-correcciones-post-cierre.md`

Entradas vivas actualizadas:

- `docs/specs/hotels-intelligence-mvp.md`
- `docs/qa/hotels-pending-closeout.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`
- `frontend/src/styles/screens.css`
- `frontend/src/modules/hotels/hooks/useHotelCompSets.ts`
- `frontend/src/modules/hotels/components/HotelCompSetPanel.tsx`
- `frontend/src/i18n/domains/hotels.ts`
- `frontend/src/modules/hotels/HotelRadarPage.tsx`

Entradas vivas retiradas:

- `hoteles.txt`
- `hoteles_2.txt`
- `hoteles_3.txt`

## Actualizacion manual 2026-08-05 (contrato H43 de flags, canary y kill switches hoteleros)

Entradas vivas agregadas:

- `docs/reference/backend/hoteles-flags-canary-killswitch-h43.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H43 de perfiles `local_demo`/`local_fixture`/`staging_canary`/`prod_off`/`prod_gradual`, precedencia fail-closed, kill switches globales y por operación, canary reversible, cero llamadas externas, rollback, evidencia y gates. Se mantienen explícitos los gaps actuales entre worker, API y job directo; no se declara rollout comercial activo.

## Actualizacion manual 2026-08-05 (contrato H44 de seed, demo y fallos reproducibles hoteleros)

Entradas vivas agregadas:

- `docs/reference/backend/hoteles-seed-demo-fallos-h44.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H44 de dataset sintético determinista, manifest, aislamiento, seed/reset seguros, perfiles de 429/timeout/empty/invalid/schema drift/no currency/sold out/ambiguity/stale/partial/deeplink inválido, escenarios User A/B, browser QA, evidencia y gates. Se distingue el fixture Mock actual del seed hotelero integral y se evita presentar datos sintéticos como disponibilidad real.

## Actualizacion manual 2026-08-05 (contrato H48 de búsquedas hoteleras guardadas y compartibles)

Entradas vivas agregadas:

- `docs/reference/backend/hoteles-busquedas-guardadas-compartibles-h48.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H48 de `StayQuery` versionada, URL pública anónima, búsqueda guardada privada, ownership/lifecycle, restore/back-forward, auth, cache/analytics redaction, no provider calls implícitas, separación frente a favorito/tracking/alerta y gates de privacidad/QA.

## Actualizacion manual 2026-08-05 (contrato H49 de personalización hotelera prudente)

Entradas vivas agregadas:

- `docs/reference/frontend/hoteles-personalizacion-prudente-h49.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H49 de personalización opcional, declarada frente a inferida, limitada a `recommended`, explicaciones estructuradas, cold start, controles de activar/desactivar/reset/borrado, privacidad, fairness guardrails, estados stale/provider/demo, i18n, accesibilidad, flags, rollback y QA.

## Actualizacion manual 2026-08-05 (contrato H50 de monetización y afiliación responsable)

Entradas vivas agregadas:

- `docs/reference/backend/hoteles-monetizacion-afiliacion-atribucion-h50.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H50 de independencia del ranking, registry y allowlist de partners, disclosure, consentimiento, atribución privacy-safe, separación de clicks/conversiones/comisiones, ledger finance-only, reconciliación, presupuestos separados, kill switch, canary, rollback y QA.

## Actualizacion manual 2026-08-05 (contrato H51 de experimentos hoteleros)

Entradas vivas agregadas:

- `docs/reference/frontend/hoteles-experimentos-hipotesis-guardrails-h51.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H51 de hipótesis falsables, variantes, asignación sticky, exposición efectiva, métricas con denominadores, MDE/stopping, SRM/novelty, guardrails de confianza/privacidad/a11y/coste, consentimiento, flags/canary, rollback, decision records y QA.

## Actualizacion manual 2026-08-05 (contrato H47 de re-engagement hotelero)

Entradas vivas agregadas:

- `docs/reference/frontend/hoteles-mis-hoteles-reengagement-h47.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H47 de retorno útil y superficie “Mis hoteles” dentro de `/hoteles`: prioridad tracking/señales/guardados, estados freshness/lifecycle, URL state objetivo, inbox/deep links contextuales, fallback seguro, ownership V2, auth/cache privados, progressive disclosure, i18n/a11y, instrumentación redacted y gates de dos usuarios/browser QA.

## Actualizacion manual 2026-08-05 (contrato H46 de primera victoria hotelera)

Entradas vivas agregadas:

- `docs/reference/frontend/hoteles-primera-victoria-h46.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H46 de activación sin tutorial largo: primera búsqueda, empty/demo honesto, separación guardar/seguir, tracking elegible, auth contextual con retorno, confirmaciones, alertas, estados H21, accesibilidad H32/H33, i18n H34, instrumentación redacted y gate de evidencia H40.

## Actualizacion manual 2026-08-05 (contrato H45 de release, smoke, canary y rollback hotelero)

Entradas vivas agregadas:

- `docs/reference/backend/hoteles-release-canary-smoke-rollback-h45.md`

Entradas vivas actualizadas:

- `docs/plans/2026-08-04-hoteles-master-roadmap.md`
- `docs/plans/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

Motivo:

- Contrato H45 de release readiness, preflight, smoke local, distinción release/provider canary, criterios de promoción/pausa/bloqueo, rollback de código/config/datos/provider, evidencia redacted y gates Q/S/C/R/E. Se documenta que el workflow canary actual solo imprime pasos, que `/health`/`/ready` son probes básicos y que el worker Kubernetes es placeholder.

## Tabla

| Ruta actual | Tipo | Estado | Acci?n propuesta | Nueva ruta | Motivo | Fuente de verdad |
|---|---|---|---|---|---|---|
| .github/pull_request_template.md | unknown | revisar manualmente | revisar manualmente | .github/pull_request_template.md | Clasificaci?n no resuelta autom?ticamente | revisi?n manual requerida |
| AGENTS.md | contexto IA | vivo | conservar | AGENTS.md | Contrato operativo principal para agentes | AGENTS.md |
| docs/archive/plans/cabinalimpia.txt | plan | archivado | conservar | docs/archive/plans/cabinalimpia.txt | Plan consolidado de correcciones post-cierre del modulo /hoteles (Fases A-E) | cabinalimpia.txt |
| DESIGN.md | contexto IA | vivo | conservar | DESIGN.md | Sistema de diseno para agentes con direccion visual calida, animada y de premium humano | DESIGN.md |
| HISTORY.md | overview | vivo | conservar | HISTORY.md | Historial de cambios significativos del proyecto | HISTORY.md |
| README.md | overview | vivo | conservar | README.md | Punto de entrada principal del repositorio | README.md |
| .codex/skills/viru-air-ui/SKILL.md | contexto IA | vivo | conservar | .codex/skills/viru-air-ui/SKILL.md | Skill de diseno incremental para Codex orientado a calidez, personalidad y claridad | .codex/skills/viru-air-ui/SKILL.md |
| .codex/skills/viru-air-ui/references/product-context.md | contexto IA | vivo | conservar | .codex/skills/viru-air-ui/references/product-context.md | Contexto de producto para tareas UI con enfoque cercano, calido y no generico | .codex/skills/viru-air-ui/references/product-context.md |
| .codex/skills/viru-air-ui/references/visual-direction.md | contexto IA | vivo | conservar | .codex/skills/viru-air-ui/references/visual-direction.md | Direccion visual calida y con personalidad para el skill Viru Air UI | .codex/skills/viru-air-ui/references/visual-direction.md |
| .codex/skills/viru-air-ui/references/qa-checklist.md | contexto IA | vivo | conservar | .codex/skills/viru-air-ui/references/qa-checklist.md | Checklist de QA visual para validar claridad, calidez y personalidad del skill | .codex/skills/viru-air-ui/references/qa-checklist.md |
| .codex/skills/taste-skill/SKILL.md | contexto IA | vivo | conservar | .codex/skills/taste-skill/SKILL.md | Skill de direccion visual frontend premium para tareas de estetica/UI | .codex/skills/taste-skill/SKILL.md |
| docs/DOCS_INVENTORY.md | overview | vivo | conservar | docs/DOCS_INVENTORY.md | Inventario documental ?nico | docs/DOCS_INVENTORY.md |
| docs/INDICE_UNICO.md | overview | vivo | conservar | docs/INDICE_UNICO.md | Mapa ?nico de navegaci?n | docs/INDICE_UNICO.md |
| docs/README.md | overview | vivo | conservar | docs/README.md | Gu?a principal de navegaci?n documental | docs/README.md |
| docs/adr/ADR-001-monolito-modular.md | ADR | vivo | conservar | docs/adr/ADR-001-monolito-modular.md | Decisi?n de arquitectura vigente | docs/adr/ADR-001-monolito-modular.md |
| docs/adr/ADR-002-stack-base.md | ADR | vivo | conservar | docs/adr/ADR-002-stack-base.md | Decisi?n de arquitectura vigente | docs/adr/ADR-002-stack-base.md |
| docs/adr/ADR-003-provider-adapter.md | ADR | vivo | conservar | docs/adr/ADR-003-provider-adapter.md | Decisi?n de arquitectura vigente | docs/adr/ADR-003-provider-adapter.md |
| docs/adr/ADR-004-flight-tracking-hub.md | ADR | vivo | conservar | docs/adr/ADR-004-flight-tracking-hub.md | Hub compartido de frescura y revalidacion para datos de vuelo | docs/adr/ADR-004-flight-tracking-hub.md |
| docs/adr/ADR-005-live-operational-flight-tracking.md | ADR | vivo | conservar | docs/adr/ADR-005-live-operational-flight-tracking.md | Identidad exacta opcional, snapshots operacionales compartidos y proveedor reemplazable para Watchlist | docs/adr/ADR-005-live-operational-flight-tracking.md |
| docs/adr/ADR-006-zero-cost-operational-provider-fallback.md | ADR | vivo | conservar | docs/adr/ADR-006-zero-cost-operational-provider-fallback.md | Fallback por capacidades con presupuesto persistente y modo sin coste por defecto | docs/adr/ADR-006-zero-cost-operational-provider-fallback.md |
| docs/archive/README.md | historical | hist?rico | conservar | docs/archive/README.md | Gu?a del archivo hist?rico | ninguna; material hist?rico |
| docs/archive/duplicated/README.md | duplicate | duplicado | conservar | docs/archive/duplicated/README.md | Copia retirada de la navegaci?n principal; la versi?n can?nica vive fuera de archive | ninguna |
| docs/archive/duplicated/UI_CONTRACT_V1.md | duplicate | duplicado | conservar | docs/archive/duplicated/UI_CONTRACT_V1.md | Copia retirada de la navegaci?n principal; la versi?n can?nica vive fuera de archive | docs/ui/UI_CONTRACT_V1.md |
| docs/archive/duplicated/UI_SYSTEM_V1.md | duplicate | duplicado | conservar | docs/archive/duplicated/UI_SYSTEM_V1.md | Copia retirada de la navegaci?n principal; la versi?n can?nica vive fuera de archive | docs/ui/UI_SYSTEM_V1.md |
| docs/archive/duplicated/UI_VISUAL_QA_CHECKLIST.md | duplicate | duplicado | conservar | docs/archive/duplicated/UI_VISUAL_QA_CHECKLIST.md | Copia retirada de la navegaci?n principal; la versi?n can?nica vive fuera de archive | docs/ui/UI_VISUAL_QA_CHECKLIST.md |
| docs/archive/duplicated/backend-docs/quick-search-acceptance-checklist.md | duplicate | duplicado | conservar | docs/archive/duplicated/backend-docs/quick-search-acceptance-checklist.md | Copia retirada de la navegaci?n principal; la versi?n can?nica vive fuera de archive | docs/reference/backend/quick-search-acceptance-checklist.md |
| docs/archive/duplicated/backend-docs/quick-search-contract.md | duplicate | duplicado | conservar | docs/archive/duplicated/backend-docs/quick-search-contract.md | Copia retirada de la navegaci?n principal; la versi?n can?nica vive fuera de archive | docs/reference/backend/quick-search-contract.md |
| docs/archive/duplicated/estetica.md | duplicate | duplicado | conservar | docs/archive/duplicated/estetica.md | Copia retirada de la navegaci?n principal; la versi?n can?nica vive fuera de archive | docs/ui/estetica.md |
| docs/archive/duplicated/feature-flags.md | duplicate | duplicado | conservar | docs/archive/duplicated/feature-flags.md | Copia retirada de la navegaci?n principal; la versi?n can?nica vive fuera de archive | docs/reference/feature-flags.md |
| docs/archive/duplicated/quick-search-weather-policy.md | duplicate | duplicado | conservar | docs/archive/duplicated/quick-search-weather-policy.md | Copia retirada de la navegaci?n principal; la versi?n can?nica vive fuera de archive | docs/reference/quick-search-weather-policy.md |
| docs/archive/extracted-txt/README.md | generated/noise | generado | conservar | docs/archive/extracted-txt/README.md | Snapshot textual o extracci?n preservada por trazabilidad | ninguna; artefacto generado |
| docs/archive/extracted-txt/tree_filtrado.txt | generated/noise | generado | conservar | docs/archive/extracted-txt/tree_filtrado.txt | Snapshot textual o extracci?n preservada por trazabilidad | ninguna; artefacto generado |
| docs/archive/fases/README.md | historical | hist?rico | conservar | docs/archive/fases/README.md | Fases y transcripciones preservadas como hist?rico | ninguna; material hist?rico |
| docs/archive/fases/transcripts/FASE_10_Futuras_Escalabilidades_Viru.txt | historical | hist?rico | conservar | docs/archive/fases/transcripts/FASE_10_Futuras_Escalabilidades_Viru.txt | Fases y transcripciones preservadas como hist?rico | ninguna; material hist?rico |
| docs/archive/fases/transcripts/FASE_1_Analisis_de_Documentacion_Viru.txt | historical | hist?rico | conservar | docs/archive/fases/transcripts/FASE_1_Analisis_de_Documentacion_Viru.txt | Fases y transcripciones preservadas como hist?rico | ninguna; material hist?rico |
| docs/archive/fases/transcripts/FASE_2_Arquitectura_Global_Viru.txt | historical | hist?rico | conservar | docs/archive/fases/transcripts/FASE_2_Arquitectura_Global_Viru.txt | Fases y transcripciones preservadas como hist?rico | ninguna; material hist?rico |
| docs/archive/fases/transcripts/FASE_3_Backend_Viru.txt | historical | hist?rico | conservar | docs/archive/fases/transcripts/FASE_3_Backend_Viru.txt | Fases y transcripciones preservadas como hist?rico | ninguna; material hist?rico |
| docs/archive/fases/transcripts/FASE_4_Frontend_Viru.txt | historical | hist?rico | conservar | docs/archive/fases/transcripts/FASE_4_Frontend_Viru.txt | Fases y transcripciones preservadas como hist?rico | ninguna; material hist?rico |
| docs/archive/fases/transcripts/FASE_5_Base_de_Datos_Viru.txt | historical | hist?rico | conservar | docs/archive/fases/transcripts/FASE_5_Base_de_Datos_Viru.txt | Fases y transcripciones preservadas como hist?rico | ninguna; material hist?rico |
| docs/archive/fases/transcripts/FASE_6_DevOps_Despliegue_Viru.txt | historical | hist?rico | conservar | docs/archive/fases/transcripts/FASE_6_DevOps_Despliegue_Viru.txt | Fases y transcripciones preservadas como hist?rico | ninguna; material hist?rico |
| docs/archive/fases/transcripts/FASE_7_Mejoras_Propuestas_Viru.txt | historical | hist?rico | conservar | docs/archive/fases/transcripts/FASE_7_Mejoras_Propuestas_Viru.txt | Fases y transcripciones preservadas como hist?rico | ninguna; material hist?rico |
| docs/archive/fases/transcripts/FASE_8_Testing_Viru.txt | historical | hist?rico | conservar | docs/archive/fases/transcripts/FASE_8_Testing_Viru.txt | Fases y transcripciones preservadas como hist?rico | ninguna; material hist?rico |
| docs/archive/fases/transcripts/FASE_9_Documentacion_Tecnica_Extensa_Viru.txt | historical | hist?rico | conservar | docs/archive/fases/transcripts/FASE_9_Documentacion_Tecnica_Extensa_Viru.txt | Fases y transcripciones preservadas como hist?rico | ninguna; material hist?rico |
| docs/archive/fases/transcripts/INDICE_MAESTRO_VIRU_IA_NAVEGACION.txt | historical | hist?rico | conservar | docs/archive/fases/transcripts/INDICE_MAESTRO_VIRU_IA_NAVEGACION.txt | Fases y transcripciones preservadas como hist?rico | ninguna; material hist?rico |
| docs/archive/old-reports/2026-03-08-c1-c6-consolidated.md | historical | hist?rico | conservar | docs/archive/old-reports/2026-03-08-c1-c6-consolidated.md | Reporte hist?rico movido fuera de la navegaci?n viva | ninguna; material hist?rico |
| docs/archive/old-reports/README.md | historical | hist?rico | conservar | docs/archive/old-reports/README.md | Reporte hist?rico movido fuera de la navegaci?n viva | ninguna; material hist?rico |
| docs/archive/old-reports/c1-smoke.md | historical | hist?rico | conservar | docs/archive/old-reports/c1-smoke.md | Reporte hist?rico movido fuera de la navegaci?n viva | ninguna; material hist?rico |
| docs/archive/prompts/05-03-26.txt | prompt | hist?rico | conservar | docs/archive/prompts/05-03-26.txt | Prompt archivado o ?ndice de prompts hist?ricos | ninguna; material hist?rico |
| docs/archive/prompts/README.md | prompt | hist?rico | conservar | docs/archive/prompts/README.md | Prompt archivado o ?ndice de prompts hist?ricos | ninguna; material hist?rico |
| docs/archive/prompts/prompt.txt | prompt | hist?rico | conservar | docs/archive/prompts/prompt.txt | Prompt archivado o ?ndice de prompts hist?ricos | docs/prompts/legacy/prompt-root-legacy.txt |
| docs/archive/qa/2026-03-08/2026-03-08-c2.1-execution-report.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c2.1-execution-report.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c3-navigation-route-mapping.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c3-navigation-route-mapping.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c4-backend-robustness-contract.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c4-backend-robustness-contract.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c5-db-operational-baseline.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c5-db-operational-baseline.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c6-checklist-cb1-cd2.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c6-checklist-cb1-cd2.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c6-command-outputs.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c6-command-outputs.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c6-docs-index.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c6-docs-index.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c6-open-issues.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c6-open-issues.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c6-qa-consolidated-report.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c6-qa-consolidated-report.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c6-readiness-acta.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c6-readiness-acta.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c7-cycle1-baseline-freeze.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c7-cycle1-baseline-freeze.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c7-cycle1-copy-i18n-matrix.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c7-cycle1-copy-i18n-matrix.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c7-cycle1-sensitive-claims-mapping.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c7-cycle1-sensitive-claims-mapping.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c7-cycle1-tech-debt-inventory.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c7-cycle1-tech-debt-inventory.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c7-cycle2-copy-i18n-admin-suggestions.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c7-cycle2-copy-i18n-admin-suggestions.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c7-cycle3-claims-evidence-final-text.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c7-cycle3-claims-evidence-final-text.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c7-cycle3-communication-risk-acceptance.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c7-cycle3-communication-risk-acceptance.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c7-cycle4-ux-visual-homogeneity.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c7-cycle4-ux-visual-homogeneity.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-08/2026-03-08-c7-cycle7-db-retention-evidence.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-08/2026-03-08-c7-cycle7-db-retention-evidence.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-09/2026-03-09-benchmark-prices-batch-vs-nplus1.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-09/2026-03-09-benchmark-prices-batch-vs-nplus1.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-09/2026-03-09-cycle6-1-hardening.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-09/2026-03-09-cycle6-1-hardening.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-09/2026-03-09-cycle6-visual-qa-core-routes.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-09/2026-03-09-cycle6-visual-qa-core-routes.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/2026-03-09/2026-03-09-dashboard-cycle2-density-qa.md | QA | hist?rico | conservar | docs/archive/qa/2026-03-09/2026-03-09-dashboard-cycle2-density-qa.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/README.md | QA | hist?rico | conservar | docs/archive/qa/README.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/feature-specific/account-system-redesign-qa.md | QA | hist?rico | conservar | docs/archive/qa/feature-specific/account-system-redesign-qa.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/qa/feature-specific/watchlist-history-fusion-pr-checklist.md | QA | hist?rico | conservar | docs/archive/qa/feature-specific/watchlist-history-fusion-pr-checklist.md | Reporte o evidencia de QA de ciclos cerrados | ninguna; material hist?rico |
| docs/archive/root-legacy/DASHBOARD_REDESIGN_V2.md | historical | hist?rico | conservar | docs/archive/root-legacy/DASHBOARD_REDESIGN_V2.md | Documento ra?z legacy preservado por trazabilidad | docs/specs/product/dashboard-redesign-v2.md |
| docs/archive/root-legacy/POLICIES_PAGE_ACCEPTANCE_CHECKLIST.md | historical | hist?rico | conservar | docs/archive/root-legacy/POLICIES_PAGE_ACCEPTANCE_CHECKLIST.md | Documento ra?z legacy preservado por trazabilidad | docs/specs/policies/policies-page-acceptance-checklist.md |
| docs/archive/root-legacy/POLICIES_PAGE_COMPONENT_SPEC.md | historical | hist?rico | conservar | docs/archive/root-legacy/POLICIES_PAGE_COMPONENT_SPEC.md | Documento ra?z legacy preservado por trazabilidad | docs/specs/policies/policies-page-component-spec.md |
| docs/archive/root-legacy/POLICIES_PAGE_COPY_DECK_ES.md | historical | hist?rico | conservar | docs/archive/root-legacy/POLICIES_PAGE_COPY_DECK_ES.md | Documento ra?z legacy preservado por trazabilidad | docs/specs/policies/policies-page-copy-deck-es.md |
| docs/archive/root-legacy/POLICIES_PAGE_REWRITE.md | historical | hist?rico | conservar | docs/archive/root-legacy/POLICIES_PAGE_REWRITE.md | Documento ra?z legacy preservado por trazabilidad | docs/specs/policies/policies-page-rewrite.md |
| docs/archive/root-legacy/README.md | historical | hist?rico | conservar | docs/archive/root-legacy/README.md | Documento ra?z legacy preservado por trazabilidad | ninguna; material hist?rico |
| docs/archive/root-legacy/UI_CHANGES.md | historical | hist?rico | conservar | docs/archive/root-legacy/UI_CHANGES.md | Documento ra?z legacy preservado por trazabilidad | docs/specs/ui/ui-changes.md |
| docs/archive/root-legacy/UI_CONTRACT_V1.duplicate.md | historical | hist?rico | conservar | docs/archive/root-legacy/UI_CONTRACT_V1.duplicate.md | Documento ra?z legacy preservado por trazabilidad | ninguna; material hist?rico |
| docs/archive/tooling/README.md | historical | hist?rico | conservar | docs/archive/tooling/README.md | Salida de tooling archivada | ninguna; material hist?rico |
| docs/archive/tooling/testsprite/SKILLSPRITE_USER_CAPABILITIES.md | historical | hist?rico | conservar | docs/archive/tooling/testsprite/SKILLSPRITE_USER_CAPABILITIES.md | Salida de tooling archivada | docs/qa/testsprite/skillsprite-user-capabilities.md |
| docs/archive/tooling/testsprite/testsprite-mcp-test-report.md | historical | hist?rico | conservar | docs/archive/tooling/testsprite/testsprite-mcp-test-report.md | Salida de tooling archivada | ninguna; material hist?rico |
| docs/engineering/backend.md | backend | vivo | conservar | docs/engineering/backend.md | Resumen t?cnico vivo por dominio | docs/engineering/backend.md |
| docs/engineering/database.md | database | vivo | conservar | docs/engineering/database.md | Resumen t?cnico vivo por dominio | docs/engineering/database.md |
| docs/engineering/frontend.md | frontend | vivo | conservar | docs/engineering/frontend.md | Resumen t?cnico vivo por dominio | docs/engineering/frontend.md |
| docs/engineering/infra.md | infra | vivo | conservar | docs/engineering/infra.md | Resumen t?cnico vivo por dominio | docs/engineering/infra.md |
| docs/engineering/observability.md | observability | vivo | conservar | docs/engineering/observability.md | Resumen t?cnico vivo por dominio | docs/engineering/observability.md |
| docs/engineering/security.md | security | vivo | conservar | docs/engineering/security.md | Resumen t?cnico vivo por dominio | docs/engineering/security.md |
| docs/engineering/testing.md | testing | vivo | conservar | docs/engineering/testing.md | Resumen t?cnico vivo por dominio | docs/engineering/testing.md |
| docs/overview/architecture-summary.md | architecture | vivo | conservar | docs/overview/architecture-summary.md | Onboarding y mapa vivo del proyecto | docs/overview/architecture-summary.md |
| docs/overview/current-state.md | overview | vivo | conservar | docs/overview/current-state.md | Onboarding y mapa vivo del proyecto | docs/overview/current-state.md |
| docs/overview/project-overview.md | overview | vivo | conservar | docs/overview/project-overview.md | Onboarding y mapa vivo del proyecto con direccion de producto clara y cercana | docs/overview/project-overview.md |
| docs/overview/repo-map.md | overview | vivo | conservar | docs/overview/repo-map.md | Onboarding y mapa vivo del proyecto | docs/overview/repo-map.md |
| docs/overview/start-here.md | overview | vivo | conservar | docs/overview/start-here.md | Onboarding y mapa vivo del proyecto | docs/overview/start-here.md |
| docs/plans/README.md | plan | vivo | conservar | docs/plans/README.md | Gu?a de organizaci?n de planes | docs/plans/README.md |
| docs/plans/2026-08-01-community-route-intelligence.md | plan | vivo | conservar | docs/plans/2026-08-01-community-route-intelligence.md | Plan full-stack para popularidad semanal, precios, tendencias, rutas relacionadas e historial comunitario | docs/plans/2026-08-01-community-route-intelligence-design.md |
| docs/plans/2026-08-01-community-route-intelligence-design.md | plan | vivo | conservar | docs/plans/2026-08-01-community-route-intelligence-design.md | Diseño aprobado de inteligencia comunitaria de rutas y variante Lazyweb Corredores más buscados | docs/plans/2026-08-01-community-route-intelligence.md |
| docs/plans/2026-08-04-hoteles-master-roadmap.md | plan | vivo | conservar | docs/plans/2026-08-04-hoteles-master-roadmap.md | Plan maestro por fases para convertir `/hoteles` en un tracker hotelero confiable y preferido | conservar como roadmap de ejecución; actualizar estado por fase |
| docs/qa/reports/2026-08-04-hoteles-h00-baseline.md | QA | vivo | conservar | docs/qa/reports/2026-08-04-hoteles-h00-baseline.md | Baseline reproducible de tests, build, entorno y limitaciones operativas de `/hoteles` | actualizar en nuevos baselines o cambios de gate |
| docs/product/hoteles-product-vision-h01.md | product | vivo | conservar | docs/product/hoteles-product-vision-h01.md | Visión, personas, jobs, no-objetivos, métricas y guardrails de `/hoteles` | fuente de verdad de dirección de producto |
| docs/benchmarks/2026-08-04-travelpricedrops-hotels-h02.md | benchmark | vivo | conservar | docs/benchmarks/2026-08-04-travelpricedrops-hotels-h02.md | Benchmark fechado de Travel Price Drops Hotels y traducción de patrones a decisiones Viru | revisar si cambia la referencia o una decisión depende de ella |
| docs/product/hoteles-information-architecture-h03.md | product | vivo | conservar | docs/product/hoteles-information-architecture-h03.md | Arquitectura de información, sitemap, URL state, wireflows, responsive y estados límite de `/hoteles` | fuente de verdad de navegación H03 |
| docs/product/hoteles-metrics-events-h04.md | product | vivo | conservar | docs/product/hoteles-metrics-events-h04.md | Taxonomía de eventos, métricas derivadas, privacidad, dedupe, guardrails y definición de done de `/hoteles` | fuente de verdad de medición H04 |
| docs/reference/backend/hoteles-freshness-provenance-confidence-h05.md | backend | vivo | conservar | docs/reference/backend/hoteles-freshness-provenance-confidence-h05.md | Contrato de procedencia, freshness, disponibilidad, comparabilidad y confidence de precios hoteleros | fuente de verdad de calidad de datos H05 |
| docs/reference/backend/hoteles-provider-neutral-contract-h06.md | backend | vivo | conservar | docs/reference/backend/hoteles-provider-neutral-contract-h06.md | Contrato V2 provider-neutral, envelope de resultados, errores, retries, rate limits, deeplinks seguros y contract tests | fuente de verdad de frontera provider-neutral H06 |
| docs/reference/backend/hoteles-makcorps-audit-h07.md | backend | vivo | conservar | docs/reference/backend/hoteles-makcorps-audit-h07.md | Auditoría de Makcorps con evidencia oficial/local/runtime, bloqueos técnicos, coste, canary y decisión de uso limitado | fuente de verdad de decisión Makcorps H07 |
| docs/reference/backend/hoteles-provider-onboarding-h08.md | backend | vivo | conservar | docs/reference/backend/hoteles-provider-onboarding-h08.md | Matriz provider-neutral de candidatos, gates de onboarding, canary, presupuesto, deduplicación y plan de salida H08 | fuente de verdad de evaluación y onboarding H08 |
| docs/reference/backend/hoteles-sweep-gateway-h09.md | backend | vivo | conservar | docs/reference/backend/hoteles-sweep-gateway-h09.md | Contrato operativo H09 para gateway, scheduler, leases, dedupe, retries, budget, circuit breaker, health, replay y rollback | fuente de verdad de ejecución segura de sweeps H09 |
| docs/reference/backend/hoteles-stay-offer-model-h10.md | backend | vivo | conservar | docs/reference/backend/hoteles-stay-offer-model-h10.md | Contrato H10 de StayQuery, ocupación, oferta, snapshot, matching, comparabilidad, fingerprints y migración compatible | fuente de verdad de modelo canónico hotelero H10 |
| docs/reference/backend/hoteles-data-migration-h11.md | backend | vivo | conservar | docs/reference/backend/hoteles-data-migration-h11.md | Contrato H11 expand-and-contract, backfill reanudable, doble lectura/escritura, índices, retención, Alembic, SQLite/PostgreSQL y rollback | fuente de verdad de migración hotelera H11 |
| docs/reference/backend/hoteles-destination-resolution-h12.md | backend | vivo | conservar | docs/reference/backend/hoteles-destination-resolution-h12.md | Contrato H12 de destinos tipados, normalización, autocomplete, confidence, ambigüedad, geocoder limitado, cache y fallback | fuente de verdad de resolución de destinos H12 |
| docs/reference/backend/hoteles-search-form-h13.md | backend | vivo | conservar | docs/reference/backend/hoteles-search-form-h13.md | Contrato H13 de formulario, URL state, validación inline, submit, recuperación, accesibilidad y compatibilidad V1 | fuente de verdad de interacción del formulario hotelero H13 |
| docs/reference/backend/hoteles-filters-ranking-h14.md | backend | vivo | conservar | docs/reference/backend/hoteles-filters-ranking-h14.md | Contrato H14 de filtros, ordenación, precedencia, precio ausente, explicabilidad y compatibilidad V1 | fuente de verdad de filtros y ordenación hotelera H14 |
| docs/reference/backend/hoteles-results-pagination-h15.md | backend | vivo | conservar | docs/reference/backend/hoteles-results-pagination-h15.md | Contrato H15 de envelope V2, metadata, warnings, capabilities, estados, paginación, cancelación y compatibilidad V1 | fuente de verdad de resultados y paginación hotelera H15 |
| docs/reference/frontend/hoteles-result-cards-h16.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-result-cards-h16.md | Contrato H16 de anatomía, jerarquía, precio, condiciones, freshness, acciones, estados, responsive y accesibilidad de result cards | fuente de verdad visual y funcional de result cards hoteleras H16 |
| docs/reference/backend/hoteles-ranking-explainability-h17.md | backend | vivo | conservar | docs/reference/backend/hoteles-ranking-explainability-h17.md | Contrato H17 de ranking determinista, recommended futuro, tie-breakers, missing data, explicaciones, personalización y afiliación | fuente de verdad de ranking y explicabilidad hotelera H17 |
| docs/reference/frontend/hoteles-detail-navigation-h18.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-detail-navigation-h18.md | Contrato H18 de detalle hotelero, selección URL-driven, retorno, back/forward, estados, ownership, acciones y deeplinks | fuente de verdad de detalle y navegación hotelera H18 |
| docs/reference/backend/hoteles-price-total-fees-h19.md | backend | vivo | conservar | docs/reference/backend/hoteles-price-total-fees-h19.md | Contrato H19 de total, noches, fees, moneda, comparabilidad, transparencia, elegibilidad de tracking y disclosure | fuente de verdad de precio y transparencia hotelera H19 |
| docs/reference/backend/hoteles-provider-comparison-nearby-h20.md | backend | vivo | conservar | docs/reference/backend/hoteles-provider-comparison-nearby-h20.md | Contrato H20 de paridad de providers, comparabilidad, estados insuficientes, comp sets, hoteles cercanos, ownership y retorno | fuente de verdad de comparación y cercanos hoteleros H20 |
| docs/reference/frontend/hoteles-state-matrix-h21.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-state-matrix-h21.md | Contrato H21 de taxonomía transversal de estados, recuperación, stale-while-error, preservación de contexto, accesibilidad, telemetría y QA | fuente de verdad de estados y recuperación hotelera H21 |
| docs/reference/backend/hoteles-favorite-vs-tracking-h22.md | backend | vivo | conservar | docs/reference/backend/hoteles-favorite-vs-tracking-h22.md | Contrato H22 de favorito simple frente a tracking, identidad, lifecycle, conversión, ownership, inbox, migración y gates | fuente de verdad de semántica de guardados y seguimientos hoteleros H22 |
| docs/reference/backend/hoteles-lifecycle-pause-edit-expire-delete-h29.md | backend | vivo | conservar | docs/reference/backend/hoteles-lifecycle-pause-edit-expire-delete-h29.md | Contrato H29 de pausa, edición, expiración, archivado, eliminación, ownership, cascadas, retención e idempotencia de seguimientos hoteleros | fuente de verdad de lifecycle hotelero H29 |
| docs/reference/backend/hoteles-flexible-dates-calendar-h30.md | backend | vivo | conservar | docs/reference/backend/hoteles-flexible-dates-calendar-h30.md | Contrato H30 de calendario, ventanas temporales, capabilities de provider, comparabilidad, coste, URL, tracking y rollout | fuente de verdad de flexibilidad de fechas hoteleras H30 |
| docs/reference/frontend/hoteles-visual-direction-states-h31.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-visual-direction-states-h31.md | Contrato H31 de dirección visual Warm-Luxe hotelera, jerarquía, estados, responsive, motion, accesibilidad e i18n | fuente de verdad visual de hoteles H31 |
| docs/reference/frontend/hoteles-responsive-accessible-ctas-h32.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-responsive-accessible-ctas-h32.md | Contrato H32 de responsive por viewport, overflow, zoom, CTAs de 48 px, teclado, foco, estados móviles, reduced motion y browser QA | fuente de verdad responsive y CTAs hoteleros H32 |
| docs/reference/frontend/hoteles-wcag-accessibility-audit-h33.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-wcag-accessibility-audit-h33.md | Contrato H33 de auditoría WCAG 2.2 AA, combobox, labels/errores, foco, estados, contraste, zoom, reduced motion, prioridades y evidencia | fuente de verdad de accesibilidad hotelera H33 |
| docs/reference/frontend/hoteles-localization-dates-currency-timezones-h34.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-localization-dates-currency-timezones-h34.md | Contrato H34 de i18n ES/EN, placeholders, pluralización, fechas civiles, timestamps, monedas de origen, timezones, copy provider y gates de QA | fuente de verdad de localización hotelera H34 |
| docs/reference/backend/hoteles-legal-privacy-disclosure-deeplinks-h35.md | backend | vivo | conservar | docs/reference/backend/hoteles-legal-privacy-disclosure-deeplinks-h35.md | Contrato H35 de legal/privacy, ownership, consentimiento por canal, retención/borrado, disclosure, redaction, allowlist de deeplinks, SSRF/open redirect y gates L/S/D/Q/O | fuente de verdad de legal, privacidad y deeplinks hoteleros H35 |
| docs/reference/frontend/hoteles-performance-web-vitals-h36.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-performance-web-vitals-h36.md | Contrato H36 de presupuesto de rendimiento, Web Vitals, primer resultado útil, requests, assets, móvil, red degradada y gates lab/field | fuente de verdad de rendimiento frontend hotelero H36 |
| docs/reference/backend/hoteles-benchmark-rate-limits-locks-cost-h37.md | backend | vivo | conservar | docs/reference/backend/hoteles-benchmark-rate-limits-locks-cost-h37.md | Contrato H37 de benchmark fixture/canary/field, rate limits, budget ledger, locks/leases, singleflight, retries, breaker, coste y gates de capacidad | fuente de verdad de benchmark, límites y coste hotelero H37 |
| docs/reference/backend/hoteles-ownership-secrets-ssrf-abuse-h38.md | backend | vivo | conservar | docs/reference/backend/hoteles-ownership-secrets-ssrf-abuse-h38.md | Contrato H38 de ownership relacional, BOLA/IDOR, secretos, redaction, SSRF, open redirect, deeplinks, egress, abuso y gates de seguridad | fuente de verdad de seguridad de dominio hotelero H38 |
| docs/reference/backend/hoteles-test-pyramid-gaps-h39.md | backend | vivo | conservar | docs/reference/backend/hoteles-test-pyramid-gaps-h39.md | Estrategia H39 de pirámide de tests, cobertura por capa, huecos P0/P1/P2, fixtures, provider contract/canary, browser, seguridad, rendimiento y gates | fuente de verdad de estrategia de tests hoteleros H39 |
| docs/reference/frontend/hoteles-visual-manual-crossbrowser-qa-h40.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-visual-manual-crossbrowser-qa-h40.md | Contrato H40 de QA browser, visual/manual, responsive, dark/light, cross-browser, foco/teclado, consola/red, screenshots y aprobación humana | fuente de verdad de QA visual hotelero H40 |
| docs/reference/backend/hoteles-observability-e2e-h41.md | backend | vivo | conservar | docs/reference/backend/hoteles-observability-e2e-h41.md | Contrato H41 de observabilidad E2E, correlación, outcomes de provider/sweep, métricas, health, redaction, cardinalidad, SLO, coste y gates | fuente de verdad de observabilidad hotelera H41 |
| docs/runbooks/hoteles-incidentes-recovery-h42.md | runbook | vivo | conservar | docs/runbooks/hoteles-incidentes-recovery-h42.md | Runbook H42 de severidad, diagnóstico, preservación de evidencia, contención, recovery, rollback, seguridad, datos, delivery y soporte hotelero | fuente de verdad de respuesta a incidentes y recovery de hoteles H42 |
| docs/reference/backend/hoteles-flags-canary-killswitch-h43.md | backend | vivo | conservar | docs/reference/backend/hoteles-flags-canary-killswitch-h43.md | Contrato H43 de perfiles, defaults fail-closed, canary, rollout gradual, kill switches, cero llamadas externas, rollback y gates | fuente de verdad de activación segura de hoteles H43 |
| docs/reference/backend/hoteles-seed-demo-fallos-h44.md | backend | vivo | conservar | docs/reference/backend/hoteles-seed-demo-fallos-h44.md | Contrato H44 de dataset sintético determinista, manifest, aislamiento, seed/reset seguros, fault profiles, ownership A/B, browser QA y gates | fuente de verdad de reproducibilidad local hotelera H44 |
| docs/reference/backend/hoteles-release-canary-smoke-rollback-h45.md | backend | vivo | conservar | docs/reference/backend/hoteles-release-canary-smoke-rollback-h45.md | Contrato H45 de release readiness, smoke, canary genérico/provider, promoción, rollback, evidencia redacted y gates Q/S/C/R/E | fuente de verdad de aprobación de release hotelera H45 |
| docs/reference/frontend/hoteles-primera-victoria-h46.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-primera-victoria-h46.md | Contrato H46 de primera victoria, onboarding implícito, jerarquía, empty/demo honesto, guardar frente a seguir, auth contextual, confirmaciones, estados, i18n, accesibilidad, instrumentación y gate browser | fuente de verdad de activación inicial de /hoteles H46 |
| docs/reference/frontend/hoteles-mis-hoteles-reengagement-h47.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-mis-hoteles-reengagement-h47.md | Contrato H47 de re-engagement, superficie Mis hoteles, prioridad tracking/señales/guardados, estados, freshness/lifecycle, URL state, inbox/deep links, ownership V2, privacidad, i18n, a11y, instrumentación y browser QA | fuente de verdad de retorno útil de /hoteles H47 |
| docs/reference/backend/hoteles-busquedas-guardadas-compartibles-h48.md | backend | vivo | conservar | docs/reference/backend/hoteles-busquedas-guardadas-compartibles-h48.md | Contrato H48 de StayQuery versionada, URLs anónimas compartibles, SavedHotelSearch privado, ownership/lifecycle, restore, auth, cache/redaction, no provider calls implícitas y QA | fuente de verdad de búsquedas hoteleras guardadas/compartibles H48 |
| docs/reference/frontend/hoteles-personalizacion-prudente-h49.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-personalizacion-prudente-h49.md | Contrato H49 de personalización prudente, preferencias declaradas/contextuales/inferidas, recommended explicable, cold start, controles, reset/borrado, privacidad, fairness, estados, i18n, accesibilidad, flags, rollback y QA | fuente de verdad de personalización hotelera H49 |
| docs/reference/backend/hoteles-monetizacion-afiliacion-atribucion-h50.md | backend | vivo | conservar | docs/reference/backend/hoteles-monetizacion-afiliacion-atribucion-h50.md | Contrato H50 de independencia de ranking, PartnerLink, disclosure, consentimiento, atribución privacy-safe, conversiones, ledger, reconciliación, presupuestos, kill switch, canary y QA | fuente de verdad de monetización hotelera H50 |
| docs/reference/frontend/hoteles-experimentos-hipotesis-guardrails-h51.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-experimentos-hipotesis-guardrails-h51.md | Contrato H51 de hipótesis, variantes, asignación, exposición, métricas, MDE/stopping, SRM/novelty, guardrails, consentimiento, a11y, flags, rollback y decision records | fuente de verdad de experimentación hotelera H51 |
| docs/reference/frontend/hoteles-feedback-correcciones-confianza-h52.md | frontend | vivo | conservar | docs/reference/frontend/hoteles-feedback-correcciones-confianza-h52.md | Contrato H52 de taxonomía de feedback, evidencia redacted, ownership, severidad, lifecycle, correcciones reversibles, privacidad, abuso, métricas TTA/TTT/TTFA/TTR, inbox, experimentos y QA | fuente de verdad de feedback y correcciones de confianza hoteleras H52 |
| docs/reference/backend/hoteles-catalogo-matching-deduplicacion-h53.md | backend | vivo | conservar | docs/reference/backend/hoteles-catalogo-matching-deduplicacion-h53.md | Contrato H53 de identidad canónica, aliases provider, normalización, candidate generation, scoring, hard negatives, revisión ambigua, gold set, merge/split, ledger, rollback, métricas y reconciliación downstream | fuente de verdad de calidad de catálogo y matching hotelero H53 |
| docs/reference/backend/hoteles-mercados-entrada-salida-h54.md | backend | vivo | conservar | docs/reference/backend/hoteles-mercados-entrada-salida-h54.md | Contrato H54 de MarketSpec, matriz provider/mercado/capability, cobertura, ocupación, precio, fees, locale, coste, canary, kill switch, rollback, soporte y criterios de entrada/salida | fuente de verdad de expansión y operación de mercados hoteleros H54 |
| docs/reference/backend/hoteles-continuidad-disaster-recovery-h55.md | backend | vivo | conservar | docs/reference/backend/hoteles-continuidad-disaster-recovery-h55.md | Contrato H55 de continuidad, backup/export, restore aislado, RPO/RTO medidos, migraciones, workers/leases, delivery, reconciliación, privacidad, recovery drills y gates de implementación | fuente de verdad de continuidad y recuperación hotelera H55 |
| docs/reference/backend/hoteles-revision-anual-roadmap-h56.md | backend | vivo | conservar | docs/reference/backend/hoteles-revision-anual-roadmap-h56.md | Contrato H56 de paquete de evidencia anual, calidad de métricas, revisión de producto/confianza, providers/mercados/capabilities, costes FinOps, experimentos, personalización, monetización, flags, deuda, decision records y siguiente roadmap | fuente de verdad de gobernanza y revisión anual hotelera H56 |
| docs/qa/hoteles-h56-annual-review-template.md | qa | vivo | conservar | docs/qa/hoteles-h56-annual-review-template.md | Plantilla operativa H56 para recopilar evidencia anual, métricas, providers, mercados, costes, flags, feedback y estados de calidad sin inventar resultados | paquete inicial de evidencia H56 en estado evidence_incomplete |
| docs/qa/hoteles-h56-decision-record-template.md | qa | vivo | conservar | docs/qa/hoteles-h56-decision-record-template.md | Plantilla H56 de DecisionRecord con estados canónicos, checklist de aprobación, owners, evidencia, rollback y siguiente roadmap | registro inicial de decisiones H56 en estado evidence_incomplete |
| docs/qa/hoteles-h56-annual-review-2026-08-05.md | qa | vivo | conservar | docs/qa/hoteles-h56-annual-review-2026-08-05.md | Primer paquete ejecutado H56 con 81 tests locales Mock/mockeados, worker desactivado, audit de Alembic y limitaciones de producción | evidencia local H56 en estado evidence_incomplete |
| docs/qa/hoteles-h56-decision-record-2026-08-05.md | qa | vivo | conservar | docs/qa/hoteles-h56-decision-record-2026-08-05.md | DecisionRecord inicial H56 basado en baseline local, sin aprobación de providers, mercados, costes, tracking diario o siguiente roadmap | decisión H56 inicial en estado evidence_incomplete |
| docs/reference/backend/hoteles-real-offer-tracking-h23.md | backend | vivo | conservar | docs/reference/backend/hoteles-real-offer-tracking-h23.md | Contrato H23 de creación desde oferta real, contexto reconstruible, snapshot inicial, estados, idempotencia, ownership, inmutabilidad y migración V1→V2 | fuente de verdad de creación de tracking hotelero H23 |
| docs/reference/backend/hoteles-price-history-curve-h24.md | backend | vivo | conservar | docs/reference/backend/hoteles-price-history-curve-h24.md | Contrato H24 de histórico ligado a oferta, elegibilidad, agregados, variaciones, gaps, providers, estados y curva accesible | fuente de verdad de histórico y curva de precio hotelera H24 |
| docs/reference/backend/hoteles-freshness-confidence-actions-h25.md | backend | vivo | conservar | docs/reference/backend/hoteles-freshness-confidence-actions-h25.md | Contrato H25 de freshness contextual, provenance, confidence, comparabilidad, recomendaciones prudentes, refresh seguro, copy y QA | fuente de verdad de calidad accionable y recomendaciones hoteleras H25 |
| docs/reference/backend/hoteles-alert-rules-dedupe-h26.md | backend | vivo | conservar | docs/reference/backend/hoteles-alert-rules-dedupe-h26.md | Contrato H26 de reglas de alerta, baselines elegibles, estados, fingerprints, cooldown, dedupe, ownership, eventos y QA | fuente de verdad de alertas deterministas y deduplicación hotelera H26 |
| docs/reference/backend/hoteles-private-inbox-deeplinks-h27.md | backend | vivo | conservar | docs/reference/backend/hoteles-private-inbox-deeplinks-h27.md | Contrato H27 de inbox privado hotelero, ownership por origen, read/unread, migración legacy, deep links contextuales, privacidad, seguridad y QA | fuente de verdad de inbox y navegación segura hotelera H27 |
| docs/reference/backend/hoteles-delivery-retries-preferences-h28.md | backend | vivo | conservar | docs/reference/backend/hoteles-delivery-retries-preferences-h28.md | Contrato H28 de delivery hotelero, canales, consentimiento, quiet hours, retries, backoff, idempotencia, dead letter, privacidad, observabilidad y QA | fuente de verdad de entrega hotelera H28 |
| docs/plans/2026-08-04-community-trending-persistence-inbox.md | plan | vivo | conservar | docs/plans/2026-08-04-community-trending-persistence-inbox.md | Mega plan implementado y verificado para persistencia diaria de tendencias comunitarias, ownership/read-state del inbox, retención, rollback y verificación | conservar como diseño e historial; contratos y runbooks vivos reflejan el estado operativo |
| docs/plans/2026-07-30-next-dev-compilation.md | plan | vivo | conservar | docs/plans/2026-07-30-next-dev-compilation.md | Plan de implementación para Turbopack y calentamiento controlado de rutas estáticas | docs/plans/2026-07-30-next-dev-compilation.md |
| docs/plans/2026-07-30-next-dev-compilation-design.md | plan | vivo | conservar | docs/plans/2026-07-30-next-dev-compilation-design.md | Diseño aprobado para acelerar Next.js en desarrollo y calentar rutas estáticas en segundo plano | docs/plans/2026-07-30-next-dev-compilation-design.md |
| docs/plans/2026-07-28-community-pricing-design.md | plan | vivo | conservar | docs/plans/2026-07-28-community-pricing-design.md | Diseño aprobado para recopilar y agregar precios reales por viajero desde Watchlist | docs/plans/2026-07-28-community-pricing-design.md |
| docs/plans/2026-07-28-community-pricing.md | plan | vivo | conservar | docs/plans/2026-07-28-community-pricing.md | Plan de implementación full-stack de Community Pricing con privacidad por umbral | docs/plans/2026-07-28-community-pricing.md |
| docs/archive/plans/2026-07-21-live-flight-tracking-watchlist.md | plan | archivado | conservar | docs/archive/plans/2026-07-21-live-flight-tracking-watchlist.md | Brainstorming, riesgos, arquitectura, fases y QA completados de Live flight tracking desde Watchlist | docs/archive/plans/2026-07-21-live-flight-tracking-watchlist.md |
| docs/plans/2026-06-04-hoteles-correcciones-post-cierre.md | plan | vivo | conservar | docs/plans/2026-06-04-hoteles-correcciones-post-cierre.md | Plan de 5 fases (A-E) de correcciones post-cierre para el modulo /hoteles | docs/plans/2026-06-04-hoteles-correcciones-post-cierre.md |
| docs/plans/2026-06-08-puerta-a-puerta-plan-aterrizado-real.md | plan | vivo | conservar | docs/plans/2026-06-08-puerta-a-puerta-plan-aterrizado-real.md | Plan operativo aterrizado para evolucionar `/puerta-a-puerta` con foco en honestidad, contratos y utilidad incremental real | docs/plans/2026-06-08-puerta-a-puerta-plan-aterrizado-real.md |
| docs/plans/2026-06-09-puerta-a-puerta-siguientes-10-fases.md | plan | vivo | conservar | docs/plans/2026-06-09-puerta-a-puerta-siguientes-10-fases.md | Roadmap de 10 fases adicionales para expandir cobertura, pricing real, orquestación avanzada y rollout por mercados | docs/plans/2026-06-09-puerta-a-puerta-siguientes-10-fases.md |
| docs/plans/2026-06-09-puerta-a-puerta-plan-10-fases-activacion-real.md | plan | vivo | conservar | docs/plans/2026-06-09-puerta-a-puerta-plan-10-fases-activacion-real.md | Plan de 10 fases centrado en activar capacidades reales de `/puerta-a-puerta` por valor, dependencias y cobertura util | docs/plans/2026-06-09-puerta-a-puerta-plan-10-fases-activacion-real.md |
| docs/plans/2026-06-10-quick-search-shared-cache-implementation.md | plan | vivo | conservar | docs/plans/2026-06-10-quick-search-shared-cache-implementation.md | Plan de implementacion en 15 fases para una cache compartida, persistente y cross-user de quick-search con recomposicion por unidades exactas | docs/plans/2026-06-10-quick-search-shared-cache-implementation.md |
| docs/plans/2026-06-10-redis-hot-layer-plan.md | plan | vivo | conservar | docs/plans/2026-06-10-redis-hot-layer-plan.md | Plan de diseno en 7 fases para anadir Redis como hot layer opcional sobre la cache persistente DB sin cambiar el contrato actual | docs/plans/2026-06-10-redis-hot-layer-plan.md |
| docs/plans/2026-06-09-puerta-a-puerta-siguientes-10-fases.md | plan | vivo | conservar | docs/plans/2026-06-09-puerta-a-puerta-siguientes-10-fases.md | Roadmap de las siguientes 10 fases para expandir la activacion real del modulo tras el checkpoint actual | docs/plans/2026-06-09-puerta-a-puerta-siguientes-10-fases.md |
| docs/product/dashboard.md | product | vivo | conservar | docs/product/dashboard.md | Resumen funcional vivo por ?rea de producto | docs/product/dashboard.md |
| docs/product/policies-page.md | product | vivo | conservar | docs/product/policies-page.md | Resumen funcional vivo por ?rea de producto | docs/product/policies-page.md |
| docs/product/quick-search.md | product | vivo | conservar | docs/product/quick-search.md | Resumen funcional vivo por ?rea de producto | docs/product/quick-search.md |
| docs/product/watchlist.md | product | vivo | conservar | docs/product/watchlist.md | Resumen funcional vivo por ?rea de producto | docs/product/watchlist.md |
| docs/prompts/README.md | contexto IA | vivo | conservar | docs/prompts/README.md | Gu?a de organizaci?n de prompts y contexto IA | docs/prompts/README.md |
| docs/prompts/codex-travel-roadmap-50-fases.md | contexto IA | vivo | conservar | docs/prompts/codex-travel-roadmap-50-fases.md | Roadmap operativo de 50 fases para agentes durante el ciclo de viaje; no sustituye contratos vivos | docs/prompts/codex-travel-roadmap-50-fases.md |
| docs/prompts/legacy/prompt-root-legacy.txt | prompt | hist?rico | conservar | docs/prompts/legacy/prompt-root-legacy.txt | Prompt legacy preservado | ninguna; material hist?rico |
| docs/qa/README.md | QA | vivo | conservar | docs/qa/README.md | Navegaci?n y matriz reutilizable de QA | docs/qa/README.md |
| docs/qa/reports/2026-07-21-watchlist-live-flight-tracking.json | QA | vivo | conservar | docs/qa/reports/2026-07-21-watchlist-live-flight-tracking.json | Resultado reproducible de Playwright para polling, errores, multi-leg, mapa y responsive dual-theme | docs/runbooks/runbook-live-flight-tracking.md |
| docs/qa/reports/2026-07-21-zero-cost-live-provider-fallback.md | QA | vivo | conservar | docs/qa/reports/2026-07-21-zero-cost-live-provider-fallback.md | Evidencia de fallback, cuotas concurrentes, migración recuperable y arranque real sin coste | docs/qa/reports/2026-07-21-zero-cost-live-provider-fallback.md |
| docs/qa/reports/2026-07-28-fare-comparison-manual-qa.md | QA | vivo | conservar | docs/qa/reports/2026-07-28-fare-comparison-manual-qa.md | Evidencia manual de cálculo, estados incompletos, persistencia y responsive dual-theme para precio comparable | docs/product/quick-search.md; docs/product/watchlist.md |
| docs/qa/reports/2026-07-30-next-dev-compilation.md | QA | vivo | conservar | docs/qa/reports/2026-07-30-next-dev-compilation.md | Evidencia de tiempos, calentamiento secuencial, opt-out, navegador, build y auditoría de runtime de Next.js | docs/plans/2026-07-30-next-dev-compilation.md |
| docs/qa/reports/2026-08-01-community-route-intelligence.md | QA | vivo | conservar | docs/qa/reports/2026-08-01-community-route-intelligence.md | Evidencia API, browser, responsive, dual-theme y privacidad de las cinco señales comunitarias de rutas | docs/plans/2026-08-01-community-route-intelligence.md; docs/product/dashboard.md; docs/product/watchlist.md |
| docs/qa/acceptance-checklists/frontend-pr-checklist.md | QA | vivo | conservar | docs/qa/acceptance-checklists/frontend-pr-checklist.md | Checklist reutilizable de QA | docs/qa/acceptance-checklists/frontend-pr-checklist.md |
| docs/qa/hotels-pending-closeout.md | QA | vivo | conservar | docs/qa/hotels-pending-closeout.md | Checklist viva de cierre operativo para `/hoteles` con deudas pendientes y checks | docs/qa/hotels-pending-closeout.md |
| docs/archive/qa-reports/quick-search-testsprite-strict-report-2026-04-23.md | QA | archivado | conservar | docs/archive/qa-reports/quick-search-testsprite-strict-report-2026-04-23.md | Reporte activo y ligero, separado del hist?rico cerrado | docs/qa/reports/quick-search-testsprite-strict-report-2026-04-23.md |
| docs/qa/testsprite/skillsprite-user-capabilities.md | QA | vivo | conservar | docs/qa/testsprite/skillsprite-user-capabilities.md | Referencia activa para TestSprite y QA funcional | docs/qa/testsprite/skillsprite-user-capabilities.md |
| docs/qa/testsprite/testsprite-catalog.md | QA | vivo | conservar | docs/qa/testsprite/testsprite-catalog.md | Referencia activa para TestSprite y QA funcional | docs/qa/testsprite/testsprite-catalog.md |
| docs/qa/traceability-matrix.md | QA | vivo | conservar | docs/qa/traceability-matrix.md | Navegaci?n y matriz reutilizable de QA | docs/qa/traceability-matrix.md |
| docs/archive/qa-visual/color-palette-audit.md | QA | archivado | conservar | docs/archive/qa-visual/color-palette-audit.md | Auditoria canonica de paleta dual dark/light con enfoque de calidez y claridad visual | docs/qa/visual/color-palette-audit.md |
| docs/reference/README.md | overview | vivo | conservar | docs/reference/README.md | Referencia t?cnica o de proceso activa | docs/reference/README.md |
| docs/reference/backend/quick-search-acceptance-checklist.md | backend | vivo | conservar | docs/reference/backend/quick-search-acceptance-checklist.md | Referencia t?cnica backend can?nica | docs/reference/backend/quick-search-acceptance-checklist.md |
| docs/reference/backend/quick-search-contract.md | backend | vivo | conservar | docs/reference/backend/quick-search-contract.md | Referencia t?cnica backend can?nica | docs/reference/backend/quick-search-contract.md |
| docs/reference/backend/live-flight-tracking-contract.md | backend | vivo | conservar | docs/reference/backend/live-flight-tracking-contract.md | Contrato canónico de identidad, snapshots y endpoint operacional de Watchlist | docs/reference/backend/live-flight-tracking-contract.md |
| docs/reference/codex-operating-contract.md | contexto IA | vivo | conservar | docs/reference/codex-operating-contract.md | Contrato operativo complementario para agentes | docs/reference/codex-operating-contract.md |
| docs/reference/done-checklist.md | overview | vivo | conservar | docs/reference/done-checklist.md | Referencia t?cnica o de proceso activa | docs/reference/done-checklist.md |
| docs/reference/feature-flags.md | reference | vivo | conservar | docs/reference/feature-flags.md | Mapa vivo de flags por dominio, fuentes canonicas de activacion y legacy preservado para trazabilidad | docs/reference/feature-flags.md |
| docs/reference/final-report-template.md | overview | vivo | conservar | docs/reference/final-report-template.md | Referencia t?cnica o de proceso activa | docs/reference/final-report-template.md |
| docs/reference/quick-search-weather-policy.md | product | vivo | conservar | docs/reference/quick-search-weather-policy.md | Pol?tica funcional activa de quick search | docs/reference/quick-search-weather-policy.md |
| docs/reference/ui-visible-language-guide.md | reference | vivo | conservar | docs/reference/ui-visible-language-guide.md | Guia canonica para humanizar lenguaje visible sin tocar labels de producto, contratos ni nombres internos | docs/reference/ui-visible-language-guide.md |
| docs/archive/reports/docs-sanitize-audit.md | historical | hist?rico | conservar | docs/archive/reports/docs-sanitize-audit.md | Reporte de auditor?a y saneamiento documental | docs/reports/docs-sanitize-audit.md |
| docs/runbooks/runbook-activation-profiles.md | runbook | vivo | conservar | docs/runbooks/runbook-activation-profiles.md | Perfiles canónicos de activación por entorno (local_demo, local_real, staging_safe, prod_gradual) con matriz de flags y blindaje anti-mock | docs/runbooks/runbook-activation-profiles.md |
| docs/runbooks/runbook-canary-rollback.md | runbook | vivo | conservar | docs/runbooks/runbook-canary-rollback.md | Runbook operativo activo | docs/runbooks/runbook-canary-rollback.md |
| docs/runbooks/runbook-db-retention.md | runbook | vivo | conservar | docs/runbooks/runbook-db-retention.md | Runbook operativo activo | docs/runbooks/runbook-db-retention.md |
| docs/runbooks/runbook-public-tunnels.md | runbook | vivo | conservar | docs/runbooks/runbook-public-tunnels.md | Runbook operativo activo para la publicacion web mediante Cloudflare Tunnel y Tailscale Funnel | docs/runbooks/runbook-public-tunnels.md |
| docs/runbooks/runbook-oom.md | runbook | vivo | conservar | docs/runbooks/runbook-oom.md | Runbook operativo activo | docs/runbooks/runbook-oom.md |
| docs/runbooks/runbook-provider-degraded.md | runbook | vivo | conservar | docs/runbooks/runbook-provider-degraded.md | Runbook operativo activo | docs/runbooks/runbook-provider-degraded.md |
| docs/runbooks/runbook-live-flight-tracking.md | runbook | vivo | conservar | docs/runbooks/runbook-live-flight-tracking.md | Activación, verificación, degradación y rollback del proveedor operacional de Watchlist | docs/runbooks/runbook-live-flight-tracking.md |
| docs/runbooks/runbook-route-canonicalization.md | runbook | vivo | conservar | docs/runbooks/runbook-route-canonicalization.md | Runbook operativo activo | docs/runbooks/runbook-route-canonicalization.md |
| docs/runbooks/runbook-ui-captures.md | runbook | vivo | conservar | docs/runbooks/runbook-ui-captures.md | Runbook operativo activo | docs/runbooks/runbook-ui-captures.md |
| docs/runbooks/runbook-watchlist-uniqueness-migration.md | runbook | vivo | conservar | docs/runbooks/runbook-watchlist-uniqueness-migration.md | Runbook operativo activo | docs/runbooks/runbook-watchlist-uniqueness-migration.md |
| docs/specs/README.md | spec | vivo | conservar | docs/specs/README.md | Especificaci?n activa | docs/specs/README.md |
| docs/specs/policies/policies-page-acceptance-checklist.md | spec | vivo | conservar | docs/specs/policies/policies-page-acceptance-checklist.md | Especificaci?n activa | docs/specs/policies/policies-page-acceptance-checklist.md |
| docs/specs/policies/policies-page-component-spec.md | spec | vivo | conservar | docs/specs/policies/policies-page-component-spec.md | Especificaci?n activa | docs/specs/policies/policies-page-component-spec.md |
| docs/specs/policies/policies-page-copy-deck-es.md | spec | vivo | conservar | docs/specs/policies/policies-page-copy-deck-es.md | Especificaci?n activa | docs/specs/policies/policies-page-copy-deck-es.md |
| docs/specs/policies/policies-page-rewrite.md | spec | vivo | conservar | docs/specs/policies/policies-page-rewrite.md | Especificaci?n activa | docs/specs/policies/policies-page-rewrite.md |
| docs/specs/product/dashboard-redesign-v2.md | spec | vivo | conservar | docs/specs/product/dashboard-redesign-v2.md | Especificaci?n activa | docs/specs/product/dashboard-redesign-v2.md |
| docs/specs/ui/ui-changes.md | spec | vivo | conservar | docs/specs/ui/ui-changes.md | Especificaci?n activa | docs/specs/ui/ui-changes.md |
| docs/ui/UI_CONTRACT_V1.md | frontend | vivo | conservar | docs/ui/UI_CONTRACT_V1.md | Contrato visual y sistema UI canonico con identidad calida y no generica | docs/ui/UI_CONTRACT_V1.md |
| docs/ui/UI_SYSTEM_V1.md | frontend | vivo | conservar | docs/ui/UI_SYSTEM_V1.md | Contrato visual y sistema UI canonico con identidad calida y no generica | docs/ui/UI_SYSTEM_V1.md |
| docs/ui/UI_VISUAL_QA_CHECKLIST.md | frontend | vivo | conservar | docs/ui/UI_VISUAL_QA_CHECKLIST.md | Contrato visual y sistema UI can?nico | docs/ui/UI_VISUAL_QA_CHECKLIST.md |
| docs/ui/estetica.md | frontend | vivo | conservar | docs/ui/estetica.md | Contrato visual y sistema UI canonico con identidad calida y no generica | docs/ui/estetica.md |
| fases/_extraido_txt/FASE_10_Futuras_Escalabilidades_Viru.txt | historical | duplicado | eliminar candidato | docs/archive/fases/transcripts/FASE_10_Futuras_Escalabilidades_Viru.txt | Transcripci?n duplicada ya preservada en archive | docs/archive/fases/transcripts/FASE_10_Futuras_Escalabilidades_Viru.txt |
| fases/_extraido_txt/FASE_1_Analisis_de_Documentacion_Viru.txt | historical | duplicado | eliminar candidato | docs/archive/fases/transcripts/FASE_1_Analisis_de_Documentacion_Viru.txt | Transcripci?n duplicada ya preservada en archive | docs/archive/fases/transcripts/FASE_1_Analisis_de_Documentacion_Viru.txt |
| fases/_extraido_txt/FASE_2_Arquitectura_Global_Viru.txt | historical | duplicado | eliminar candidato | docs/archive/fases/transcripts/FASE_2_Arquitectura_Global_Viru.txt | Transcripci?n duplicada ya preservada en archive | docs/archive/fases/transcripts/FASE_2_Arquitectura_Global_Viru.txt |
| fases/_extraido_txt/FASE_3_Backend_Viru.txt | historical | duplicado | eliminar candidato | docs/archive/fases/transcripts/FASE_3_Backend_Viru.txt | Transcripci?n duplicada ya preservada en archive | docs/archive/fases/transcripts/FASE_3_Backend_Viru.txt |
| fases/_extraido_txt/FASE_4_Frontend_Viru.txt | historical | duplicado | eliminar candidato | docs/archive/fases/transcripts/FASE_4_Frontend_Viru.txt | Transcripci?n duplicada ya preservada en archive | docs/archive/fases/transcripts/FASE_4_Frontend_Viru.txt |
| fases/_extraido_txt/FASE_5_Base_de_Datos_Viru.txt | historical | duplicado | eliminar candidato | docs/archive/fases/transcripts/FASE_5_Base_de_Datos_Viru.txt | Transcripci?n duplicada ya preservada en archive | docs/archive/fases/transcripts/FASE_5_Base_de_Datos_Viru.txt |
| fases/_extraido_txt/FASE_6_DevOps_Despliegue_Viru.txt | historical | duplicado | eliminar candidato | docs/archive/fases/transcripts/FASE_6_DevOps_Despliegue_Viru.txt | Transcripci?n duplicada ya preservada en archive | docs/archive/fases/transcripts/FASE_6_DevOps_Despliegue_Viru.txt |
| fases/_extraido_txt/FASE_7_Mejoras_Propuestas_Viru.txt | historical | duplicado | eliminar candidato | docs/archive/fases/transcripts/FASE_7_Mejoras_Propuestas_Viru.txt | Transcripci?n duplicada ya preservada en archive | docs/archive/fases/transcripts/FASE_7_Mejoras_Propuestas_Viru.txt |
| fases/_extraido_txt/FASE_8_Testing_Viru.txt | historical | duplicado | eliminar candidato | docs/archive/fases/transcripts/FASE_8_Testing_Viru.txt | Transcripci?n duplicada ya preservada en archive | docs/archive/fases/transcripts/FASE_8_Testing_Viru.txt |
| fases/_extraido_txt/FASE_9_Documentacion_Tecnica_Extensa_Viru.txt | historical | duplicado | eliminar candidato | docs/archive/fases/transcripts/FASE_9_Documentacion_Tecnica_Extensa_Viru.txt | Transcripci?n duplicada ya preservada en archive | docs/archive/fases/transcripts/FASE_9_Documentacion_Tecnica_Extensa_Viru.txt |
| fases/_extraido_txt/INDICE_MAESTRO_VIRU_IA_NAVEGACION.txt | historical | duplicado | eliminar candidato | docs/archive/fases/transcripts/INDICE_MAESTRO_VIRU_IA_NAVEGACION.txt | Transcripci?n duplicada ya preservada en archive | docs/archive/fases/transcripts/INDICE_MAESTRO_VIRU_IA_NAVEGACION.txt |
| skills/viru-air-context/SKILL.md | contexto IA | vivo | conservar | skills/viru-air-context/SKILL.md | Contexto reusable para agentes dentro de Viru | skills/viru-air-context/SKILL.md |
| skills/viru-air-context/references/operating-rules.md | contexto IA | vivo | conservar | skills/viru-air-context/references/operating-rules.md | Contexto reusable para agentes dentro de Viru | skills/viru-air-context/references/operating-rules.md |
| skills/viru-air-context/references/project-context.md | contexto IA | vivo | conservar | skills/viru-air-context/references/project-context.md | Contexto reusable para agentes dentro de Viru | skills/viru-air-context/references/project-context.md |
| users_prueba.txt | sensitive | sensible | revisar manualmente | users_prueba.txt | Posible dato personal o material de prueba sensible | revisi?n manual requerida |

## Actualizacion manual 2026-05-12 (F3C.2)

Entradas vivas agregadas:

- `docs/runbooks/runbook-notification-worker.md`
- `backend/tests/integration/test_notification_worker.py`

## Actualizacion manual 2026-05-12 (release closure)

Entradas vivas agregadas:

- `docs/archive/qa-reports/2026-05-12-release-closure.md`

Entradas vivas actualizadas:

- `docs/archive/qa-reports/2026-05-12-fases-0-3-audit.md`
- `docs/overview/current-state.md`

## Actualizacion manual 2026-05-12 (watchlist W0 baseline)

Entradas vivas agregadas:

- `docs/archive/qa-reports/2026-05-12-watchlist-w0-baseline.md`
- `docs/archive/qa-screenshots/watchlist-w0-baseline.png`

## Actualizacion manual 2026-05-13 (watchlist W1 layout)

Entradas vivas agregadas:

- `docs/archive/qa-reports/2026-05-12-watchlist-w1-layout.md`

## Actualizacion manual 2026-05-13 (watchlist W2 single route selection)

Entradas vivas agregadas:

- docs/archive/qa-reports/2026-05-12-watchlist-w2-single-route-selection.md


## Actualizacion manual 2026-05-13 (watchlist W3 contextual actions)

Entradas vivas agregadas:

- docs/archive/qa-reports/2026-05-12-watchlist-w3-contextual-actions.md

## Actualizacion manual 2026-05-13 (watchlist W4 routes heading)

Entradas vivas agregadas:

- docs/archive/qa-reports/2026-05-12-watchlist-w4-routes-heading.md

## Actualizacion manual 2026-05-13 (watchlist W5 history confidence)

Entradas vivas agregadas:

- docs/archive/qa-reports/2026-05-12-watchlist-w5-history-confidence.md

## Actualizacion manual 2026-05-13 (watchlist W6 actionable freshness)

Entradas vivas agregadas:

- docs/archive/qa-reports/2026-05-12-watchlist-w6-actionable-freshness.md

## Actualizacion manual 2026-05-13 (watchlist W7 map empty state)

Entradas vivas agregadas:

- docs/archive/qa-reports/2026-05-12-watchlist-w7-map-empty-state.md


## Actualizacion manual 2026-05-13 (watchlist W8 reactive compare)

Entradas vivas agregadas:

- docs/archive/qa-reports/2026-05-12-watchlist-w8-reactive-compare.md

## Actualizacion manual 2026-05-13 (watchlist W9 final polish)

Entradas vivas agregadas:

- docs/archive/qa-reports/2026-05-12-watchlist-w9-final-polish.md
- docs/qa/screenshots/watchlist-w9-final.png


## Actualizacion manual 2026-05-13 (watchlist W9.1 final remedy)

Entradas vivas agregadas:

- docs/archive/qa-reports/2026-05-12-watchlist-w9-1-final-remedy.md

## Actualizacion manual 2026-05-13 (watchlist W9.2 history rescue)

Entradas vivas agregadas:

- docs/archive/qa-reports/2026-05-12-watchlist-w9-2-history-rescue.md


## Actualizacion manual 2026-05-27 (DuckDNS domain setup)

Entradas historicas agregadas y retiradas posteriormente:

- docs/runbooks/runbook-duckdns-public-domain.md
- `infra/Caddyfile`
- infra/docker-compose.prod.yml
- `infra/.env.prod.example`

Entradas vivas actualizadas:

- infra/docker-compose.yml
- infra/docker-compose.relaunch.yml
- `backend/.env.example`
- `frontend/.env.example`
- `backend/app/main.py`
- `docs/INDICE_UNICO.md`

## Actualizacion manual 2026-05-20 (Puerta a puerta V1)

Entradas vivas agregadas:

- `docs/product/door-to-door.md`
- `docs/reference/backend/door-to-door-contract.md`

Entradas vivas actualizadas:

- `docs/INDICE_UNICO.md`

## Actualizacion manual 2026-06-09 (puerta-a-puerta F9+F10 cierre del plan)

Entradas vivas agregadas:

- `docs/qa/qa-puerta-a-puerta.md`
- `backend/app/door_to_door/providers/gtfs_corridors.json`

Entradas vivas actualizadas:

- `docs/product/door-to-door.md`
- `docs/reference/backend/door-to-door-contract.md`
- `docs/runbooks/runbook-gtfs-activacion.md`
- `docs/DOCS_INVENTORY.md`
## Actualizacion manual 2026-07-21 (Live flight tracking desde Watchlist)

Entradas vivas agregadas:

- `docs/adr/ADR-005-live-operational-flight-tracking.md`
- `docs/reference/backend/live-flight-tracking-contract.md`
- `docs/runbooks/runbook-live-flight-tracking.md`
- `docs/qa/reports/2026-07-21-watchlist-live-flight-tracking.json`

Entrada archivada agregada:

- `docs/archive/plans/2026-07-21-live-flight-tracking-watchlist.md`

Entradas vivas actualizadas:

- `docs/product/watchlist.md`

## Actualizacion manual 2026-07-21 (Fallback operacional sin coste)

Entrada viva agregada:

- `docs/adr/ADR-006-zero-cost-operational-provider-fallback.md`

Evidencia QA agregada:

- `docs/qa/reports/2026-07-21-zero-cost-live-provider-fallback.md`

Entradas vivas actualizadas:

- `docs/adr/ADR-005-live-operational-flight-tracking.md`
- `docs/reference/backend/live-flight-tracking-contract.md`
- `docs/runbooks/runbook-live-flight-tracking.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`
- `docs/overview/current-state.md`
- `docs/engineering/backend.md`
- `docs/reference/README.md`
- `docs/reference/backend/quick-search-contract.md`
- `docs/qa/README.md`
- `docs/INDICE_UNICO.md`
- `docs/plans/README.md`
- `HISTORY.md`

## Actualizacion manual 2026-08-06 (runtime hotelero)

Entradas vivas agregadas:

- `docs/runbooks/hotels-runtime-activation.md`

Motivo:

- Runbook operativo para publicar la imagen GHCR, crear el Secret `viru-backend-runtime`, ejecutar la migracion y activar el CronJob de sweep Mock (overlay `infra/k8s/overlays/staging/`, plantilla `infra/k8s/runtime-secret.example.yaml`), con verificacion y rollback.
