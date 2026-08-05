# H09 — Gateway, scheduler y sweeps hoteleros seguros

**Estado:** completa como contrato operativo; implementación y canary pendientes  
**Fecha:** 2026-08-04  
**Área:** backend / infraestructura / workers / costes / observabilidad  
**Fuente de verdad:** sí para la semántica de ejecución de sweeps hoteleros hasta que una fase posterior la sustituya con evidencia de implementación.

**Depende de:** [H06 — contrato provider-neutral](hoteles-provider-neutral-contract-h06.md), [H07 — auditoría Makcorps](hoteles-makcorps-audit-h07.md), [H08 — onboarding de providers](hoteles-provider-onboarding-h08.md)  
**Relacionado con:** H05 freshness/provenance/confidence, H10 estancia/oferta, H11 migración, H15 resultados, H26 dedupe de alertas, H35 seguridad, H37 coste/rendimiento, H41 observabilidad y H43 flags/canary.

---

## 1. Propósito y decisión de fase

H09 define cómo ejecutar búsquedas y revalidaciones hoteleras periódicas sin convertir un worker opcional en una promesa de tracking estable. Fija límites para concurrencia, presupuesto, retries, locks, circuit breaker, estados y replay.

La fase **no activa un provider comercial**, no ejecuta requests externos, no añade credenciales y no afirma que el tracking periódico esté listo. Produce:

- un contrato de gateway/scheduler reutilizable por Mock, Makcorps y futuros adapters;
- una política de leases y deduplicación cross-process;
- una máquina de estados de `HotelProviderRun` y de cada unidad de trabajo;
- un presupuesto de requests/coste antes de salir a red;
- un canary reproducible y reversible;
- un handoff de implementación a H10/H11/H37/H41/H43.

### Decisión H09

**Diseñar y preparar la ejecución; mantener los sweeps externos automáticos desactivados.**

- Mock puede seguir ejecutándose manualmente para QA y fixtures.
- Makcorps permanece bloqueado para worker periódico por H07.
- Hotelbeds/LiteAPI y demás candidatos permanecen bloqueados hasta superar H08 Gates 1–5.
- `HOTEL_SWEEP_ENABLED=false` continúa siendo el valor seguro de producción.
- La ausencia de una ejecución no se presenta como “sin disponibilidad” ni como “precio sin cambios”.

---

## 2. Estado real de partida

### 2.1. Lo que ya existe

| Pieza | Estado comprobable | Límite actual |
|---|---|---|
| `backend/app/worker/hotels_sweep.py` | worker separado con `--once` y `--loop` | lee `HOTEL_SWEEP_ENABLED` al importar; no tiene lease global ni backoff de ciclo |
| `run_hotel_sweep()` | crea `HotelProviderRun`, ingesta, alertas y tracked offers | solo distingue `running`, `completed`, `failed`; no expresa `partial`/`skipped` |
| `sweep_tracked_offers()` | recorre ofertas activas y crea snapshots | captura excepciones del provider como lista vacía; no conserva resultado V2 por oferta |
| `HotelProviderRun` | guarda provider, timestamps, status, items y error corto | no guarda attempts, counts por estado, budget, lock, latency, cost ni warnings |
| `HotelTrackedOffer` | identidad única por usuario/hotel/estancia/guests/provider | no tiene `next_sweep_at`, prioridad operativa, last outcome ni lease |
| `HotelRateSnapshot` | guarda provider run, precio, disponibilidad y timestamp | no basta para explicar un sweep omitido, rate limit o error sin snapshot |
| `RevalidationJob` | patrón existente de dedupe, claim, `FOR UPDATE SKIP LOCKED` y lock token | pertenece al flujo de revalidación de vuelos; no se debe reutilizar sin adaptar su contrato hotelero |
| quota ledger de vuelos | reserva atómica por ventana y bloqueo por `blocked_until` | es de vuelos; H09 requiere política hotelera y unidades/coste propios |
| circuit breakers existentes | hay patrones por provider, principalmente in-memory | un breaker local no coordina múltiples workers ni sobrevive a despliegues |

### 2.2. Riesgos concretos del flujo actual

