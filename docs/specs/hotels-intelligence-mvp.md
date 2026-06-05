Status: active
Scope: hotel intelligence MVP definition
Last reviewed: 2026-06-03
Canonical source: docs/specs/hotels-intelligence-mvp.md
Related: docs/overview/project-overview.md, docs/reference/backend/provider-integration-guide.md, docs/specs/phase1-codex.md

---
# Hotels Intelligence MVP (Fase 0)

## 1. Contexto del producto actual

Viru Tracker es una plataforma centrada en seguimiento de vuelos (watchlists, historico de precios, alertas y quick search) con backend FastAPI + SQLAlchemy + Alembic y frontend Next.js/TypeScript.

Esta especificacion define una nueva vertical incremental de inteligencia hotelera sin alterar el core funcional de vuelos ni sus rutas actuales.

## 2. Alcance del MVP hotelero

El MVP de hoteles se limita a capacidades de inteligencia de datos:

1. Catalogo interno de hoteles.
2. Normalizacion basica de hoteles por proveedor.
3. Watchlist hotelera.
4. Comp sets por usuario.
5. Historico de tarifas por hotel/proveedor.
6. Alertas simples de bajada, subida y paridad.
7. UI inicial "Radar hotelero" conectada a datos internos/mock.

## 3. Fuera de alcance del MVP

Quedan explicitamente fuera del MVP:

1. Reservas reales.
2. Pagos.
3. Integracion GDS completa.
4. Sabre MCP.
5. Google Hotel Center.
6. NLP avanzado de reviews.
7. White label.
8. Integraciones BI externas (Power BI/Tableau/Snowflake).
9. Scraping directo propio con proxies/CAPTCHAs.

## 4. Modelos backend propuestos (para Fase 1+)

Estos modelos son propuesta de contrato interno inicial. No se implementan en Fase 0.

1. `HotelProperty`
2. `HotelProviderAlias`
3. `HotelRateSnapshot`
4. `HotelWatchlistItem`
5. `HotelCompSet`
6. `HotelCompSetMember`
7. `HotelAlertRule`

Notas de diseño inicial:

1. Mantener `lat`/`lng` como numericos para MVP; PostGIS queda para fase posterior.
2. Respetar ownership por `user_id` en watchlist/comp sets/alertas.
3. Mantener `raw_payload` controlado y no exponerlo en respuestas publicas por defecto.

## 5. Endpoints propuestos (internos MVP)

Naming orientativo, sujeto al estilo final del backend:

1. `GET /api/hotels/search`
2. `GET /api/hotels/{hotel_id}`
3. `GET /api/hotels/{hotel_id}/rates`
4. `POST /api/hotels/ingest/mock`
5. `GET /api/hotel-watchlist`
6. `POST /api/hotel-watchlist`
7. `DELETE /api/hotel-watchlist/{item_id}`
8. `GET /api/hotel-comp-sets`
9. `POST /api/hotel-comp-sets`
10. `GET /api/hotel-comp-sets/{comp_set_id}`
11. `POST /api/hotel-comp-sets/{comp_set_id}/members`
12. `DELETE /api/hotel-comp-sets/{comp_set_id}/members/{member_id}`
13. `GET /api/hotel-alert-rules`
14. `POST /api/hotel-alert-rules`
15. `PATCH /api/hotel-alert-rules/{rule_id}`
16. `DELETE /api/hotel-alert-rules/{rule_id}`
17. `GET /api/hotels/comp-sets/{comp_set_id}/nearby-suggestions`

## 6. Feature flags y variables de entorno iniciales

Minimo recomendado para despliegue incremental:

1. `HOTEL_FEATURE_ENABLED=false`
2. `HOTEL_PROVIDER=mock`
3. `HOTEL_PROVIDER_TIMEOUT_SECONDS=10`
4. `HOTEL_PROVIDER_MAX_RETRIES=2`
5. `HOTEL_PROVIDER_CACHE_TTL_SECONDS=3600`

Principio operativo:

1. La ruta `/hoteles` y los endpoints de lectura pueden seguir disponibles si existen datos persistidos.
2. `HOTEL_FEATURE_ENABLED` gobierna solo ingesta, providers y sweeps hoteleros.
3. Con `HOTEL_FEATURE_ENABLED=true`, el modulo debe funcionar con provider `mock` y fixtures locales sin API keys.
4. Providers reales se habilitan despues y detras de flag.
5. `HOTEL_PROVIDER_CACHE_TTL_SECONDS` queda reservado para una futura cache de proveedor; en este MVP no activa cache en runtime.
6. El piloto Makcorps usa de momento el endpoint fijo `/v1/hotels/pricing`; cualquier parametrizacion posterior requiere contrato explicito.

## 7. Fases de implementacion (0->9)

1. Fase 0: spec viva (este documento).
2. Fase 1: esqueleto backend del dominio hotelero.
3. Fase 2: provider mock + normalizacion + matching.
4. Fase 3: API interna MVP.
5. Fase 4: UI inicial Radar hotelero.
6. Fase 5: historico y senales simples de paridad.
7. Fase 6: sweeps internos + alert events.
8. Fase 7: primer provider real detras de flag.
9. Fase 8: geoespacial ligero (Haversine).
10. Fase 9: QA visual y polish final.

## 8. Riesgos tecnicos/comerciales

1. Matching ambiguo entre hoteles con nombres similares.
2. Calidad y consistencia irregular de payloads de proveedor.
3. Riesgo de mezclar contratos de vuelos y hoteles sin boundaries claros.
4. Sobrealcance (intentar integrar reservas/pagos/GDS demasiado pronto).
5. Falsa sensacion de paridad si hay pocos proveedores o snapshots insuficientes.

## 9. Criterios de verificacion por fase

Principios transversales:

1. Cambios pequenos y verificables.
2. Tests dirigidos por fase cuando aplique.
3. No romper rutas ni logica existente de vuelos.
4. Sin dependencias nuevas salvo justificacion explicita.

Verificacion minima por fase:

1. Fase 0: diffs solo en `docs/` e indices actualizados.
2. Fase 1: migraciones y tests backend de modelos/servicios base.
3. Fase 2: tests unitarios de normalizacion y matching.
4. Fase 3: tests API de busqueda, ingesta mock y ownership.
5. Fase 4: typecheck/build/lint frontend + evidencia visual de ruta nueva.
6. Fase 5: tests de paridad + validacion UI de estados.
7. Fase 6: ejecucion de job manual + validacion de registros/eventos.
8. Fase 7: tests con fixtures de provider real + desactivacion segura sin API key.
9. Fase 8: tests de distancia/sugerencias + estado sin coordenadas.
10. Fase 9: checklist QA visual dark/light/responsive/focus/copy.

## 10. Guardrails de Fase 0

Durante esta fase:

1. No se toca `backend/app/**`.
2. No se toca `backend/alembic/**`.
3. No se toca `frontend/**`.
4. No se introducen dependencias.
5. No se cambian contratos API existentes.

## 11. Observaciones de cumplimiento (auditoria rapida)

Fecha de auditoria: 2026-06-03.

Checklist de estado:

1. Fase 0: completada.
2. Fase 1: completada.
3. Fase 2: completada.
4. Fase 3: completada.
5. Fase 4: completada.
6. Fase 5: completada.
7. Fase 6: completada.
8. Fase 7: completada.
9. Fase 8: completada.
10. Fase 9: completada.

Evidencia concreta:

1. Migracion de dominio presente: `backend/alembic/versions/0017_hotels_domain_skeleton.py`.
2. Migracion de sweeps/alert events presente: `backend/alembic/versions/0018_hotels_provider_run_and_alert_event.py`.
3. Siete modelos hoteleros presentes en `backend/app/infrastructure/db/models.py`:
   `HotelProperty`, `HotelProviderAlias`, `HotelRateSnapshot`, `HotelWatchlistItem`,
   `HotelCompSet`, `HotelCompSetMember`, `HotelAlertRule`.
