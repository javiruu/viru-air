# History

## 2026-07-05 - Iberia como provider publico de vuelos

- Quick Search registra `iberia`/`ib`/`iberia_ndc` en `FlightProviderRegistry`, dentro del orden por defecto, sin exigir credenciales privadas.
- `IberiaProvider` usa el contrato publico de la web de booking de Iberia (`/flights/` + `ibisservices.iberia.com/api/sse-avm/rs/v2/availability`), emite `iberia_provider_unavailable_total`/`provider_total_outage` cuando Akamai o la respuesta publica bloquean la consulta backend y expone `source=iberia-public-availability`.
- El frontend reconoce fuentes Iberia publicas e historicas en badges, carril de providers, resumen de fuentes, warnings y cobertura de Watchlist mediante el catalogo compartido.

## 2026-07-04 â€” Dashboard con descubrimiento ocasional y continuidad de busqueda

- El dashboard suma dos bloques contextuales y opcionales: `Viru encontro algo para ti`, que solo aparece con una oportunidad realmente alineada y barata, y `Donde estabas`, que recupera la ultima busqueda retomable del usuario.
- Quick Search guarda una unica busqueda util en `localStorage`, restaura ruta, fechas, ida/vuelta, flexibilidad, radio, cercanos, exclusiones y filtros visibles, y muestra una confirmacion suave al retomar.
- La restauracion ya no se degrada cuando cargan las preferencias del usuario: los defaults de `/preferences/search` dejan de sobrescribir un snapshot retomado.
- Verificacion focalizada: `npm test -- tests/dashboard-next-best-action.test.ts tests/dashboard-found-for-you.test.ts tests/quick-search-resume-search.test.ts tests/watchlist-refresh-affordances.test.ts tests/watchlist-w6-actionable-freshness.test.ts tests/quick-search-form-contract.test.ts tests/quick-search-visible-results.test.ts` -> 29 passed; `npm run build` OK; Playwright con mocks sobre `/dashboard` y `/quick-search?resume=1` en claro/oscuro y desktop/mobile.

## 2026-07-04 — Dashboard con siguiente mejor accion prioritaria

- El hero superior del dashboard ya no muestra una oportunidad placeholder: ahora prioriza una unica `Siguiente mejor accion` basada en senales reales de watchlist, historico de precios y alertas sin leer.
- La prioridad actual favorece bajadas fuertes, nuevos minimos, mejor precio mensual, alertas pendientes, rutas stale y estados tranquilos/onboarding cuando no hay nada fuerte que mirar.
- El dashboard recuerda la ultima accion debil ya vista para no reciclarla siempre si existe otra pista mejor disponible.
- Verificacion focalizada: `npm test -- tests/dashboard-next-best-action.test.ts tests/watchlist-refresh-affordances.test.ts tests/watchlist-w6-actionable-freshness.test.ts tests/quick-search-form-contract.test.ts tests/quick-search-visible-results.test.ts` -> 22 passed; `npm run build` OK.

## 2026-07-04 — Watchlist startup refresh con ventana de 4 horas

- El startup refresh de watchlist ya no encola rutas revisadas hace menos de 4 horas; las marca en el reporte interno como `fresh_skipped` sin llamar al proveedor ni crear `RevalidationJob`.
- Las rutas sin snapshot o con precio revisado hace 4 horas o mas siguen entrando en la cola de arranque, con deduplicacion por ruta compartida.
- `WATCHLIST_STARTUP_REFRESH_MAX_AGE_SECONDS` queda alineado en codigo y `.env.example` con el nuevo valor por defecto de 14.400 segundos.
- Verificacion focalizada: `python -m pytest backend/tests/unit/test_watchlist_manual_revalidation.py backend/tests/unit/test_watchlist_refresh_policy.py backend/tests/unit/test_watchlist_startup_refresh.py backend/tests/unit/test_watchlist_startup_refresh_regression.py` -> 13 passed.

## 2026-07-03 — Centro de notificaciones persistente

- Nueva pantalla privada `/notifications` con bandeja persistente para senales de precio, seguridad, digest y workers, con resumen, filtros, acciones de apertura y marcado de lectura.
- Nuevo contrato backend `/api/v1/notifications` que agrega `notification_event`, `hotel_alert_event` y `security_activity` sin duplicar el pipeline existente, mas estado de lectura por usuario en `user_notification_state`.
- La navegacion privada muestra un contador persistente de senales sin leer usando `/api/v1/notifications/summary`, y el borrado de cuenta/watch limpia estados de lectura asociados.
- Verificacion: test de integracion del inbox, migracion Alembic hasta `head`, lint backend focalizado, tests de navegacion frontend, `tsc`, `npm run build` y QA Playwright light/dark sobre `/notifications`.

