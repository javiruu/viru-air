# H44 — Seed, demo y fallos reproducibles de hoteles

**Estado:** COMPLETA como contrato de reproducibilidad; seed hotelero integral, reset seguro y perfiles de fallo reutilizables pendientes  
**Fecha:** 2026-08-05  
**Área:** backend / QA / frontend / datos  
**Fuente de verdad:** sí para datos sintéticos, fixtures y reproducción local de `/hoteles`  
**Depende de:** H06, H10, H11, H39, H42 y H43  
**Siguiente fase:** H45 — canary, smoke tests y rollback aprobado

> H44 define una base de investigación local que no dependa de producción ni de un provider comercial. No convierte la existencia de un fixture Mock en un entorno demo completo, ni presenta datos sintéticos como disponibilidad real.

## 1. Objetivo y reglas de seguridad

El objetivo es que una IA o una persona pueda levantar desde cero un escenario hotelero conocido, ejecutar búsqueda → detalle → tracking → alerta → inbox, reproducir degradaciones y limpiar el entorno sin tocar datos ajenos.

Reglas no negociables:

1. **Determinismo:** el mismo dataset, versión de fixture, configuración y comando producen las mismas entidades, fechas relativas congeladas, precios, estados y expectativas.
2. **Aislamiento:** los seeds destructivos solo pueden operar sobre SQLite temporal, una base de test o un esquema explícitamente dedicado a demo; nunca sobre `backend/.env`/producción por defecto.
3. **Synthetic-first:** todo hotel, precio, usuario, evento y URL sintética debe estar rotulado como demo/fixture en metadata, copy de QA o documentación del escenario.
4. **No availability claim:** una tarifa Mock es un dato sintético reproducible, no disponibilidad, precio live ni promesa de reserva.
5. **No red por defecto:** `local_demo` y `local_fixture` no deben llamar a Makcorps, geocoder externo, email ni otro servicio externo.
6. **Reset explícito:** no se permite `drop_all`, truncado o borrado masivo si no se ha comprobado `APP_ENV=test/demo`, `DB_URL` aislada y una confirmación no ambigua.
7. **Fallos tipados:** 429, timeout, respuesta vacía, payload inválido, rate sin moneda, hotel ambiguo, sold out y deeplink inválido son escenarios distintos; no se convierten todos en `empty`.
8. **Reproducible antes que realista:** añadir volumen o variación no justifica fechas aleatorias, moneda implícita, timezone del host o dependencia de red.

## 2. Baseline real comprobado

### 2.1 Lo que existe hoy

| Superficie | Evidencia | Lectura correcta |
|---|---|---|
| Provider Mock | `backend/app/hotels/mock_provider.py` | Lee JSON, normaliza strings/country/currency y valida fechas/rates |
| Fixture base | `backend/app/hotels/fixtures/mock_hotels.json` | 3 hoteles, Madrid/Málaga, 3 rates, EUR, fechas fijas de julio de 2026 |
| Ingestión | `backend/app/hotels/ingestion.py` + `HotelIngestionService` | Puede persistir propiedades, aliases y snapshots en la DB que reciba |
| Test DB | `backend/tests/unit/test_hotels_ingestion.py`, `test_hotels_area_search.py`, `test_hotels_area_resolve.py` | SQLite in-memory con `Base.metadata.create_all`; cada helper crea su propio engine |
| Fixture API | `backend/tests/conftest.py` | `TestClient` con SQLite temporal y override de `get_db`; no es seed hotelero completo |
| Worker manual | `python -m app.worker.hotels_sweep --once --provider mock` | Existe, pero depende de flags y puede mutar `DB_URL`; no es dry-run |
| Seed genérico | `backend/app/infrastructure/db/seed.py` | Siembra usuarios y compatibilidad legacy; no siembra hoteles |
| Seed TestSprite | `backend/scripts/seed_testsprite_data.py` | Siembra watchlists/snapshots/reglas de vuelos; no es un seed de hoteles |
| Tests de Mock | `backend/tests/unit/test_hotels_mock_provider.py` | Cubren fixture válido y country inválido; no cubren toda la matriz H44 |
| Tests de ingestión | `backend/tests/unit/test_hotels_ingestion.py` | Cubren idempotencia, flag, provider desconocido, moneda/rango inválidos y lectura persistida |
| Tests de área | `backend/tests/unit/test_hotels_area_search.py`, `test_hotels_area_resolve.py` | Cubren radio, precio, estrellas, moneda, coordenadas y fallback geocoder apagado |

### 2.2 Lo que no existe todavía

No se debe documentar como comando disponible hasta implementarlo y probarlo:

- `seed_hotels_demo.py` o equivalente hotelero versionado;
- `reset_hotels_demo.py` o un reset con guardas de entorno;
- dataset completo con tracked offers, usuarios A/B, reglas, snapshots históricos e inbox;
- catálogo de fault profiles seleccionable desde CLI/configuración;
- transporte Mock de provider con 429/timeout/invalid response como perfiles reutilizables;
- fixture Playwright/TestSprite de `/hoteles` de puerta a puerta;
- snapshot de expectativas o manifest que detecte drift del dataset;
- reporte estándar de `dataset_id`, `fixture_version`, `seed_revision` y counts;
- modo dry-run que garantice cero mutaciones del Mock.

## 3. Contrato de identidad del dataset

Cada dataset H44 debe tener un manifest legible y versionado. Como mínimo:

```text
dataset_id: hoteles-demo-v1
fixture_version: 1
seed_revision: <git revision or declared fixture revision>
created_at_utc: fixed/documented
default_locale: es-ES
default_timezone: Europe/Madrid
default_currency: EUR
source: local_mock
sensitive_data: none
synthetic_label: DEMO_NO_LIVE_AVAILABILITY
expected_external_calls: 0  # contrato de los fault adapters locales; no evidencia actual de loader implementado
```

El manifest futuro puede vivir junto al fixture bajo `backend/app/hotels/fixtures/`; esa ruta ya existe para `mock_hotels.json`, pero el manifest y el loader aún son entregables de H44.

Requisitos de IDs y nombres:

- IDs sintéticos estables, con prefijo `demo-` o `mock-` y sin colisionar con datos comerciales.
- Emails de prueba en dominios reservados/locales, nunca personales.
- Hotel names, addresses y copy marcados como sintéticos cuando aparezcan en UI de demo.
- No incluir API keys, tokens, URLs firmadas, payloads privados ni datos copiados sin sanitizar.
- La fecha de referencia debe ser inyectable o fija por manifest; nunca depender de `date.today()` para expectativas históricas.

## 4. Dataset mínimo objetivo

El seed H44 debe cubrir al menos:

### 4.1 Propiedades y geografía

- Madrid con tres o más hoteles y coordenadas próximas para centroid/radio.
- Málaga u otra ciudad con cobertura distinta.
- Una propiedad sin coordenadas para estados incompletos.
- Dos nombres parecidos y un alias provider para matching/dedupe.
- Un caso ambiguo que exija `needs_review` o no se presente como identidad segura.
- Un hotel sin rates, uno con una rate y uno con varias rates comparables.

### 4.2 Estancias y precios

- Fechas cortas y largas, al menos dos ocupaciones y más de una moneda solo si la comparación lo declara.
- Habitación, régimen y cancelación diferenciados.
- Precio total observado y unidad documentada; no inferir total/noches donde el fixture no lo respalda.
- Historial con precio inicial, bajada, subida, gap y observación stale.
- Snapshot incompatible por fechas/guests/currency para probar que no entra en ranking/tracking.
- Estado `available`, `unavailable/sold_out`, `partial`, `stale` y sin precio.

### 4.3 Usuarios y ownership

- User A y User B sintéticos.
- Ambos pueden seguir el mismo hotel sin compartir tracking, regla, evento o estado read/unread.
- Un favorito simple sin contexto y un tracked offer completo.
- Tracking pendiente/incompleto y tracking activo con snapshot inicial.
- Alertas de bajada, subida, target y disponibilidad recuperada.
- Evento legacy sin ownership suficiente para probar quarantine, nunca visible por defecto.

### 4.4 Navegación y deeplinks

- Deeplink allowlisted de ejemplo y deeplink inválido.
- URL con query sensible para verificar redaction/rechazo.
- Detalle, búsqueda, tracking e inbox con contexto reconstruible.
- Copy visible que indique `DEMO`/`fixture` cuando el usuario pueda confundirlo con live.

## 5. Fault profiles H44

Los perfiles deben ser declarativos, deterministas y seleccionables sin editar código de producción. El nombre es contrato objetivo; no existe todavía un loader/fault injector H44. Hasta implementarlo, los tests pueden representarlos con fixtures locales o mocks de sesión, pero deben etiquetar esa cobertura como contrato parcial, no como una matriz ya disponible para demo.

