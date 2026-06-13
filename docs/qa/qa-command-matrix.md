# Matriz QA por area

**Estado:** vivo  
**Ultima revision:** 2026-06-13  
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
| Frontend general | Detectar problemas basicos de calidad en UI y app privada | `cd frontend && npm run lint` | Salida de lint sin errores bloqueantes; warnings documentados si son preexistentes | canonico | En esta sesion hay warnings preexistentes en `HotelSearchPanel.tsx`, `useHotelSearch.ts` y `QuickSearchView.tsx` |
| Backend general | Verificar cambios backend por suite focalizada antes de ampliar alcance | `cd backend && python -m pytest -q` | Tests de la superficie tocada en verde | heredado/contextual | No usar la suite completa como gate minimo en cambios documentales o muy acotados |
| Quick Search | Validar cache compartida y contrato cercano al cambio | `cd C:\Users\javiru\Desktop\viru-tracker && python -m pytest backend\tests\unit\test_quick_search_cache_models.py -q` | `17 passed` o equivalente focalizado | canonico | La cache persistente V2.1 existe; no usar docs antiguas que aun hablen de cache solo en memoria |
| Quick Search | Validar regresiones de pantalla y estados visibles | `cd frontend && npm test -- --test-name-pattern="quick-search-screen-state|quick-search-refactor-utils|quick-search-dual-regression|quick-search-response-normalizer"` | Tests de UI/logica en verde | canonico | Complementar con revision humana si el cambio altera layout, loading, empty o copy |
| Watchlist/Alertas | Verificar estabilizacion minima de flujos guardados e historico | `cd C:\Users\javiru\Desktop\viru-tracker && python -m pytest backend\tests\integration\test_watchlist_flow.py backend\tests\integration\test_watchlist_refresh_cooldown.py -q` | Integraciones focalizadas en verde | heredado/contextual | El runbook de estabilizacion sigue siendo la referencia viva para diagnostico |
| Watchlist/Alertas | Confirmar flujo visible real | Abrir `/watchlist` o `/alerts` con cuenta limpia y seguir checklist del runbook | Ruta, interaccion, resultado observado y feedback humano | requiere validacion humana | La QA visual final depende de revision manual del usuario en navegador real |
| Puerta a puerta | Verificar contrato y deeplinks sin tocar providers externos | `cd backend && python -m pytest tests/unit/test_door_to_door_deeplinks.py -q` | `24 passed` o equivalente focalizado | canonico | Test ejecutado y en verde en esta sesion |
| Puerta a puerta | Verificar estructura frontend del modulo | `cd frontend && node --import tsx --test tests/door-to-door-v1.test.tsx` | Suite estructural/render en verde | canonico | Complementar con dark/light y mobile si hay cambio visible |
| Hoteles | Verificar tipado/cierre tecnico en frontend hotelero | `cd frontend && npx tsc --noEmit` | Typecheck sin errores en la superficie tocada | canonico | `npm run typecheck` no existe como script dedicado |
| Hoteles | Verificar contrato y flujo backend hotelero | `cd backend && python -m pytest tests/unit/test_hotels_*.py tests/integration/test_hotels_*.py` | Suites hoteleras en verde | canonico | La validacion visual manual de `/hoteles` sigue pendiente como deuda viva |
| Hoteles | Confirmar UX real del radar hotelero | Abrir `/hoteles` y revisar dark/light/responsive/focus/copy | Ruta, pasos y evidencia observada | requiere validacion humana | Pendiente recurrente documentado en `docs/qa/hotels-pending-closeout.md` |
| Documentacion | Verificar coherencia de docs tocadas | Revisar links, rutas y fuentes vivas referenciadas | Paths validos y ausencia de contradiccion nueva | canonico | `rg` no estuvo disponible en esta sesion; se uso PowerShell (`Select-String`, `Get-Content`) como fallback |

## Hallazgos confirmados en esta iteracion

- `npm run lint` funciona, pero arroja warnings preexistentes y no relacionados con
  este cambio documental.
- `python -m pytest backend\tests\unit\test_quick_search_cache_models.py -q`
  pasa en esta sesion.
- `python -m pytest tests/unit/test_door_to_door_deeplinks.py -q` pasa en esta
  sesion.
- `rg` no estuvo disponible; para exploracion local se usaron comandos nativos de
  PowerShell.
