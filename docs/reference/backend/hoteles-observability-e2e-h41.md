# H41 — Observabilidad end-to-end del tracker hotelero

**Estado:** COMPLETA como contrato; instrumentación hotelera, métricas persistentes, dashboards, SLO y alertas operativas pendientes  
**Fecha:** 2026-08-05  
**Área:** backend / frontend / workers / providers / alertas / operación / privacidad  
**Fuente de verdad:** sí para la matriz de observabilidad hotelera y sus gates; no certifica que la instrumentación objetivo ya esté desplegada  
**Fase del roadmap:** H41  
**Depende de:** H06, H09, H26-H28, H35-H40  
**Relacionado con:** H04 métricas de producto, H05 freshness/provenance/confidence, H23 tracking desde oferta, H37 coste/rendimiento, H38 secretos/SSRF/abuso, H42 runbooks, H43 flags/canary, H45 release

> H41 define cómo explicar una búsqueda, un sweep, una revalidación o una alerta hotelera desde la primera petición hasta el resultado visible. No añade por sí sola un sistema de métricas, OpenTelemetry, un SaaS de monitorización ni un dashboard: primero fija señales, privacidad, cardinalidad, ownership, SLO candidatos y evidencia necesaria para implementarlos sin inventar cobertura.

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
| Correlación HTTP | `backend/app/main.py` normaliza `x-correlation-id`, lo coloca en `request.state`, lo conserva en contexto y lo devuelve en la respuesta | las requests HTTP pueden correlacionarse si el ID llega o se genera | que el ID se propague a cada llamada externa, job, query o acción frontend |
| Logs backend | `backend/app/core/logging.py` configura stdout + fichero, formatter JSON-like y `CorrelationIdFilter` | hay una base común de logs con `correlation_id` | el formatter actual no garantiza JSON seguro frente a comillas/newlines; tampoco existe agregación, búsqueda, rotación, retención o alerting centralizado |
| Redacción HTTP | `test_unhandled_exception_contract.py` cubre sanitización de bodies y el nivel de `urllib3.connectionpool` | algunos errores y cuerpos de validación no deben exponer secretos | que excepciones de provider, raw payloads, trazas y stacks frontend estén completamente saneados |
| Worker hotelero | `backend/app/worker/hotels_sweep.py` y `app/hotels/jobs/run_hotel_sweep.py` emiten start/cycle/finished/failed y conteos básicos | un operador puede encontrar eventos de ciclo en logs locales | que los runs sean métricas persistentes, que tengan outcomes por unidad o que haya alertas de SLO |
| Makcorps | `backend/app/hotels/makcorps_provider.py` emite `makcorps_disabled` y `makcorps_request_failed` | se registra que el adapter está desactivado o que una request falló | que haya latency/outcome/attempt/budget consistente; str(exc) puede contener URL/query y requiere scrubber antes de considerarse seguro |
| Health del proceso | `/health` y `/ready` devuelven estados básicos | existen probes sintéticos mínimos | que el provider, worker, DB, budget o freshness hoteleros estén saludables |
| Health en memoria | `provider_health_stats.py` agrupa muestras por `provider_id`, con latencia y códigos de warning | existe un patrón de agregación de salud en memoria | no es un ledger hotelero persistente: sus campos actuales son de vuelos (`flights_count`, warnings de flight provider) y se pierde al reiniciar |
| Alertas | `services/alert_service.py` registra revalidaciones de alertas de vuelos; `notification_inbox.py` resuelve fuentes hoteleras, pero conserva un fallback por `hotel_id` señalado por H38 como riesgo cross-user | hay patrones de logging y lectura privada reutilizables, con una limitación de aislamiento ya conocida | no hay evidencia de métricas hoteleras de evaluación, dedupe, delivery, lectura o deep-link; el inbox no puede declararse estrictamente privado hasta cerrar ese fallback |
| Frontend | `frontend/src/lib/errorLogging.ts` trunca sección, mensaje y stack y envía `/ux/errors` cuando hay token | existe un canal best-effort de errores cliente | truncar no es redaction; no hay evidencia de RUM hotelero, correlation propagation, métricas de interacción o dashboard |
| Tests | existen tests de logging/correlation y tests hoteleros de provider/sweep/API | hay regresiones parciales útiles | H39 confirma que faltan gates de provider live, locks, SSRF, migraciones y browser hotelero |

