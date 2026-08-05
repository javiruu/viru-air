# H37 — Benchmark, rate limits, locks y coste máximo hotelero

**Estado:** COMPLETA como contrato; implementación, benchmark de canary y revisión del plan comercial pendientes  
**Fecha:** 2026-08-05  
**Área:** backend / providers / workers / base de datos / costes / observabilidad  
**Fuente de verdad:** sí para la metodología, límites, presupuestos y criterios de cierre de H37  
**No es:** una medición de producción, una garantía de capacidad, una aprobación de provider ni una tarifa comercial

**Depende de:** H06 provider-neutral, H07 auditoría Makcorps, H08 onboarding, H09 gateway/sweeps, H10 estancia/oferta, H11 migración  
**Relacionado con:** H05 freshness/provenance/confidence, H15 resultados, H23 tracking, H26 alertas, H27 inbox, H28 delivery, H29 lifecycle, H35 legal/privacy, H36 frontend performance, H39 tests, H41 observabilidad, H43 flags/canary.

> H37 evita que una búsqueda o un sweep conviertan el coste, la cuota o la concurrencia del provider en una sorpresa. Un benchmark local no demuestra capacidad externa; una respuesta `200` no demuestra precio estable; y un worker que termina sin excepción no demuestra que haya ejecutado el trabajo correcto una sola vez.

---

## 1. Objetivo y frontera

H37 debe permitir responder con evidencia:

1. cuántas consultas puede aceptar `/hoteles` sin saturar la base ni el provider;
2. cuántas unidades de tracking puede procesar una ventana de sweep;
3. qué trabajo se comparte, deduplica, retrasa o rechaza;
4. qué sucede ante `429`, timeout, `5xx`, respuesta inválida o caída del provider;
5. cuál es el límite duro de requests/unidades/coste por ventana;
6. cómo se evita que dos workers ejecuten dos veces la misma `StayQuery`;
7. cómo se recupera un lease expirado sin que el owner antiguo escriba resultados tardíos;
8. cómo se demuestra el resultado con fixtures, canary y datos de producción sin PII.

H37 cubre:

- benchmark de API, consultas SQL, provider gateway y worker;
- rate limits por provider, operación, usuario/IP cuando corresponda y ventana;
- reserva de presupuesto antes de cada llamada externa;
- locks, leases, singleflight, dedupe e idempotencia;
- concurrencia, pool DB, fan-out y backpressure;
- timeout, retry, `Retry-After`, jitter y circuit breaker;
- coste estimado por búsqueda, mapping, revalidación y sweep;
- límites, degradación, replay, kill switch y rollback;
- observabilidad agregada y redaction según H35.

H37 no decide:

- qué provider comercial se aprueba (H07/H08);
- el modelo canónico definitivo de estancia (H10/H11);
- la semántica de freshness o elegibilidad de alertas (H05/H26);
- la compra de una plataforma externa de métricas o rate limiting;
- una tarifa que no esté respaldada por cuenta, contrato o factura del provider.

---

## 2. Estado real V1 observado

| Superficie | Evidencia en código/docs | Lectura correcta |
|---|---|---|
| Makcorps timeout | `backend/app/hotels/makcorps_provider.py` usa `HOTEL_PROVIDER_TIMEOUT_SECONDS`, 10 s por defecto | Es un timeout local por request, no un SLA del provider |
| Makcorps retry | `urllib3 Retry` tiene hasta 2 retries para 429/500/502/503/504 y backoff local | No existe presupuesto global de retries ni propagación de `Retry-After` al dominio |
| API key | El adapter añade `api_key` a los query params | H35 debe revisar leakage en access logs, proxies, tracing y redaction; no es un control de coste |
| Búsqueda de área | `_fetch_and_store_provider_rates()` usa `ThreadPoolExecutor(max_workers=5)` | Existe concurrencia local fija; no es un límite provider-aware ni un budget persistente |
| Sweep | `run_hotel_sweep()` crea `HotelProviderRun`, ingesta, evalúa alertas y barre tracking | No hay lease distribuido, reserva previa, estado parcial ni coste agregado demostrable |
| Worker | `hotels_sweep.py` ofrece `--once`/`--loop` y sleep | `--loop` no evita que otro proceso/cron ejecute el mismo trabajo |
| Identidad | El sweep dirigido pasa `offer.hotel_id` al adapter; H07 exige `provider_hotel_id` | Hay un bloqueo de mapping antes de aprobar tracking Makcorps |
| Errores | El adapter devuelve `None`/`[]` y varias capas capturan excepciones | Timeout/429 puede confundirse con ausencia de rate si no se introduce un resultado tipado |
| DB | Hay patrones de locks/quota en vuelos y `RevalidationJob`, no un contrato hotelero equivalente | No reutilizar tablas o límites sin comprobar semántica y aislamiento |
| Feature flags | `HOTEL_FEATURE_ENABLED` y `HOTEL_SWEEP_ENABLED` mantienen defaults seguros | Las flags desactivan trabajo; no son ledger, lock ni observabilidad |
| Coste | H07 indica cuota/precio Makcorps no verificados | El presupuesto automático de producción es cero hasta verificar el plan |

