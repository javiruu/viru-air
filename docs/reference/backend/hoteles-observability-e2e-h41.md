# H41 — Observabilidad end-to-end del tracker hotelero

**Estado:** EN QA (contrato aprobado; logs/redaction, browser→API por request, intent estable browser→API para resultados y detalle/rates/parity, API→provider/DB→`HotelProviderRun`, instrumentación `latency_sink` en fixture/canary controlado para ingestion/revalidation/area search, persistencia multi-operación agregada por run mediante migración `0053`, runner offline Mock + kill switch con evidencia redacted, alertas→inbox, delivery hotelero `in_app`, ledger diario agregado, health hotelero persistente admin-only, diagnóstico de runs recientes y cabina admin visual implementados y validados con regresiones verdes; smoke Chromium automatizado de la cabina pasado en desktop/mobile × light/dark con mocks y evidencia vigente); provider live/canary comercial, revisión humana/cross-browser, dashboards RED/provider, SLO y alertas operativas siguen pendientes
**Fecha:** 2026-08-05  
**Área:** backend / frontend / workers / providers / alertas / operación / privacidad
**Fuente de verdad:** sí para la matriz de observabilidad hotelera y sus gates; no certifica que la instrumentación objetivo ya esté desplegada  
**Fase del roadmap:** H41  
**Depende de:** H06, H09, H26-H28, H35-H40  
**Relacionado con:** H04 métricas de producto, H05 freshness/provenance/confidence, H23 tracking desde oferta, H37 coste/rendimiento, H38 secretos/SSRF/abuso, H42 runbooks, H43 flags/canary, H45 release

> H41 define cómo explicar una búsqueda, un sweep, una revalidación o una alerta hotelera desde la primera petición hasta el resultado visible. Este incremento añade un ledger diario agregado, un health admin local basado en estado persistido y una cabina admin visual acotada; no añade OpenTelemetry, un SaaS de monitorización, dashboards RED/provider ni SLO productivos.

---

## 1. Decisión de fase y límite

El tracker hotelero no puede considerarse operable porque una pantalla cargue o porque exista un log aislado. Ante una incidencia debe ser posible contestar, con datos correlacionables y redacted:

1. qué intención inició la operación;
2. qué request/API la recibió;
3. qué provider, operación y attempts se ejecutaron;
4. qué resultado normalizado se obtuvo (`success`, `empty`, `partial`, `timeout`, `rate_limited`, `unavailable`, `invalid_response` o `failed`);
5. qué snapshot/run/tracking quedó afectado;
6. si una regla fue evaluada, suprimida o disparada;
7. si el evento llegó al inbox o a otro canal;
8. qué vio la UI y qué acción de recuperación podía tomar la persona;
9. cuánto costó la operación y si consumió budget;
10. si la evidencia contiene PII, secretos, URLs firmadas o IDs de alta cardinalidad.

### Dentro de H41

- contrato de correlation/request IDs entre UI, API, provider, worker, DB, alertas, delivery e inbox;
- eventos y métricas hoteleras con vocabulario H05/H06/H09/H26-H28;
- logs estructurados y redaction verificable;
- health operativo sin llamadas externas implícitas;
- dashboards, alertas de SLO y ownership de cada señal;
- política de labels, cardinalidad, sampling y retención;
- coste y budget como señales de primera clase;
- tests y evidencias que cierran la cadena.

### Fuera de H41

- escoger un proveedor comercial;
- activar sweeps externos o prometer frecuencia diaria;
- contratar un servicio de observabilidad;
- decidir retención legal definitiva sin H35/legal;
- convertir logs actuales en métricas históricas retroactivas;
- presentar el contrato como prueba de que `/hoteles` ya tiene SLO aprobado.

---

## 2. Baseline real comprobable

H41 parte de estas piezas observadas en el repositorio. La existencia de una pieza no implica que cubra todo el flujo hotelero.

| Superficie | Evidencia actual | Qué sí permite afirmar | Qué no permite afirmar |
|---|---|---|---|
| Correlación HTTP | `backend/app/main.py` normaliza `x-correlation-id` y el `x-client-event-id` opcional, los coloca en `request.state`, los conserva durante el request y los devuelve en la respuesta; `HotelProviderRun` conserva `correlation_id`/`client_event_id`/`execution_id` cuando la operación crea un run | las requests HTTP, las lecturas de detalle/rates/parity y las operaciones de ingestión/sweep pueden investigarse con IDs opacos; el detalle reutiliza el intent de la búsqueda que originó la selección y el worker autónomo conserva su ejecución sin heredar intents browser | que el intent se persista para búsquedas de catálogo o lecturas read-only, o que exista agrupación en inbox/delivery; tampoco prueba una llamada comercial live completa |
| Logs backend | `backend/app/core/logging.py` configura stdout + fichero, `SafeJsonFormatter` y `CorrelationIdFilter`; el formatter serializa con `json.dumps` y sanea secretos antes del sink | hay una base común de logs válidos, con `correlation_id`, escapes seguros y redaction local | no existe agregación, búsqueda, rotación, retención o alerting centralizado; la evidencia es de sinks locales, no de operación productiva |
| Redacción HTTP | `test_unhandled_exception_contract.py` cubre sanitización de bodies y el nivel de `urllib3.connectionpool` | algunos errores y cuerpos de validación no deben exponer secretos | que excepciones de provider, raw payloads, trazas y stacks frontend estén completamente saneados |
| Worker hotelero | `backend/app/worker/hotels_sweep.py` genera/conserva `correlation_id`, crea `execution_id`, persiste ambos en `HotelProviderRun` y los emite en `hotel_sweep_cycle`; snapshots/eventos ya enlazan por `provider_run_id` | un operador puede enlazar el ciclo del worker con el provider-run y localizar snapshots/eventos asociados en una fixture local | que exista propagación por unidad hacia cada llamada externa, que el job directo comparta el mismo envelope o que haya métricas persistentes/alertas SLO |
| Makcorps | `backend/app/hotels/makcorps_provider.py` emite `makcorps_disabled` y `makcorps_request_failed`; su helper y el sink común sanean errores antes de escribirlos | se registra que el adapter está desactivado o que una request falló sin conservar los secretos cubiertos por las regresiones | que haya latency/outcome/attempt/budget consistente; faltan pruebas exhaustivas de todos los formatos de excepción y un backend centralizado |
| Health del proceso | `/health` y `/ready` devuelven estados básicos | existen probes sintéticos mínimos | que el provider, worker, DB, budget o freshness hoteleros estén saludables |
| Health en memoria | `provider_health_stats.py` agrupa muestras por `provider_id`, con latencia y códigos de warning | existe un patrón de agregación de salud en memoria | no es un ledger hotelero persistente: sus campos actuales son de vuelos (`flights_count`, warnings de flight provider) y se pierde al reiniciar |
| Alertas/delivery/metrics | `services/hotels_service.py` crea `HotelAlertEvent` con ownership y `provider_run_id`, materializa `HotelNotificationDelivery` idempotente y el worker procesa `in_app` separado de vuelos; `hotel_observability_metrics.py` agrega estados diarios allowlisted; `notification_inbox.py` mantiene la lectura privada; `frontend/src/app/(private)/admin/hotels-observability/page.tsx` expone la cabina admin; `frontend/scripts/qa_admin_hotels_observability.mjs` cubre desktop/mobile × light/dark | alertas, inbox, traza interna, delivery local, métricas agregadas `sweep_run/alert_event/hotel_delivery` y su lectura visual admin pueden investigarse sin usar `hotel_id` como ownership; endpoint acotado, smoke Chromium mockeado y evidencia vigente verifican la cabina | no hay delivery externo, dashboards RED/provider, métricas de evaluación/dedupe/lectura detalladas, retención automática ni eventos legacy sin vínculo atribuible |
| Frontend | `frontend/src/lib/errorLogging.ts` trunca sección, mensaje y stack y envía `/ux/errors` cuando hay token; `/hoteles` añade `HotelRumTracker` opt-in y `hotel_rum_vitals` bucketizado; el hook de búsqueda genera un `x-client-event-id` estable por ejecución y lo pasa a resultados y a las lecturas de detalle/rates/parity | existe un canal best-effort de errores cliente, RUM local, correlación browser→API, agrupación de la selección con su búsqueda y persistencia del intent en operaciones de ingestión/sweep que crean `HotelProviderRun` | no existe persistencia del intent para lecturas read-only, inbox/delivery ni métricas persistentes agregadas, dashboard, p75 de producción o field compliance; INP es una aproximación de Event Timing |
| Tests | existen tests de logging/correlation y tests hoteleros de provider/sweep/API | hay regresiones parciales útiles | H39 confirma que faltan gates de provider live, locks, SSRF, migraciones y browser hotelero |