4. Modelos operativos adicionales presentes: `HotelProviderRun` y `HotelAlertEvent`.
5. Endpoints internos activos en `backend/app/api/v1/hotels.py`, incluida paridad y alert events.
6. Ruta frontend activa: `/hoteles`.
7. Config de proveedor real presente: `backend/app/hotels/makcorps_provider.py`.
8. Cierre de semantica 2026-06-03: `HOTEL_FEATURE_ENABLED` deja de implicar que `/hoteles` desaparece y pasa a gobernar solo ingesta, providers y sweeps.
9. Cierre de endurecimiento 2026-06-03: Makcorps valida payloads vacios/malformados, descarta rates invalidos y no promete fallback automatico a mock ni cache activa inexistente.
10. Verificacion focalizada de backend hoteles: `46 passed` con `python -m pytest backend/tests/unit/test_hotels_ingestion.py backend/tests/unit/test_hotels_makcorps_provider.py backend/tests/integration/test_hotels_api_flow.py`.
11. Verificacion frontend: `npm run build` OK tras actualizar el copy de estados ligados al flag.
12. Correccion nucleo 2026-06-02: `GET /api/v1/hotels/alert-events` deja de colisionar con `GET /{hotel_id}` al declararse antes de las rutas dinamicas.
13. Fase 8 activa: endpoint `GET /api/v1/hotels/comp-sets/{comp_set_id}/nearby-suggestions` y bloque UI de `Sugerencias cercanas` dentro del panel de comp set.
14. Correccion de cierre 2026-06-03: frontend consume `GET /api/v1/hotels/{hotel_id}/parity` como unica fuente de verdad de paridad.
15. Correccion de cierre 2026-06-03: el hotel base del comp set se resuelve por `hotel_id` y ya no depende de seguir visible en `results`.
16. Checklist viva de cierre agregada en `docs/qa/hotels-pending-closeout.md`.
17. Cierre operativo 2026-06-03: sweeps hoteleros documentados en `docs/runbooks/hotels-sweeps.md`, con worker opcional separado y `HOTEL_SWEEP_ENABLED=false` por defecto.
18. Cierre de busqueda 2026-06-03: `HotelProperty.normalized_city` respalda la busqueda por ciudad y corrige coincidencias con acentos y case-insensitive.

19. Cierre Phase 9-10 2026-06-04: plan de 10 fases completado. Alertas humanas implementadas (price_below, price_above, percentage_drop, percentage_increase, provider_changed, availability_returned) con UI en lenguaje humano. HotelAlertRule con tracked_offer_id opcional. evaluate_hotel_alerts delega a _evaluate_tracked_alert_rule para reglas vinculadas a tracked offers. list_hotel_alert_events incluye eventos sweep sin rule_id. 132 tests backend pasan. Build frontend OK. Documentación actualizada en 5 archivos.

Observaciones pendientes:

1. Verificación visual manual en navegador real (dark/light/responsive).

## 12. Fases post-cierre A-E (2026-06-05)

Tras el cierre de las 10 fases originales, se ejecutaron 5 fases adicionales de correcciones y polish.
El plan maestro esta en `docs/plans/2026-06-04-hoteles-correcciones-post-cierre.md`.

1. **Fase A — DELETE comp-set**: Ya existia endpoint y tests (184/184 pasan).
2. **Fase B — Refactor hooks**: Ya completado. 6 hooks extraidos de HotelRadarPage.
3. **Fase C — Unificar tracking**: Ya completado. initial_price, snapshots, diferenciacion watchlist/tracked.
4. **Fase D — CSS area-search**: 165 lineas CSS nuevas en screens.css (tabs, autocomplete, spinner, grid responsive).
5. **Fase E — Polish final**: deleteHotelCompSet conectado en UI, parity_break relegado a seccion avanzada, i18n sincronizado.

Verificacion final:
- Backend: 184/184 tests pasan.
- Frontend: npx tsc --noEmit sin errores de hoteles.
- Todos los cambios comiteados y pusheados a main.

Observaciones pendientes:

1. Verificacion visual manual en navegador real (dark/light/responsive).

Siguiente paso propuesto (acotado):

1. Verificar visualmente en navegador el buscador por area y el boton de eliminar comparativa.
2. Documentar sweeps hoteleros manuales y su ausencia de scheduler automatico.
3. Revisar polish visual y responsive fino del bloque de sugerencias cercanas, watchlist y alertas en Fase 9.