**Conclusión V1:** existen protecciones parciales para fixtures y ejecución manual, pero no hay evidencia suficiente para declarar capacidad, coste por sweep, dedupe cross-process, p95 de provider o escalabilidad de producción.

---

## 3. Modelo de unidades y fingerprints

La unidad de coste, lock y benchmark debe ser una `StayQuery` ligada a una operación:

```text
provider_id
canonical_hotel_id
provider_hotel_id
operation: mapping | area_search | hotel_rates | revalidation
check_in
check_out
rooms
adults
children_ages
currency
room_id/room_label
meal_plan
cancellation_policy
tracked_offer_id o search fingerprint
```

El fingerprint debe incluir toda dimensión que pueda cambiar precio o comparabilidad:

```text
sha256(
  provider_id + operation + provider_hotel_id + canonical_hotel_id +
  check_in + check_out + rooms + adults + children_ages + currency +
  room_id/room_label + meal_plan + cancellation_policy
)
```

Reglas:

- Nunca deduplicar solo por `hotel_id`.
- `HotelProperty.id` y `provider_hotel_id` son identificadores distintos.
- El `tracked_offer_id` asocia ownership, snapshot y alertas; no reemplaza el fingerprint.
- Dos usuarios pueden compartir una consulta externa idéntica solo si el resultado se minimiza, no contiene PII y H35/H10 permiten el aislamiento.
- Cambiar fechas, ocupación, moneda, habitación, régimen, cancelación, provider u operación crea otra unidad.
- Un mapping ambiguo o inexistente se marca `skipped_mapping`; nunca se llama al provider con el ID interno como sustituto.

---

## 4. Presupuesto de coste y rate limits

### 4.1. Regla de presupuesto desconocido

Mientras no exista una cuota/precio verificable del plan real del provider:

```text
automatic_production_requests = 0
production_sweep_budget = 0
canary_budget = explicit_and_time_bounded
```

No se extrapolan al endpoint de Viru cifras publicitadas para otro endpoint. El ledger debe registrar la fuente del límite: `provider_contract`, `account_observed`, `local_config` o `fixture_only`.

### 4.2. Ledger mínimo

Cada reserva previa a una llamada externa debe poder asociarse a:

```text
provider_id
operation
budget_window: canary | hour | day | month
hard_limit
units_reserved
units_used
estimated_cost
currency
request_fingerprint
run_id/job_id
reserved_at
released_at
outcome
```

Si la reserva falla, la operación termina como `skipped_budget` o `rate_limited` con `source=local_budget` y no sale ninguna request.

Los retries consumen la misma cuota. No existe el concepto de retry gratis.

### 4.3. Dimensiones de límite

El gateway debe poder limitar por separado:

- `provider + operation` para proteger cuota externa;
- `provider + window` para budget diario/mensual;
- `user_id` para abuso de búsqueda autenticada, con política H35 y sin registrar PII innecesaria;
- IP o fingerprint anónimo para abuso de endpoints públicos, con retención y redaction aprobadas;
- `StayQuery fingerprint` para singleflight;
- worker/pod para evitar que un único proceso consuma toda la ventana;
- tamaño de lote y fan-out de una búsqueda.

El límite efectivo es el mínimo de:

```text
provider_limit
local_hard_limit
remaining_budget
worker_capacity
database_capacity
UX_time_budget
```

### 4.4. Valores y defaults

H37 no fija valores comerciales universales. La configuración debe declarar explícitamente, con default seguro:

