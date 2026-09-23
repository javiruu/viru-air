# Arquitectura Actual de Viru Tracker (Baseline Pre-Migración)

**Fecha de auditoría:** 2026-09-12  
**Commit de referencia:** `750e9a1fa06fede4fcad5076c8d90d188402bf9a`  
**Estado:** VIVO — Baseline obligatorio antes de iniciar la modernización  

---

## 1. Diagrama Textual de Requests

```
[ Usuario / Navegador ]
       │
       ▼
[ Next.js 15 App Router Frontend (Port 3000) ]
       │  (Turbopack / React 19 / TypeScript)
       │  Modules: quick-search, watchlist, hotels, door-to-door, signals, account
       │  API Client: Orval generado en api/generated/* (mutator: api/mutator/custom-client.ts), módulos: hotels/api.ts, door-to-door/api.ts
       │
       ▼  HTTP / REST (JSON, Bearer JWT, Correlation IDs, Client-Event-ID)
[ FastAPI Backend (Port 8000) ]
       │
       ├── Core & Middleware:
       │     - AccessLogMiddleware (Request latency, correlation tracking)
       │     - CORS Middleware (Origin whitelist: localhost:3000, 127.0.0.1:3000, DOMAIN)
       │     - Exception Handlers (Normalized AppError responses, status codes)
       │
       ├── API Router (/api/v1):
       │     - /auth, /search, /watchlist, /hotels, /door-to-door, /alerts, /airports,
       │       /community, /prices, /recommendations, /admin, /preferences, /notifications
       │
       ├── Service Layer:
       │     - QuickSearch: Execution, CacheService, Planner, Dedupe, Ranking, Singleflight
       │     - FareMemory: Ingestion, Volatility, HistoricalAggregates, ObservationDedupe
       │     - Watchlist: Revalidation, RefreshPolicy, DelayPrediction, Snapshots
       │     - Hotels: HotelsService, Parity, StayOffer, ObservabilityMetrics, CircuitBreaker
       │     - DoorToDoor: SearchService, GTFSFeedService, DecisionEngine, RouteOptimizer
       │
       ├── Providers & Scrapers (Outbound HTTP / Browser / Scraping):
       │     - Flights Public: Ryanair, Vueling, Wizz Air, Iberia, EasyJet, Duffel
       │     - Operational Tracking: ADSB Exchange, Aerodatabox, Amadeus, Aviationstack, OpenSky
       │     - Hotels: LocalScrape (HTML/JSON-LD), Makcorps, Overpass OSM, Mock
       │     - DoorToDoor: Navitia, GTFS Transit, Google Routes, Open-Meteo
       │
       └── Persistence Layer:
             - SQLAlchemy 2.0 ORM (62 tables)
             - SQLite (local: viru.db / viru_local.db) / PostgreSQL (production target via psycopg3)
             - Optional Redis / Valkey layer (Hot cache, distributed singleflight locks)
             - File caches (.gtfs_cache, log files)
```

---

## 2. Tabla Resumen de Endpoints Principales por Dominio

Total de endpoints registrados: **155** (151 API + 4 documentación/OpenAPI).

