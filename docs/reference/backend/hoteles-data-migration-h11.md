# H11 — Migración compatible, backfill, índices y retención de datos hoteleros

**Estado:** completa como contrato de migración; implementación, migración Alembic y backfill pendientes  
**Fecha:** 2026-08-04  
**Área:** DB / backend / datos / QA / operación  
**Fuente de verdad:** sí para la evolución segura del modelo hotelero V1 hacia H10 mientras convivan los contratos legacy y canónico.

**Depende de:** [H10 — modelo canónico de estancia/oferta](hoteles-stay-offer-model-h10.md), [H09 — gateway y sweeps](hoteles-sweep-gateway-h09.md), [H05 — freshness/provenance/confidence](hoteles-freshness-provenance-confidence-h05.md)  
**Relacionado con:** H12 schemas API, H15 resultados, H19 fees, H20 habitaciones/régimen, H23 tracking, H26 dedupe de alertas, H35 deeplinks, H37 coste/rendimiento, H39 QA, H41 observabilidad y H43 flags.

---

## 1. Propósito y decisión de fase

H11 define cómo introducir el modelo H10 sin perder `HotelTrackedOffer`, snapshots, aliases, runs, alertas ni compatibilidad con SQLite/Postgres. La estrategia obligatoria es **expand-and-contract**:

```text
expand → backfill → dual-write → dual-read → validate → cutover → contract
```

La fase no ejecuta una migración ni modifica las tablas actuales. No se borran columnas, no se cambia una unicidad existente y no se declara migrado ningún dato hasta completar los gates de QA y rollback.

### Decisión H11

**Crear estructuras canónicas nuevas de forma aditiva, conservar V1 durante toda la transición y retirar solo después de una ventana de observación reversible.**

Nombres conceptuales usados en este documento:

- `StayOffer`: representación compartida/canónica de una consulta/oferta comparable.
- `UserStayWatch`: suscripción privada de un usuario a una `StayQuery`/`StayOffer`.
- `HotelTrackedOffer`: tabla V1 que permanece como fuente de compatibilidad hasta el cutover.
- `HotelRateSnapshot`: tabla V1 que conserva históricos; puede recibir referencias canónicas aditivas.

Los nombres finales de tablas/columnas y la decisión de reutilizar `RevalidationJob` o crear jobs hoteleros propios deben aprobarse en el diseño de H12/H23 antes de escribir la migración.

---

## 2. Inventario V1 y riesgos

| Pieza actual | Evidencia | Riesgo de migración |
|---|---|---|
| `HotelProviderAlias` | alias único por `(provider, provider_hotel_id)` | no tiene estado explícito de mapping/confidence completo |
| `HotelRateSnapshot` | fechas, `guests`, amount, labels, provider, run y tracked FK | no tiene ocupación estructurada, offer fingerprint ni provider hotel ID directo |
| `HotelTrackedOffer` | ownership por `user_id`, hotel, fechas, guests, provider | su unique key no incluye room/meal/cancelación/fees; no es identidad global |
| `HotelProviderRun` | provider, timestamps, status V1, items y error corto | no conserva outcomes parciales, budget, attempts, warnings ni health |
| `HotelAlertRule` | puede enlazar `tracked_offer_id` | no debe apuntar a una suscripción canónica sin bridge de ownership |
| API schemas | `guests` scalar, strings libres y amount único | romperlos bloquearía frontend y clients actuales |
| Alembic H17–H25 | migraciones aditivas con `batch_alter_table` en zonas compatibles | alterar FK/unique sin auditar datos puede fallar en SQLite/Postgres |

### Riesgos obligatorios

- duplicar una oferta compartida por cada usuario;
- mezclar dos ocupaciones porque ambas tienen `guests=2`;
- asignar a una oferta una tarifa de otro provider o estancia;
- perder snapshots al actualizar FKs;
- crear unicidad sobre datos duplicados y bloquear el upgrade;
- borrar `user_id` o thresholds privados de alertas;
- backfillear `amount_total` o fees sin evidencia;
- convertir una fecha parcial o `availability=available` legacy en dato canónico fiable;
- ejecutar doble escritura en una transacción que deje V1 y V2 divergentes;
- asumir que una migración SQLite se comporta igual que PostgreSQL.