```text
HOTEL_PROVIDER_<ID>_ENABLED=false
HOTEL_PROVIDER_<ID>_CANARY_ONLY=true
HOTEL_PROVIDER_<ID>_DAILY_REQUEST_BUDGET=0
HOTEL_PROVIDER_<ID>_MONTHLY_REQUEST_BUDGET=0
HOTEL_PROVIDER_<ID>_MAX_CONCURRENCY=1
HOTEL_PROVIDER_<ID>_MAX_RETRIES=0
HOTEL_PROVIDER_<ID>_MAX_BATCH_SIZE=1
HOTEL_PROVIDER_<ID>_COOLDOWN_SECONDS=300
```

Son nombres de contrato para H43, no afirmación de que todas estas variables ya existan. Un cambio de límite requiere owner, fecha, motivo, fuente y rollback.

---

## 5. Locks, leases y singleflight

### 5.1. Requisito cross-process

Un lock en memoria no basta para varios workers, pods, procesos `--loop` o cronjobs. La implementación debe usar una fuente coordinada (por ejemplo, DB transaccional) y demostrar su comportamiento en PostgreSQL. SQLite debe tener un comportamiento de desarrollo documentado, sin simular garantías que no ofrece.

### 5.2. Registro mínimo de trabajo

```text
job_id/fingerprint
status: queued | running | done | partial | skipped | failed
lock_token
lock_acquired_at
lease_expires_at
attempt_count
scheduled_at
started_at
finished_at
last_error_code
last_provider_run_id
```

### 5.3. Claim atómico

1. seleccionar trabajo vencido o solicitado;
2. ordenar por check-in próximo, alerta crítica, freshness, antigüedad y fingerprint;
3. reclamar con transacción y `FOR UPDATE SKIP LOCKED` en PostgreSQL cuando corresponda;
4. escribir `lock_token` y `lease_expires_at` en el mismo claim;
5. verificar el token al completar y antes de persistir snapshot/alerta;
6. liberar lease en success, skip o fallo;
7. recuperar únicamente leases expirados y aumentar `attempt_count`.

Un owner antiguo que perdió el lease no puede convertir una respuesta tardía en snapshot actual. El resultado puede conservarse como diagnóstico redacted y descartado.

### 5.4. Scopes

| Scope | Propósito |
|---|---|
| `provider + operation` | limitar concurrencia contra el mismo endpoint |
| `StayQuery fingerprint` | singleflight de búsquedas/revalidaciones idénticas |
| `HotelProviderRun` | evitar dos ciclos completos superpuestos cuando la política lo requiera |
| `tracked_offer_id` | serializar snapshot/alerta de una oferta sin bloquear otras |

No usar un lock global para todos los hoteles.

---

## 6. Retry, backoff y circuit breaker

| Resultado normalizado | Retry | Tratamiento |
|---|---:|---|
| `success` | no | persistir resultado elegible |
| `empty` | no | estado válido, no `sold_out` implícito |
| `invalid_request`/`unsupported` | no | corregir capability o StayQuery |
| `authentication_failed` | no | pausar provider y alertar configuración |
| `rate_limited` con `Retry-After` | limitado | respetar cooldown acotado y registrar origen |
| `timeout`/network/5xx | limitado | backoff con jitter y budget restante |
| `invalid_response` | no inmediato | abrir incidente/pausar adapter |
| `unavailable` | según breaker | cache elegible con freshness visible |

Requisitos:

- un único contador de attempts en el gateway;
- ningún retry oculto adicional en adapter, service y worker;
- jitter obligatorio;
- no reintentar tras superar lease, timeout total o budget;
- limitar y sanitizar `Retry-After`;
- propagar outcome, attempts, latencia y request ID opaco;
- distinguir `empty` válido de `rate_limited`, `timeout` y `failed`.

El breaker mínimo por `provider + operation` es `closed`, `open`, `half_open`, con `failure_count`, `opened_at`, `next_probe_at` y `last_error_code`. Un breaker in-memory puede ser protección local, pero no es coordinación definitiva entre workers.

---

## 7. Estados del run y degradación

`HotelProviderRun` objetivo:

```text
created → running → completed
                 ↘ partial
                 ↘ skipped
                 ↘ failed
```

| Estado | Significado |
|---|---|
| `completed` | las unidades planificadas terminaron con resultado válido o vacío, sin degradación bloqueante |
| `partial` | hubo resultados válidos y también timeout, rate limit, error o skip |
| `skipped` | no se ejecutó ninguna unidad por flag, budget, breaker, ventana o ausencia de trabajo |
| `failed` | no se obtuvo un resultado operativo válido para la ventana |