**Conclusión del baseline:** hay instrumentación de logs, una cadena reproducible browser→API→detalle/rates/parity, browser→API→run/DB→snapshot para operaciones con run y ahora un ledger diario local para estados hoteleros agregados. Provider live por unidad, delivery externo, dashboards visuales, traces distribuidos, SLO y alertas de operación siguen pendientes.

---

## 3. Flujo de correlación objetivo

```text
UI intent
  │  client_event_id opaco (sin PII)
  ▼
Hotel API request
  │  correlation_id / request_id
  ├──────────────► logs + RED metrics
  ▼
Hotel gateway
  │  operation + provider_id + attempt + timeout/budget
  ▼
Provider adapter
  │  provider_request_id si existe, nunca API key/query secret
  ▼
DB / provider run / snapshot
  │  provider_run_id + outcome + observed_at
  ▼
Tracking / rule evaluator
  │  event_id + rule outcome + dedupe/suppression reason
  ▼
Delivery / inbox
  │  notification source ref + delivery outcome
  ▼
Frontend state
  │  safe UI state + visible freshness + recovery action
```

### Invariantes

- `correlation_id` es opaco, acotado y no contiene email, hotel, estancia ni token.
- Un `request_id` de operación puede ser hijo del correlation ID, pero no sustituye el ownership de DB.
- Un worker sin request HTTP crea un `run_id`/job execution ID propio y lo enlaza con `provider_run_id` y `job_id`.
- Un provider request ID externo se conserva solo si es seguro y se redacts antes de logs públicos.
- Los IDs se usan para buscar logs/traces, no como labels de métricas.
- Un evento tardío o de un lease perdido no puede sobrescribir el resultado del owner válido solo porque comparta correlation ID.
- La UI no muestra IDs internos como sustituto de un mensaje humano; puede mostrar un código de soporte derivado y seguro cuando H21 lo requiera.

### Propagación mínima

| Frontera | Debe transportar | Estado actual |
|---|---|---|
| Browser → API | `apiFetchWithStatus`/`apiFetch` generan un `x-correlation-id` opaco por request; el flujo de búsqueda genera un `x-client-event-id` opaco por ejecución, lo expone al detalle seleccionado y el backend lo normaliza, conserva durante el request y devuelve; errores leen también los IDs devueltos por API | propagación browser→API por request, agrupación explícita de resultados y agrupación de las tres lecturas detail/rates/parity están verificadas; dos búsquedas concurrentes conservan intents aislados | no existe persistencia de requests read-only, agrupación inbox/delivery ni prueba browser→provider live |
| API → gateway/provider | request ID, intent estable cuando la operación lo admite, operación, timeout y budget | propagación de `correlation_id`/`client_event_id` al adapter Makcorps mediante headers y logs; el contexto se copia explícitamente a las llamadas paralelas; `latency_sink` mide fixture/canary alrededor de ingestion, revalidation y area search; sin `HotelProviderRun` es no persistente y con run alimenta agregados bounded de la migración `0053`; faltan provider live, canary real y outcomes/latencia field completos del contrato V2 |
| API → DB | provider run/job ID, intent y outcome | `HotelProviderRun.client_event_id` nullable está persistido por migración `0049`; `/ingest/mock` y sweeps enlazan snapshots con `provider_run_id`; búsquedas read-only no crean runs |
| Worker → provider | execution/run ID, provider/operation, attempt | `execution_id`/`correlation_id` quedan persistidos y visibles en el ciclo; falta propagación por unidad/provider request y `attempt` estructurado |
| Evaluador → evento | snapshot/base/current, rule ID, reason, dedupe key | contrato H26 lo exige; métricas hoteleras no están demostradas |
| Evento → delivery/inbox | source ref, delivery attempt/outcome, read state | inbox hotelero mantiene ownership estricto; `HotelAlertEvent → HotelNotificationDelivery → worker` conserva ownership/idempotencia, y no se crean `NotificationEvent` artificiales para hoteles; los canales externos permanecen fuera |
| API → frontend | correlation ID y estado/error normalizado | envelopes generales existen; cobertura hotelera V2 pendiente |

---

## 4. Taxonomía de eventos

Todos los eventos operativos deben ser estructurados. El nombre y los códigos son contrato interno versionado; no se debe parsear texto libre como API estable.

### 4.1. Campos comunes

```json
{
  "event_name": "hotel_provider_call_finished",
  "schema_version": "hotel-observability-v1",
  "timestamp_utc": "2026-08-05T12:00:00Z",
  "environment": "local|staging|production",
  "service": "api|worker|provider-gateway|notification|frontend",
  "operation": "search|area_search|detail|rates|revalidate|sweep|alert_evaluate|delivery|inbox",
  "correlation_id": "opaque",
  "execution_id": "opaque",
  "provider_id": "makcorps",
  "provider_run_id": "opaque-or-null",
  "outcome": "success|empty|partial|timeout|rate_limited|unavailable|unsupported|invalid_response|failed",
  "duration_ms": 0,
  "attempt": 1,
  "error_code": "safe_code_or_null"
}
```

