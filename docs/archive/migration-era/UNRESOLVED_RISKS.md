# Unresolved Risks

**Fecha:** 2026-09-16
**Alcance:** Estado consolidado tras el cierre del cutover de modernización y la verificación adversarial completa.

Este documento registra únicamente los riesgos reales que permanecen diferidos, con su severidad, justificación y acción sugerida. Los riesgos de la auditoría del 2026-09-12 (`maplibre-gl <= 6.4.0`, avisos Next.js/sharp, discrepancias de formato con Biome) quedaron **resueltos**; el detalle está en `POST_MIGRATION_AUDIT.md`.

## 1. Adopción de TanStack Query pendiente por pantalla (SL-08)
- **Severidad:** P2 / Media
- **Descripción:** El `QueryProvider` está activo en `RootLayout` y el cliente Orval genera hooks tipados de React Query, pero las pantallas históricas conservan sus `useEffect` manuales contra `src/modules/shared/api.ts`.
- **Motivo de diferimiento:** Los flujos actuales están probados y estables (620 tests frontend, 6/6 E2E); una migración forzada en bloque añadiría riesgo de regresión visual sin beneficio inmediato.
- **Next Action / Owner:** Migrar pantalla a pantalla, empezando por una superficie de bajo riesgo (p. ej. preferencias), usando los hooks generados por Orval.

## 2. Pruebas locales de Supabase (`supabase test db`)
- **Severidad:** P2 / Informativa
- **Descripción:** Ausencia de CLI de Supabase en la estación de trabajo local.
- **Motivo de diferimiento:** La autoridad DDL ya es Supabase migrations sobre PostgreSQL; sin entorno local no se puede ejecutar el reset/test del CLI. No existe doble autoridad: el backend no crea esquema en runtime y exige `DB_URL`.
- **Next Action / Owner:** Configurar un proyecto remoto de Supabase para validar el baseline canónico con `supabase db reset` antes del primer despliegue real.

## 3. Playwright multi-navegador (Firefox/WebKit)
- **Severidad:** P3 / Baja
- **Descripción:** La suite E2E (6 tests, 3 specs) se ejecuta solo en Chromium local con 1 worker.
- **Motivo de diferimiento:** Suficiente para los journeys críticos actuales; ampliar navegadores pertenece al ciclo de CI.
- **Next Action / Owner:** Añadir proyectos Firefox/WebKit en `playwright.config.ts` cuando se formalice CI.

## 4. Exportador OpenTelemetry a Collector (OTLP)
- **Severidad:** P3 / Baja
- **Descripción:** `backend/app/core/telemetry.py` inicializa SDK y traza spans con redacción de atributos sensibles, pero no hay exporter de red configurado (clasificado `LOCAL_ONLY_SCAFFOLD`).
- **Motivo de diferimiento:** Sin entorno productivo todavía; activar OTLP requiere Collector y decisión de backend de trazas.
- **Next Action / Owner:** Configurar OTLP en el arranque productivo, junto a la decisión de Valkey documentada en `docs/architecture/adr/0002-infrastructure-gates.md`.