**Conclusión del baseline:** hay instrumentación de logs y correlación reutilizable, pero no una observabilidad E2E hotelera. Los dashboards, series temporales, traces distribuidos, SLO y alertas de operación siguen pendientes.

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
| Browser → API | `x-correlation-id` o equivalente generado por cliente; locale y operación sin PII | response correlation está probado; propagación cliente hotelera no está demostrada |
| API → gateway/provider | request ID, operación, timeout y budget | pendiente de contrato V2 H06/H09 |
| API → DB | provider run/job ID y outcome | parcialmente persistido en modelos V1; falta envelope completo |
| Worker → provider | execution/run ID, provider/operation, attempt | worker registra run básico; falta cadena por unidad |
| Evaluador → evento | snapshot/base/current, rule ID, reason, dedupe key | contrato H26 lo exige; métricas hoteleras no están demostradas |
| Evento → delivery/inbox | source ref, delivery attempt/outcome, read state | inbox privado existe parcialmente; delivery E2E queda en H28 |
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

Las métricas objetivo siguientes son un contrato de implementación, no métricas activas hoy.

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
| H41-P0-01 | Correlación no demostrada de UI→API→provider→worker→event/inbox | P0 | fixture multiusuario y sweep reproducen una operación completa con IDs enlazados |
| H41-P0-02 | No hay métricas hoteleras persistentes ni dashboards activos | P0 | backend de métricas elegido, schema versionado, dashboard y consulta de ejemplo |
| H41-P0-03 | `HotelProviderRun` no expresa todos los outcomes/latencia/budget del contrato H09 | P0 | migración compatible y resumen por unidad/run |
| H41-P0-04 | Redaction incompleta de excepciones Makcorps y errores frontend | P0 | tests con API key en query, URL firmada, email/token en stack y newline injection |
| H41-P0-05 | No hay alertas operativas de freshness, sweep missed, 429, timeout, delivery backlog o cost | P0 | reglas con owner/runbook/cooldown y prueba de firing/recovery |
| H41-P0-06 | Formatter JSON-like y `str(exc)` pueden permitir log injection o exposición de URL/query | P0 | logging estructurado con serialización segura, scrubber antes de emitir y tests de comillas/newlines/secrets |
| H41-P1-01 | `provider_health_stats` no es modelo hotelero persistente y usa semántica de vuelos | P1 | adapter/aggregator hotelero con outcomes H06 y storage/expiración definidos |
| H41-P1-02 | No hay propagación de trace context ni span provider/DB | P1 | trace context probado en API→provider→DB o decisión documentada de no introducir OTEL todavía |
| H41-P1-03 | No hay métricas de alert evaluation, dedupe, inbox read ni delivery E2E | P1 | eventos contractuales y tests H26-H28/H39 cubren estados terminales |
| H41-P1-04 | Health `/health` y `/ready` son básicos | P1 | health hotelero sin side effects y con `unknown/not_configured` honesto |
| H41-P1-05 | Inbox hotelero conserva un fallback de ownership por `hotel_id` | P1 | eliminar/quarantinar la relación legacy, exigir regla/tracking relacional y probar dos usuarios con el mismo hotel |
| H41-P2-01 | Retención/sampling/coste de logs y traces no están fijados | P2 | política aprobada por H35/H42 y valores efectivos auditables |
| H41-P2-02 | Falta RUM hotelero y relación entre errores frontend y operaciones API | P2 | eventos minimizados, correlation segura y dashboard de experiencia |

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

**Resultado H41:** contrato de observabilidad aprobado. No se declara que el tracker tenga ya métricas, trazas, dashboards o SLO operativos en producción.
