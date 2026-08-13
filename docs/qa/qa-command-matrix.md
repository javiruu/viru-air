# Matriz QA por area

**Estado:** vivo  
**Ultima revision:** 2026-08-09
**Fuente de verdad:** si  
**Area:** QA

## Objetivo

Consolidar los comandos minimos y el tipo de evidencia esperado por superficie
para validar cambios sin depender de memoria de sesion ni de wrappers dudosos.

## Criterio operativo

- `canonico`: comando o check respaldado por scripts activos, docs vivas o ambos.
- `heredado/contextual`: util en ciertos flujos, pero no debe asumirse como gate
  universal.
- `requiere validacion humana`: la verificacion terminal no basta; hace falta
  revision manual en UI o flujo real.

## Matriz

| Area | Objetivo | Comando minimo | Evidencia esperada | Clasificacion | Notas de bloqueo o advertencia |
|---|---|---|---|---|---|
| Frontend general | Detectar problemas basicos de calidad en UI y app privada | `cd frontend && npm run lint` | Salida de lint sin errores bloqueantes; warnings documentados si son preexistentes | canonico | Verificacion actual sin warnings |
| Backend general | Verificar cambios backend por suite focalizada antes de ampliar alcance | `cd backend && python -m pytest -q` | Tests de la superficie tocada en verde | heredado/contextual | No usar la suite completa como gate minimo en cambios documentales o muy acotados |
| Quick Search | Validar cache compartida y contrato cercano al cambio | `cd C:\Users\javiru\Desktop\viru-air && python -m pytest backend\tests\unit\test_quick_search_cache_models.py -q` | `17 passed` o equivalente focalizado | canonico | La cache persistente V2.1 existe; no usar docs antiguas que aun hablen de cache solo en memoria |
| Quick Search | Validar regresiones de pantalla y estados visibles | `cd frontend && npm test -- --test-name-pattern="quick-search-screen-state|quick-search-refactor-utils|quick-search-dual-regression|quick-search-response-normalizer"` | Tests de UI/logica en verde | canonico | Complementar con revision humana si el cambio altera layout, loading, empty o copy |
| Watchlist/Alertas | Verificar estabilizacion minima de flujos guardados e historico | `cd C:\Users\javiru\Desktop\viru-air && python -m pytest backend\tests\integration\test_watchlist_flow.py backend\tests\integration\test_watchlist_refresh_cooldown.py -q` | Integraciones focalizadas en verde | heredado/contextual | El runbook de estabilizacion sigue siendo la referencia viva para diagnostico |
| Watchlist/Señales | Confirmar flujo visible real | Abrir `/watchlist` o `/notifications?view=rules` con cuenta limpia y seguir checklist del runbook | Ruta, interaccion, resultado observado y feedback humano | requiere validacion humana | La QA visual final depende de revision manual del usuario en navegador real |
| Puerta a puerta | Verificar contrato y deeplinks sin tocar providers externos | `cd backend && python -m pytest tests/unit/test_door_to_door_deeplinks.py -q` | `24 passed` o equivalente focalizado | canonico | Test ejecutado y en verde en esta sesion |
| Puerta a puerta | Verificar estructura frontend del modulo | `cd frontend && node --import tsx --test tests/door-to-door-v1.test.tsx` | Suite estructural/render en verde | canonico | Complementar con dark/light y mobile si hay cambio visible |
| Hoteles | Verificar tipado/cierre tecnico en frontend hotelero | `cd frontend && npx tsc --noEmit` | Comprobacion de TypeScript sin errores en la superficie tocada | canonico | El frontend no tiene script dedicado de typecheck |
| Hoteles | Verificar contrato y flujo backend hotelero | `cd backend && python -m pytest tests/unit/test_hotels_*.py tests/integration/test_hotels_*.py` | Suites hoteleras en verde | canonico | La validacion visual manual de `/hoteles` sigue pendiente como deuda viva |
| Hoteles | Confirmar UX real del radar hotelero | Abrir `/hoteles` y revisar dark/light/responsive/focus/copy | Ruta, pasos y evidencia observada | requiere validacion humana | Pendiente recurrente documentado en `docs/qa/hotels-pending-closeout.md` |
| Hoteles | Baseline lab reproducible de rendimiento | `cd frontend && MSYS_NO_PATHCONV=1 SKIP_SERVER=1 BASE_URL=http://127.0.0.1:<qa-port> PERF_AUTH_API_BASE=http://127.0.0.1:8000/api/v1 PERF_ROUTES=/hoteles PERF_PROFILES=desktop,mobile,fast3g PERF_JSON=1 PERF_HOTELS_FLOW=1 PERF_HOTELS_CITY=Madrid PERF_OUTPUT_DIR=../docs/qa/evidence/hotels-h36-auth-baseline-<run> LOGIN_EMAIL='<qa>' LOGIN_PASSWORD='<qa-password>' node scripts/perf_profile_playwright.cjs` | Markdown + JSON con TTFB/LCP/CLS/hitos/requests hoteleras y errores de consola | canonico | En Git Bash requiere `MSYS_NO_PATHCONV=1`; usar un build/puerto QA sano y una cuenta efímera. Evidencia válida actual: `docs/qa/evidence/hotels-h36-auth-baseline-3400-final/perf_playwright_20260808T153149.{md,json}`. Una ronda local no equivale a INP, p75 de producción ni cumplimiento de Web Vitals |
| Hoteles | Gate R de recorrido real autenticado y solo lectura | `cd frontend && E2E_BASE_URL=http://127.0.0.1:<qa-port> E2E_API_BASE_URL=http://127.0.0.1:8000/api/v1 GATE_R_OUTPUT_DIR=../docs/qa/evidence/hotels-h36-gate-r-<run> LOGIN_EMAIL='<qa>' LOGIN_PASSWORD='<qa-password>' node scripts/qa_hotels_gate_r.mjs` | JSON sanitizado con búsqueda, selección, autocomplete/area-search, error, empty, paridad, cancelación, requests GET y errores redacted | canonico | No pulsa tracking/watchlist/alertas/comp-set/ingest. La evidencia válida actual está en `docs/qa/evidence/hotels-h36-gate-r-3500/`; 503 y `ERR_ABORTED` son simulaciones/resultado esperado, no regresiones. `GATE_R_TRACE=1` es opt-in y no debe conservarse con sesión autenticada sin auditoría |
| Hoteles | Gate M responsive/performance lab, autenticado y solo lectura | `cd frontend && E2E_BASE_URL=http://127.0.0.1:<qa-port> E2E_API_BASE_URL=http://127.0.0.1:8000/api/v1 GATE_M_OUTPUT_DIR=../docs/qa/evidence/hotels-h36-gate-m-<run> LOGIN_EMAIL='<qa>' LOGIN_PASSWORD='<qa-password>' node scripts/qa_hotels_gate_m.mjs` | JSON sanitizado por perfil con status/auth, shell/primer resultado, TTFB/LCP/CLS, long tasks observacionales, foco, overflow visual, requests hoteleras, 5xx, escrituras, errores y privacidad | canonico | Perfiles `desktop`, `tablet`, `mobile`, `fast3g-cpu4`; Fast 3G/CPU4 se emula por CDP. Evidencia válida actual: `docs/qa/evidence/hotels-h36-gate-m-3602/`; una ronda lab no equivale a INP, p75 de producción, RUM ni latencia real del provider. `html` usa zoom 75% en desktop: el runner usa overflow visual normalizado, no `scrollWidth` bruto |
| Hoteles | Gate F RUM lab opt-in y privacy-safe | `cd frontend && E2E_BASE_URL=http://127.0.0.1:<qa-port> E2E_API_BASE_URL=http://127.0.0.1:8000/api/v1 GATE_F_OUTPUT_DIR=../docs/qa/evidence/hotels-h36-gate-f-<run> LOGIN_EMAIL='<qa>' LOGIN_PASSWORD='<qa-password>' node scripts/qa_hotels_gate_f.mjs` | JSON sanitizado con consentimiento ausente/concedido, nombres de eventos, conteos RUM, payload failures, consola y privacidad | canonico | Evidencia válida actual: `docs/qa/evidence/hotels-h36-gate-f-3603-final/`; intercepta `/ux/events` sin persistir telemetría QA, valida solo `hotel_rum_vitals` y no demuestra p75 de producción, INP oficial ni field compliance |
| Hoteles admin | Smoke visual de cabina de observabilidad | `cd frontend && E2E_BASE_URL=http://127.0.0.1:<qa-port> ADMIN_HOTELS_OUTPUT_DIR=../docs/qa/evidence/h41-admin-hotels-observability node scripts/qa_admin_hotels_observability.mjs` | `report.json` + capturas Chromium desktop/mobile × light/dark; título, health observado, runs recientes, controles budget/circuit, leases/expiración, outcomes por provider, filtros, tabla, filtro provider, focus, overflow visual y consola | canonico | Usa token sintético y API mockeada, incluidos `/admin/hotels/health` y `/admin/hotels/provider-controls`; evidencia vigente: `docs/qa/evidence/h41-admin-hotels-observability/`; requiere un servidor QA autenticable/mock-compatible; no sustituye revisión humana, Firefox/WebKit ni backend/provider live |
| Documentacion | Verificar coherencia de docs tocadas | Revisar links, rutas y fuentes vivas referenciadas | Paths validos y ausencia de contradiccion nueva | canonico | `rg` esta disponible de nuevo y debe usarse para busquedas repo; PowerShell queda como fallback nativo de Windows |

