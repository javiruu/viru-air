# H56 — Paquete de evidencia anual hotelera: baseline local seguro

**Artefacto:** `HotelAnnualReview` parcial  
**Estado:** `evidence_incomplete`  
**Fecha de ejecución:** 2026-08-05  
**Entorno:** backend local, tests/fixtures, sin provider comercial  
**Fuente de verdad:** [contrato H56](../reference/backend/hoteles-revision-anual-roadmap-h56.md)  
**Plantillas:** [revisión anual](hoteles-h56-annual-review-template.md) · [DecisionRecord](hoteles-h56-decision-record-template.md)  
**Objetivo:** producir la primera evidencia ejecutada de `/hoteles` sin confundir pruebas locales con salud de producción.

> Este documento no aprueba providers, mercados, costes, SLOs, delivery ni tracking automático. Solo registra observaciones reproducibles de código local, Mock, fixtures y rutas desactivadas.

---

## 1. Identidad de la ejecución

```text
review_id: H56-2026-08-05-local-baseline
review_period_start_utc: 2026-08-05T15:56:00Z
review_period_end_utc: 2026-08-05T15:58:00Z
execution_environment: local_test
provider_mode: mock_only (Makcorps remains mocked in the selected test suite)
external_calls_allowed: false
commercial_credentials_used: false
network_suite: excluded
source_commit: TBD
schema_revision: 0041_add_community_trending_snapshots observed after isolated Alembic upgrade head
prior_audit_caveat: separate in-memory audit had no alembic_version because it was not upgraded
migrated_db_run: isolated temporary SQLite file; deleted after evidence capture
worker_once_run: isolated temporary SQLite file; worker exit=0; log file deleted after evidence capture
worker_restart_two_cycle: two fresh --once processes; both exit=0; 2 completed runs; 6 snapshots (3 per run)
k8s_worker_status: legacy_placeholder_command_not_hotel_sweep
k8s_worker_gate: blocked — legacy Deployment remains placeholder; new CronJob is suspend=true; image published immutable, DB/Secret contract, provider approval, lease contract and active scheduling remain unverified
runtime_image_status: backend/Dockerfile multi-stage with uv.lock; image built and runtime-verified locally (build exit 0; app.main import OK; uvicorn /health 200 on migrated isolated DB); CI build without push; published digest unapproved
k8s_migration_job_status: suspended in K8s; alembic upgrade head executed inside the image container against isolated SQLite (exit 0 to 0041_add_community_trending_snapshots); real DB/Secret execution unverified
provider_run_traceability: complete_for_sweep_ingestion_snapshots_after_fix
legacy_direct_ingestion_traceability: intentionally_none_when_no_provider_run_id_is_supplied
source_of_truth_for_runtime_counts: ephemeral command output; no production database used
config_source: backend/.env.example + test monkeypatches
review_owner: TBD
approver: TBD
decision_status: evidence_incomplete
```

La hora del worker se capturó como `2026-08-05T17:56:48+0200`; el rango UTC anterior es una referencia operativa aproximada del proceso y debe sustituirse por timestamps de ejecución del CI si se publica como evidencia formal.

---

## 2. Ejecución de tests segura

### Comando

```bash
cd backend
python -m pytest \
  tests/integration/test_hotels_api_flow.py \
  tests/unit/test_hotels_sweep.py \
  tests/unit/test_hotels_sweep_worker.py \
  tests/unit/test_hotels_makcorps_provider.py \
  -q -m 'not network'
```

### Resultado observado

```text
........................................................................ [ 88%]
.........                                                                [100%]
81 passed in 65.76s (0:01:05)
```

| Señal | Estado | Qué demuestra | Qué no demuestra |
|---|---|---|---|
| API hotelera con Mock | `measured` en ejecución local | rutas de búsqueda, ingestión, ownership, tracking, alert events, estados HTTP y fixtures cubiertos por la suite | disponibilidad, latencia o coste de un provider externo |
| Sweep Mock | `measured` en ejecución local | comportamiento del servicio/worker bajo fixtures y DB de test | scheduler productivo, lease distribuido, HA o frecuencia garantizada |
| Worker hotelero | `measured` en ejecución local | tests del worker y su control por flags | deployment Kubernetes productivo o recuperación automática |
| Adapter Makcorps | `measured` solo con sesión/respuestas mockeadas | parser, errores simulados, 429/500/timeout simulados y redacción local cubierta por tests | cuota, SLA, cobertura, coste, latencia o estabilidad del API real |
| Red externa | `not_used` por alcance del comando | se excluyó el marker `network` | no certifica que otros comandos futuros sean offline |

### Interpretación

La ejecución prueba el comportamiento local bajo contrato/fixture. No se debe incorporar `81 passed` como “81 casos live”, ni derivar de ello un `provider_error_rate`, cobertura de mercado o SLO.