No enviar en este envelope:

- API keys, Authorization, cookies o URLs completas con query params;
- email, nombre, teléfono, edades o payload de ocupación innecesario;
- `hotel_id`, `tracked_offer_id` o `user_id` como labels de métrica;
- raw provider payloads o stack traces sin scrubber;
- target price o cualquier preferencia privada salvo en un almacén de auditoría con acceso controlado.

### 4.2. Eventos mínimos por dominio

| Familia | Eventos mínimos | Campos de resultado |
|---|---|---|
| Request | `hotel_request_started`, `hotel_request_finished`, `hotel_request_failed` | route template, status, duration, outcome, error code |
| Provider | `hotel_provider_call_started`, `hotel_provider_call_finished`, `hotel_provider_call_failed` | provider, operation, attempt, timeout, latency, HTTP class, normalized outcome |
| Sweep | `hotel_sweep_started`, `hotel_sweep_unit_finished`, `hotel_sweep_finished`, `hotel_sweep_window_missed` | run, units planned/scanned, counts by outcome, budget, duration |
| Snapshot | `hotel_snapshot_created`, `hotel_snapshot_rejected` | eligibility reason, observed_at presence, provider run, rejection code |
| Tracking | `hotel_tracking_created`, `hotel_tracking_revalidation_finished` | state transition, source type, outcome, stale/partial reason |
| Alert | `hotel_alert_evaluation_finished`, `hotel_alert_suppressed`, `hotel_alert_created` | rule scope, baseline/current eligibility, dedupe/cooldown reason |
| Delivery | `hotel_notification_queued`, `hotel_notification_sent`, `hotel_notification_failed`, `hotel_notification_suppressed` | channel, attempts, retry class, safe failure code |
| Inbox/UI | `hotel_inbox_item_read`, `hotel_deeplink_opened`, `hotel_client_error` | source type, safe result, UI section, locale, viewport class if sampled |
| Budget | `hotel_budget_reserved`, `hotel_budget_denied`, `hotel_circuit_state_changed` | provider, operation, unit count, reason, window; never credentials |

`hotel_*_finished` debe emitirse también para `empty`, `partial`, `timeout`, `rate_limited` y `unavailable`; no solo para éxitos.

---

## 5. Métricas y labels

Las métricas RED/provider y los gauges siguientes siguen siendo contrato objetivo. El incremento implementado activa únicamente el ledger diario local descrito en §5.5.

### 5.1. RED de API y providers

```text
hotel_http_requests_total{route,method,status_class,outcome}
hotel_http_request_duration_seconds{route,method,outcome}
hotel_provider_requests_total{provider,operation,outcome}
hotel_provider_request_duration_seconds{provider,operation,outcome}
hotel_provider_attempts_total{provider,operation}
hotel_provider_rate_limited_total{provider,operation}
hotel_provider_timeouts_total{provider,operation}
hotel_provider_invalid_response_total{provider,operation}
hotel_provider_circuit_open_total{provider,operation}
```

### 5.2. Sweeps, tracking y snapshots

```text
hotel_sweep_runs_total{provider,status}
hotel_sweep_units_total{provider,outcome}
hotel_sweep_duration_seconds{provider,status}
hotel_sweep_snapshots_created_total{provider,outcome}
hotel_sweep_alerts_created_total{provider,rule_type}
hotel_tracking_revalidations_total{provider,outcome}
hotel_tracking_stale_total{provider,reason}
hotel_snapshot_rejections_total{provider,reason}
```

No usar `hotel_id`, `user_id`, `tracked_offer_id`, correlation ID, URL, email o fingerprint como label. Si se necesita investigar una entidad concreta, usar logs/traces con acceso controlado y muestreo, no una serie temporal por entidad.

### 5.3. Alertas, delivery y coste

```text
hotel_alert_evaluations_total{provider,rule_type,outcome}
hotel_alert_suppressed_total{reason}
hotel_notifications_total{channel,outcome}
hotel_notification_attempts_total{channel}
hotel_notification_delivery_duration_seconds{channel,outcome}
hotel_provider_budget_units_total{provider,operation,decision}
hotel_provider_cost_estimate_total{provider,operation,currency}
```

El coste es estimado hasta que H37 defina unidad y precio verificables. No mostrar una cifra comercial inferida como coste real.

### 5.4. Gauges y freshness

```text
hotel_sweep_due_units{provider}
hotel_sweep_running_units{provider}
hotel_provider_budget_remaining{provider,operation,window}
hotel_circuit_state{provider,operation}
hotel_latest_observation_age_seconds{provider,scope}
```

`scope` debe ser de baja cardinalidad (`catalog`, `tracked_offers`, `area_search`), nunca una entidad privada.

### 5.5. Ledger diario implementado en este incremento

`hotel_daily_metric` persiste una fila por `(metric_date, metric_name, provider, outcome)` con `count` acumulado. Las métricas allowlisted actuales son:

```text
sweep_run{provider,outcome=completed|partial|failed|skipped}
alert_event{provider,outcome=created}
hotel_delivery{provider=local,outcome=delivered|retried|failed}
```

El upsert es atómico para SQLite/PostgreSQL y no hace commit implícito; otros dialectos se rechazan explícitamente: el sweep y el worker publican la métrica en la misma transacción que el estado representado. Los providers persistibles están allowlisted (`mock`, `local_scrape`, `makcorps`, `local`, `unknown`). No se guardan `user_id`, `hotel_id`, `event_id`, intents, datos de contacto, payloads ni URLs. `GET /api/v1/admin/hotels/observability` requiere admin, limita la ventana a 31 días y solo devuelve dimensiones allowlisted. Esto es una consulta y cabina operativa local para admins, no un dashboard RED/provider ni un SLO activo.

`GET /api/v1/admin/hotels/health` añade un resumen admin-only, de solo lectura, derivado de `HotelProviderRun` y del ledger: devuelve `unknown` sin runs, `not_configured` para un último run explícitamente `skipped`, `critical` ante run fallido o delivery fallido, y `degraded` ante parcial, run en curso, reintentos o antigüedad fuera de la ventana. La ventana está limitada a 1–168 horas, los estados de run desconocidos se normalizan a `unknown`, no hay llamadas a providers ni commits implícitos, y la respuesta no contiene IDs privados. La frescura de las métricas diarias es aproximada al día de `hotel_daily_metric`; no se presenta como disponibilidad live ni como SLO.

`GET /api/v1/admin/hotels/runs` devuelve hasta 50 resúmenes recientes de `HotelProviderRun`. Expone únicamente provider allowlisted, estado normalizado, timestamps, duración calculada cuando existe `finished_at`, `items_processed`, booleano `has_error` y outcomes agregados de una allowlist fija. No expone IDs, correlation/client intents, texto de error ni claves JSON arbitrarias; requiere admin y no contacta providers.