1. `run_hotel_sweep()` crea el run y ejecuta ingesta; después evalúa alertas y hace `sweep_tracked_offers()`. Si la fase posterior falla, el run puede terminar como `failed` aunque ya haya persistido parte del trabajo, sin un resumen de parcialidad.
2. El run no tiene un lock de provider/ventana. Dos procesos `--loop`, cron y ejecución manual pueden llamar al mismo provider simultáneamente.
3. `sweep_tracked_offers()` usa el `HotelTrackedOffer.hotel_id` interno cuando llama a `fetch_hotel_rates()`. H07 ya identificó que Makcorps necesita `provider_hotel_id` externo.
4. Los errores del provider se convierten en `[]`; un timeout/429 puede activar el fallback a snapshot general o parecer ausencia de rates.
5. `_fetch_and_store_provider_rates()` puede abrir hasta cinco llamadas concurrentes por lote, sin presupuesto persistente, sin Retry-After coordinado y con `requests.Session` compartida por futures.
6. El worker acepta `--provider`, pero la resolución de Makcorps depende también de `HOTEL_PROVIDER`; el argumento no constituye todavía un registry/configuración provider-neutral completa.
7. `DEFAULT_SWEEP_ENABLED`, intervalo y provider se leen al importar el módulo; cambios de entorno durante la vida del proceso no son un mecanismo de control dinámico.
8. No existe un health check hotelero que diferencie `empty`, `rate_limited`, `timeout`, `unavailable`, `invalid_response`, `partial` y `failed`.

Estos son prerrequisitos de implementación, no defectos que H09 vaya a ocultar con una flag.

---

## 3. Arquitectura objetivo

```text
Scheduler / cron / worker
          |
          v
Hotel sweep coordinator
  - selecciona due work
  - adquiere lease
  - reserva budget
  - consulta breaker
          |
          v
Provider gateway H06
  - StayQuery canónico
  - timeout/retry global
  - error/status normalizado
  - request ID y latencia
          |
          v
Provider adapter aislado
          |
          v
Provider externo

Resultado V2
  -> snapshot elegible o estado explícito
  -> HotelProviderRun agregado
  -> health/metrics
  -> alertas solo si el dato es comparable y elegible H05
```

### Regla de ownership

- **Scheduler:** decide cuándo despertar; no llama directamente a providers.
- **Coordinator:** selecciona unidades, leasea, reserva presupuesto y agrega resultados.
- **Gateway:** aplica contrato H06, timeout, retry, circuit breaker y redaction.
- **Adapter:** traduce HTTP/payload externo; no decide alertas ni crea entidades de usuario.
- **Dominio:** valida matching, elegibilidad H05, dedupe y alertas.
- **Worker:** no interpreta `[]` como estado de negocio; consume resultados tipados.

Ninguna capa puede duplicar retries ni saltarse el presupuesto de la capa anterior.

---

## 4. Unidad de trabajo y deduplicación

La unidad mínima de revalidación hotelera debe ser una `StayQuery` asociada a un target:

```text
provider_id
canonical_hotel_id
provider_hotel_id
check_in
check_out
rooms
adults
children_ages
currency
room_label / room_id cuando exista
meal_plan cuando forme parte del tracking
cancellation_policy cuando forme parte del tracking
tracked_offer_id o fingerprint de búsqueda
```

### Fingerprint

El fingerprint debe incluir toda dimensión que pueda cambiar precio o comparabilidad. Como mínimo:

```text
sha256(
  provider_id + provider_hotel_id + canonical_hotel_id +
  check_in + check_out + rooms + adults + children_ages +
  currency + room_id/room_label + meal_plan + cancellation_policy
)
```

No se debe deduplicar solo por `hotel_id`, porque eso puede mezclar estancias o proveedores.

### Reglas

- Una única unidad activa por fingerprint y ventana de ejecución.
- Dos usuarios que rastrean la misma estancia pueden compartir una consulta externa solo si H10 define el aislamiento correcto y el resultado no incluye PII.
- El `tracked_offer_id` sirve para asociar snapshots/alertas; no sustituye el fingerprint de la consulta.
- Si el mapping externo no existe o es ambiguo, la unidad se marca `skipped`/`blocked_mapping`, no se llama con el ID interno.
- Replays deben ser idempotentes: repetir la misma respuesta no crea snapshots duplicados ni alertas duplicadas.

---

## 5. Lease, locks y reclamación

### 5.1. Requisito

El control de concurrencia debe funcionar con varios procesos, pods o cronjobs. Un lock solo en memoria no es suficiente.

La implementación puede extender `RevalidationJob` o crear una tabla específica de hotel, pero debe conservar:

```text
job_id / fingerprint
status: queued | running | done | skipped | failed
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

### 5.2. Claim atómico

1. Seleccionar trabajos `queued` y `scheduled_at <= now`.
2. Ordenar por prioridad, proximidad de check-in, antigüedad y fingerprint estable.
3. Usar `FOR UPDATE SKIP LOCKED` en PostgreSQL cuando esté disponible.
4. Cambiar `queued → running` solo si la fila sigue disponible.
5. Guardar `lock_token` y `lease_expires_at`.
6. Liberar/terminar el lease en éxito, skip o fallo.
7. Permitir recuperación de leases expirados sin ejecutar simultáneamente el trabajo original.

### 5.3. Lock scopes

| Scope | Propósito | Regla |
|---|---|---|
| `provider + operation` | evitar stampede contra el mismo endpoint | limita concurrencia global del provider |
| `StayQuery fingerprint` | evitar dos refreshes idénticos | uno activo por fingerprint |
| `HotelProviderRun` | evitar dos ciclos completos simultáneos si el modo lo exige | lease con expiración y owner |
| `tracked_offer_id` | serializar escritura/alerta de una watch | no bloquear otras estancias innecesariamente |

No usar un lock global único para todos los hoteles: una oferta bloqueada no debe detener todo el tracker.

### 5.4. Expiración y recuperación

- El lease debe durar más que el timeout total permitido, con margen de cleanup.
- Un proceso que pierde el lease no puede completar ni escribir el resultado como owner.
- El resultado tardío puede guardarse como diagnóstico descartado, nunca como snapshot actual sin comprobar ownership.
- Un job recuperado incrementa `attempt_count` y respeta el presupuesto restante.

---

## 6. Presupuesto, concurrencia y coste

### 6.1. Reserva antes de salir a red

Toda llamada externa debe reservar unidades antes de ejecutarse:

```text
provider_id
operation
budget_window: day | month
hard_limit
units_per_request
estimated_cost
request_fingerprint
reserved_at
```

Si no se puede reservar, se devuelve `rate_limited` con `source=local_budget`; no se llama al provider.

El ledger de vuelos existente es un patrón reutilizable, pero H09 debe evitar compartir tabla, nombres o límites hasta confirmar que las unidades y ventanas son semánticamente compatibles.

### 6.2. Presupuestos separados

- `search`: coste por consulta de área/catalogue.
- `revalidation`: coste por oferta/estancia.
- `mapping`: coste por resolución de ciudad/hotel.
- `retry`: consume presupuesto, nunca es gratis.
- `canary`: ventana y límite independiente de producción.

Mientras el precio o cuota de un provider sea desconocido, el hard limit automático es `0`.

### 6.3. Concurrencia

El límite efectivo es el mínimo de:

```text
provider declared max_concurrency
local configured max_concurrency
remaining budget
worker capacity
UX time budget
```

Valores de ejemplo no aprobados todavía:

```text
max_concurrency = 1 para canary inicial
max_retries = 0 o 1 para canary
max_batch_size = pequeño y explícito
```

No usar `ThreadPoolExecutor(max_workers=5)` como constante de producto. El gateway debe poseer el semaphore y el adapter no debe crear concurrencia oculta.

---

## 7. Retry, Retry-After y circuit breaker

### 7.1. Clasificación

| Resultado | ¿Retry? | Acción |
|---|---:|---|
| `empty` | no | guardar resultado vacío con freshness de respuesta |
| `invalid_request` | no | corregir StayQuery; no reintentar ciego |
| `authentication_failed` | no | pausar provider y alertar configuración |
| `unsupported` | no | marcar capacidad ausente |
| `rate_limited` con Retry-After | limitado | bloquear provider/operación hasta ventana indicada |
| `timeout` | limitado | backoff con presupuesto restante |
| `network_error` | limitado | backoff y breaker |
| `provider_5xx` | limitado | backoff y breaker |
| `invalid_response` | no inmediato | pausar adapter/abrir incidente |
| `unavailable` | según breaker | servir cache elegible si existe |

### 7.2. Presupuesto de retries

- El gateway posee el contador global de intentos.
- Un retry del adapter cuenta contra el mismo `attempt_count`.
- El máximo de tiempo de la unidad incluye todos los retries.
- No reintentar si ya se superó `lease_expires_at` o el presupuesto.
- Jitter obligatorio para evitar sincronización de workers.
- `Retry-After` se limita a un máximo operativo y se registra como valor sanitizado.
- Si falta `Retry-After` en un 429, usar cooldown local conservador y no repetir inmediatamente.

### 7.3. Circuit breaker

El estado mínimo por `provider + operation` es:

```text
closed
open
half_open
failure_count
opened_at
next_probe_at
last_error_code
```

- `closed`: llamadas permitidas dentro del budget.
- `open`: no salen llamadas; resultados son `unavailable` o `rate_limited` según la causa.
- `half_open`: una sola prueba controlada.
- éxito válido: cerrar y resetear fallos consecutivos.
- fallo: volver a abrir y ampliar cooldown según política.

El breaker in-memory existente puede servir de primera protección dentro de un proceso, pero no es suficiente como coordinación definitiva entre workers. H09 exige estado persistente o un mecanismo distribuido equivalente antes del worker productivo.

---

## 8. Máquina de estados

### 8.1. `HotelProviderRun`

Estados mínimos objetivo:

```text
created → running → completed
                 ↘ partial
                 ↘ skipped
                 ↘ failed