## Hallazgos confirmados en esta iteracion

- El baseline autenticado H36 válido se ejecutó el 2026-08-08 en build aislado/puerto QA `3400`: `/hoteles` y asset estático devolvieron 200, los tres perfiles renderizaron shell y primer resultado, hubo 9 GETs hoteleras por perfil y no hubo errores de consola. La evidencia está en `docs/qa/evidence/hotels-h36-auth-baseline-3400-final/`.
- Gate R se ejecutó el 2026-08-08 en build aislado/puerto QA `3500` con `frontend/scripts/qa_hotels_gate_r.mjs`: ciudad, selección, autocomplete/area-search (empty válido), error controlado, empty controlado, error de paridad controlado y cancelación por navegación pasaron; solo hubo `ERR_ABORTED` esperado y 503 simulados esperados. Evidencia sanitizada: `docs/qa/evidence/hotels-h36-gate-r-3500/gate-r.json`. El trace es opt-in (`GATE_R_TRACE=1`) y no se conserva con sesión autenticada sin auditoría.
- Gate M se ejecutó el 2026-08-08 en build aislado/puerto QA `3602` con `frontend/scripts/qa_hotels_gate_m.mjs`: los cuatro perfiles pasaron HTTP 200, auth lista, resultados, foco, overflow visual y controles read-only; `failedGateMAssertions=0`. Evidencia sanitizada: `docs/qa/evidence/hotels-h36-gate-m-3602/gate-m.json`. Fast 3G/CPU4 observó tareas largas, pero siguen siendo métricas observacionales; el gate no declara cumplimiento de INP/p75/RUM.
- Gate F se repitió el 2026-08-08 en build aislado/puerto QA `3603` con `frontend/scripts/qa_hotels_gate_f.mjs`: sin consentimiento hubo `rumEventsSeen=0`; con consentimiento hubo un `hotel_rum_vitals` válido; `failedGateFAssertions=0`, cero errores de consola y cero violaciones de privacidad. Evidencia sanitizada: `docs/qa/evidence/hotels-h36-gate-f-3603-final/gate-f.json`. El canal compartido también emitió `dashboard_view`, que no se clasifica como RUM. Esto cierra la verificación lab del contrato opt-in, no el field/RUM de producción ni p75/INP oficial.
- Los puertos `3000`, `3100`, `3200` y `3300` produjeron artefactos inválidos o conflictos de procesos durante el diagnóstico; no se usan como baseline válido.

- El lint de frontend funciona y no emite warnings en la verificacion actual.
- `cd backend && python -m pytest -q` pasa con `945 passed, 2 skipped`.
- `cd frontend && npm test` pasa con `421 passed, 17 skipped`; los skips son
  E2E que requieren frontend/backend locales o sesion auth cuando no estan levantados.
- `cd frontend && npm run build` pasa.
- `cd frontend && npx tsc --noEmit` pasa.
- `cd frontend && npm run test:e2e:quick-search` pasa contra backend/frontend
  locales levantados en esta sesion.
- `python -m pytest backend\tests\unit\test_quick_search_cache_models.py -q`
  pasa en esta sesion.
- `python -m pytest tests/unit/test_door_to_door_deeplinks.py -q` pasa en esta
  sesion.
- `rg` vuelve a estar disponible para exploracion local; PowerShell queda como fallback
  nativo de Windows.