---

## 6. SLO candidatos y alertas operativas

Los valores de esta sección son **candidatos de calibración**, no SLOs activos. H42/H43/H45 deben ajustarlos contra baseline, provider capabilities, coste y expectativas de producto antes de ponerlos en producción.

| Señal | Candidato inicial | Ventana/alerta | Acción |
|---|---:|---|---|
| API hotelera con error 5xx | < 2% | warning si >2%/15 min; critical si >5%/5 min | revisar release, DB y provider gateway |
| Búsqueda hotelera p95 | ≤ 2.5 s en provider disponible | warning si duplica baseline 15 min | separar latencia externa de API y degradar honestamente |
| Timeout provider | < 5% | warning >5%/15 min; critical >15%/5 min | abrir breaker/cooldown según H09 |
| HTTP 429/provider budget denied | 0 como objetivo de canary | warning en cualquier canary; production alert si supera budget | pausar sweep, respetar Retry-After y revisar cuota |
| Sweep no observado | ejecución dentro de la ventana configurada y aprobada por H09/H43; antes de eso, solo canary/manual | alertar si vence la ventana configurada + grace period | H42 runbook; no decir “sin cambios” ni convertir ausencia de worker en freshness actual |
| Runs `failed`/`partial` | baseline por provider | warning por aumento sostenido, no por un caso aislado | revisar outcome y cobertura |
| Edad de observación trackeada | ≤ TTL H05 cuando hay cobertura | alertar por exceso de TTL, no por ausencia de provider | mostrar stale/unavailable y priorizar refresh |
| Alert delivery | queued→terminal outcome dentro de política H28 | alertar por backlog/failed sostenido | retry, pausa de canal y soporte |
| Errores de redacción | 0 filtraciones | critical inmediato | cortar logs/canal, rotar secretos si aplica, revisar H35/H38 |

### Reglas contra alert fatigue

- alertar por ratio, tendencia, burn rate o backlog; no por cada hotel/evento;
- agrupar por provider/operation/status y conservar ejemplos opacos en logs;
- usar cooldown y dedupe en alertas operativas, igual que H26 exige para alertas de producto;
- distinguir provider outage, budget exhaustion, worker down, DB degradation y frontend error;
- toda alerta debe tener owner, severidad, enlace a dashboard, runbook H42 y criterio de recuperación;
- si no existe una ruta de recuperación, la señal no está lista para alertar.

---

## 7. Dashboards y health

### Dashboard 1 — Radar de producto

- búsquedas por outcome y latencia;
- resultados `success/empty/partial/unavailable`;
- selección de resultado, tracking creado y alertas creadas enlazadas con H04;
- freshness visible y porcentaje de estados desconocidos;
- segmentación de bajo volumen, sin PII.

### Dashboard 2 — Providers y coste

- requests, attempts, latency p50/p95, timeout, 429, invalid response y circuit state;
- budget reservado/denegado/restante;
- coste estimado por operación y ventana;
- cobertura por provider/operación sin prometer cobertura geográfica no medida.

### Dashboard 3 — Sweeps y tracking

- runs por estado, unidades por outcome, leases expirados, ventana perdida;
- snapshots creados/rechazados y razones;
- ofertas stale, revalidaciones pendientes y backlog;
- alertas creadas/suprimidas/deduplicadas.

### Dashboard 4 — Delivery e inbox

- queued/sent/failed/retry/suppressed por canal;
- edad del backlog y tasa terminal;
- lectura de inbox y deep links, si H04/H28 aprueban el evento;
- no inferir “alerta entregada” desde “fila creada”.

### Health mínimo sin side effects

El endpoint de health debe poder devolver o alimentar, desde estado local/persistido:

```json
{
  "hotel": {
    "enabled": false,
    "provider": "mock",
    "mode": "fixture",
    "last_run_status": "skipped",
    "last_run_finished_at": null,
    "latest_observation_age_seconds": null,
    "budget_remaining": 0,
    "circuit_state": "closed",
    "open_incidents": 0
  }
}
```

- No llamar a Makcorps ni a otro provider desde `/health` o `/ready`.
- No presentar `enabled=false` como error del usuario.
- Si no existe estado persistido, devolver `unknown` o `not_configured`, no `healthy` optimista.
- Separar salud del proceso, salud de DB, salud del worker y cobertura del provider.

---

## 8. Privacidad, redaction y acceso

### Reglas obligatorias

1. Aplicar redaction antes de escribir logs, no solo al exportar.
2. Sanitizar `str(exc)` de requests: nunca asumir que una excepción no contiene URL, query o header.
3. No registrar el parámetro `api_key` ni URLs firmadas; el adapter debe ocultar credenciales también cuando usa `params`.
4. No almacenar raw provider payload en observabilidad si no está scrubbed; H06/H38 deben decidir si queda en DB, en storage restringido o se descarta.
5. `reportClientError` debe aplicar allowlist/scrubber a message y stack antes de enviarlos a `/ux/errors`; truncar longitud no elimina emails, tokens ni query secrets.
6. No meter IDs de usuario/hotel/oferta en métricas; en logs solo con motivo operativo, TTL, acceso y formato opaco definidos.
7. No incluir valores de target price, ocupación detallada o preferencias privadas en eventos de producto salvo que H04/H35 lo autoricen y se minimicen.
8. Separar logs de aplicación, auditoría de seguridad, métricas agregadas y traces; cada uno tiene acceso y retención distintos.
9. Testear intentos de inyección en mensajes externos y saltos de línea en logs.
10. Si se detecta exposición real, activar el procedimiento H38: contener, revisar alcance y rotar credenciales cuando corresponda.

### Retención propuesta para calibrar

No es una política legal aprobada. Como punto de trabajo para H35/H42:

- métricas agregadas: suficiente histórico para comparar ventanas de release;
- logs operativos: retención corta con rotación y acceso restringido;
- traces: muestreo y retención menor, conservando 100% de errores críticos durante una ventana acordada;
- auditoría de seguridad/delivery: según obligación y contrato;
- errores frontend: TTL limitado y sin stack crudo si contiene datos no saneados.

La implementación debe documentar valores efectivos, responsable, ubicación y borrado; no dejar la retención implícita en un fichero local `server-*.log`.

---

## 9. Sampling, cardinalidad y costes

### Sampling

- conservar 100% de errores normalizados, 429, timeouts, invalid responses, circuit opens y fallos de delivery;
- muestrear éxitos repetitivos de búsquedas/sweeps cuando el volumen lo exija;
- nunca muestrear de forma que desaparezca la evidencia de una alerta privada o una fuga de seguridad;
- mantener un contador agregado aunque el evento detallado se muestree;
- documentar el porcentaje efectivo por environment y operación.