## 2026-07-03 — easyJet Flight Connections más compatible

- El fallback Dohop/Flight Connections de easyJet acepta payloads `data.search.offers` además de `data.boundSearch.offers`, lee la salida desde el primer tramo cuando la ruta no trae `departure` y admite `transferUrl`/`transfer_url`.
- Los errores GraphQL de Flight Connections ya no se confunden con un resultado vacío: se elevan como outage canónico del provider para que Quick Search no esconda bloqueos operativos.
- Verificacion: `uv run ruff check .`, `uv run pytest tests/unit -q` -> 543 passed, degradación de providers -> 19 passed; smoke real BLQ->BER sigue bloqueado por EasyJet/Dohop desde backend y devuelve outage canónico.

## 2026-07-02 — easyJet conectado a Quick Search

- Quick Search registra `easyjet` como provider público sin API key dentro de `FlightProviderRegistry`, con aliases `easy_jet`, `easy-jet`, `ezj`, `ezy` y `u2`.
- El provider consulta `ejavailability/api/v16/availability/query`, mapea `AvailableFlights` a `ProviderFlight`, usa Flight Connections/Dohop como fallback para conexiones con escala, emite warnings canónicos y genera deeplinks oficiales de easyJet.
- El carril visual de proveedores reconoce fuentes `easyjet`, `easy-jet`, `easy_jet`, `ezj`, `ezy` y `u2` como `easyJet`, y muestra su icono corporativo.
- Verificacion: provider + registry + presentación frontend pasan en tests focalizados; smoke real de easyJet directo devuelve 403 de Akamai y Flight Connections devuelve 403 de Datadome desde esta máquina, ambos tratados como outage canónico salvo configuración operativa de bypass.

## 2026-06-30 — Vueling como provider público sin API key

- Quick Search puede cargar `vueling`/`vy` como provider adicional mediante `FlightProviderRegistry`.
- El provider crea una sesión anónima pública contra Vueling y consulta `avy/v3/AvailabilityServices/allFlights`, igual que Ryanair opera contra endpoints públicos sin API key.
- Los resultados Vueling mapean precio, moneda, hora local, source `vueling-public-availability` y deeplink oficial de búsqueda.
- Verificacion: provider + registry + orquestador + quick-search cercano -> 48 passed; smoke real Vueling BCN->ORY devolvio precio sin API key.

---

## 2026-06-30 — Panel local autorepara dependencias backend corruptas

- `iniciar_viru.ps1` ahora captura la salida real de la auditoria Alembic, detecta instalaciones Python incompletas o corruptas y repara `backend/.venv` una vez antes de abortar.
- El fallback cubre el caso de pip con metadata rota (`uninstall-no-record-file` / `RECORD` ausente) usando `--ignore-installed`.
- El auditor Alembic ya no falla en import-time si SQLAlchemy esta roto; devuelve un diagnostico JSON `db_error` para que el panel pueda actuar.
- Verificacion: arranque real con `iniciar_viru.ps1 -Foreground` reparo el venv, aplico migraciones y dejo backend/frontend en status 200; `python -m pytest backend/tests/unit/test_alembic_audit.py` -> 4 passed.

---

## 2026-06-30 — Watchlist startup refresh completo sin puntos planos

- El startup refresh de watchlist ahora encola todas las rutas activas compartidas al abrir el servidor, no solo las que superan `WATCHLIST_STARTUP_REFRESH_MAX_AGE_SECONDS`.
- La revalidacion por ruta sigue actualizando todos los watches activos de todos los usuarios, pero no persiste nuevos `PriceSnapshot` cuando el precio y la moneda no cambiaron y el dato anterior no era stale.
- Verificacion focalizada: `python -m pytest backend/tests/unit/test_watchlist_startup_refresh_regression.py -q` -> 2 passed.

---

## 2026-06-10 — Quick-search shared persistent cache (Fases 1–15 + auditoría + fixes)

Se implementó una cache compartida persistente (cross-user, DB-backed) para `quick-search` que reutiliza resultados de tracking de vuelos entre usuarios, con TTL por categoría de resultado y bloqueo anti-stampede. El plan maestro está en `docs/plans/2026-06-10-quick-search-shared-cache-implementation.md`.

### Fases completadas (15/15)