---

## 3. Diseño expand-and-contract

### Fase A — Expandir schema, sin cambiar lecturas

Añadir de forma nullable/aditiva, según el diseño aprobado:

```text
stay_offer / canonical offer table
user_stay_watch / subscription table
stay_query payload o columnas canónicas versionadas
HotelRateSnapshot.stay_offer_id nullable
HotelRateSnapshot.stay_query_fingerprint nullable
HotelRateSnapshot.offer_fingerprint nullable
HotelAlertRule.user_stay_watch_id nullable
HotelTrackedOffer.canonical_query_id nullable, si aporta compatibilidad
```

La expansión no debe:

- exigir NOT NULL sobre filas existentes;
- eliminar `tracked_offer_id` ni `hotel_id` legacy;
- cambiar el comportamiento de endpoints V1;
- activar providers o workers;
- crear unicidad nueva antes de medir duplicados.

Cada columna nueva necesita un índice justificado por consultas reales. No crear índices redundantes por cada campo si el plan de ejecución no los requiere.

### Fase B — Preparar tipos y bridge

Implementar antes del backfill:

- parser/normalizador de `StayQuery` H10;
- `occupancy_source` y estados `legacy_inferred`, `user_confirmed`, `provider_observed`;
- normalización conservadora de room/meal/cancellation;
- fingerprint determinista con versión (`fingerprint_version`);
- bridge de `HotelTrackedOffer` a `UserStayWatch`;
- resolver `HotelProperty.id → HotelProviderAlias.provider_hotel_id`;
- clasificación `unknown` para fees, total, disponibilidad y deeplink ausentes.

El bridge debe poder responder “no migrable automáticamente” para datos ambiguos; no rellenar defaults optimistas.

### Fase C — Backfill por lotes

El backfill debe ser un job reanudable, acotado y observable:

```text
batch_size
cursor por ID estable
dry_run
max_rows
owner
started_at/finished_at
last_cursor
migration_version
```

Orden recomendado:

1. validar el esquema y registrar conteos iniciales;
2. backfillear aliases canónicos sin cambiar su identidad;
3. convertir cada tracked offer V1 a `StayQuery` legacy inferida;
4. deduplicar `StayOffer` por fingerprint canónico, no por texto bruto;
5. crear una `UserStayWatch` por cada ownership V1;
6. enlazar snapshots mediante `stay_offer_id` solo si estancia/ocupación/conditions son compatibles;
7. enlazar alert rules únicamente cuando `user_id` coincide con la suscripción;
8. dejar las filas ambiguas en `migration_status=needs_review`;
9. emitir un resumen de migradas, omitidas, duplicadas, inválidas y divergentes.

### Reglas de backfill

- Nunca eliminar ni sobreescribir valores V1 originales.
- Una fila no migrable permanece legible por el bridge legacy.
- `guests → adults=guests, children_ages=[]` solo con `occupancy_source=legacy_inferred`.
- No inferir número de habitaciones, edades, régimen, cancelación, fees o total.
- No enlazar snapshots a una oferta si falta una dimensión que pueda cambiar el precio.
- Si dos usuarios comparten la misma consulta, comparten `StayOffer` pero no `UserStayWatch`.
- Si dos filas tienen distinta configuración privada, no fusionar sus suscripciones aunque coincidan en hotel/estancia.
- Backfill idempotente: repetirlo no duplica ofertas, watches, snapshots ni alertas.

---

## 4. Doble escritura

### 4.1. Activación

La doble escritura se activa solo detrás de flags por entorno y permanece apagada por defecto:

```text
HOTEL_CANONICAL_MODEL_ENABLED=false
HOTEL_CANONICAL_DUAL_WRITE_ENABLED=false
HOTEL_CANONICAL_DUAL_READ_ENABLED=false
HOTEL_CANONICAL_BACKFILL_ENABLED=false
HOTEL_CANONICAL_SHADOW_COMPARE_ENABLED=false
```

Los nombres son contractuales/provisionales; H43 debe consolidarlos con la convención real antes de implementar.

### 4.2. Escritura de una nueva watch

Una creación V1/V2 debe:

1. validar el request con H10;
2. resolver hotel/alias sin llamada externa;
3. construir fingerprint canónico;
4. crear o recuperar `StayOffer` compartida dentro de la misma transacción;
5. crear `UserStayWatch` privada;
6. conservar/crear `HotelTrackedOffer` V1 para compatibilidad;
7. enlazar alertas solo al owner correcto;
8. confirmar ambas representaciones o hacer rollback de ambas.

No aceptar “éxito” si solo se escribió V2 y un caller V1 seguirá leyendo una ausencia; durante la ventana de dual-write la operación es atómica o queda en estado explícito de reparación.

### 4.3. Escritura de snapshot

Un snapshot nuevo debe:

- conservar `tracked_offer_id` legacy cuando exista;
- enlazar `stay_offer_id` solo tras comprobar fingerprint y provider;
- guardar `provider_run_id`, observed_at, outcome y provenance;
- no convertir un error/timeout/replay en `available`;
- no escribir `amount_total` si la semántica es desconocida;
- emitir métrica de divergencia si V1 y V2 resolverían ofertas distintas.

Si una escritura canónica falla después de persistir V1, se conserva V1 y se registra `canonical_write_failed`; no se intenta “arreglar” borrando el histórico.

---

## 5. Doble lectura y shadow compare

### Orden de lectura

Durante la transición:

1. leer V2 si está habilitada y la fila está validada;
2. si falta V2, leer V1 mediante bridge y marcar `legacy_hotel_contract`;
3. opcionalmente leer ambas en shadow mode sin cambiar respuesta;
4. comparar IDs, fingerprints, ownership, precios, outcomes y freshness;
5. registrar divergencia sanitizada;
6. devolver la respuesta de la fuente seleccionada por flag.

### No hacer

- no hacer fallback silencioso de un error V2 a un precio V1 sin disclosure interno;
- no convertir ausencia V2 en `empty` si significa “no migrado”;
- no mezclar el mejor precio V1 con condiciones V2;
- no esconder divergencias de ownership;
- no cambiar el orden de ranking solo porque V2 tenga más campos hasta validar igualdad semántica.

### Métricas de shadow compare

```text
canonical_read_total
legacy_bridge_read_total
canonical_write_total
canonical_write_failed_total
shadow_compare_total
shadow_compare_equal_total
shadow_compare_identity_mismatch_total
shadow_compare_occupancy_mismatch_total
shadow_compare_price_semantics_mismatch_total
shadow_compare_ownership_mismatch_total
shadow_compare_freshness_mismatch_total
unmigrated_legacy_rows_total
needs_review_rows_total
```

El cutover requiere divergencia cero o explicada por categorías aceptadas, no solo una tasa global aparentemente baja.

---

## 6. Integridad, unicidad y ownership

### Unicidades nuevas

No crear una constraint única sobre ofertas canónicas hasta:

1. calcular fingerprints en modo dry-run;
2. agrupar duplicados y definir cuál es canónica;
3. verificar que no se fusionan habitaciones/conditions incompatibles;
4. resolver carreras con upsert/lock transaccional;
5. probar en una copia representativa;
6. tener un rollback de la constraint.

Candidata conceptual:

```text
StayOffer unique:
(provider_id, provider_hotel_id, stay_query_fingerprint, offer_fingerprint)

UserStayWatch unique:
(user_id, stay_query_fingerprint, provider_scope, alert_identity)
```

La clave definitiva se fijará con H10/H23; no incluir `user_id` en `StayOffer`, sí aislarlo en `UserStayWatch`.

### Foreign keys y cascadas

- eliminar una `UserStayWatch` no debe borrar `StayOffer` compartida ni snapshots históricos;
- eliminar/desactivar una propiedad no debe borrar evidencia histórica sin política explícita;
- alertas privadas deben tener FK/ownership verificable;
- snapshots no deben depender exclusivamente de una suscripción que puede borrarse;
- `SET NULL` o soft delete debe preferirse cuando la evidencia histórica lo requiera;
- cualquier `CASCADE` debe probarse con fixtures de varios usuarios.

### IDs y secretos

- `provider_hotel_id` permanece opaco;
- IDs internos no se envían al provider;
- fingerprints no contienen PII ni API keys;
- raw payloads se redacted y no se exponen en API;
- migraciones y logs no imprimen URLs con secretos.

