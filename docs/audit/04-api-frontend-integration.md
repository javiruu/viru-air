# 04 — API, Frontend, Generated Code e Integracion Real

**Fecha:** 2026-09-12  
**Commit auditado:** 91e6717d9bbd43d4ba148c6a114426266fabb823  

## Matriz de Integracion por Tecnologia

| Tecnologia | Installed | Wired | Used | Old path removed | Tests | Status |
|---|---:|---:|---:|---:|---:|---|
| **OpenAPI Export** | Si | Si | Si | N/A | `test_openapi_contract.py` | `VERIFIED_OK` |
| **Orval Generated Client** | Si (`orval.config.ts`) | Si (`api:check`) | **NO** (0 call sites en src) | **NO** (100% fetch manual activo) | `orval-client.test.ts` | `PARTIAL_SCAFFOLD` |
| **TanStack React Query** | Si (package.json) | Si (`QueryProvider` en layout) | **NO** (0 `useQuery`, 243 `useEffect`) | **NO** | `layout.tsx` wrapper | `PARTIAL_SCAFFOLD` |
| **shadcn/ui Primitives** | Si (`button, badge, card`) | No | **NO** (0 imports en pantallas) | **NO** | `shadcn-ui-primitives.test.tsx` | `DEFERRED` |
| **PostHog Analytics** | Si (`posthog-js`) | No | **NO** (0 llamadas a `trackEvent`) | **NO** | `posthog-governance.test.ts` | `PARTIAL_SCAFFOLD` |
| **OpenTelemetry Backend** | Si (`opentelemetry-sdk`) | No | **NO** (0 imports en `app/main.py`) | N/A | `test_telemetry.py` | `LOCAL_ONLY_SCAFFOLD` |
| **Zod Validation** | Si (`zod`) | No | **NO** (0 imports en entrypoints) | N/A | `runtime-validation-zod.test.ts` | `PARTIAL_SCAFFOLD` |
| **Biome Linter** | Si (`biome.json`) | Si (scripts npm) | Evaluado sobre 852 archivos (1.021 errors) | **NO** (ESLint sigue activo) | N/A | `COEXISTENCE_DEFERRED` |
| **Playwright E2E** | Si (`playwright.config.ts`) | Si | Si (6 tests en 3 specs) | N/A | 6 tests | `VERIFIED_OK` |

## Analisis Detallado
1. **OpenAPI y Orval:**
   - La regeneracion desde `backend/scripts/export_openapi.py` es 100% determinista (121 paths unicos, 151 operaciones, 0 diff tras regeneraciones consecutivas).
   - `npm run api:check` valida que los tipos generados en `frontend/src/api/generated/` estan sincronizados con el schema.
   - **Diagnostico de adopcion:** Ninguna pagina o componente de `frontend/src/` importa todavia `src/api/generated/`. Las llamadas de red siguen realizandose a traves del cliente HTTP manual (`src/modules/shared/api.ts`).

2. **TanStack Query:**
   - `QueryProvider` esta correctamente configurado con politicas de proteccion (`staleTime: 30s`, `refetchOnWindowFocus: false`) en `frontend/src/app/layout.tsx`.
   - La aplicacion cuenta con 243 ocurrencias de `useEffect`. No se ha realizado una migracion forzada a `useQuery` para respetar la regla contra refactors masivos destructivos.

3. **Arquitectura de Dominio:**
   - No hay bifurcacion dual activa: el producto mantiene un unico camino en ejecucion (`UI -> fetch manual -> FastAPI endpoint -> SQLAlchemy Repository -> DB`).
   - Los modulos nuevos existen en aislamiento como scaffolds sin competir con los caminos productivos.