### Cardinalidad

**Labels permitidos:** route template, operation, provider, outcome, status class, channel, rule type y environment.  
**Labels restringidos:** country/market solo si el conjunto es acotado y aprobado.  
**Prohibidos:** user ID, hotel ID, tracked offer ID, source ID, correlation ID, request ID, raw URL, email y texto externo.

### Coste de observabilidad

El budget debe incluir:

- volumen de logs por request/provider/sweep;
- coste de ingestión y almacenamiento si se añade un backend externo;
- coste de traces y errores frontend;
- coste de health probes y canaries;
- coste de métricas de provider, separado del coste de llamadas al provider;
- límite mensual y kill switch.

No se añade un servicio externo de observabilidad sin investigar opciones actuales, privacidad, coste, exportación y salida mediante `gravity_index` y documentación oficial, tal como exige el roadmap.

---

## 10. Matriz de gaps priorizados

| ID | Gap | Prioridad | Criterio de cierre |
|---|---|---:|---|
| H41-P0-01 | Correlación no demostrada de UI→API→provider→worker→event/inbox | P0 | **Parcialmente cerrado en cinco tramos:** browser→API por request, intent estable browser→API para resultados y detalle/rates/parity, API→provider/DB para ingestión/sweeps y worker→provider-run→snapshot/event están probados; queda provider live completo, inbox/delivery y fixture multiusuario |
| H41-P0-02 | No hay dashboards RED/provider activos ni métricas RED/provider persistentes | P0 | backend de métricas elegido, dashboard RED/provider y consulta de ejemplo; el ledger diario agregado, endpoint admin local y cabina operativa visual admin están implementados |
| H41-P0-03 | `HotelProviderRun` no expresa todos los outcomes/latencia/budget del contrato H09 | P0 | **Parcialmente cerrado:** endpoint admin de runs recientes calcula duración desde timestamps y devuelve outcomes/items de forma segura; `latency_sink` mide fixture/canary en ingestion, revalidation y area search y, cuando existe run, persiste agregados multi-operación mediante `0053`; siguen faltando budget/cost, resumen por unidad, provider live y evidencia de canary real. El [plan de contrato de latencia](../../plans/2026-08-09-hotel-provider-latency-contract-plan.md) distingue esta persistencia local de las métricas field |
| H41-P0-04 | Redaction incompleta de excepciones Makcorps y errores frontend | P0 | tests con API key en query, URL firmada, email/token en stack y newline injection |
| H41-P0-05 | No hay alertas operativas de freshness, sweep missed, 429, timeout, delivery backlog o cost | P0 | reglas con owner/runbook/cooldown y prueba de firing/recovery |
| H41-P0-06 | Formatter JSON-like y `str(exc)` pueden permitir log injection o exposición de URL/query | P0 | **Parcialmente cerrado en sinks locales:** `SafeJsonFormatter` usa serialización segura, redaction de query/Authorization/Cookie/URLs firmadas y regresiones de comillas/newlines/secrets; queda validar formatos adicionales y operación centralizada |
| H41-P1-01 | `provider_health_stats` no es modelo hotelero persistente y usa semántica de vuelos | P1 | **Parcialmente cerrado:** agregador admin hotelero persistente sobre `HotelProviderRun` + `hotel_daily_metric`, con estados honestos y ventana acotada; quedan storage/expiración operativos y dashboards RED/provider |
| H41-P1-02 | No hay propagación de trace context ni span provider/DB | P1 | trace context probado en API→provider→DB o decisión documentada de no introducir OTEL todavía |
| H41-P1-03 | No hay métricas persistentes detalladas de alert evaluation, dedupe, inbox read ni delivery externo | P1 | ampliar el ledger solo con dimensiones allowlisted y tests H26-H28/H39; el bridge `in_app` y los agregados diarios básicos están verificados |
| H41-P1-04 | Health `/health` y `/ready` son básicos | P1 | **Parcialmente cerrado:** endpoint admin separado `/api/v1/admin/hotels/health`, sin side effects ni provider calls, con `unknown/not_configured` honesto; probes de proceso permanecen mínimos |
| H41-P1-05 | ~~Inbox hotelero conserva un fallback de ownership por `hotel_id`~~ | ~~P1~~ | **Cerrado parcialmente:** el inbox no atribuye por `hotel_id` solo; exige `user_id` o regla histórica del usuario, y la trazabilidad de intent exige el mismo ownership más `provider_run_id`; quedan fuera de alcance los eventos legacy sin vínculo atribuible |
| H41-P2-01 | Retención/sampling/coste de logs y traces no están fijados | P2 | política aprobada por H35/H42 y valores efectivos auditables |
| H41-P2-02 | Falta RUM hotelero operativo y relación entre errores frontend y operaciones API | P2 | eventos minimizados, correlation segura, volumen suficiente y dashboard de experiencia; la instrumentación lab opt-in ya existe |

---

## 11. Gates y pruebas

### Gate O — Correlación

- request con `x-correlation-id` conserva el valor en response y logs;
- request sin header obtiene un ID nuevo, acotado y no predecible;
- provider call conserva operación/provider/attempt sin secreto;
- worker sin HTTP crea execution/run ID;
- evento de alerta e inbox se puede localizar sin usar `hotel_id` como único ownership;
- operación concurrente no mezcla IDs de dos usuarios.

### Gate M — Métricas

- success, empty, partial, timeout, 429, unavailable e invalid response incrementan outcomes distintos;
- histogramas tienen labels de baja cardinalidad;
- los contadores sobreviven al restart según el backend elegido o declaran la pérdida;
- budget denied y circuit open son visibles sin llamadas externas;
- no se crea una serie por hotel/usuario/oferta.

### Gate R — Redaction

- API keys en params, Authorization, cookies y URLs firmadas no aparecen;
- errores con email, teléfono, target price o stack externo se sanean;
- raw payload incompatible no llega a logs públicos;
- mensajes con newline no falsifican líneas de log;
- `/ux/errors` rechaza o sanea datos no permitidos;
- tests de H35/H38 y logging pasan.

### Gate S — SLO/alerting

- cada regla tiene owner, severidad, ventana, cooldown, dashboard y runbook;
- se prueban firing, recovery y ausencia de alert storm;
- no se alerta por un solo hotel ni un solo usuario;
- un sweep omitido se distingue de un sweep vacío/completado;
- delivery `queued` no se cuenta como `sent`.

### Gate E — E2E hotelero

Fixture reproducible:

```text
search → provider outcome → snapshot/tracking → sweep/revalidation
→ rule evaluation → inbox/delivery → UI recovery
```

Debe cubrir al menos:

- provider mock exitoso y vacío;
- timeout/429/partial sin falso `sold_out`;
- error de red y retry/circuit;
- dos usuarios con el mismo hotel sin fuga de evento;
- alert dedupe y cooldown;
- delivery failed/retry/suppressed;
- frontend error con correlation segura;
- restart del worker y lease/run outcome.