---

## 7. Índices y consultas

### Índices candidatos a validar

```text
HotelProviderAlias(provider, provider_hotel_id)
HotelRateSnapshot(stay_offer_id, observed_at)
HotelRateSnapshot(offer_fingerprint, collected_at)
HotelRateSnapshot(hotel_id, check_in, check_out, currency, collected_at)
HotelTrackedOffer(user_id, is_active, updated_at)
UserStayWatch(user_id, is_active, updated_at)
StayOffer(stay_query_fingerprint, provider_id)
```

No añadir índices sin medir cardinalidad y plan de ejecución. Cada índice debe tener:

- consulta objetivo;
- cardinalidad esperada;
- coste de escritura;
- plan SQLite y PostgreSQL;
- estrategia de downgrade.

### Consulta legacy

Mientras existan callers V1, mantener índices actuales para:

- `hotel_id` y provider;
- fechas de estancia;
- `tracked_offer_id` y `provider_run_id`;
- `collected_at`;
- ownership de tracked offers.

El nuevo índice no justifica retirar el anterior hasta que no haya callers legacy.

---

## 8. Retención y datos históricos

H11 no autoriza borrar snapshots por “duplicados” sin definir observación y outcome.

### Capas propuestas

| Capa | Contenido | Política propuesta |
|---|---|---|
| hot | snapshots recientes elegibles para UI/tracking | TTL según H05 y frecuencia real |
| warm | histórico suficiente para tendencias, parity y alertas | agregados y snapshots seleccionados |
| cold | auditoría/diagnóstico legal-operativo | almacenamiento comprimido o export controlado |
| privado | watches, thresholds, labels y ownership | retención separada, nunca en cache público |

Los TTL definitivos deben venir de H05/H37 y del coste real. No borrar automáticamente datos cuando:

- están ligados a una alerta o incidente;
- son la única evidencia de una decisión enviada;
- forman parte de un replay o migración pendiente;
- son necesarios para comparar una ventana de producto.

### Agregados

Antes de compactar snapshots, conservar agregados diarios/semanales con:

```text
canonical_hotel_id
stay_query/offer fingerprint
provider
currency/price semantics
min/max/median si hay muestra suficiente
observations_count
valid/partial/error counts
freshness bounds
```

Los agregados nunca se presentan como una observación live.

---

## 9. Alembic, SQLite y PostgreSQL

### Reglas

- no editar migraciones ya aplicadas salvo una política explícita del repositorio;
- cada expansión tiene una revisión nueva con `upgrade` y `downgrade` seguro;
- usar helpers de inspección existentes para migraciones idempotentes;
- ejecutar `alembic check`, upgrade desde una base limpia y upgrade desde una base representativa;
- probar downgrade de la fase expand sin borrar datos legacy;
- usar `batch_alter_table` cuando SQLite requiera reconstruir tabla/FK;
- revisar nombres de constraints e índices por dialecto;
- no depender de `FOR UPDATE` en SQLite: documentar comportamiento de desarrollo y probar Postgres para locks reales;
- evitar backfills largos dentro de una transacción única;
- registrar revisión y cursor del backfill.

### Matriz de migración

| Escenario | Debe probarse |
|---|---|
| base limpia → head | todas las tablas y constraints |
| base con H17–H25 → expand H11 | preserva filas, FKs e índices |
| base con duplicados legacy | dry-run bloquea constraint o genera reporte |
| backfill parcial → resume | no duplica ni pierde filas |
| rollback antes de cutover | API V1 sigue operativa |
| rollback después de dual-write | V1 sigue leyendo y se marca divergencia |
| SQLite local | batch migration y fixtures pasan |
| PostgreSQL | locks, upserts y concurrencia pasan |
| restart en backfill | cursor reanuda sin doble efecto |

---

## 10. Observabilidad y runbook de migración

### Métricas

```text
hotel_migration_rows_seen_total
hotel_migration_rows_migrated_total
hotel_migration_rows_skipped_total{reason}
hotel_migration_duplicates_total
hotel_migration_needs_review_total
hotel_migration_fk_relinked_total
hotel_migration_shadow_mismatch_total{kind}
hotel_migration_duration_ms
hotel_migration_cursor_lag
hotel_migration_rollback_total
```

