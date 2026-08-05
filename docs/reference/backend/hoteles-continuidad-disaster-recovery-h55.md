# H55 — Continuidad, backup/restore y disaster recovery del tracker hotelero

**Estado:** COMPLETA como contrato de continuidad y recuperación; backup/restore automatizado, worker productivo y recovery drill ejecutado pendientes  
**Fecha:** 2026-08-05  
**Área:** infraestructura / DB / backend / workers / delivery / providers / seguridad / QA / soporte  
**Fuente de verdad:** sí para diseñar, ejecutar, medir y aprobar la recuperación de `/hoteles`  
**Fase del roadmap:** H55  
**Depende de:** H11, H28, H38, H41, H42, H43, H44, H45, H54  
**Relacionado con:** H05 freshness/provenance/confidence, H09 gateway/sweeps, H10 modelo de estancia/oferta, H23 tracking, H24 histórico, H26 alertas, H27 inbox, H29 lifecycle, H35 legal/privacy, H37 coste/límites, H39 tests
**Handoff:** [H56 — revisión anual de producto, providers y costes](../../plans/2026-08-04-hoteles-master-roadmap.md#fase-h56--revisión-anual-de-producto-providers-y-costes)

> H55 no convierte un runbook en alta disponibilidad ni inventa RTO/RPO. Define qué debe protegerse, cómo se mide la pérdida y el tiempo de recuperación, qué dependencias se deben restaurar en orden, cómo se reconcilian los datos y qué evidencia permite declarar un drill `passed`, `partial`, `blocked` o `failed`.

---

## 1. Decisión de fase y frontera

El tracker hotelero acumula valor en más que el último precio: identidad de propiedades, aliases de providers, consultas, ofertas, snapshots, históricos, seguimientos privados, reglas, eventos de alerta, inbox, preferencias, procedencia, auditoría y decisiones de soporte. Una caída puede dejar la API viva pero destruir la confianza si:

- se pierden snapshots o se presentan como actuales;
- un restore mezcla usuarios, mercados, providers u ownership;
- un worker reanuda desde un cursor incorrecto y duplica llamadas/alertas;
- una migración restaurada no coincide con el código desplegado;
- delivery reenvía dos veces una alerta o marca como entregado lo que no se confirmó;
- se recupera el catálogo pero no la relación entre tracking, oferta y snapshot;
- se reabre un mercado/provider sin comprobar coste, identidad o freshness.

### Dentro de H55

- mapa de dependencias y prioridades de recuperación;
- clasificación de datos por criticidad, reconstruibilidad y privacidad;
- backup, restore, verificación de integridad y retención de evidencia;
- compatibilidad de schema/Alembic y backfill durante una recuperación;
- reanudación segura de workers, leases, locks, colas y delivery;
- recuperación después de provider outage, corrupción o duplicación;
- definición y medición de RPO/RTO sin fijar objetivos ficticios;
- drills repetibles en DB/entorno aislado, con rollback del propio drill;
- comunicación, soporte, decision log, ownership y criterios de salida.

### Fuera de H55

- elegir un proveedor cloud, base de datos, observabilidad, email o colas sin una investigación separada;
- declarar que Kubernetes, GitHub Actions o un fichero YAML ya proporcionan failover;
- prometer disponibilidad, frecuencia de sweep o recuperación automática sin ejecución medida;
- borrar snapshots, aliases, eventos o datos privados para simplificar el restore;
- sustituir los gates legales de H35, de seguridad H38 o de release H45;
- usar un fixture Mock como evidencia de recuperación de datos live.

---

## 2. Baseline actual comprobable

H55 parte de la evidencia del repositorio y mantiene una separación estricta entre contrato, scaffolding y capacidad ejecutada.

| Superficie | Evidencia actual | Permite afirmar | No permite afirmar |
|---|---|---|---|
| Incidentes | H42 define severidad, preservación de evidencia, contención, recuperación y cierre | existe un procedimiento contractual reutilizable | que los simulacros, owners de guardia o comandos de producción estén operativamente probados |
| Migraciones | H11 define expand-and-contract, backfill reanudable, `dry_run`, dual-read/write y rollback; `alembic_audit.py` audita el grafo y estado local | hay reglas y una auditoría de revisiones útil | que exista un restore de una copia hotelera representativa ni un rollback de datos destructivo seguro |
| Retención | `backend/ops/db-retention/run-db-retention.sh` y sus servicios soportan dry-run, lock y logs según H42 | hay una base para retención operativa | que todas las tablas hoteleras, backups o exports legales estén cubiertos |
| Worker hotelero | `app.worker.hotels_sweep` y `run_hotel_sweep` existen; `backend/Dockerfile` construye una imagen multi-stage y `infra/k8s/hotels-sweep-cronjob.yaml` define un CronJob `--once` suspendido | la imagen se **construyó y validó en contenedor** (build exit 0, `/health` 200) y el sweep `--once --provider mock` terminó `completed` (3 items) sobre DB aislada migrada | que haya una imagen publicada, Secret/DB operativo, CronJob activo, lease distribuido, HA o failover automático |
| Worker Kubernetes legacy | `infra/k8s/worker.yaml` sigue ejecutando `python -c "print('worker placeholder')"` | el placeholder queda identificado y no se confunde con el CronJob nuevo | que ese Deployment ejecute sweeps o sea una ruta productiva válida |
| Migración Kubernetes | `infra/k8s/hotels-migrate-job.yaml` define `alembic upgrade head` separado y suspendido | el Job se **ejecutó dentro de la imagen** contra SQLite aislada (exit 0 hasta `0041_add_community_trending_snapshots`), además de la ruta explícita para revisar migraciones sin arrancar el worker | que se ejecute contra la DB/Secret real o que el restore sea compatible |
| Notificaciones | `app.worker.notifications` y H28 documentan estados/reintentos; H28 advierte que HotelAlertEvent aún no pasa por el dispatcher V1 | hay patrones de cola y backoff reutilizables | que exista delivery hotelero externo, DLQ física o exactly-once |
| Release | `infra/github/workflows/release.yml` ejecuta tests/build y un paso nominal de canary; H45 lo marca como scaffolding | existe una intención de quality gate y rollout | que exista traffic split, restore de infraestructura o rollback automático ejecutado |
| Health | `/health` y `/ready` son probes básicas | la API puede comprobarse superficialmente | que DB, worker, provider, freshness, delivery o integridad hotelera estén sanos |
| Observabilidad | H41 define correlación, eventos, redaction, métricas y SLO candidatos | hay un contrato de evidencia | que dashboards, métricas persistentes, SLO y alertas hoteleras estén activos |
| Backups | no hay evidencia suficiente de un job de backup/restore hotelero automatizado y verificado en este repositorio | el contrato puede exigirlo | que exista una copia restaurable, un RPO/RTO medido o un mecanismo de failover |

**Conclusión:** H55 es un contrato de hardening. La implementación avanzada no se declara completa hasta ejecutar un restore y un drill sobre datos sanitizados/aislados, conservar evidencia y pasar los gates de este documento.

---

## 3. Objetivos de recuperación: medir antes de prometer

### 3.1 Definiciones

- **RPO observado:** pérdida efectiva de datos entre el último punto de datos transaccional restaurable y el instante declarado del incidente; se contrasta con la antigüedad del backup/export usado, se mide en UTC y se separa por dataset.
- **RTO observado:** tiempo desde el inicio declarado del incidente/drill hasta que la superficie acordada vuelve a un estado verificado y útil, no solo hasta que un proceso escucha en un puerto.
- **RTO de servicio:** recuperación de lectura, autenticación y estado degradado de `/hoteles`.
- **RTO de tracking:** recuperación de lecturas privadas, creación segura de nuevas observaciones y reanudación controlada de revalidaciones.
- **RTO de delivery:** recuperación del pipeline de eventos sin afirmar que un provider externo aceptó/entregó mensajes durante una interrupción.
- **RPO por capa:** pérdida tolerable/observada de DB, cola, snapshots, configuración, artefactos y evidencias; no asumir que una sola cifra sirve para todo.
- **Punto de recuperación:** `backup_id`, timestamp, schema revision, código/config revision y estado de verificación que identifican la copia usada.

### 3.2 Regla de no invención

H55 no fija números universales de RTO/RPO. Antes del primer drill, el owner debe registrar objetivos aprobados por producto/operación/DB y su justificación en función de:

- criticidad de la lectura y del tracking;
- coste de snapshots y frecuencia de sweeps;
- obligaciones de H35 y retención;
- presupuesto y límites de H37;
- capacidad real del entorno y del proveedor de almacenamiento;
- impacto de perder un evento de alerta frente a perder una observación histórica;
- tiempo de soporte y comunicación aceptable.

Si no hay un objetivo aprobado, el resultado solo puede ser `blocked` para una declaración de readiness, aunque el experimento técnico termine correctamente. El drill debe registrar tanto el objetivo como el valor observado:

```text
objective_rpo_by_dataset:
observed_rpo_by_dataset:  # pérdida efectiva y backup/export de referencia
objective_rto_by_surface:
observed_rto_by_surface:
measurement_start:
measurement_end:
clock_source: UTC
assumptions:
```

Una prueba que solo verifica que `/health` responde 200 no mide el RTO de `/hoteles`.

---

## 4. Inventario de datos y prioridad de recuperación

Cada tabla/cola/artefacto debe tener owner, clasificación, backup policy, reconstruibilidad, privacy class y criterio de validación. La siguiente matriz es contractual y debe completarse con nombres finales y valores efectivos durante la implementación.

| Capa | Ejemplos | Prioridad | ¿Reconstruible? | Validación mínima |
|---|---|---:|---|---|
| A — identidad y ownership | usuarios, `HotelProperty`, aliases, `HotelTrackedOffer`/`UserStayWatch`, reglas, preferencias y relaciones privadas | P0 | no o solo parcialmente | counts, FKs, unicidad, dos usuarios aislados, ownership por origen |
| B — evidencia de precio | `HotelProviderRun`, `HotelRateSnapshot`, oferta/estancia, provenance, observed_at, outcomes | P0 | snapshots antiguos no; nuevos parcialmente | counts por run/provider/outcome, fingerprints, monotonicidad temporal, no error→available |
| C — confianza y comunicación | `HotelAlertEvent`, inbox, delivery intents/events, read/unread, dedupe keys | P0/P1 | algunos eventos pueden reconstruirse, estados no siempre | ownership, no duplicados, estado terminal correcto, read != delivered |
| D — calidad de catálogo | mappings, revisión ambigua H53, merge/split ledger, gold-set labels | P1 | catálogo externo puede reingestarse, decisiones no | policy version, ledger append-only, casos ambiguos conservados |
| E — configuración operativa | flags H43, market specs H54, provider capability, budgets, allowlists, schema/config revision | P0 | puede versionarse, pero perderla bloquea seguridad | fail-closed, no secretos, revision reproducible, kill switch funcional |
| F — colas/leases/cursors | jobs, lease tokens, attempt counters, backoff, sweep cursor, delivery retries | P0/P1 | puede regenerarse con riesgo de duplicado | no dos owners, resume idempotente, intents no se envían dos veces |
| G — observabilidad y auditoría | logs redacted, decision records, incident timeline, métrica exportada | P1/P2 | no toda evidencia puede reconstruirse | redaction, timestamps, correlation/run IDs, acceso restringido |
| H — artefactos | imagen, commit, dependencias, migraciones, fixtures, manifiestos y documentación | P0 | sí si se versiona correctamente | checksum, build reproducible, schema compatible, provenance |

### Reglas de privacidad

- Los backups mantienen la misma clasificación de datos que la fuente, o una más restrictiva.
- No copiar tokens, API keys, cookies, URLs firmadas ni raw provider payloads a un fixture de drill.
- Restaurar en un entorno con acceso mínimo, red externa bloqueada y credenciales revocadas/placeholder.
- No usar una exportación de producción en portátil o tests locales sin redaction y aprobación de H35/H38.
- Registrar quién restaura, qué dataset usa, dónde queda y cuándo se destruye la copia temporal.
- La evidencia del drill usa conteos, hashes, IDs opacos y muestras mínimas; nunca dumps privados completos.

---

## 5. Backup, export y restore

### 5.1 Contrato mínimo de cada backup

Cada backup o export restaurable debe registrar un manifiesto firmado o íntegro, versionado y no ambiguo:

```text
backup_id
created_at_utc
source_environment
source_database_or_dataset
schema_revision
application_commit
config_revision_sanitized
coverage_scope
included_tables_or_streams
excluded_tables_or_streams
encryption/key_reference_without_secret
checksum_or_integrity_method
retention_until
owner
restore_tested_at
restore_test_result
privacy_class
```

`backup_id` no es un sustituto de `provider_run_id`, `incident_id` o `migration_revision`. La relación entre ellos debe estar en el decision log del drill.

### 5.2 Requisitos del proceso

La implementación debe proporcionar, según la tecnología finalmente aprobada:

1. backup consistente o snapshot transaccional de las capas P0;
2. export/versionado de configuración efectiva sin secretos;
3. copia/versionado de migraciones y artefactos del release;
4. integridad verificable antes de declarar el backup usable;
5. retención y borrado con owner, motivo y trazabilidad;
6. restore a un entorno aislado, sin llamadas externas por defecto;
7. prueba de que el restore no altera la fuente;
8. validación de schema, FKs, índices y counts;
9. reporte de lo que no se pudo restaurar;
10. mecanismo de abortar y limpiar una recuperación fallida.

No se acepta “el proveedor de infraestructura hace backups” sin un `backup_id`, alcance, timestamp, checksum/estado y restore probado.

### 5.3 Restore por capas

El orden recomendado es:

```text
0. congelar escrituras y declarar incidente/drill
1. seleccionar backup + artefacto + schema compatibles
2. restaurar DB/config en entorno aislado
3. ejecutar auditoría Alembic y comprobaciones de integridad
4. restaurar/rehidratar colas, leases y cursores como cuarentena
5. arrancar API en modo lectura/repair, sin provider externo
6. validar ownership, snapshots, tracking, alertas e inbox
7. reconciliar datos posteriores al backup
8. ejecutar smoke Mock/fault profiles sobre DB aislada
9. habilitar delivery interno de forma controlada
10. reabrir sweeps/providers/mercados solo tras decisión explícita
```

Nunca arrancar el worker hotelero sobre una DB restaurada antes de saber si contiene leases vivos, jobs `running`, `next_attempt_at` vencidos o snapshots ya evaluados.

### 5.4 Integridad post-restore

Como mínimo, ejecutar:

- conteo y checksum por entidad crítica y por ventana temporal;
- FKs sin huérfanos en tracking, snapshots, reglas, eventos e inbox;
- unicidad de aliases, fingerprints, dedupe keys y lease tokens;
- consistencia `observed_at ≤ created_at` cuando el contrato lo exija;
- ningún snapshot de error/timeout/429 marcado como elegible/live;
- currency, fechas, ocupación y conditions no mutadas por el restore;
- `HotelProperty`/canonical identity separada de provider alias H53;
- no existe relación privada accesible por un usuario diferente;
- H27 `read/unread` no se transforma en `delivered`;
- H28 `queued/sent/delivered/failed` conserva su semántica;
- H43 vuelve a `prod_off` si no se puede verificar el entorno.

Un restore con counts correctos pero ownership incorrecto es `failed`.

---

## 6. Migraciones, schema y compatibilidad durante recovery

### 6.1 Matriz de compatibilidad

Antes del drill, seleccionar explícitamente una combinación:

| Código | Schema | Acción |
|---|---|---|
| anterior | anterior | baseline de lectura y rollback |
| nuevo | anterior | debe fallar cerrado o ejecutar solo si H11 garantiza compatibilidad |
| nuevo | nuevo expandido | ruta esperada de recuperación |
| anterior | nuevo expandido | debe seguir leyendo durante expand-and-contract |
| nuevo | nuevo contractado | solo después de gate H11 y ventana reversible |

No ejecutar `contract` ni eliminar columnas legacy como parte de una recuperación urgente. Si hay duda entre código y schema, arrancar una versión compatible en modo restringido y registrar la discrepancia.

### 6.2 Alembic y backfills

- conservar el revision graph y ejecutar `alembic check`/auditoría antes de abrir tráfico;
- registrar `migration_revision`, `down_revision`, batch cursor y estado del backfill;
- no repetir un backfill sin comprobar idempotencia;
- dejar `needs_review`/`ambiguous` intacto, no convertirlo en match confirmado;
- no ejecutar migración destructiva sobre el único backup disponible;
- probar upgrade desde una copia representativa y downgrade solo donde H11 lo autorice;
- si el restore se toma antes de una migración, congelar el job de migración hasta decidir si se reanuda o se revierte;
- si el restore se toma después, verificar que el binario desplegado conoce esa revisión;
- separar la recuperación de datos de la promoción de provider/mercado.

### 6.3 Criterio de bloqueo

El recovery queda `blocked` si:

- el revision graph tiene heads inesperadas, duplicados o down revisions ausentes;
- la aplicación no puede leer de forma compatible sin mutar datos;
- hay FKs huérfanas o constraints duplicadas;
- se desconoce qué batch de backfill estaba activo;
- no hay un punto de rollback y una copia íntegra;
- una migración exige acceso externo o credenciales no disponibles.

---

## 7. Workers, leases, locks y jobs en vuelo

### 7.1 Estado seguro al declarar incidente

Primero pausar nuevas escrituras externas y registrar:

```text
incident_id
worker_instance_id
job_id/run_id/provider_run_id
lease_owner/token_hash
lease_acquired_at/expires_at
cursor/batch
attempt_count
last_snapshot_or_event_id
next_attempt_at
```

No poner tokens de lease, payloads de provider ni secretos en el ticket.

### 7.2 Recuperación de sweep

1. asegurar que no quedan dos supervisores activos;
2. dejar expirar o revocar leases siguiendo H09, sin borrar evidencia;
3. clasificar runs `running` como `unknown/reconcile`, nunca como `completed` por defecto;
4. comparar último snapshot/evento confirmado con cursor y batch;
5. reanudar desde un cursor estable e idempotente;
6. usar provider Mock en DB aislada para comprobar dedupe;
7. reabrir provider real solo con H43/H54 y budget aprobado;
8. verificar que un retry no cambia `current_price` con outcome inválido;
9. comprobar que una misma transición no vuelve a generar una alerta.

El deployment `infra/k8s/worker.yaml` no satisface este gate mientras su comando sea un placeholder. El nuevo `CronJob` y el Job de migración permanecen `suspend: true`: la imagen ya se construyó y validó localmente y el Job de migración se ejecutó contra SQLite aislada, pero falta imagen publicada inmutable, Secret/DB real, provider aprobado y operación. Un `replicas: 1` nominal o un manifiesto suspendido no es evidencia de lease, restart seguro, scheduling activo o HA.

### 7.3 Recuperación de notifications/delivery

- distinguir evento hotelero persistido, `DeliveryIntent`, intento, aceptación del adapter y entrega confirmada;
- poner en cuarentena intents con resultado ambiguo antes de reemitir;
- respetar `idempotency_key`, `attempt_count`, `next_attempt_at` y estado terminal;
- no convertir `sent` en `delivered` por el hecho de restaurar una fila;
- no ejecutar email/push real en un drill salvo sandbox/consentimiento y provider aprobado;
- ejecutar primero el canal in-app/fixture y comprobar ownership H27;
- replay manual solo con scope, owner, razón y dedupe verificables;
- no borrar eventos fallidos para “vaciar” backlog.

### 7.4 Locks y carreras

El drill debe probar al menos:

- dos workers intentando reclamar el mismo run;
- lease expirado durante un provider timeout;
- restart después de persistir snapshot pero antes de marcar run;
- restart después de crear alert event pero antes de delivery intent;
- dos retries con la misma idempotency key;
- cambio de kill switch mientras un ciclo está en vuelo.

El resultado esperado es un único owner lógico, reanudación segura o estado explícito `needs_review`; no se exige exactly-once si H28 conserva at-least-once con consumidores idempotentes.

---

## 8. Provider outage, mercado pausado y reconciliación

### 8.1 Durante el outage

- activar el kill switch de menor alcance que contenga el riesgo; usar `prod_off` si no se puede aislar;
- conservar snapshots históricos con freshness/stale visible;
- no traducir timeout, 429, schema drift o unavailable a `empty`/`sold_out`;
- impedir que una observación inválida actualice tracking o dispare una alerta;
- bloquear nuevas llamadas del provider sin borrar aliases, mapping, feedback o procedencia;
- marcar el mercado H54 como `paused` solo con owner, razón, timestamp y scope;
- registrar coste, requests y evidencia redacted.

### 8.2 Después del restore/provider recovery

La reconciliación debe separar:

1. **ventana conocida:** observaciones confirmadas antes del incidente;
2. **ventana perdida:** tiempo sin observación, que no se rellena artificialmente;
3. **ventana ambigua:** requests posiblemente aceptadas pero sin respuesta;
4. **ventana posterior:** nuevas observaciones después de reabrir;
5. **eventos derivados:** alertas que sí/no deben reemitirse según baseline y dedupe.

La primera pasada post-recovery debe ser limitada, observable y preferiblemente Mock/fixture. Para provider real exige H07/H08/H37/H41/H43/H54, budget, canary y kill switch.

### 8.3 Regla de confianza

Una recuperación no autoriza copy como “precio actual” si el último dato está fuera de TTL o si la ventana contiene observaciones desconocidas. La UI debe comunicar `stale`, `unavailable`, `partial` o “comprobación pendiente” con la siguiente acción segura.

---

## 9. Corrupción, duplicación y reconciliación de snapshots

### 9.1 Contención

Ante precios imposibles, snapshots duplicados, provider cruzado o tracking incoherente:

1. detener nuevas escrituras del provider/sweep afectado;
2. conservar la fuente y el estado original;
3. tomar backup/snapshot antes de corregir;
4. generar reporte dry-run por `provider_run_id`, fingerprint y ventana;
5. poner datos sospechosos en cuarentena lógica, sin borrado masivo;
6. suspender evaluación de alertas sobre observaciones no elegibles;
7. preservar históricos válidos y provenance;
8. abrir incidente H42/H38 si hay ownership o privacidad;
9. preparar reparación versionada, idempotente y reversible.

### 9.2 H53 y reconciliación de identidad

- no fusionar `HotelProperty` solo por nombre, coordenadas cercanas o un único provider ID;
- aliases `pending/ambiguous` no pueden alimentar tracking dirigido como si fueran confirmados;
- merge/split requiere dry-run, ledger append-only, policy version, owner, impacto downstream y rollback;
- revalidar snapshots, tracked offers, alertas, inbox y feedback después de una corrección;
- comparar counts antes/después y conservar los IDs externos opacos;
- todo caso ambiguo queda visible para revisión, no oculto bajo un match automático.

### 9.3 Checks de reconciliación

```text
orphan_snapshot_count = 0 o explicado
orphan_tracking_count = 0 o needs_review explícito
cross_user_relation_count = 0
invalid_outcome_as_eligible_count = 0
duplicate_idempotency_key_count = 0
provider_identity_conflict_count = medido y clasificado
alert_replay_without_dedupe_count = 0
unexplained_price_mutation_count = 0
```

No convertir un valor “desconocido” en cero para que el informe parezca limpio.

---

## 10. Recovery drill: protocolo repetible

### 10.1 Preparación

El owner del drill debe abrir un registro con:

```text
drill_id: H55-YYYYMMDD-<opaque>
scenario: restore | provider_outage | worker_loss | corruption | release_rollback | mixed
environment: isolated_staging_or_fixture
owner / observers / approver
objective_rto_by_surface
objective_rpo_by_dataset
source_backup_id
schema_revision
application_commit
config_revision_sanitized
fixture_version
external_calls_allowed: false by default
start/end clocks: UTC
stop_conditions
```

Precondiciones:

- DB y credenciales aisladas;
- red externa bloqueada o provider Mock explícito;
- dataset sanitizado con al menos dos usuarios, dos propiedades, dos ofertas/estancias, snapshots, una regla, eventos inbox y estados delivery;
- fixture de fallo: timeout/429/invalid response/worker restart y un caso de mapping ambiguo;
- backup íntegro y manifiesto disponible;
- observadores de DB, backend/worker, seguridad y QA;
- mecanismo de abortar y limpiar el entorno.

### 10.2 Escenarios mínimos

| Escenario | Inyección | Debe demostrar |
|---|---|---|
| Restore limpio | restaurar copia a entorno aislado | integridad, schema, ownership y lectura segura |
| Pérdida de worker | detener/reiniciar proceso durante un run | lease/cursor/retry sin doble snapshot/alerta |
| Provider outage | timeout/429/unavailable fixture | stale/unavailable honesto, no falso sold out y cooldown |
| Delivery ambiguo | aceptar/timeout fixture después de enqueue | idempotencia, no doble envío y estados separados |
| Corrupción | duplicado o precio inválido inyectado en fixture | cuarentena, dry-run, reparación reversible |
| Release rollback | volver a commit compatible | health + smoke hotelero + flags off + datos intactos |
| Migración interrumpida | parar backfill entre batches | resume idempotente o rollback seguro |
| Identidad ambigua | alias pendiente reutilizable | bloqueo de tracking dirigido y revisión H53 |

### 10.3 Ejecución

1. registrar baseline de counts, hashes y estados sin exponer datos;
2. iniciar reloj de RTO y declarar el incidente simulado;
3. aplicar contención H42/H43;
4. tomar evidencia de procesos, runs, leases, flags y últimos eventos;
5. restaurar o reparar solo con comandos aprobados y `dry-run` cuando aplique;
6. ejecutar auditoría schema/Alembic y checks de integridad;
7. arrancar API en modo restringido y verificar lectura/ownership;
8. reconciliar jobs, delivery y ventanas perdidas;
9. ejecutar smoke de H44 y fault profiles sin red externa;
10. habilitar progresivamente escritura interna, después sweeps Mock, y dejar provider real apagado;
11. medir el instante en que cada superficie satisface su criterio;
12. registrar desviaciones, decisiones y stop conditions;
13. limpiar el entorno temporal y confirmar que no se tocaron datos de fuente;
14. aprobar, rechazar o dejar parcial el drill.

### 10.4 Resultado y severidad

- **`passed`:** objetivos aprobados y medidos satisfechos, checks de integridad/privacidad limpios, evidencia reproducible y sin gaps bloqueantes.
- **`partial`:** recuperación técnica demostrada para una capa, pero falta un objetivo, canal, owner, evidencia o integración; no autoriza readiness global.
- **`blocked`:** no se pudo medir de forma segura, falta backup/credencial/entorno/owner o el escenario exige infraestructura inexistente.
- **`failed`:** se ejecutó y hubo pérdida no explicada, fuga, cross-user, corrupción, duplicado no deduplicable o incumplimiento del objetivo aprobado.

Un drill `passed` en Mock no certifica provider live, delivery externo ni worker Kubernetes productivo.

---

## 11. Evidencia, auditoría y postmortem

### Paquete mínimo

- `drill_id`, escenario, timestamps UTC y commit;
- manifiesto `backup_id`, checksum/estado, schema/config revision;
- objetivo y observado de RPO/RTO por capa;
- baseline y post-restore counts/hashes;
- logs estructurados redacted y correlation/run/job IDs opacos;
- estado de flags, kill switch y external calls observadas;
- resultados de Alembic/schema/FK/ownership/dedupe;
- comandos exactos, fixtures, versiones y resultados de tests;
- screenshots/capturas de UI solo si son necesarias y sin PII;
- desviaciones, stop conditions y decisiones aprobadas;
- owner, reviewer, fecha de caducidad y siguiente drill;
- cleanup confirmado y evidencia de que la fuente no fue mutada.

### Postmortem

Para un `failed` o un `partial` con impacto relevante, H42 exige un postmortem sin culpas que cubra:

```text
impact_scope
what_was_lost_or_ambiguous
first_detected_at
containment
root_cause_or_unknowns
recovery_steps
observed_rpo/rto
privacy/security_assessment
what_prevented_faster_recovery
corrective_actions
owner/due_date
retest_plan
```

No cerrar un incidente con “se reinició el worker” si no se comprobó la cadena de datos y la experiencia visible.

---

## 12. Gates de implementación H55

### Gate B — Backup y restore

- [ ] existe un backup/export de alcance explícito y `backup_id`;
- [ ] integridad/checksum y retención están verificadas;
- [ ] restore aislado no toca la fuente;
- [ ] restore funciona con un schema/código compatible;
- [ ] los datos P0, privacidad y ownership pasan checks;
- [ ] la copia temporal se limpia según H35/H38.

### Gate M — Migración y compatibilidad

- [ ] revision graph y Alembic audit pasan;
- [ ] upgrade/rollback están clasificados por reversibilidad;
- [ ] backfill interrumpido puede reanudarse o queda en estado seguro;
- [ ] no se borran columnas/aliases/snapshots en recovery urgente;
- [ ] SQLite/PostgreSQL o los entornos soportados tienen evidencia equivalente.

### Gate W — Workers, locks y delivery

- [ ] no hay dos owners tras restart;
- [ ] runs `running` se reconcilian, no se marcan completados a ciegas;
- [ ] cursores/leases/locks son idempotentes;
- [ ] snapshots y alert events no se duplican;
- [ ] delivery conserva estados y dedupe, sin afirmar `sent=delivered`;
- [ ] el worker Kubernetes legacy no se presenta como productivo mientras sea placeholder;
- [ ] el CronJob y el Job de migración nuevos siguen suspendidos hasta que imagen, Secret/DB, migración, provider y operación tengan evidencia reproducible.

### Gate D — Datos, identidad y privacidad

- [ ] no hay cross-user leak;
- [ ] aliases ambiguos no alimentan tracking dirigido;
- [ ] snapshots inválidos quedan fuera de alertas/ranking;
- [ ] merge/split y reparación tienen ledger y rollback;
- [ ] no aparecen secretos, PII o URLs firmadas en evidencia.

### Gate R — Drill medido

- [ ] escenario, objetivo y owners están registrados;
- [ ] RPO/RTO se miden por superficie/dataset;
- [ ] H44 reproduce smoke y estados degradados;
- [ ] H42/H43/H45 se prueban en la secuencia correcta;
- [ ] resultado `passed/partial/blocked/failed` tiene justificación;
- [ ] acciones correctivas tienen owner, fecha y re-test.

### Criterio de salida

H55 podrá declararse **implementada**, no solo contractualmente completa, cuando:

1. exista al menos un backup restaurable y verificado de las capas P0;
2. haya un restore aislado con integridad, ownership y privacidad comprobados;
3. una interrupción de worker y una migración interrumpida tengan recuperación idempotente;
4. provider outage y delivery ambiguo no produzcan falsos precios, alertas duplicadas ni estados engañosos;
5. RPO/RTO aprobados estén medidos con reloj y evidencia;
6. haya un drill `passed` o un conjunto de drills que cubra todas las superficies críticas;
7. H41 aporte señales consultables, H42 runbook ejecutable, H43 kill switch verificable y H45 rollback de release reproducible;
8. los gaps restantes estén explícitos y no se anuncie tracking automático más allá de lo demostrado.

**Resultado H55 actual:** contrato de continuidad aprobado. No se declara que exista backup/restore automatizado, failover, RTO/RPO operativo, worker Kubernetes productivo o recovery drill pasado hasta ejecutar los gates anteriores.