---

## 3. Configuración efectiva de referencia

La inspección de `backend/.env.example` registró:

```text
HOTEL_PROVIDER=mock
HOTEL_FEATURE_ENABLED=false
HOTEL_SWEEP_ENABLED=false
HOTEL_SWEEP_INTERVAL_SECONDS=3600
HOTEL_PROVIDER_TIMEOUT_SECONDS=10
HOTEL_PROVIDER_MAX_RETRIES=2
HOTEL_PROVIDER_CACHE_TTL_SECONDS=3600
HOTEL_GEOCODER_ENABLED=true
MAKCORPS_API_KEY=
MAKCORPS_BASE_URL=https://api.makcorps.com
```

### Clasificación

| Configuración | Observación | Estado H56 |
|---|---|---|
| provider por defecto | `mock` | `measured` como valor de plantilla |
| feature hotelera | `false` | `measured` como valor de plantilla |
| sweep | `false` | `measured` como valor de plantilla |
| intervalo | `3600` segundos | `measured` como valor de plantilla; no es frecuencia operativa probada |
| timeout/retries | `10`/`2` | `measured` como configuración local; no implica política global de cuota |
| cache provider | `3600` reservado | `measured` como variable; la propia plantilla indica que no hay cache runtime activa |
| geocoder | `true` | `measured` como valor de plantilla; requiere el gate H43 para saber cuándo puede producir tráfico externo |
| credencial Makcorps | vacía en plantilla | `measured` como plantilla; nunca se registra el valor efectivo de un entorno privado |

La plantilla no sustituye una auditoría de configuración efectiva de staging/producción.

---

## 4. Worker desactivado

### Comando

```bash
cd backend
HOTEL_SWEEP_ENABLED=false HOTEL_PROVIDER=mock \
  python -m app.worker.hotels_sweep --once --provider mock
```

### Resultado observado

```json
{"event": "hotel_sweep_disabled", "message": "HOTEL_SWEEP_ENABLED=false"}
```

**Estado:** `measured` para el entrypoint `app.worker.hotels_sweep` en local.  
**Significado:** el worker no inició un sweep cuando la flag efectiva del proceso estaba desactivada.  
**Limitación:** H43/H42 documentan que esto no prueba el bloqueo del job directo `run_hotel_sweep`, de procesos ya arrancados ni de un deployment productivo.

No se ejecutó `--loop`, no se usó una DB de producción y no se activó Makcorps.

---

## 5. Auditoría del grafo Alembic

### Comando

```bash
cd backend
DB_URL=sqlite:///:memory: \
  python -m app.infrastructure.db.alembic_audit --json
```

### Resultado relevante

```json
{
  "chain_ok": true,
  "heads": ["0041_add_community_trending_snapshots"],
  "missing_down_revisions": [],
  "duplicate_revisions": {},
  "files_missing_identifiers": [],
  "untracked_migration_files": [],
  "db_state": {
    "status": "no_version_table",
    "db_url": "sqlite:///:memory:",
    "version_rows": []
  }
}
```

| Señal | Estado | Interpretación |
|---|---|---|
| revision graph | `measured` | no hay down revisions ausentes, duplicados ni ficheros sin identificadores en el grafo inspeccionado |
| head | `measured` | la cabeza observada es `0041_add_community_trending_snapshots` |
| DB restaurada/migrada | `blocked` | una SQLite en memoria vacía no tiene `alembic_version`; no se ejecutó `upgrade head` en este comando |
| restore/recovery | `not_measured` | este audit no es un backup/restore ni un recovery drill H55 |

No convertir `chain_ok=true` en “migración de producción sana”: solo describe el grafo de revisiones y la ausencia de una tabla de versión en la DB efímera usada.

---

## 6. DB aislada migrada y sweep Mock real

### Alcance y seguridad

Se repitió el flujo sobre una SQLite temporal aislada, creada y eliminada dentro del proceso:

```bash
cd backend
DB_URL=sqlite:///./<temporary-file>.db \\
  python -m alembic upgrade head
```

Después se ejecutaron dos llamadas directas a `run_hotel_sweep(db, provider="mock")` y, en una DB temporal separada, el entrypoint real `python -m app.worker.hotels_sweep --once --provider mock` con:

```text
HOTEL_FEATURE_ENABLED=true
HOTEL_PROVIDER=mock
RUN_DB_INIT=false
RUN_SEED_USERS=false
external_calls_allowed=false
commercial_credentials_used=false
```

No se usó Makcorps, no se leyó una credencial comercial y no se hizo ninguna llamada HTTP externa. La DB temporal se eliminó al terminar.

### Resultado observado

