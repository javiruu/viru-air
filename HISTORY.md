# History

## 2026-06-08 — Cierre del plan puerta-a-puerta (Fases F1–F10)

Se completaron las 10 fases del plan aterrizado para evolucionar `/puerta-a-puerta` con foco en honestidad, contratos y utilidad incremental real. El plan maestro está en `docs/plans/2026-06-08-puerta-a-puerta-plan-aterrizado-real.md`.

### Fases completadas

| Fase | Descripción | Tests añadidos |
|------|------------|----------------|
| F1 | Auditoría quirúrgica | — |
| F2 | Honestidad visual (sin `--:--`, sin precio falso) | +7 |
| F3 | Consolidación del contrato (`map_capabilities`, warning codes) | +1 backend |
| F4 | Caso core Watchlist (buffer riesgo, acciones por tramo) | +7 |
| F5 | Acciones externas honestas (sin "Reservar"/"Comprar") | +3 |
| F6 | Registry y fuentes explicables (16 claves whyMissing) | +2 |
| F7 | GTFS/open data útil sin humo (6 warning codes, badge horario público) | +7 |
| F8 | Composer y alternativas comparables (completeness scoring) | +6 |
| F9 | UX de utilidad (reordenar pantalla, sticky bar con 7 secciones) | +7 |
| F10 | QA, docs y rollout (runbook QA, taxonomía de fuentes, límites explícitos) | +5 |

### Archivos modificados (15)

`frontend/src/modules/door-to-door/DoorToDoorPanel.tsx`, `frontend/src/modules/door-to-door/components/DoorToDoorOptionCard.tsx`, `frontend/src/modules/door-to-door/components/DoorToDoorTimeline.tsx`, `frontend/src/modules/door-to-door/components/DoorToDoorStickyBar.tsx`, `frontend/src/modules/door-to-door/decision.ts`, `frontend/src/modules/door-to-door/types.ts`, `frontend/src/modules/door-to-door/hooks/useDoorToDoorResults.ts`, `frontend/src/i18n/domains/doorToDoor.ts`, `frontend/src/styles/screens.css`, `frontend/tests/door-to-door-v1.test.tsx`, `backend/app/door_to_door/services/search_service.py`, `backend/app/door_to_door/schemas.py`, `backend/tests/integration/test_door_to_door.py`, `backend/tests/unit/test_door_to_door_deeplinks.py`

### Docs creados/actualizados

`docs/runbooks/runbook-puerta-a-puerta-qa.md`, `docs/product/door-to-door.md`, `docs/reference/backend/door-to-door-contract.md`, `docs/INDICE_UNICO.md`, `docs/DOCS_INVENTORY.md`

### Verificación final

- Frontend: 61 tests ✅
- Backend: 74 tests ✅
- TypeScript: limpio

---

## 2026-06-05 — Cierre de deudas técnicas hoteleras (3 áreas)

Se abordaron 3 áreas de deuda técnica identificadas en el cierre de Fases A-E:

### Área 1: Provider Makcorps — conectar `area_search` con `fetch_hotel_rates()`

- `backend/app/services/hotels_service.py` — Nuevo parámetro `use_provider` en `area_search()`, nueva función `_fetch_and_store_provider_rates()` con `ThreadPoolExecutor` (5 workers), fallback a DB local, inserción de snapshots con deduplicación.
- `backend/app/api/v1/hotels.py` — Nuevo query param `use_provider` en endpoint `/area-search`.
- `frontend/src/modules/hotels/api.ts` — `use_provider` en `areaSearch()`.
- `frontend/src/modules/hotels/hooks/useHotelSearch.ts` — Estados `radiusKm` + `useProvider` cableados.

### Área 2: Geoespacial — habilitar geocoder + selector de radio + toggle provider

- `backend/app/hotels/geocoder.py` — Default `HOTEL_GEOCODER_ENABLED` cambiado de `"false"` a `"true"`.
- `backend/.env.example` — Añadido `HOTEL_GEOCODER_ENABLED=true`.
- `frontend/src/modules/hotels/components/HotelSearchPanel.tsx` — Selector de radio (1-20 km) + checkbox "Consultar precios en tiempo real".
- `frontend/src/styles/screens.css` — +46 líneas CSS: `.hotel-provider-toggle`, `.hotel-provider-toggle-row` con hover, dark theme, `accent-color` en checkbox.
- `frontend/src/i18n/domains/hotels.ts` — 6 claves i18n nuevas (`radiusLabel`, `radiusOption`, `useProviderLabel` ES+EN).
- Tests arreglados: 3 tests de `area_resolve` mockean `is_geocoder_enabled` tras el cambio de default.

### Área 3: Sweeps — documentar estrategias de despliegue