| Fase | Descripción | Estado |
|------|------------|--------|
| F1 | Contrato de cache compartida (quick-search-contract.md V2.1) | ✅ |
| F2 | Canonicalización de claves (`build_unit_cache_key`, `build_cache_source_hash`, `classify_cache_result`) | ✅ |
| F3 | Modelo persistente `QuickSearchCacheEntry` + migración 0030 + índices | ✅ |
| F4 | Servicio `quick_search_cache_service.py` (get/set/prune/serialize con `_DB_LOCK`) | ✅ |
| F5 | Serialización/deserialización de `ProviderFetchResult` ↔ JSON | ✅ |
| F6 | Integración read-through/write-through en `_fetch_with_cache` (L1→L2→provider) | ✅ |
| F7 | Reutilización para búsquedas ampliadas (nearby/flex comparten espacio de claves L2) | ✅ |
| F8 | Anti-stampede con `_FETCH_LOCKS` per-key + try/finally | ✅ |
| F9 | Política de TTL diferenciado: ready=24h, empty=2h, degraded=30min + outage→degraded | ✅ |
| F10 | Integración con watchlist (`_refresh_watch_now` consulta y puebla cache compartida) | ✅ |
| F11 | Feature flags (`QUICK_SEARCH_SHARED_CACHE_ENABLED` + 4 env vars de TTL) | ✅ |
| F12 | Observabilidad (l1_hits/l2_hits/provider_calls en logs y pipeline_counters) | ✅ |
| F13 | Pruning probabilístico (~10% requests) con daemon thread asíncrono | ✅ |
| F14 | QA de regresión (30 tests unitarios + 13 tests de integración de cache) | ✅ |
| F15 | Documentación final (contrato, backend.md, DOCS_INVENTORY, HISTORY) | ✅ |

### Auditoría de 9 fases y 5 fixes

Tras la implementación, se ejecutó una auditoría exhaustiva (`docs/plans/2026-06-10-quick-search-shared-cache-review-plan.md`) que encontró y corrigió 5 issues:

| ID | Severidad | Fix |
|----|-----------|-----|
| H1 | CRÍTICA | Sesiones SQLAlchemy por thread (`SessionLocal()`) en vez de compartir `db` |
| H2 | ALTA | Lock cleanup en `try/finally` — evita fuga de memoria si `fetch_flights()` lanza excepción |
| H3 | ALTA | Outages totales ahora se cachean como `degraded` (30min) en vez de `empty` (2h) |
| H4 | MEDIA | Watchlist respeta entradas `empty` del cache en vez de re-pegar al provider |
| R3.4 | MEDIA | `build_cache_source_hash` incluye `currency` para evitar cross-currency poisoning |
| H5 | MEDIA | Pruning asíncrono con daemon thread (`prune_expired_entries_async`) |

### Archivos creados (5)

`backend/app/services/quick_search_cache_service.py`, `backend/alembic/versions/0030_add_quick_search_shared_cache.py`, `backend/tests/unit/test_quick_search_cache_models.py`, `backend/tests/unit/test_quick_search_shared_cache.py`, `backend/alembic/versions/5f465bd665fa_add_missing_indexes_for_quick_search_.py`

### Archivos modificados (10)

`backend/.env.example`, `backend/app/api/v1/search.py`, `backend/app/api/v1/watchlist.py`, `backend/app/infrastructure/db/models.py`, `backend/app/services/quick_search_execution.py`, `backend/alembic/script.py.mako`, `backend/tests/unit/test_quick_search_cache_models.py`, `backend/tests/unit/test_quick_search_shared_cache.py`, `backend/tests/unit/test_alembic_audit.py`, `backend/tests/unit/test_quick_search_execution.py`

### Docs actualizados

`docs/reference/backend/quick-search-contract.md`, `docs/engineering/backend.md`, `docs/DOCS_INVENTORY.md`, `docs/plans/2026-06-10-quick-search-shared-cache-review-plan.md` (nuevo)

### Verificación final

- Backend unit tests: 425/426 pasan (1 fallo pre-existente en hoteles Makcorps)
- Cache tests: 51/51 ✅
- Alembic audit: 3/3 ✅
- `alembic check`: limpio (sin operaciones pendientes)
- Feature-flagged: `QUICK_SEARCH_SHARED_CACHE_ENABLED=false` por defecto

### Commits

`5f10a25` feat: quick-search shared persistent cache · `0113e4d` chore: pending changes · `148cd0c` docs: review plan · `dbb5de4` fix: audit findings · `dc1aaf3` perf: async pruning · `37ddc00` chore: missing indexes migration

---

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