| Dominio | Prefijo Ruta | Métodos | Auth Requerida | Principales Handlers | Consumidores Frontend |
|---|---|---|---|---|---|
| **Auth** | `/api/v1/auth` | POST, GET | Pública / Bearer JWT | `register`, `login`, `me`, `refresh`, `logout`, `forgot_password`, `reset_password` | `api/generated/auth/*` + `modules/shared/*` (LoginModal, SessionProvider) |
| **Search (Vuelos)** | `/api/v1/search` | GET, POST | Opcional / Pública | `quick_search`, `search_stream`, `search_calendar`, `search_combinations` | `modules/quick-search` (QuickSearchView) |
| **Watchlist** | `/api/v1/watchlist` | GET, POST, DELETE, PATCH | `get_current_user` | `list_watchlist`, `create_watch`, `delete_watch`, `refresh_watch`, `get_history` | `modules/watchlist` (WatchlistView, Panels) |
| **Hotels** | `/api/v1/hotels` | GET, POST, DELETE, PATCH | Opcional / `get_current_user` | `search_hotels`, `area_search`, `tracked_offers`, `comp_sets`, `alert_rules`, `rates`, `parity` | `modules/hotels` (HotelRadarPage, HotelDetail) |
| **Door-to-Door** | `/api/v1/door-to-door` | GET, POST, DELETE | Opcional / `get_current_user` | `search_route`, `options`, `saved_places`, `history`, `gtfs_status` | `modules/door-to-door` (DoorToDoorPanel) |
| **Airports** | `/api/v1/airports` | GET | Pública | `catalog`, `seeds`, `nearby`, `compatible` | `modules/shared/airports.ts`, QuickSearch Autocomplete |
| **Alerts & Signals**| `/api/v1/alerts` | GET, POST, DELETE, PATCH | `get_current_user` | `list_rules`, `create_rule`, `update_rule`, `delete_rule`, `events` | `modules/signals` (AlertRulesWorkspace) |
| **Community** | `/api/v1/community` | GET, POST | Opcional / `get_current_user` | `routes`, `trending`, `reports` | `modules/community-routes` |
| **Admin** | `/api/v1/admin` | GET, POST, PUT, DELETE, PATCH | `require_admin` | `list_users`, `update_user`, `product_health`, `hotel_health`, `metrics` | `app/(private)/admin` |
| **Preferences & Notes** | `/api/v1/preferences`, `/api/v1/notes` | GET, POST, PUT, DELETE | `get_current_user` | `get_preferences`, `update_preferences`, `list_notes`, `create_note` | `app/(private)/dashboard`, AccountSettings |
| **Notifications** | `/api/v1/notifications`| GET, POST, PATCH | `get_current_user` | `inbox`, `mark_read`, `settings` | `modules/notifications` |
| **Public / Support**| `/api/v1/public`, `/api/v1/support` | GET, POST | Pública | `landing_metrics`, `submit_feedback`, `system_status` | Public landing, Contact modal |

---

## 3. Inventario de Persistencia

- **Driver / ORM:** SQLAlchemy 2.0.36 (sin Alembic: retirado según ADR 0003).
- **Motores Soportados:**
  - Desarrollo local / tests: SQLite (`viru.db`, `viru_local.db`, DBs en memoria en tests).
  - Producción: Supabase PostgreSQL vía pooler de sesión (`psycopg` v3, `sslmode=require`). Ver `docs/runbooks/runbook-supabase-native.md`.
- **Tablas Mapeadas (62 tablas):**
  - *Usuarios y Sesiones (6):* `users`, `user_profile`, `user_session`, `refresh_token`, `password_reset_token`, `security_activity`.
  - *Preferencias y Personalización (3):* `user_preference`, `user_preference_appearance`, `user_preference_region`.
  - *Vuelos y Tarifas (11):* `flight_watch`, `watch_tracked_flight_leg`, `flight_price_observation`, `price_snapshot`, `flight_offer_cache_entry`, `quick_search_cache_entry`, `quick_search_negative_cache_entry`, `calendar_price_observation`, `quick_search_popularity_counter`, `quick_search_popularity_daily`, `quick_search_provider_lock`.
  - *Operacional y Tráfico Aéreo (3):* `flight_operational_snapshot`, `flight_operational_refresh_lock`, `flight_provider_quota`.
  - *Hoteles (19):* `hotel_property`, `hotel_stay_offer`, `hotel_rate_snapshot`, `hotel_tracked_offer`, `hotel_tracked_offer_lifecycle_event`, `hotel_watchlist_item`, `hotel_user_stay_watch`, `hotel_saved_search`, `hotel_comp_set`, `hotel_comp_set_member`, `hotel_alert_rule`, `hotel_alert_event`, `hotel_provider_run`, `hotel_provider_circuit`, `hotel_provider_budget`, `hotel_provider_budget_reservation`, `hotel_provider_latency_aggregate`, `hotel_daily_metric`, `hotel_sweep_lease`.
  - *Door-to-Door (4):* `door_to_door_search_history`, `door_to_door_saved_place`, `door_to_door_saved_location`, `door_to_door_chosen_option`.
  - *Comunidad y Aeropuertos (4):* `airport`, `community_price_report`, `community_trending_snapshot`, `community_trending_snapshot_route`.
  - *Alertas, Notificaciones y Auditoría (12):* `alert_rule`, `notification_event`, `hotel_notification_delivery`, `user_notification_state`, `revalidation_job`, `idempotency_record`, `user_note`, `suggestion`, `support_feedback`, `ux_event`, `client_error_event`, `hotel_provider_alias`.