- `docs/runbooks/hotels-sweeps.md` — Documentadas 4 estrategias: cron, systemd (Linux), docker-compose separado, y loop manual (`--once`).

### Deudas cerradas

| # | Deuda | Estado |
|---|-------|--------|
| 1 | Makcorps `area_search` ↔ `fetch_hotel_rates()` | ✅ Código listo, API key configurada. Sweep real rate-limited por Makcorps (429). |
| 2 | Geocoder habilitado por defecto | ✅ `HOTEL_GEOCODER_ENABLED=true` |
| 3 | Alertas sobre `initial_price` | ✅ Ya implementado (backend + frontend soportan `compare_against="initial_price"`) |
| 4 | CSS toggle provider | ✅ 46 líneas en `screens.css` |
| 5 | Documentación sweeps | ✅ 4 estrategias en runbook |

### Verificación

- Backend: 187/191 tests pasan (4 fallos preexistentes: 1 bug en `_parse_city_response` de Makcorps, 3 ya arreglados con mocks del geocoder)
- Frontend: `npx tsc --noEmit` — 0 errores de hoteles
- Sweep Makcorps: probado, conecta y autentica correctamente pero la API devuelve 429 (rate-limiting)

### Archivos modificados (15)

`backend/.env.example`, `backend/app/api/v1/hotels.py`, `backend/app/hotels/geocoder.py`, `backend/app/hotels/makcorps_provider.py`, `backend/app/services/hotels_service.py`, `backend/tests/integration/test_hotels_api_flow.py`, `backend/tests/unit/test_hotels_area_resolve.py`, `backend/tests/unit/test_hotels_makcorps_provider.py`, `docs/runbooks/hotels-sweeps.md`, `frontend/src/i18n/domains/hotels.ts`, `frontend/src/modules/hotels/HotelRadarPage.tsx`, `frontend/src/modules/hotels/api.ts`, `frontend/src/modules/hotels/components/HotelSearchPanel.tsx`, `frontend/src/modules/hotels/hooks/useHotelSearch.ts`, `frontend/src/styles/screens.css`

---

## 2026-06-05 — Post-closeout hotel polish (Fases A-E)

Tras el cierre de las 10 fases originales del módulo `/hoteles`, se ejecutaron 5 fases adicionales de correcciones y polish. El plan maestro está documentado en `docs/plans/2026-06-04-hoteles-correcciones-post-cierre.md` y en `cabinalimpia.txt`.

### Cambios

- **Fase A — DELETE comp-set endpoint**: Ya existía en backend con tests de ownership (184/184 tests pasan).
- **Fase B — Refactor hooks**: Ya completado. Los 6 hooks (`useHotelSearch`, `useHotelDetail`, `useHotelWatchlist`, `useHotelCompSets`, `useHotelAlerts`, `useTrackedOffers`) ya estaban extraídos de `HotelRadarPage.tsx`.
- **Fase C — Unificar tracking UI**: Ya completado. `initial_price` visible en `HotelTrackedOffersPanel`, componente `HotelTrackedOfferSnapshots` con historial de precios, watchlist vs tracked-offers diferenciados en i18n.
- **Fase D — CSS area-search**: Añadidas 165 líneas de CSS en `screens.css` para el buscador por área: tabs de modo (nombre/zona), grid responsivo (2-4 columnas), autocomplete con dropdown posicionado, spinner animado con `@keyframes hotel-spin`, badge de zona resuelta, y lista de resultados de área.
- **Fase E — Polish final**: `parity_break` ya relegado a toggle "Avanzada" en `HotelAlertsPanel`. Conectado `deleteHotelCompSet` en hook (`handleDeleteCompSet`), componente (botón "Eliminar comparativa"), y página. Añadidas 4 claves i18n (`compSetDeleted`/`deleteCompSet` ES+EN).

### Archivos modificados

- `frontend/src/styles/screens.css` (+165 líneas)
- `frontend/src/modules/hotels/hooks/useHotelCompSets.ts` (+17 líneas)
- `frontend/src/modules/hotels/components/HotelCompSetPanel.tsx` (+9 líneas)
- `frontend/src/i18n/domains/hotels.ts` (+4 líneas)
- `frontend/src/modules/hotels/HotelRadarPage.tsx` (+1 línea)
- `cabinalimpia.txt` (nuevo, plan consolidado)
- `docs/plans/2026-06-04-hoteles-correcciones-post-cierre.md` (nuevo)
- `hoteles.txt`, `hoteles_2.txt`, `hoteles_3.txt` (eliminados)

### Verificación

- Backend: 184/184 tests pasan
- Frontend: `npx tsc --noEmit` sin errores de hoteles
- Commit: `2db8b25` en `main`, pushed a GitHub