Outcomes de unidad mínimos:

```text
success | empty | partial | rate_limited | timeout | unavailable |
unsupported | invalid_response | failed | skipped_mapping |
skipped_budget | skipped_circuit | skipped_window
```

Reglas de producto:

- `429`, timeout, 5xx o breaker abierto no se convierten en `empty`, `sold_out` ni precio cero;
- `partial` no dispara alerta si la incertidumbre afecta a la condición comparada;
- un snapshot debe conservar `provider_run_id`, outcome, observed_at y fingerprint;
- un fallback histórico debe mostrar freshness y no fingir observación live;
- un sweep omitido no se rellena con timestamp actual.

---

## 8. Metodología de benchmark

### 8.1. Escenarios reproducibles

Separar tres capas:

1. **Fixture:** provider simulado, DB representativa y respuestas deterministas. Mide código local.
2. **Canary:** provider real, ventana pequeña, owner, plan y budget explícitos. Mide contrato externo limitado.
3. **Field:** producción, agregados por operación/provider/estado, sin payload sensible. Mide comportamiento real con volumen suficiente.

Registrar versión de código, Python, DB, esquema, hardware, número de workers, configuración, dataset, provider plan abstracto y fecha. No incluir API keys ni query privada completa.

### 8.2. Dataset mínimo

- búsqueda sin resultados;
- 1, 10, 30 y 100 hoteles;
- 1, 10, 100 y 1.000 tracked offers en fixture;
- una única consulta repetida concurrentemente;
- consultas distintas con mismo hotel;
- fechas/ocupaciones/monedas distintas;
- provider success, empty, 429, timeout, 5xx e invalid response;
- leases expirados, restart y ventana perdida;
- SQLite de desarrollo y PostgreSQL de concurrencia.

### 8.3. Métricas

```text
request_count
attempt_count
budget_reserved/used/denied
p50/p95/p99 latency
error_rate
429_rate
timeout_rate
partial_rate
provider_call_dedup_rate
snapshot_duplicate_rate
lock_contention_rate
lease_recovery_rate
DB query count and p95
pool wait time
worker CPU/memory
sweep duration
offers scanned
snapshots created
alerts created
cost_estimate and cost_source
```

No llamar “cumple” a un p95 basado en una sola ejecución. Si no hay volumen suficiente, el resultado es `no concluyente`.

### 8.4. Gates de capacidad propuestos

Los siguientes son criterios de cierre, no resultados actuales:

- no duplicar llamadas por fingerprint bajo concurrencia controlada;
- cero llamadas externas cuando flags o budget están en cero;
- 429 visible y cooldown respetado;
- retries dentro del límite común;
- ningún snapshot/alerta escrito por owner sin lease;
- p95 de consultas SQL y gateway dentro del presupuesto aprobado por producto/infra;
- coste por búsqueda y sweep menor o igual al presupuesto firmado;
- degradación estable cuando el provider no está disponible;
- memoria, CPU y pool DB dentro de capacidad acordada;
- selección determinista de trabajo cuando el budget no alcanza.

No se fija un umbral universal de p95, porcentaje de éxito ni coste unitario hasta tener hardware, provider, mercado y plan definidos.

---

## 9. Prioridades

### P0 — evitar coste o datos falsos

- mantener providers comerciales automáticos en cero hasta verificar plan y canary;
- resolver `provider_hotel_id` antes de cualquier request dirigida;
- distinguir error externo de `empty`;
- impedir duplicados cross-process por fingerprint;
- reservar budget antes de salir a red;
- asegurar que flags off no realizan llamadas;
- redaction de API key y URLs según H35.

### P1 — capacidad controlada

- gateway único de timeout/retry/budget/breaker;
- ledger por provider/operación/ventana;
- leases y recovery en PostgreSQL;
- límites configurables por usuario/IP/provider sin PII innecesaria;
- reducir N+1, fan-out y consultas de detalle;
- medir pool DB, p95, attempts y coste estimado;
- estados `partial`, `skipped`, `rate_limited` y `unavailable` visibles en run/health.

### P2 — optimización

- batch endpoints del provider cuando la semántica sea comparable;
- singleflight compartido entre búsqueda y tracking;
- priorización adaptativa según check-in/freshness;
- auto-tuning de concurrencia solo con guardrails;
- dashboard histórico de capacidad y coste;
- forecast de crecimiento y límites por mercado.

---