- **Caché y Almacenamiento en Memoria:**
  - Redis opcional (clave hot-layer, locks distribuidos, singleflight).
  - Singleflight en memoria de proceso para requests idénticos a proveedores.
  - Caché de archivos en disco: `.gtfs_cache` (datos de tránsito).

---

## 4. Inventario de Autenticación, Sesiones y Autorización

- **Mecanismo:** JSON Web Tokens (JWT) firmados con algoritmo HS256 mediante librería `python-jose`.
- **Secretos:** `JWT_SECRET` obligatorio; el backend lanza excepción en arranque si no está configurado o si es el valor por defecto.
- **Tokens:**
  - Access Token: Vida corta (30 minutos por defecto), contiene `sub` (user ID o email) y `exp`.
  - Refresh Token: Vida larga (30 días), hash SHA256 almacenado en tabla `refresh_token`.
- **Hashing de Contraseñas:** `passlib` con `bcrypt` seguro.
- **Puntos de Verificación de Permisos:**
  - `get_current_user`: Extrae token del header `Authorization: Bearer <token>`, valida expiración, firma y existencia en base de datos.
  - `get_current_active_user`: Comprueba flag `is_active`.
  - `require_admin`: Comprueba que `user.role == "admin"`.
- **Seguridad en Frontend:**
  - El frontend gestiona la sesión vía Supabase Auth SSR (@supabase/ssr, cookies + middleware) y el mutator de Orval (`api/mutator/custom-client.ts`) inyecta el Bearer token en cada llamada.

---

## 5. Inventario de Jobs, Tareas en Segundo Plano y Workers

1. **Revalidation Worker (`app/services/fare_memory_revalidation_worker.py`):**
   - Refresco periódico de rutas en watchlist y observaciones de tarifas.
   - Control de locks para evitar colisiones entre procesos.
2. **Watchlist Revalidation (`app/services/watchlist_revalidation.py`):**
   - Encola y procesa `RevalidationJob` con cálculo de jitter y backoff exponencial en fallos.
3. **Fare Memory Retention Job (`app/services/fare_memory_retention_job.py`):**
   - Purga periódica de observaciones antiguas por lotes (`batch_size`) para mantener la base de datos acotada.
4. **Hotels Sweep Worker (`app/worker/hotels_sweep.py`):**
   - Rastreo de precios de hoteles con arriendo distribuido (`hotel_sweep_lease`) y presupuestos por proveedor (`hotel_provider_budget`).
5. **Notification Delivery Worker (`app/worker/notifications.py`):**
   - Despacho y entrega de notificaciones pendientes con deduplicación y ventanas de silencio (`quiet hours`).

---

## 6. Inventario de Proveedores y Scrapers

- **Vuelos (Comerciales y LCCs):**
  - Ryanair (scraper público + adaptador `ryanair_py_adapter`).
  - Vueling (`vueling_provider.py`).
  - Wizz Air (`wizz_air_provider.py`).
  - Iberia (`iberia_provider.py`).
  - EasyJet (`easyjet_provider.py`).
  - Duffel API (`duffel_provider.py`).
- **Vuelos (Operacionales y ADS-B):**
  - ADSB Exchange, OpenSky Network, Aerodatabox, Amadeus, FlightAware, AviationStack.
- **Hoteles:**
  - Scraper local HTML/JSON-LD, Makcorps API, Overpass OpenStreetMap (geodatos), Mock canary provider.
- **Transporte Terrestre (Door-to-Door):**
  - Navitia, GTFS transit feeds, Google Routes, Open-Meteo.
- **Normalización:**
  - Todos los resultados externos se normalizan en `FlightOffer`, `FlightPriceObservation` o `HotelRateSnapshot` antes de persistir o devolver al cliente.

---

## 7. Inventario de Duplicaciones y Código Muerto

- **Auditoría de patrones:**
  - 0 `except:` genéricos o `except...: pass` desatendidos.
  - 0 `TODO`/`FIXME`/`HACK` en código activo de backend.
  - 0 `@ts-ignore` o `@ts-nocheck` en frontend.
  - Llamadas `fetch` centralizadas en el mutator de Orval (`api/mutator/custom-client.ts`); sin fetchs dispersos en módulos.
- **Áreas con oportunidad de consolidación:**
  - 162 `useEffect` en frontend, muchos de ellos sincronizando estado remoto manualmente (serán reemplazados por TanStack Query en Fase 1).
  - `QuickSearchView.tsx` (6,187 líneas) agrupa lógica de presentación, estado de filtros, manipulación de URL y renderizado de resultados.
  - Archivos temporales de validaciones pasadas en `backend/` (`_tmp_*.db`, `tmp*.db`) que deben limpiarse.