```json
{
  "alembic_version": "0041_add_community_trending_snapshots",
  "first_run": {"provider": "mock", "status": "completed", "items_processed": 3},
  "second_run": {"provider": "mock", "status": "completed", "items_processed": 3},
  "counts": {
    "provider_runs": 2,
    "hotels": 3,
    "aliases": 3,
    "snapshots_total": 6,
    "snapshots_first_run": 3,
    "snapshots_second_run": 3,
    "alert_events_second_run": 1
  },
  "alert_events_second": [
    {"event_type": "price_below", "trigger_value": 210.0}
  ]
}
```

### Interpretación y límite de trazabilidad

- `0041_add_community_trending_snapshots` demuestra que **esta DB temporal aislada** completó `alembic upgrade head`; no demuestra que staging o producción estén migrados.
- Los dos `HotelProviderRun` terminaron `completed` y procesaron tres registros Mock cada uno.
- Se observaron tres `HotelProperty`, tres `HotelProviderAlias` y seis `HotelRateSnapshot` persistidas en total, tres por cada run.
- Tras el fix, una repetición aislada con dos runs confirmó 6 snapshots de ingestión: 3 vinculadas al primer `provider_run_id` y 3 al segundo.
- La deduplicación incluye el `provider_run_id` cuando existe: cada sweep nuevo registra su observación, mientras que repetir el mismo run sigue siendo idempotente (`rates_ingested=0` en el replay).
- Las llamadas directas a `HotelIngestionService(db).ingest()` siguen sin `provider_run_id` por diseño de compatibilidad y conservan la idempotencia histórica; no se presentan como evidencia de un sweep.
- El único evento `price_below` del baseline anterior estaba asociado al segundo run, con `trigger_value=210.0`, pero usaba un umbral sintético de fixture (`100000`) y solo demostraba evaluación local de alertas; no era una señal de producción ni un cambio real de precio de usuario.
- El gap de propagación de `provider_run_id` queda resuelto para los caminos `run_hotel_sweep()`.
- El entrypoint real del worker terminó con exit `0`, emitió un evento estructurado `hotel_sweep_cycle` con `status=completed`, `items_processed=3` y un `provider_run_id` válido.
- La DB separada del worker observó `0041_add_community_trending_snapshots`, 3 hoteles, 3 aliases y 3 snapshots, todas vinculadas al mismo run; no se usaron llamadas externas.
- Dos procesos independientes `--once` sobre la misma DB temporal simularon un reinicio entre ciclos: ambos terminaron con exit `0`, crearon 2 runs `completed` y dejaron 6 snapshots trazables, 3 por run.
- El manifest `infra/k8s/worker.yaml` sigue clasificado como `legacy_placeholder_command_not_hotel_sweep` (`python -c "print('worker placeholder')"`); esta prueba no demuestra scheduling, restartPolicy, HA ni ejecución hotelera en Kubernetes.

**Estado H56 de esta ejecución:** `measured` para migración y trazabilidad del sweep Mock local; `evidence_incomplete` para cualquier conclusión productiva, comercial o de aprobación de provider.

## 7. Métricas H56 resultantes

| Métrica/claim | Estado | Resultado | Evidencia | Limitación |
|---|---|---|---|---|
| baseline hotelero inicial | `measured` | `81 passed`, 65.76 s | salida pytest del baseline anterior | local/fixture; no es producción |
| suite hotelera ampliada tras trazabilidad | `measured` | `122 passed`, 71.64 s | salida pytest final con `-m 'not network'` | local/fixture; no es producción |
| provider comercial aprobado | `not_measured` | ninguno | H07/H08 + alcance offline | no se ejecutó canary |
| coste por búsqueda/sweep | `not_measured` | TBD | no hay ledger hotelero | no inventar precio ni cuota |
| 429 real actual | `not_measured` en esta ejecución | TBD | tests solo simulan errores | H07 contiene una observación histórica, no una nueva medición |
| latencia provider | `not_measured` | TBD | no hubo red comercial | la duración global de tests no es latencia API |
| tracking diario garantizado | `not_measured` | TBD | worker se probó localmente, pero no hay scheduling sostenido | H09/H43/H55 siguen pendientes |
| métricas funnel H04 | `not_measured` | TBD | allowlist UX actual no demuestra taxonomía completa `hotel_*` | falta instrumentación hotelera y denominadores |
| feedback de producción | `not_measured` | TBD | endpoint/modelo existen | no se agregaron datos de producción |
| DB aislada migrada con Alembic | `measured` | `0041_add_community_trending_snapshots`; 2 runs Mock `completed`, 3 items cada uno | salida JSON del sweep temporal | solo DB local efímera; no staging/producción |
| worker real `--once` | `measured` local | exit `0`, `hotel_sweep_cycle` `completed`, 3 items | stdout/log estructurado y DB temporal | no prueba scheduling sostenido, HA ni producción |
| reinicio entre dos ciclos `--once` | `measured` local | 2 procesos independientes exit `0`, 2 runs completed, 6 snapshots (3/run) | dos logs y DB temporal | no prueba Deployment K8s; manifest sigue siendo placeholder |
| hoteles, aliases y snapshots Mock persistidos | `measured` | 3 hoteles, 3 aliases, 6 snapshots; 3 por cada run | consulta redacted de la DB temporal | solo Mock/local; ingesta directa sin run conserva `None` |
| snapshots atribuibles por run | `measured` local | 6 snapshots con `provider_run_id`, 3 por cada sweep aislado | assertion `snapshot_counts_by_run={first: 3, second: 3}` | solo Mock/local; ingesta directa sin run conserva `None` |
| alert event asociado al segundo run | `measured` local/fixture | 1 `price_below`, `trigger_value=210.0` | consulta por `provider_run_id` | umbral sintético; no producción |
| recovery drill H55 | `not_measured` | TBD | no se restauró backup ni se simuló pérdida | este baseline no toca datos live |
| decision anual | `evidence_incomplete` | sin decisión final | este paquete | falta periodo real, owners y revisión aprobadora |