### Evidencia requerida

- fixture/payload sanitizado y comando reproducible;
- captura de logs estructurados redacted;
- consulta o export de métricas;
- screenshot o enlace de dashboard cuando exista;
- resultado de tests y versión de schema;
- owner de revisión y fecha de expiración de la evidencia;
- ninguna afirmación de “SLO passed” basada solo en un test estático.

---

## 11.1. Delta implementado en este incremento (2026-08-08)

- `SafeJsonFormatter` sustituyó el template JSON-like concatenado en `backend/app/core/logging.py`.
- Los mensajes se serializan con `json.dumps`, por lo que comillas y saltos de línea no pueden falsificar registros adicionales.
- El sink local aplica redaction a credenciales comunes, valores `Authorization: Bearer`, cookies y parámetros de URLs firmadas antes de emitir el registro.
- `backend/tests/unit/test_safe_logging.py` cubre JSON válido, inyección de comillas/newlines, `api_key`, firma de URL, bearer token, cookie y payload de worker.
- Validación focalizada: **20 tests pasados** y Ruff sin errores.

Este delta cierra solo la parte demostrada de seguridad del sink local. No convierte logs en métricas persistentes, no crea dashboards y no activa SLO/alertas de producción.

## 11.2. Delta de correlación de sweeps (2026-08-08)

- La revisión de modelos añade `HotelProviderRun.correlation_id` y `HotelProviderRun.execution_id`, ambos nullable para conservar históricos, con índices de investigación.
- La revisión `0048_hotel_provider_run_context` es reversible y está cubierta por roundtrip SQLite y `alembic check` focalizado.
- `run_hotel_sweep` conserva el correlation ID del contexto HTTP cuando existe y genera un execution ID para jobs autónomos.
- `hotels_sweep.run_once`/`run_loop` generan IDs opacos por ejecución y `hotel_sweep_cycle` los emite junto al `provider_run_id`.
- El endpoint administrativo de provider-run expone los IDs de correlación sin convertirlos en labels métricos.
- La evidencia actual demuestra worker→run→snapshot/evento, evento→ledger hotelero→worker→estado local y publicación transaccional de agregados diarios; no demuestra todavía browser→API→provider live, propagación por unidad, delivery externo ni dashboards/SLO.
- Validación: **78 tests hoteleros**, **7 tests de migración/Alembic**, compilación, Ruff y `git diff --check` correctos.

Este delta no convierte H41-P0-01 en cierre completo ni declara un ID estable de intención, trazas distribuidas, dashboards o SLO productivos.

## 11.3. Delta browser→API por request (2026-08-08)

- La capa compartida `frontend/src/modules/shared/api.ts` ya genera `x-correlation-id` opaco para `apiFetch`, `apiFetchWithStatus` y best-effort, por lo que las llamadas hoteleras lo heredan sin duplicar lógica.
- `frontend/tests/api-correlation.test.ts` verifica el header real enviado en una ruta `/hotels/*`, la preservación de headers caller-safe y la generación de IDs distintos por request.
- La misma capa ya conserva el `x-correlation-id` de respuesta en `ApiError.correlation_id` para diagnósticos de errores.
- Validación frontend: typecheck, ESLint y **4 tests** de correlación/error observability pasados.

Este delta demuestra correlación browser→API por request y un intent estable para la request de resultados hoteleros; la persistencia posterior en `HotelProviderRun` para ingestión/sweeps se documenta en el delta siguiente. No demuestra todavía agrupación de detalle/rates/parity ni propagación a inbox/delivery.

## 11.4. Delta de intent estable browser→API (2026-08-08)

- `frontend/src/modules/hotels/hooks/useHotelSearch.ts` genera un ID opaco por ejecución de búsqueda; no usa estado global ni `localStorage`.
- `searchHotels` y `areaSearch` aceptan el intent de forma explícita y lo envían como `x-client-event-id`, manteniendo separado el `x-correlation-id` nuevo por request.
- La capa backend normaliza el header opcional, lo conserva en el contexto del request, lo incluye en logs/error envelopes y lo devuelve solo cuando es válido; valores con email/espacios se descartan.
- Las regresiones cubren unicidad del generador, header real, concurrencia/aislamiento y compatibilidad de callers legacy; el backend cubre normalización, respuesta y error envelope.
- Validación focalizada: **12 tests frontend** y **27 tests backend** pasados; TypeScript, ESLint, compilación Python, Ruff y `git diff --check` correctos.

Este delta cierra solo browser→API para la request de resultados. No persiste el intent ni lo lleva todavía a provider, DB, detalle/rates/parity, inbox o delivery; el siguiente delta cubre la frontera de runs y el posterior las lecturas read-only.

## 11.5. Delta API→provider/DB→HotelProviderRun (2026-08-08)

- `HotelProviderRun.client_event_id` es nullable, indexado y compatible con históricos mediante la migración reversible `0049_hotel_provider_run_client_event`.
- `/api/v1/hotels/ingest/mock` crea un run explícito, conserva `correlation_id` + `client_event_id` + `execution_id`, enlaza sus snapshots por `provider_run_id` y devuelve el identificador del run; las búsquedas `/search` y `/area-search` siguen siendo read-only y no crean runs artificiales.
- `run_hotel_sweep` nunca hereda ni acepta `client_event_id`: al evaluar reglas globales de varios usuarios, el `HotelProviderRun` permanece sin intent browser; el worker autónomo además limpia cualquier intent heredado y genera su propio `execution_id`.
- El adapter Makcorps recibe `x-correlation-id` y `x-client-event-id` como headers opacos; las llamadas paralelas de `area_search` copian explícitamente el `ContextVar` al hilo ejecutor. Ningún ID se usa como label métrico.
- Un fallo de ingestión descarta la transacción parcial antes de guardar el run terminal `failed`; no se publican aliases/snapshots parciales.
- Regresiones añadidas: persistencia API→run→snapshot, worker sin herencia de intent, headers del adapter/redaction y rollback ante ingestión parcial.
- Validación focalizada: **88 tests hoteleros**, compilación Python, Ruff y `git diff --check` correctos.

Este delta cierra la frontera API→provider/DB para operaciones con run. No crea persistencia para búsquedas de catálogo, no agrupa detalle/rates/parity ni inbox/delivery, y no declara provider live, métricas persistentes, dashboards o SLO productivos.

## 11.6. Delta de agrupación de lecturas detail/rates/parity (2026-08-08)

