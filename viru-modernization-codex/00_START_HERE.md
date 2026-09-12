# Viru — Modernization Pack for Codex

Este paquete define una migración progresiva orientada a **reducir AI slop**, aumentar observabilidad y hacer que el proyecto sea mucho más fácil de comprender y modificar por agentes como Codex.

## Regla principal

**No implementes todo de golpe.** Lee todos los documentos para entender el destino, pero ejecuta **una etapa cada vez**, en orden, y no pases a la siguiente hasta que los gates de la etapa actual estén verdes.

## Orden recomendado

### Fase 0 — entender y congelar comportamiento
1. `00_GLOBAL_GUARDRAILS.md`
2. `00_BACKEND_AUDIT.md`
3. `01_PLAYWRIGHT.md`
4. `02_BIOME.md`
5. `03_TYPESCRIPT_STRICT.md`

### Fase 1 — convertir la API en un contrato verificable
6. `04_OPENAPI.md`
7. `05_ORVAL.md`
8. `06_TANSTACK_QUERY.md`
9. `07_ZOD.md`

### Fase 2 — estado y datos
10. `08_SUPABASE.md`
11. `09_DRIZZLE_DECISION.md` — **decision gate, no instalación automática**

### Fase 3 — UI y medición
12. `10_SHADCN_UI.md`
13. `11_POSTHOG.md`
14. `12_OPENTELEMETRY.md`

### Fase 4 — infraestructura solo cuando exista necesidad demostrable
15. `13_VALKEY.md`
16. `14_TRIGGER_DEV.md`
17. `15_TYPESENSE.md`
18. `16_TEMPORAL.md`

## Criterio para tecnologías opcionales

Valkey, Trigger.dev, Typesense, Drizzle y Temporal **no se instalan porque sean modernas**. Cada archivo contiene un decision gate. Si el proyecto no presenta el problema que solucionan, Codex debe marcarlo `NOT_APPLICABLE` o `DEFERRED` y no añadir dependencias.

## Estrategia de commits

Un commit por unidad lógica. Ejemplos:

- `test(e2e): establish playwright baseline`
- `chore(tooling): add biome without behavior changes`
- `refactor(api): formalize openapi response models`
- `chore(api): generate frontend client with orval`
- `refactor(data): migrate watchlists to supabase`

Nunca mezclar en el mismo commit una migración de datos irreversible con un rediseño visual o una limpieza masiva no relacionada.

## Archivos auxiliares que Codex debe crear en Viru

- `MIGRATION_STATUS.md` — bitácora de cada etapa.
- `docs/architecture/current.md` — arquitectura real antes de migrar.
- `docs/architecture/target.md` — arquitectura objetivo actualizada conforme se toman decisiones.
- `docs/architecture/adr/` — ADRs para decisiones importantes (p.ej. Supabase como source of truth, o decisión de no usar Drizzle).
- `docs/runbooks/rollback/` — rollback de migraciones de datos o infraestructura.

## Definition of Done global

Una etapa está acabada cuando: comportamiento relevante cubierto por tests; gates verdes; documentación actualizada; no queda una segunda implementación activa sin fecha de retirada; y el rollback es viable.