---

## 8. Análisis de Riesgos de Seguridad

- **Secretos:** Sin secretos commiteados en el repositorio; validación estricta de variables de entorno en arranque.
- **Autorización:** Endpoints protegidos en el backend mediante dependencias FastAPI. Frontend nunca asume autorización por sí mismo.
- **SQL Injection:** 100% prevenido por uso de SQLAlchemy ORM y queries tipadas; cero consultas dinámicas concatenadas con strings no confiables.
- **CORS:** Restringido a orígenes explícitos configurados (`http://localhost:3000`, `http://127.0.0.1:3000` y `DOMAIN` en producción).
- **SSRF:** Base URLs de proveedores externos son constantes cerradas o configuraciones administrativas, no provistas por parámetros de usuario arbitrarios.

---

## 9. Matriz de Decisión de Componentes

| Componente / Dominio | Clasificación | Justificación y Plan |
|---|---|---|
| Esquemas Pydantic (`domain/schemas.py`) | **KEEP** | Base sólida y validada para la generación de OpenAPI. |
| Migraciones Alembic (`alembic/versions`) | **RETIRED** | Retirado (ADR 0003); autoridad de esquema: `supabase/migrations/` + `create_all`/`schema_compat.py`. |
| Scrapers y conectores de aerolíneas | **KEEP** | Lógica de negocio esencial y probada con singleflight y resiliencia. |
| Catálogo maestro de aeropuertos | **KEEP** | Base de datos geoespacial validada y optimizada para autocompletado. |
| Sistema de i18n (@/i18n) | **KEEP** | Estructura bilingüe centralizada sin mojibake. |
| Monolito `QuickSearchView.tsx` | **REFACTOR** | Modularizar en componentes UI reutilizables (chips, filtros, cards). |
| Estado remoto en `useEffect` | **REFACTOR** | Migrar a TanStack Query v5 (`06_TANSTACK_QUERY.md`). |
| Cliente HTTP manual (módulo modules/shared/api.ts, eliminado) | **DONE (REPLACED)** | Sustituido por cliente tipado Orval (`api/generated/*` + mutator `api/mutator/custom-client.ts`). |
| Persistencia SQLite única | **REPLACE** | Conectar a Supabase PostgreSQL para entorno multiusuario (`08_SUPABASE.md`). |
| Tooling ESLint / Prettier clásico | **REPLACE** | Reemplazar por Biome (`02_BIOME.md`). |
| Ficheros temporales `_tmp_*.db` en backend | **DELETE** | Artefactos temporales de migraciones de prueba anteriores. |
| Valkey / Trigger.dev / Typesense / Temporal | **UNKNOWN** | Evaluar en fases posteriores solo tras métricas de necesidad reales. |

---

## 10. Métricas de Tamaño y Complejidad

- **Backend App (`backend/app`):** 49,329 líneas en 200 archivos Python.
  - `services/`: 16,710 líneas (64 archivos)
  - `api/`: 9,303 líneas (24 archivos)
  - `door_to_door/`: 8,799 líneas (41 archivos)
  - `infrastructure/`: 7,581 líneas (41 archivos)
  - `hotels/`: 3,723 líneas (22 archivos)
  - `domain/`: 1,821 líneas (6 archivos)
  - `core/`: 667 líneas (10 archivos)
  - `worker/`: 328 líneas (3 archivos)
- **Frontend App (`frontend/src`):** 53,481 líneas en 299 archivos TypeScript/TSX.
  - `modules/`: 39,255 líneas (208 archivos)
  - `app/`: 6,502 líneas (51 archivos)
  - `i18n/`: 5,789 líneas (19 archivos)
  - `components/`: 1,504 líneas (7 archivos)
- **Archivos de Complejidad Anormal (> 1,000 LOC):**
  - Frontend: `modules/quick-search/QuickSearchView.tsx` (6,187 LOC), `i18n/domains/watchlist.ts` (1,096 LOC).
  - Backend: `services/hotels_service.py` (3,624 LOC), `api/v1/search.py` (3,596 LOC), `api/v1/hotels.py` (1,548 LOC), `infrastructure/db/models.py` (1,462 LOC), `door_to_door/api/routes.py` (1,064 LOC).

