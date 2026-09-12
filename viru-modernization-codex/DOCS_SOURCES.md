# Índice de documentación oficial consultada

Este archivo existe para que Codex tenga una lista corta de fuentes canónicas y no empiece la implementación leyendo blogs SEO o snippets antiguos. Cada guía contiene fuentes específicas adicionales.

- Playwright: https://playwright.dev/docs/
- Biome: https://biomejs.dev/
- TypeScript: https://www.typescriptlang.org/docs/
- OpenAPI Specification: https://spec.openapis.org/oas/
- FastAPI: https://fastapi.tiangolo.com/
- Orval: https://orval.dev/docs/
- TanStack Query: https://tanstack.com/query/latest/docs/framework/react/overview
- Zod: https://zod.dev/
- Supabase: https://supabase.com/docs
- Drizzle: https://orm.drizzle.team/docs/overview
- shadcn/ui: https://ui.shadcn.com/docs
- PostHog: https://posthog.com/docs
- OpenTelemetry: https://opentelemetry.io/docs/
- Valkey: https://valkey.io/topics/
- Trigger.dev: https://trigger.dev/docs/introduction
- Typesense: https://typesense.org/docs/
- Temporal: https://docs.temporal.io/

## Regla para agentes

Siempre preferir documentación oficial y, cuando exista `llms.txt`/Markdown para agentes (por ejemplo Temporal, Typesense, Trigger.dev, OpenTelemetry en varias áreas), usarla para recuperar documentación actual con menos ruido. No confiar en memoria del modelo para APIs que cambian rápido.