---

## 8. Gaps que bloquean el siguiente nivel

1. Registrar `source_commit`, owners, approver y timestamps CI para convertir esta ejecución local en artefacto reproducible.
2. Repetir el paquete desde CI con una DB aislada migrada, conservando el alcance sin provider externo.
3. Repetir el worker `--once --provider mock` desde CI/staging-like y conservar `HotelProviderRun`/snapshots/eventos redacted.
4. Mantener bloqueado el cambio de `infra/k8s/worker.yaml`: el legacy Deployment sigue siendo placeholder. El nuevo CronJob queda suspendido hasta demostrar imagen publicada inmutable, Secret/DB, migración compatible, provider aprobado y operación/scheduling conforme H43/H45/H55.
5. Mantener el contrato: todo sweep debe pasar `provider_run_id`; no usar ingesta directa como evidencia de un run.
6. Auditar flags en API, worker y job directo; H43 documenta que no todos los entrypoints comparten todavía la misma decisión.
7. Implementar/medir la allowlist hotelera H04 antes de calcular funnel causal.
8. Obtener evidencia comercial aprobada antes de cualquier canary Makcorps/otro provider.
9. Ejecutar H55 restore/drill aislado antes de reclamar RPO/RTO.
10. Crear un `DecisionRecord` final solo después de resolver estas limitaciones y revisar el paquete con owners.

---

## 9. Estado de aprobación

```text
review_id: H56-2026-08-05-local-baseline
status: evidence_incomplete
measured_claims:
  - initial selected local hotel suite: 81 passed
  - expanded traceability hotel suite: 122 passed
  - Alembic revision graph: chain_ok=true
  - isolated SQLite `upgrade head`: `0041_add_community_trending_snapshots`
  - 2 Mock runs `completed`, 3 items each; 3 hotels, 3 aliases, 6 snapshots total (3 per run)
  - 1 local `price_below` event associated with the second run; synthetic threshold
  - hotels_sweep worker disabled path: observed
  - real worker `--once` with Mock: exit=0, structured `hotel_sweep_cycle` completed, 3 items
  - two fresh worker processes: exit=0 each, 2 completed runs, 6 snapshots (3 per run)
  - Kubernetes legacy Deployment remains placeholder, not hotel sweep
  - backend lock-based image build contract exists and CI builds without push; immutable image digest remains unverified
  - new hotel sweep CronJob and separate migration Job exist but are `suspend: true`; image publication, Secret/DB, provider approval and active scheduling remain unverified
  - backend runtime image build: exit 0; app.main import OK; uvicorn `/health` 200 on migrated isolated DB
  - plain `alembic upgrade head` inside the image container: exit 0 to `0041_add_community_trending_snapshots` on isolated SQLite
  - hotel sweep inside the image container: `hotel_sweep_cycle` completed, 3 items (mock)
approximate_claims: []
not_measured_claims:
  - provider live health/coverage/cost/latency
  - production funnel/retention/feedback
  - RPO/RTO and restore
  - delivery hotelero externo
  - canary/traffic split
measured_traceability:
  - sweep ingestion snapshots carry provider_run_id in isolated Mock run
contract_only_claims:
  - H04 event taxonomy
  - H37 cost/rate-limit policy
  - H41 dashboards/SLO
  - H43 unified flags/canary
  - H55 backup/restore/drill
provider_decisions: none_yet
market_decisions: none_yet
next_roadmap: not_created
approver: TBD
```

**Resultado:** primer baseline H56 ejecutado de forma segura, útil para orientar el siguiente trabajo, pero insuficiente para una revisión anual aprobada o para declarar `/hoteles` listo para tracking comercial.