| Profile | Simula | Resultado esperado | External calls |
|---|---|---|---:|
| `happy_path` | hoteles y rates válidos | ingestión/search completa | 0 |
| `empty_provider` | provider responde lista vacía | `empty`/sin precio, no `sold_out` automático | 0 |
| `rate_limited_429` | respuesta 429 con/sin Retry-After | `rate_limited`, budget/retry visible, no falso empty | 0 |
| `provider_timeout` | timeout/connection reset | `timeout`/unavailable, no snapshot elegible | 0 |
| `invalid_json` | payload no parseable | `invalid_response`, run failed/partial según contrato | 0 |
| `schema_drift` | campo requerido ausente/tipo incorrecto | rechazo controlado y evidencia | 0 |
| `rate_without_currency` | importe sin moneda | rate no comparable/persistible como elegible | 0 |
| `sold_out` | hotel/rate no disponible | unavailable/sold_out explícito, no precio cero | 0 |
| `hotel_ambiguous` | matching con candidatos parecidos | `needs_review`/ambiguous, no alias automático peligroso | 0 |
| `deeplink_invalid` | URL privada, no allowlisted o malformada | CTA bloqueado/neutralizado y warning | 0 |
| `stale_history` | snapshots fuera de TTL | histórico visible como stale, no live | 0 |
| `partial_batch` | algunos hoteles válidos y otros fallidos | resultados parciales + warnings por item | 0 |
| `ownership_cross_user` | evento/regla de User A consultado por B | 403/404/oculto según contrato, nunca filtrado | 0 |

Un fault profile no debe usar `requests` real para simular un 429 o timeout. La prueba debe interceptar el adapter/transporte y registrar que el contador de red permanece en cero.

## 6. Aislamiento y reset

### 6.1 Local unit/integration

Baseline válido actual:

```bash
cd backend
pytest tests/unit/test_hotels_mock_provider.py \
       tests/unit/test_hotels_ingestion.py \
       tests/unit/test_hotels_area_search.py \
       tests/unit/test_hotels_area_resolve.py
```

Este comando ejecuta tests existentes y no es un seed/reset de demo. La suite debe seguir siendo independiente del `backend/.env` y de providers externos.

### 6.2 Demo local futura

H44 debe entregar comandos explícitos, con guardas, por ejemplo:

Los comandos de seed/reset que H44 debe entregar son todavía conceptuales; los módulos no existen hoy:

```text
MÓDULO FUTURO DE SEED HOTELERO — pendiente de implementar
MÓDULO FUTURO DE RESET HOTELERO — pendiente de implementar
```

El único worker hotelero existente puede ejecutarse manualmente, pero solo después de comprobar una DB aislada y activar explícitamente las flags necesarias:

```bash
cd backend
: "${AISOLATED_DB_URL:?Set an isolated demo DB URL before running the hotel worker}"
DB_URL="$AISOLATED_DB_URL" HOTEL_FEATURE_ENABLED=true HOTEL_SWEEP_ENABLED=true \
  python -m app.worker.hotels_sweep --once --provider mock
```

`AISOLATED_DB_URL` es una variable conceptual propuesta por H44, no una variable que el repositorio configure hoy. El comando anterior muta la DB indicada y no es un dry-run. Antes de ejecutarlo hay que comprobar que la URL apunta exclusivamente a una base de test/demo; no se debe sustituir por una URL de staging o producción.

Guardas obligatorias del futuro reset:

- exigir `APP_ENV in {test, demo, local_fixture}`;
- exigir URL SQLite temporal o esquema dedicado explícitamente permitido;
- rechazar URLs de producción/staging y valores vacíos/ambiguos;
- mostrar `dataset_id` y counts antes de borrar;
- requerir `--confirm-demo-db` o equivalente;
- no borrar migraciones, archivos `.env`, usuarios reales ni datos fuera del scope;
- devolver un resumen verificable y dejar `seed_revision`.

### 6.3 No usar comandos destructivos genéricos

`alembic downgrade`, `drop_all`, truncados manuales, borrar `viru.db` o cambiar `DB_URL` no son un reset hotelero seguro por sí solos. Solo pueden aparecer en un procedimiento específico, con backup/aislamiento y rollback documentados por H11/H42.

## 7. Reutilización por QA y frontend

### Backend

- Cada profile debe tener tests unitarios del parser/adapter y al menos una integración con SQLite aislado.
- El test debe declarar `dataset_id`, `fault_profile`, `expected_status`, `expected_counts` y `expected_external_calls`.
- Tests de provider comercial siguen marcados `network`/canary y fuera del gate local; si falta contrato o budget, el resultado es `blocked`, no `passed`.
- Test de idempotencia: seed repetido no duplica aliases/rates/tracked offers/events.
- Test de reset: solo elimina el dataset permitido y deja intactos recursos fuera del scope.

### Frontend/browser

El flujo futuro reusable debe poder seleccionar dataset/profile sin modificar el componente:

1. preparar DB aislada y dataset;
2. arrancar API con flags H43 del perfil;
3. abrir `/hoteles` con usuario sintético;
4. ejecutar búsqueda, detalle, favorito, tracking, alerta e inbox;
5. inyectar `empty_provider`, `provider_timeout`, `rate_limited_429` o `deeplink_invalid`;
6. verificar copy, estados, foco, URL state, consola y requests;
7. guardar screenshot/trace/network evidence con `dataset_id` y profile.

`frontend/tests/hotels-f56-audit.test.ts` y `hotels-signal-assessment.test.ts` aportan evidencia estructural, pero no son todavía un flujo browser E2E completo de H44. H40/H45 deben cerrar esa evidencia.

TestSprite puede reutilizar el mismo dataset si se implementa un adapter/fixture explícito; `backend/scripts/seed_testsprite_data.py` actualmente siembra vuelos y no debe recibir responsabilidades hoteleras implícitas.

## 8. Manifest y evidencia de ejecución

Cada ejecución reproducible debe poder producir:

```text
commit_or_seed_revision
 dataset_id
 fixture_version
 fault_profile
 app_env
 db_isolation_kind
 user_scope
 provider_mode
 external_calls_expected
 external_calls_observed
 rows_created_by_table
 rows_reused
 rows_rejected
 warnings
 test_command
 result
```

No guardar raw payloads de providers ni secretos en screenshots, logs o artefactos. Si un fallo requiere payload, usar una copia sanitizada y etiquetada.

Clasificación de fallo:

- `code`: comportamiento del sistema;
- `fixture`: datos inválidos o expectativa incorrecta;
- `provider_contract`: respuesta/contrato externo;
- `infrastructure`: DB, proceso, red o supervisor;
- `environment`: configuración/flags/credenciales;
- `test_harness`: browser, fixture o aserción defectuosa.

## 9. Gates de cierre H44

### Gate D — dataset

- [ ] manifest versionado y determinista;
- [ ] ciudades, coordenadas, fechas, ocupaciones, providers y monedas declarados;
- [ ] hoteles sin rates, con rates múltiples, ambiguos y sin coordenadas;
- [ ] tracking, alertas, historial, inbox y ownership User A/B;
- [ ] todo dato sintético está etiquetado y no se llama live.

### Gate I — aislamiento

- [ ] seed/reset exige entorno y DB aislados;
- [ ] repetir seed es idempotente;
- [ ] reset no toca recursos fuera del dataset;
- [ ] no hay dependencia de `date.today()`, timezone del host o red;
- [ ] Mock no se presenta como dry-run.

### Gate F — fallos

- [ ] perfiles 429, timeout, vacío, invalid JSON, schema drift, no currency, sold out, ambiguo, deeplink inválido, stale y partial;
- [ ] outcomes se distinguen y no crean snapshots/precios falsos;
- [ ] fallos son deterministas y no requieren llamadas externas;
- [ ] logs/evidencia redacted.

### Gate E — E2E

- [ ] búsqueda → detalle → tracking → alerta → inbox reproducible;
- [ ] User B no ve recursos/eventos de User A;
- [ ] estados empty/partial/stale/error tienen recuperación;
- [ ] mobile, dark/light, ES/EN, teclado y reduced motion cubiertos por H40/H45;
- [ ] screenshots/traces llevan dataset y fault profile.

### Gate R — release handoff

- [ ] comandos actuales y futuros están diferenciados;
- [ ] H43 `prod_off` mantiene cero red en local fixture;
- [ ] H42 cubre incidentes/reset accidental y evidencia;
- [ ] H39 recibe matriz de cobertura y gaps;
- [ ] H45 recibe smoke/canary con dataset congelado;
- [ ] ningún seed hotelero depende de producción.

## 10. Handoff

H44 entrega a H45:

- dataset base versionado y manifest;
- comandos seguros de seed/reset/sweep cuando estén implementados;
- matriz de fault profiles y expected outcomes;
- usuario A/B y escenarios de ownership;
- evidencia reusable para browser, smoke, canary y rollback.

H44 devuelve a fases relacionadas:

- **H06:** envelopes y outcomes provider-neutral;
- **H10/H11:** estancia, fingerprints, migración y rollback;
- **H39:** pirámide, markers, fixtures y gaps P0/P1/P2;
- **H42:** recovery ante seed/reset/fixture corrupto;
- **H43:** perfiles `local_demo`/`local_fixture`, cero red y kill switches;
- **H45:** release smoke, canary y rollback.

**Decisión actual:** conservar `mock_hotels.json` como fixture base, sin llamarlo catálogo de producción; no declarar H44 completamente implementada hasta que exista seed hotelero, manifest, reset seguro, perfiles de fallo y un flujo E2E reproducible.