### Runbook mínimo

1. verificar backup/copia y revisión Alembic;
2. ejecutar `dry_run` y guardar conteos;
3. revisar duplicados, filas ambiguas y FKs huérfanas;
4. aplicar expand sin activar reads/writes;
5. comprobar schema audit y API V1;
6. ejecutar backfill por batches pequeños;
7. comparar conteos y muestrear ownership/IDs;
8. activar dual-write en staging/canary;
9. activar shadow compare;
10. observar divergencias durante ventana definida;
11. activar dual-read gradualmente;
12. declarar cutover solo con criterios H11;
13. conservar rollback y legacy durante la ventana de seguridad;
14. contractuar únicamente tras aprobación explícita.

No ejecutar el backfill junto con un sweep externo comercial ni con un cambio de provider: se deben poder atribuir errores a una sola variable.

---

## 11. Criterios de cutover y rollback

### Cutover requiere

- 100% de filas migrables procesadas o clasificadas `needs_review`;
- cero FKs huérfanas nuevas;
- cero cross-user leaks en pruebas;
- unicidades nuevas validadas en dry-run;
- divergencias V1/V2 cero o explicadas y aceptadas;
- API V1 y V2 serializan el mismo significado;
- snapshots conservan timestamps, provider, run y outcome;
- alertas no se duplican;
- índices y queries revisados en SQLite/Postgres;
- restore/rollback probado con copia representativa;
- H12/H23/H39/H41/H43 aprobados.

### Rollback

Si falla cualquier gate:

1. apagar `HOTEL_CANONICAL_DUAL_READ_ENABLED`;
2. mantener V1 como fuente de respuesta;
3. apagar dual-write si genera divergencia;
4. detener backfill y conservar cursor/log;
5. no borrar tablas canónicas ni datos para facilitar forensics;
6. dejar snapshots legacy intactos;
7. corregir/reanudar con una nueva revisión o limpiar tablas canónicas aisladas solo tras backup;
8. registrar causa, filas afectadas, revisión y owner.

Nunca hacer rollback destruyendo históricos como primer mecanismo.

---

## 12. Tests y gate de implementación

### Unitarios

- normalización legacy `guests` → ocupación inferida marcada;
- fingerprint determinista y versionado;
- dedupe de `StayOffer` entre usuarios sin mezclar ownership;
- no fusionar room/meal/cancellation incompatibles;
- bridge V1 conserva campos y IDs;
- backfill idempotente por lotes;
- `needs_review` para fechas parciales, alias ambiguo y fees desconocidos;
- alert rules solo enlazan owner correcto;
- snapshots no se borran al eliminar una watch;
- amount/available legacy no se presentan como total/live sin evidencia.

### Integración DB

- upgrade/downgrade limpio;
- upgrade desde base representativa;
- SQLite batch migration;
- PostgreSQL concurrency/upsert/locks;
- FKs y cascadas con dos usuarios;
- duplicate fingerprints antes/después de constraint;
- restart/resume del backfill;
- shadow compare y rollback de flags.

### Contract/API

- V1 endpoints sin cambios incompatibles;
- V2 devuelve occupancy/fingerprints/outcome solo cuando están disponibles;
- no se exponen `user_id` de otra suscripción ni thresholds privados;
- provider ID externo permanece opaco;
- parity/ranking respetan comparability key;
- frontend tolera campos nuevos y estados `unknown/partial`.

### Gate H11

H11 podrá considerarse implementada solo cuando:

- exista una migración Alembic nueva, revisada y reversible;
- schema audit y `alembic check` pasen;
- backfill dry-run y real sean reanudables e idempotentes;
- doble escritura y doble lectura tengan flags y métricas;
- no haya pérdida de históricos ni FKs huérfanas;
- ownership y privacidad estén probados;
- SQLite y PostgreSQL estén verificados;
- rollback funcione antes y después del cutover;
- retención no borre evidencia válida;
- H12/H23/H39/H41/H43 hayan cerrado sus dependencias.

**Resultado H11:** contrato de migración aprobado. El esquema actual permanece V1 hasta ejecutar la expansión, backfill, doble lectura/escritura y cutover con evidencia.
