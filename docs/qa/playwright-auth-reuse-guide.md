# Playwright/Auth Reuse Guide (Viru Tracker)

Objetivo: evitar empezar desde cero en cada conversacion cuando hay que validar flujos reales con login/sesion usando Playwright.

## Regla base

- Reutilizar primero tests, helpers, scripts y reportes existentes.
- Solo crear nuevos flujos cuando falte cobertura real para el caso pedido.

## Referencias principales ya existentes

- E2E con guardas de sesion/auth:
  - `frontend/tests/quick-search-network-guards.e2e.test.ts`
  - `frontend/tests/quick-search-loading-transition.e2e.test.ts`
  - `frontend/tests/quick-search-testsprite-strict.e2e.test.ts`
  - `frontend/tests/quick-search-testsprite-ultra-strict.e2e.test.ts`
- Scripts QA Playwright:
  - `frontend/scripts/qa_capture_notification_login.mjs`
  - `frontend/scripts/qa_quick_search_visual.mjs`
  - `frontend/scripts/perf_profile_playwright.cjs`
- Evidencia previa:
  - `docs/qa/reports/quick-search-auth-flow-report.json`
  - `docs/qa/reports/quick-search-auth-verified-report.json`
  - `docs/qa/reports/quick-search-visual-report.json`
  - `docs/qa/reports/2026-05-12-watchlist-w0-baseline.md`

## Flujo operativo minimo recomendado

1. Arrancar backend y frontend segun comandos del repo.
2. Ejecutar primero el test/script mas cercano al caso actual (no crear uno nuevo de entrada).
3. Si el flujo requiere sesion, reutilizar el patron existente:
   - crear usuario/token contra `/api/v1/auth/register` o `/api/v1/auth/login`;
   - inyectar token en `localStorage` (`viru_token`) antes de navegar cuando aplique.
4. Validar ruta objetivo en navegador automatizado y capturar evidencia.
5. Guardar resultado en `docs/qa/reports/` solo si aporta evidencia nueva relevante.

## No hacer

- No reinstalar Playwright/Chromium por defecto.
- No duplicar scripts/tests que ya cubren lo mismo con otro nombre.
- No declarar "no se puede verificar" sin antes intentar un flujo reutilizable existente.