## 10. Replay, ventana perdida y rollback

Un replay exige run/fingerprint explícito, owner, budget separado, dry-run/fixture previo, lease normal e idempotencia. No reemite alertas históricas por defecto.

Si se pierde una ventana:

1. registrar `skipped_window` y motivo;
2. no ejecutar todas las ventanas atrasadas de golpe;
3. aplicar catch-up máximo por provider/operación;
4. priorizar check-in próximo y alertas críticas;
5. mantener freshness real y razón de omisión.

Ante anomalía:

1. apagar flag de provider/sweep;
2. bloquear nuevas unidades y dejar expirar leases;
3. abrir/mantener breaker;
4. conservar snapshots sin marcarlos live;
5. servir cache/histórico elegible con edad visible;
6. rotar credenciales si procede H35;
7. registrar requests, budget, run y owner;
8. reabrir solo tras repetir canary y gates H35/H41/H43.

---

## 11. Gates de cierre

### Gate B — benchmark

- fixtures deterministas y dataset versionado;
- benchmark de 1/10/30/100 resultados y varias escalas de tracking;
- p50/p95/p99, query count, pool y worker registrados;
- PostgreSQL usado para locks/concurrencia;
- resultados marcados medidos, objetivo o no concluyentes.

### Gate L — límites y locks

- claim atómico y lease recovery probados con dos workers;
- una sola llamada externa por fingerprint;
- owner token validado al completar;
- budget denegado no realiza request;
- límites provider/operación/ventana y backpressure observables.

### Gate C — provider/coste

- plan/cuota/coste del provider documentados sin secretos;
- canary pequeño con `max_concurrency=1` y retries explícitos;
- `Retry-After`, 429, timeout, 5xx e invalid response clasificados;
- coste por operación calculado con fuente identificada;
- kill switch y rollback comprobados.

### Gate O — observabilidad y privacidad

- métricas agregadas de requests, attempts, latency, budget, breaker, locks y outcomes;
- logs sin API keys, Authorization, URLs secretas, emails ni payloads innecesarios;
- H35 valida retención, IP/user limits y tracing;
- health no hace requests externas implícitas.

### Gate Q — regresión

- unit/integration/contract tests de provider, gateway, sweep y worker;
- `git diff --check`, lint/typecheck/tests relevantes;
- no regresión en Mock/manual QA;
- documentación de ejecución real, flags y rollback.

**Criterio final:** no quedan P0; los locks, budgets y outcomes están implementados y medidos; el canary tiene coste/cuota verificables; el benchmark de producción está aprobado o marcado no concluyente; y H35/H41/H43 revisan privacidad, observabilidad y rollout.

---

## 12. Claims que H37 no autoriza

Hasta cerrar los gates, no puede afirmarse que `/hoteles`:

- escala a cualquier número de trackings;
- tiene coste fijo o gratuito;
- respeta siempre la cuota del provider;
- evita duplicados entre workers;
- tiene rate limiting distribuido;
- procesa sweeps diarios de forma garantizada;
- ofrece p95 o SLA de provider;
- convierte todos los errores en estados correctos;
- comparte cache/singleflight entre usuarios de forma segura;
- soporta rooms, niños, fees o mercados que no hayan pasado canary;
- usa el provider comercial como fallback equivalente;
- tiene circuito breaker, budget ledger o lease si solo están documentados.

H37 sí autoriza el contrato de que toda llamada futura deberá tener una unidad identificable, un límite, un owner, un outcome, una fuente de coste y una evidencia de benchmark proporcional al riesgo.

---

## 13. Handoff

| Fase | Entrega H37 |
|---|---|
| H09 | gateway, leases, estados parciales y ejecución de sweeps |
| H10/H11 | fingerprint canónico, índices, migración y concurrencia DB |
| H15 | envelope de outcomes y paginación/límites visibles |
| H23/H26 | snapshots, alertas, dedupe y elegibilidad sin duplicar retries |
| H35 | redaction, IP/user limits, retención y secretos |
| H36 | primer resultado, fan-out y presupuesto de frontend |
| H39 | tests de locks, budget, provider y regresión |
| H41 | métricas, health, traces redacted y SLO |
| H43 | flags, canary, rollout y kill switch |

**Resultado H37:** contrato de benchmark, límites, concurrencia y coste aprobado. La implementación actual sigue siendo V1/manual/Mock y no se declara escalable ni económicamente aprobada para providers comerciales hasta superar los gates.