- `useHotelSearch` conserva el `searchIntentId` de la ejecución actual y lo expone a la página sin estado global ni `localStorage`.
- `useHotelDetail` recibe ese intent y lo reenvía a `getHotelDetail`, `getHotelRates` y `getHotelParity`; las tres requests conservan correlaciones independientes y comparten el mismo `x-client-event-id`.
- El `AbortController` compartido sigue cancelando las tres lecturas cuando cambia la selección o se desmonta el hook.
- Los endpoints siguen siendo read-only: el middleware devuelve el intent válido, pero no crea `HotelProviderRun` ni filas de request.
- Validación focalizada: **15 tests frontend**, **67 tests backend**, TypeScript, ESLint, Ruff, compilación Python y `git diff --check` correctos.

Este delta cierra la agrupación browser→API de la selección hotelera. No persiste lecturas, no enlaza inbox/delivery y no demuestra provider live ni métricas persistentes.

## 11.7. Delta alertas → inbox → trazabilidad de intent (2026-08-09)

- `HotelAlertEvent` conserva el enlace existente a `user_id`, `rule_id` y `provider_run_id`; no se añadieron columnas duplicadas de `correlation_id` ni `client_event_id`.
- `get_hotel_alert_trace` deriva esos IDs mediante `HotelAlertEvent.provider_run_id → HotelProviderRun`, y devuelve `None` si el evento no pertenece al usuario o solo comparte `hotel_id`; los runs globales no reciben intents browser.
- Eventos históricos sin `user_id` siguen siendo atribuibles únicamente cuando su `rule_id` pertenece al usuario; eventos sin regla no se recuperan.
- `evaluate_hotel_alerts` registra la creación con IDs opacos de alerta/run y la correlación heredada; la redacción común no expone secretos.
- El inbox público mantiene solo `source_type/source_id` y estado de lectura; no expone intent, correlación ni ownership interno.
- No se crean `NotificationEvent` artificiales para hoteles: el bridge separado `HotelNotificationDelivery` cubre solo `in_app` local con worker/retry; los canales externos siguen fuera de H28/H41.
- Regresión añadida para dos usuarios con el mismo hotel, evento legacy, derivación correcta y ausencia de fuga en inbox.
- Validación focalizada: **73 tests backend**, Ruff, compilación Python y `git diff --check` correctos.

Este delta cierra la atribución segura de alertas hoteleras hacia el run y el inbox. Los incrementos posteriores añaden delivery `in_app` local separado, un ledger diario agregado y una cabina admin visual consultable; no declaran canales externos, dashboards RED/provider ni SLO de producción.

## 11.8. Delta cabina admin de observabilidad (2026-08-09)

- `frontend/src/app/(private)/admin/hotels-observability/page.tsx` añade una vista admin separada para consultar `GET /api/v1/admin/hotels/observability`.
- La cabina reutiliza `apiFetch`, valida `/auth/me`, redirige usuarios no admin y ofrece estados loading/error/empty con reintento.
- Los filtros respetan los límites del backend: ventana 1–31 días y providers, métricas y outcomes allowlisted; el cambio de señal restringe los outcomes compatibles.
- El ledger se presenta como tabla semántica responsive con barras CSS proporcionales, cifras exactas accesibles y estado interpretativo de atención; no expone IDs privados ni payloads.
- Se añaden helpers puros, regresiones frontend, copy ES/EN y enlace desde Product Health. No se introduce dependencia de charts ni servicio externo.
- Validación: typecheck, lint, **530 tests frontend** (17 omitidos), backend focalizado, Ruff y `git diff --check` correctos; smoke Chromium automatizado con **4 escenarios**, `failedAssertions=0`, cero errores de consola y cero overflow visual. Evidencia: `docs/qa/evidence/h41-admin-hotels-observability/report.json` y sus capturas. La revisión humana y cross-browser siguen pendientes.

Este delta activa una lectura visual operativa del ledger local para admins. No cierra dashboards RED/provider, trazas distribuidas, alertas SLO ni delivery externo.

## 11.9. Delta health hotelero persistente admin-only (2026-08-09)

- `GET /api/v1/admin/hotels/health` consulta únicamente `HotelProviderRun` y `hotel_daily_metric`; no modifica la transacción, no contacta con Makcorps u otro provider y mantiene intactos `/health` y `/ready`.
- La ventana de lectura es explícita y acotada a 1–168 horas. El resumen devuelve `generated_at`, `window_hours`, `latest_run` y providers de baja cardinalidad con counts de runs, estado terminal observado, edad y delivery failures.
- Los estados son prudentes: `unknown` sin evidencia, `not_configured` para `skipped`, `ok` para run completado reciente sin señales negativas, `degraded` para parcial/en curso/retry/antigüedad y `critical` para fallo de run o delivery.
- Los estados persistidos desconocidos se normalizan a `unknown`; no se exponen `user_id`, `hotel_id`, email, payloads, URLs ni IDs de alta cardinalidad.
- La cabina reutiliza `apiFetch`, carga health y ledger en paralelo, muestra el resumen observado localizado ES/EN y conserva protección admin, retry, guard de requests obsoletas y responsive QA.
- Regresiones: acceso admin, ausencia de runs honesta, run completado con métricas persistidas, bounds de ventana, normalización de contrato y helper de tonos frontend.
- Validación focalizada: **10 tests backend**, **5 tests frontend**, Ruff, TypeScript, ESLint, sintaxis del runner, `git diff --check` y smoke Chromium actualizado con `healthVisible=true`, request al endpoint de health y `failedAssertions=0` en cuatro escenarios.

Este delta cierra solo la lectura persistente local de health para admins. No convierte `/health`/`/ready` en probes hoteleros, no demuestra provider live, frescura subdiaria, dashboards RED/provider, firing/recovery de SLO, retención o delivery externo.

## 11.10. Delta diagnóstico de runs recientes (2026-08-09)

- `GET /api/v1/admin/hotels/runs?limit=1..50` ofrece una lista admin-only y bounded de `HotelProviderRun` persistidos.
- La transformación es privacy-safe: status desconocido → `unknown`, provider allowlisted, duración solo si hay timestamps, `items_processed` no negativo, `has_error` booleano y outcomes filtrados por allowlist.
- No se exponen IDs internos, correlation IDs, intents browser, errores raw ni claves JSON arbitrarias; no se realizan llamadas externas ni commits.
- La cabina muestra los runs recientes con estado, provider, hora, items, duración e indicador de error, reutilizando la misma carga protegida y copy ES/EN.
- El runner Chromium mockea y verifica `/admin/hotels/runs`, además de health y ledger, en desktop/mobile × light/dark.
- Validación focalizada: 13 tests backend, 6 tests frontend, Ruff, TypeScript, ESLint, compileall y diff check. La evidencia visual final se regenera con `runsVisible=true`, request al endpoint y `failedAssertions=0`.

Este delta mejora el diagnóstico de runs persistidos sin afirmar latencia provider, budget/cost, outcomes por unidad, provider live ni dashboards RED/provider.

## 11.11. Delta de controles persistidos de provider (2026-08-09)