```

| Estado | Significado |
|---|---|
| `created` | run reservado pero aún no comenzó trabajo |
| `running` | hay unidades leaseadas o en ejecución |
| `completed` | todas las unidades planificadas terminaron con resultado válido o vacío, sin degradación bloqueante |
| `partial` | algunas unidades válidas terminaron y otras tuvieron timeout, rate limit, error o skip |
| `skipped` | no se ejecutó ninguna unidad por flag, budget, breaker, ventana o ausencia de trabajo |
| `failed` | el run no pudo producir un resultado operativo y no hay datos válidos de la ventana |

`completed` no significa “todos los hoteles tienen rates live”; significa que el conjunto planificado terminó sin una degradación que cambie la interpretación.

### 8.2. Resultado de unidad

Cada unidad debe conservar al menos:

```text
success
empty
partial
rate_limited
timeout
unavailable
unsupported
invalid_response
failed
skipped_mapping
skipped_budget
skipped_circuit
```

El agregador calcula el estado del run a partir de esas unidades. No se debe inferir desde `items_processed` ni desde la longitud de una lista.

### 8.3. Persistencia y alertas

- `empty` puede actualizar freshness y mostrar “sin resultados” si la respuesta fue válida.
- `rate_limited`, `timeout`, `unavailable` y `failed` no crean `sold_out` ni un precio cero.
- `partial` solo puede disparar alertas si la oferta comparada es elegible H05 y la incertidumbre no afecta a la condición de alerta.
- Un cambio de precio necesita snapshot comparable, no solo una cifra devuelta por un fallback antiguo.
- La alerta debe conservar `provider_run_id`, outcome, observed_at y razón de elegibilidad.

---

## 9. Selección y prioridad de tracked offers

La prioridad operativa propuesta es:

1. check-in próximo dentro de la ventana de producto;
2. oferta activa con alerta crítica habilitada;
3. oferta cuya freshness H05 esté a punto de caducar;
4. oferta con fallo transitorio reintentable y cooldown cumplido;
5. antigüedad desde el último intento;
6. stable fingerprint como desempate.

No priorizar por usuario privilegiado ni por precio sin una decisión de producto documentada.

Si el número de ofertas supera el budget:

- seleccionar determinísticamente;
- registrar `skipped_budget` para las restantes;
- conservar `next_scheduled_at` y razón;
- no borrar ni desactivar la oferta;
- no prometer frecuencia diaria a todas las ofertas mientras el budget no alcance.

---

## 10. Scheduler y ventanas perdidas

### Modo recomendado

- Scheduler externo o worker dedicado despierta con intervalo fijo.
- El coordinator calcula trabajo vencido desde la base de datos.
- Un ciclo no debe depender de que el API HTTP esté vivo.
- `--once` es el modo canary/replay; `--loop` es una conveniencia operativa, no un lock.
- El proceso debe tolerar reinicio sin duplicar trabajo.

### Si se pierde una ventana

1. Registrar evento `scheduler_window_missed` con motivo sanitizado.
2. No ejecutar todas las ventanas históricas de golpe.
3. Aplicar catch-up máximo configurado por provider/operación.
4. Priorizar ofertas críticas y próximas a check-in.
5. Marcar las no ejecutadas como `skipped_window` o `skipped_budget`.
6. Exponer freshness real en UI y health, sin rellenar huecos con timestamp actual.

El catch-up no puede superar budget, concurrencia ni lease; tampoco debe convertirse en una tormenta al recuperar un pod.

---

## 11. Observabilidad y health check

### Métricas obligatorias

Por provider, operación y ventana:

```text
hotel_sweep_runs_total{status}
hotel_sweep_units_total{outcome}
hotel_sweep_duration_ms
hotel_sweep_offers_scanned_total
hotel_sweep_snapshots_created_total
hotel_sweep_alerts_created_total
hotel_provider_requests_total{operation,outcome}
hotel_provider_attempts_total
hotel_provider_latency_ms
hotel_provider_rate_limited_total
hotel_provider_timeout_total
hotel_provider_invalid_response_total
hotel_provider_budget_denied_total
hotel_provider_circuit_open_total
hotel_provider_replayed_total
```

### Health payload mínimo

```json
{
  "provider": "mock",
  "enabled": false,
  "mode": "fixture_or_live",
  "last_run": {
    "id": null,
    "status": "skipped",
    "finished_at": null,
    "units": 0,
    "partial": false
  },
  "budget": {
    "window": "day",
    "used": 0,
    "limit": 0,
    "remaining": 0,
    "source": "local_config"
  },
  "circuit": {
    "state": "closed",
    "next_probe_at": null
  },
  "freshness": {
    "latest_observation_at": null,
    "age_seconds": null
  }
}
```

El health check no debe hacer una llamada externa por request. Un probe provider real solo puede existir como job de health separado, con budget propio y propósito documentado.

### Redacción

Nunca registrar:

- API keys o tokens;
- URLs completas con query secrets;
- cookies, Authorization headers o payloads sin sanitizar;
- emails o IDs de usuario innecesarios.

Registrar sí:

- provider/operation;
- run ID y request ID opacos;
- outcome normalizado;
- attempts, latency, budget source y cooldown;
- conteos agregados y códigos externos sanitizados.

---

## 12. Flags y configuración de rollout

H09 no crea un sistema central de flags. Usa la convención de `docs/reference/feature-flags.md` y deja los defaults seguros en `.env.example`.

La política mínima futura por provider/operación es equivalente a:

```text
HOTEL_FEATURE_ENABLED=false
HOTEL_SWEEP_ENABLED=false
HOTEL_PROVIDER=mock
HOTEL_PROVIDER_ORDER=mock
HOTEL_PROVIDER_<ID>_ENABLED=false
HOTEL_PROVIDER_<ID>_SWEEP_ENABLED=false
HOTEL_PROVIDER_<ID>_REVALIDATION_ENABLED=false
HOTEL_PROVIDER_<ID>_DAILY_REQUEST_BUDGET=0
HOTEL_PROVIDER_<ID>_MAX_CONCURRENCY=1
HOTEL_PROVIDER_<ID>_MAX_RETRIES=0
HOTEL_PROVIDER_<ID>_CIRCUIT_FAILURE_THRESHOLD=1
HOTEL_PROVIDER_<ID>_CIRCUIT_RECOVERY_SECONDS=300
HOTEL_PROVIDER_<ID>_CANARY_ONLY=true
```

Estas variables son contrato de rollout, no cambios ya implementados. H43 deberá escoger nombres definitivos, evitar duplicar flags y añadir pruebas de “off means no external call”.

El argumento `--provider` debe acabar resolviendo un provider del registry explícito y validado contra la flag, no saltarse configuración ni secretos del entorno.

---

## 13. Replay seguro y rollback

### Replay

Un replay se autoriza solo para:

- un `run_id` o fingerprint explícito;
- provider y operación permitidos;
- budget de replay separado;
- `dry_run` o fixture antes de salir a red;
- lock/lease normal;
- idempotency/dedupe activo;
- owner y ventana registrados.

Un replay no debe reemitir alertas históricas automáticamente. Por defecto puede crear snapshot de diagnóstico marcado como replay, pero H11 debe definir si entra en ranking/freshness.

### Rollback

Al detectar anomalía:

1. apagar `HOTEL_PROVIDER_<ID>_SWEEP_ENABLED` y/o `HOTEL_SWEEP_ENABLED`;
2. bloquear nuevas unidades y dejar expirar leases con timeout;
3. cerrar el breaker o mantenerlo abierto según causa;
4. conservar snapshots existentes sin convertirlos en live;
5. servir cache/histórico H05 con edad visible;
6. desactivar deeplinks del provider pausado;
7. revocar/rotar credenciales si hubo exposición;
8. registrar run, coste, requests y owner;
9. reabrir solo tras repetir H08 Gates 2–5.

No borrar aliases ni snapshots como parte del kill switch.

---

## 14. Tests y criterios de implementación

### Unitarios

- fingerprint cambia al variar estancia, ocupación, moneda, room o meal plan;
- enqueue es idempotente para unidades activas iguales;
- claim atómico solo permite un owner;
- lease expirado se recupera una vez;
- completion con lock token incorrecto no modifica el job;
- budget denegado no realiza request;
- retry consume attempts y budget;
- Retry-After produce cooldown acotado;
- breaker abre, permite un half-open y cierra solo con éxito válido;
- estado agregado distingue `completed`, `partial`, `skipped` y `failed`;
- timeout/429 no se convierte en `empty` ni `sold_out`;
- replay no duplica snapshots ni alertas;
- logs no contienen secretos.

### Integración con base de datos

- dos workers sobre la misma unidad dejan un solo claim;
- PostgreSQL usa `SKIP LOCKED` cuando corresponde;
- SQLite/dev mantiene comportamiento determinista documentado;
- rollover de budget conserva límites y bloqueos;
- un restart libera leases expirados;
- snapshots tienen provider run/outcome/freshness consistentes;
- una ventana perdida genera skip explícito y no una observación falsa.

### Contract tests del gateway

Ejecutar contra Mock y cada adapter habilitado:

- success/empty/partial;
- unsupported;
- 429 con y sin Retry-After;
- timeout/network/5xx;
- invalid response;
- mapping ausente/ambiguo;
- ocupación no soportada;
- deeplink ausente o rechazado;
- provider disabled/canary-only;
- budget agotado y breaker abierto.

### Criterio de “done” de implementación

No basta con que el worker termine sin excepción. Debe existir evidencia de:

- dos procesos concurrentes sin duplicar llamada por fingerprint;
- límites de requests/coste respetados;
- outcomes visibles en `HotelProviderRun` y health;
- rollback de flags probado;
- canary sin secretos y con latencia/coste medidos;
- tests de regresión de `run_hotel_sweep`, `sweep_tracked_offers` y worker;
- documentación de cómo se ejecuta en la infraestructura real.

---

## 15. Canary H09

El canary se limita inicialmente a Mock y fixtures; ningún provider comercial se activa por defecto.

Cuando H08 Gates 1–5 estén aprobados para un provider:

1. ejecutar `--once` con una única operación y un owner;
2. usar 1–3 unidades y `max_concurrency=1`;
3. reservar budget antes de cada request;
4. simular 429, timeout, invalid response y reinicio con fixtures;
5. verificar estados, lease recovery, dedupe y redaction;
6. medir p50/p95, attempts, budget, snapshots y alerts;
7. comparar con H05/H10;
8. detener antes de habilitar `--loop`;
9. revisar H35, H37 y H41;
10. activar solo una ventana gradual con kill switch probado.

### Criterios de salida

- cero llamadas externas con flags off;
- cero duplicados por fingerprint bajo concurrencia;
- cero errores convertidos en `empty`/`sold_out`;
- 429/cooldown visibles;
- budget y retries dentro de límite;
- leases recuperables;
- snapshot y alertas comparables;
- rollback probado;
- ningún secreto en logs/traces;
- decisión explícita `approved_limited`, `paused` o `rejected`.

---

## 16. Handoff a fases siguientes

| Fase | Entrega H09 |
|---|---|
| H10 | `StayQuery`, fingerprint, identidad interna/externa y rate comparable |
| H11 | migración compatible de run/outcome/warnings/freshness sin perder históricos |
| H15 | exposición API de estados `partial`, `skipped`, `rate_limited`, `timeout` y `unavailable` |
| H26 | dedupe de alertas basado en snapshot/outcome y no en cada retry |
| H35 | redaction, API keys en query params, allowlist y disclosure |
| H37 | coste por operación, latencia, concurrency y capacidad del worker |
| H41 | métricas, health, run/request IDs y dashboards |
| H43 | flags definitivas, canary, rollout gradual y kill switches |

### Gate H09

H09 podrá considerarse implementada solo cuando:

- el coordinator tenga lease distribuido y dedupe por `StayQuery`;
- el gateway posea timeout/retry/budget/breaker sin duplicación;
- `HotelProviderRun` y unidades expresen estados parciales y skips;
- se resuelva el mapping a `provider_hotel_id` antes de llamar;
- ningún error externo se convierta en vacío o disponibilidad falsa;
- exista health operativo sin requests implícitos;
- el canary y el replay estén presupuestados y sean reversibles;
- tests unitarios/integración/contract pasen;
- H35/H37/H41/H43 revisen seguridad, coste, observabilidad y flags.

**Resultado H09:** contrato operativo aprobado. El worker actual sigue siendo una base V1 útil para Mock/manual, pero no se declara scheduler de tracking hotelero estable hasta implementar y verificar este contrato.
