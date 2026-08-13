# Hotel Provider Latency Persistence Design

**Fecha:** 2026-08-09
**Estado:** aprobado para implementación incremental
**Relacionado con:** H37, H41, `2026-08-09-hotel-provider-latency-contract-plan.md`

## Objetivo

Persistir telemetría de latencia hotelera de forma multi-operación, bounded y privacy-safe, sin sobrescribir muestras ni confundir la duración del provider con la duración total de `HotelProviderRun`.

## Decisión

Usar una tabla agregada por run, no un ledger por muestra ni el JSON de outcomes del run.

La unidad persistida es:

```text
provider_run_id + provider + operation + outcome + error_code
```

Cada fila resume las muestras equivalentes observadas durante un `HotelProviderRun`:

- `sample_count`
- `total_duration_ms`
- `min_duration_ms`
- `max_duration_ms`
- `created_at`
- `updated_at`

La tabla tendrá una restricción única sobre las cinco dimensiones y una FK al run con borrado en cascada. No almacenará excepciones, payloads, URLs, credenciales, intents, usuarios, hoteles, offers ni fingerprints.

## Flujo de datos

1. `latency_sink` recibe `ProviderLatencySample` únicamente alrededor de I/O efectivo.
2. Un acumulador en memoria agrupa por las dimensiones allowlisted.
3. Al finalizar un run, el servicio convierte cada grupo en una fila agregada mediante upsert dentro de la transacción del run.
4. Si el run falla, la política de persistencia conserva el diagnóstico agregado únicamente cuando el run persistido alcanza un estado terminal y la transacción final puede completarse; no se hace un commit independiente por muestra.
5. Operaciones sin `HotelProviderRun` permanecen no persistentes en esta frontera.

## Contrato y límites

- `duration_ms` siempre es entero no negativo y está limitado por el techo del helper.
- `sample_count` y todos los acumuladores deben ser no negativos y bounded.
- `provider`, `operation`, `outcome` y `error_code` se normalizan con las allowlists existentes.
- `attempt` se conserva en la muestra local para futura segmentación, pero no se añade a la clave agregada en esta primera migración; los reintentos cuentan como muestras y no se regalan.
- El promedio se puede derivar como `total_duration_ms / sample_count`.
- Percentiles no se persistirán con esta forma; se marcarán como no concluyentes hasta que exista un histograma/ledger apropiado y volumen suficiente.
- La lectura admin tendrá límite estricto, filtrará por runs recientes y no devolverá `provider_run_id` crudo.

## Compatibilidad y migración

- Migración Alembic aditiva, reversible y compatible con SQLite/PostgreSQL.
- No se modifica ni se renombra `HotelProviderRun.tracked_outcomes`.
- Historical runs no tendrán filas artificiales: ausencia de agregados significa `no_sample`/`unknown`, no latencia cero.
- La migración deberá probar upgrade, downgrade y creación de la tabla desde un esquema limpio.

## Operación y privacidad

- El provider live continúa apagado por defecto.
- El health endpoint no hará llamadas externas.
- La persistencia no incluye PII ni cardinalidad por entidad.
- El endpoint admin será read-only, admin-only y bounded.
- Un fallo de observabilidad no debe convertir una llamada provider exitosa en fallo funcional; la escritura agregada debe fallar cerradamente y quedar visible para diagnóstico local sin exponer datos.

## Gates de implementación

1. Tests unitarios del acumulador y validación de allowlists/bounds.
2. Tests de persistencia SQLite con upsert e idempotencia.
3. Tests de integración de run: success, empty, failure y skip sin muestra.
4. Migration roundtrip Alembic.
5. Endpoint admin bounded/RBAC/redaction.
6. Ruff, compileall, tests focalizados y diff check.
7. Revisión independiente de privacidad, side effects y claims H37/H41.

## Fuera de alcance

- Provider live/canary real.
- Percentiles p50/p95/p99.
- Dashboard RED productivo.
- Persistencia por entidad o por request.
- Selección de un servicio externo de observabilidad.