- `GET /api/v1/admin/hotels/provider-controls?limit=1..50` añade una lectura admin-only, bounded y de solo lectura sobre `HotelProviderBudget` y `HotelProviderCircuit` ya persistidos.
- Devuelve únicamente provider y operación allowlisted, ventana y consumo de unidades, unidades restantes, expiración, origen local, estado del circuito, fallos consecutivos, threshold, próximas fechas de probe y códigos de error allowlisted.
- No expone IDs, `probe_token`, correlation/client intent, texto de error raw ni permite resetear/forzar budget o circuit; la lectura no contacta providers ni hace commits.
- Los providers y operaciones fuera de la allowlist se excluyen del listado; en las filas admitidas, estados, sources, error codes y formatos de ventana legacy desconocidos se normalizan a `unknown`; las ventanas expiradas no se presentan como budget activo.
- La cabina admin carga esta lectura junto a health/runs/ledger y muestra tarjetas responsive de budget/circuit con copy ES/EN y etiqueta explícita de solo lectura.
- La regresión cubre RBAC, límites, cálculo de unidades restantes y redacción de IDs/tokens/errores; el runner Chromium verifica la request y visibilidad en desktop/mobile × light/dark.

Este delta hace consultable la protección operativa persistida local. No afirma latencia provider, coste monetario, provider live, firing/recovery de alertas, dashboards RED/provider ni SLO productivo.

## 11.12. Delta de diagnóstico de leases y expiración (2026-08-09)

- `GET /api/v1/admin/hotels/sweep-leases?limit=1..50` añade una lectura admin-only y bounded de `HotelSweepLease` persistido.
- La respuesta expone solo estado derivado, intentos acotados, expiración, finalización, código de error allowlisted, indicador booleano de run enlazado y timestamp de actualización; no expone fingerprints, lock tokens ni `last_provider_run_id`.
- Un lease `running` cuyo `lease_expires_at` ya venció se clasifica como `expired` y `attention=true`. Esto es señal de lock expirado, no prueba de una ventana de scheduler perdida porque el modelo actual no persiste una ventana programada.
- La cabina admin muestra una muestra de leases, contadores de atención/expirados/en curso y estados responsive ES/EN; no activa alertas ni repara/renueva leases.
- Regresiones cubren RBAC, límite, expiración derivada, redacción de identificadores y normalización de error codes; el runner Chromium verifica request y visibilidad en desktop/mobile × light/dark.

Este delta prepara el diagnóstico para H42 sin afirmar freshness de scheduler, latencia provider, provider live, alertas productivas ni SLO.

## 11.13. Delta de agregados de outcomes por provider (2026-08-09)

- `GET /api/v1/admin/hotels/provider-outcomes?limit=1..50` agrega los `tracked_outcomes` de los últimos runs persistidos por provider allowlisted.
- La respuesta conserva `sample_size`, runs por provider, estados normalizados, claves de outcome allowlisted y totales; no expone IDs, mapas JSON raw, hoteles, usuarios ni fingerprints.
- El contrato llama a estos valores contadores agregados de run: no son una traza individual por hotel ni una prueba de cobertura completa por unidad.
- La cabina admin muestra una tarjeta responsive con los contadores observados y copy ES/EN que limita explícitamente su interpretación.
- Regresiones cubren RBAC, límite, normalización de estados y redacción de claves arbitrarias; el runner Chromium verifica request y visibilidad junto a health, controls y leases.

Este delta mejora la lectura de outcomes persistidos sin añadir latencia provider, coste monetario, provider live, métricas RED completas ni alertas productivas.

## 11.14. Delta de contrato de latencia provider (2026-08-09)

- Se añade el [plan de contrato de latencia provider](../../plans/2026-08-09-hotel-provider-latency-contract-plan.md), el modelo `HotelProviderLatencyAggregate` y la migración reversible `0053_hotel_provider_latency_aggregate`; no se activa ninguna llamada live.
- El contrato separa `provider_duration_ms` de `run_duration_seconds`, exige reloj monotónico alrededor de la llamada efectiva y mantiene outcomes/error codes allowlisted sin PII, URLs, credenciales ni payloads.
- La persistencia agrega varias operaciones, intentos y outcomes por `HotelProviderRun`; la clave incluye provider/operation/outcome/error code y la escritura es bounded, idempotente por grupo y sin commit interno.
- Este delta no aporta muestras productivas ni cierra el canary real: la latencia provider agregada por run está persistida y cubierta con migración/tests; la evidencia field, dashboards RED/provider y el provider live siguen pendientes.

## 12. Handoff a H42-H45

| Fase | Entrega de H41 |
|---|---|
| H42 | cada alerta operativa necesita runbook de diagnóstico, contención, recovery y comunicación |
| H43 | flags off deben impedir llamadas externas; canary debe emitir métricas y tener kill switch |
| H44 | seed/fixtures deben generar provider outcomes, runs, snapshots, alertas e inbox reproducibles |
| H45 | release gate debe consultar errores, freshness, delivery, coste, dashboard y evidencia de rollback |
| H35/H38 | redaction, acceso, retención, secretos y minimización deben revisarse antes de producción |
| H39/H40 | tests de observabilidad y browser deben formar parte de los gates, sin convertir evidencia histórica en pase actual |

### Criterio de salida de H41

H41 está **contractualmente completa** cuando este documento, H04-H06, H09, H26-H28, H35, H37-H40 y el roadmap expresan la misma taxonomía y ownership. La **implementación de H41** solo podrá declararse completa cuando:

1. exista una cadena correlacionada reproducible de búsqueda/sweep a inbox/UI;
2. haya métricas persistentes hoteleras y dashboards consultables;
3. los outcomes H06/H09 estén separados y no se oculten como `empty`;
4. provider, worker, DB, alertas y delivery tengan owners y health verificable;
5. redaction y cardinalidad pasen pruebas adversariales;
6. SLOs calibrados tengan firing/recovery y runbooks H42;
7. coste, sampling y retención estén aprobados;
8. H43/H45 prueben flags, canary y rollback.

**Resultado H41:** contrato de observabilidad aprobado, hardening local de logs en QA, correlación parcial browser→API→detalle/rates/parity + browser→API→provider/DB→run/snapshot verificada, ledger diario agregado local, health persistente admin-only basado en DB, diagnóstico bounded de runs recientes, controles persistidos de budget/circuit, diagnóstico de leases expirados, agregados de outcomes por provider y cabina admin visual con smoke Chromium automatizado en QA. No se declara que el tracker tenga ya correlación browser/provider live completa, persistencia para lecturas read-only, métricas RED/provider completas, trazas, health productivo de `/health`/`ready`, freshness de scheduler, coste monetario, dashboards RED/provider o SLO operativos en producción; la persistencia de latencia agregada por run no equivale a métricas field ni a un SLO; la revisión humana/cross-browser de la cabina sigue pendiente.
