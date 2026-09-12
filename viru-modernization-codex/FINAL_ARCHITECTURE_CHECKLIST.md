# Checklist de arquitectura objetivo

No es obligatorio marcar todas las tecnologías como instaladas. El objetivo es una arquitectura pequeña y explícita.

- [ ] Los journeys críticos están cubiertos por Playwright.
- [ ] Lint/format/typecheck están automatizados.
- [ ] El frontend no adivina DTOs del backend; OpenAPI/Orval gobiernan el contrato si aplica.
- [ ] Server state React usa TanStack Query si React es el stack real.
- [ ] Datos externos no confiables se validan runtime en los boundaries necesarios.
- [ ] Supabase, si se adopta, tiene migrations reproducibles, tests RLS y generated types.
- [ ] Solo existe una autoridad de migrations/schema de DB.
- [ ] UI primitives no están duplicadas entre múltiples librerías.
- [ ] Analytics/replay respetan privacidad y no son dependencia crítica del producto.
- [ ] Backend tiene trazas/métricas suficientes antes de añadir caches/colas.
- [ ] Valkey solo existe si hay caso medido y sigue siendo disposable/reconstructible cuando actúa como cache.
- [ ] Jobs tienen retries/idempotency/concurrency conscientes; Trigger.dev solo si aporta valor.
- [ ] Search index es derivado y reconstruible; Typesense solo si mejora un caso medido.
- [ ] Temporal solo si existe un caso de workflow durable que justifique la plataforma.
- [ ] No hay implementaciones `old/new/v2/final` duplicadas sin plan de retirada.
- [ ] `MIGRATION_STATUS.md` y ADRs explican las decisiones actuales.
