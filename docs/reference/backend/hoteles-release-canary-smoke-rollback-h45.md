# H45 — Release, smoke tests, canary y rollback hotelero

**Estado:** COMPLETA como contrato de release readiness; smoke offline Mock + kill switch y smoke E2E local H44 con evidencia redacted están verificados; canary comercial, promoción/rollback real y firma de release siguen pendientes
**Fecha:** 2026-08-05  
**Área:** release / QA / backend / frontend / infraestructura  
**Fuente de verdad:** sí para aprobar o bloquear una release hotelera  
**Depende de:** H32, H39, H40, H41, H42, H43 y H44  
**Siguiente fase:** H46 — primera victoria sin tutorial largo

> H45 define el gate para poner cambios delante de usuarios sin convertirlos en testers involuntarios. Distingue el pipeline genérico de release, el smoke local hotelero y el canary de provider comercial. No declara que exista tráfico dividido, rollback automático ni worker hotelero productivo solo porque haya manifests o un workflow con mensajes de ejemplo.

## 1. Objetivo y frontera

Una release hotelera solo puede avanzar si se demuestra:

1. que el artefacto compila y pasa sus suites afectadas;
2. que API, frontend, datos y flags son compatibles;
3. que el flujo principal hotelero funciona con dataset determinista H44;
4. que los estados degradados no mienten;
5. que el canary tiene owner, ventana, presupuesto, métricas y rollback;
6. que apagar provider/sweep/geocoder conserva datos y evita nuevas llamadas externas;
7. que existe evidencia suficiente para repetir la decisión o explicar por qué se bloqueó.

H45 no mezcla tres cosas distintas:

| Superficie | Qué valida | Estado real |
|---|---|---|
| Release canary | artefacto backend/frontend, probes y comportamiento de la release | workflow y runbook genéricos; canary real no demostrado |
| Smoke hotelero | `/hoteles`, auth, búsqueda, detalle, tracking, alertas, inbox y deeplink sobre Mock/H44 | E2E local Chromium aislado verificado; cross-browser y aprobación humana pendientes |
| Provider canary | tráfico controlado a provider comercial aprobado | objetivo H43/H45; Makcorps tiene riesgo 429 y no está aprobado como camino estable |

## 2. Baseline de release comprobado

### 2.1 Controles existentes

| Control | Evidencia | Qué demuestra | Qué no demuestra |
|---|---|---|---|
| Release guard | `scripts/release_guard.ps1` | rama `main`, working tree limpio salvo override, remote y artefactos prohibidos; con `-ExpectedPaths` también acota el staging | calidad funcional, despliegue o rollback |
| Workflow CI | `infra/github/workflows/release.yml` | `workflow_dispatch`, pytest backend, build frontend y pasos nominales de canary | el job canary solo ejecuta `echo`; no hace traffic split ni mide SLI |
| Health | `GET /health` en `backend/app/main.py` | proceso API responde `{status: ok}` | DB, provider, worker, leases, datos o flujo hotelero |
| Readiness | `GET /ready` en `backend/app/main.py` | proceso API responde `{status: ready}` | no verifica dependencias hoteleras; no es una garantía de worker |
| Backend probes | `infra/k8s/backend.yaml` | liveness `/health` y readiness `/ready` del deployment placeholder | imagen real, secrets, servicio productivo o canary funcional |
| Worker manifest | `infra/k8s/worker.yaml` | existe un deployment descrito | el comando es `python -c "print('worker placeholder')"`; no ejecuta sweeps |
| Worker image | `backend/Dockerfile`, `backend/uv.lock`, `infra/github/workflows/ci.yml` y `infra/github/workflows/release.yml` | build multi-stage basado en lock **construido y validado en contenedor** (exit 0; `import app.main` OK; uvicorn `/health` → 200 con DB aislada migrada); CI construye sin push; `release.yml` incluye el job `publish-image` preparado (tags `sha-<commit>`/`latest`, `packages: write`) | no demuestra que el publish se haya ejecutado contra GHCR: imagen publicada, digest aprobado y despliegue real quedan por demostrar |
| Sweep CronJob | `infra/k8s/hotels-sweep-cronjob.yaml` | existe un `CronJob --once` con `concurrencyPolicy: Forbid`, `DB_URL` y `JWT_SECRET` desde Secret y `suspend: true`; el worker `--once --provider mock` **ejecutado dentro de la imagen** terminó `completed` (3 items) sobre DB aislada | no demuestra scheduler activo, Secret creado, DB real, migración compatible ni provider autorizado |
| Migration Job | `infra/k8s/hotels-migrate-job.yaml` | existe un Job Alembic separado, con `DB_URL` y `JWT_SECRET` desde Secret y `suspend: true`; **`alembic upgrade head` ejecutado dentro de la imagen** terminó exit 0 hasta `0041_add_community_trending_snapshots` sobre SQLite aislada | no demuestra ejecución contra una DB/Secret real ni compatibilidad con un restore productivo |
| Activation patch | `infra/k8s/hotels-sweep-cronjob-enabled-patch.yaml` | patch Kustomize separado que deja explícitos `suspend: false` y flags Mock `true` | no debe aplicarse como YAML independiente ni sin aprobación H43/H45/H55, imagen/Secret/migración y provider autorizados |
| Canary genérico | `docs/runbooks/runbook-canary-rollback.md` | propone 5% → 25% → 50% → 100%, observación p95/5xx/auth/jobs y rollback | no prueba que exista esa infraestructura para hoteles |
| Backend tests | `backend/pyproject.toml`, `backend/tests/` | pytest, SQLite fixtures y markers `integration`/`network` | suite hotelera E2E, PostgreSQL lock/lease o provider comercial |
| Frontend checks | `frontend/package.json` | scripts de calidad y tests `tsx --test`; el workflow CI actual solo ejecuta la compilación | browser E2E completo de hoteles |

### 2.2 Suites hoteleras de referencia

- `backend/tests/unit/test_health.py`;
- `backend/tests/unit/test_hotels_mock_provider.py`;
- `backend/tests/unit/test_hotels_ingestion.py`;
- `backend/tests/unit/test_hotels_area_search.py`;
- `backend/tests/unit/test_hotels_area_resolve.py`;
- `backend/tests/unit/test_hotels_sweep.py`;
- `backend/tests/unit/test_hotels_sweep_worker.py`;
- `backend/tests/integration/test_hotels_api_flow.py`;
- `frontend/tests/hotels-f56-audit.test.ts`;
- `frontend/tests/hotels-signal-assessment.test.ts`.

Estas pruebas no deben presentarse como un smoke E2E completo hasta que una ejecución cubra navegador, red, DB aislada, usuario y evidencia de los estados definidos.

## 3. Preflight de release

### 3.1 Cambios y artefacto

Antes de ejecutar una release:

- identificar commit, alcance, owner y fase H45;
- revisar `git status`, diff y archivos esperados;
- ejecutar `scripts/release_guard.ps1` en PowerShell desde la raíz, sin `-AllowDirtyWorktree` salvo decisión registrada; usar `-ExpectedPaths` únicamente cuando el alcance esté staged y se quiera validar la lista exacta;
- confirmar que no hay secretos, builds, binarios ni artefactos temporales en el alcance;
- comprobar migraciones H11, compatibilidad V1/V2 y plan de rollback;
- confirmar que `backend/.env` y credenciales no se incluyen en evidencia;
- registrar versiones de Python, Node, dependencias, dataset H44 y configuración H43.

`release_guard.ps1` falla si el árbol está sucio por defecto. En el flujo actual hay muchos documentos H01-H44 no trackeados de la construcción del roadmap; no se debe falsear el gate: hay que acotar/stagear el alcance o registrar explícitamente el bloqueo.

### 3.2 Preflight de datos y configuración

- migración ejecutada en DB aislada/staging representativa;
- backup/restore o procedimiento reversible probado según H11/H42;
- `prod_off` explícito para smoke sin provider comercial;
- `HOTEL_FEATURE_ENABLED`, `HOTEL_SWEEP_ENABLED` y `HOTEL_GEOCODER_ENABLED` coherentes con H43;
- Mock y dataset H44 etiquetados `DEMO_NO_LIVE_AVAILABILITY`;
- no usar `backend/.env` como fixture ni ejecutar reset contra una DB desconocida;
- worker Kubernetes identificado como placeholder y excluido del criterio de “worker productivo sano”;
- el CronJob hotelero y el Job de migración están suspendidos por defecto; el patch de activación es explícito y separado; la imagen GHCR y el Secret son configurables;
- gate runtime 2026-08-05 — fixes exigidos por la validación de la imagen: `prepend_sys_path = .` en `backend/alembic.ini` (el console script `alembic` no encontraba `app`), `httpx` movido a dependencias core (el import de `app.main` lo requiere en runtime) y `JWT_SECRET` añadido al env del CronJob/Job de migración desde el Secret `viru-backend-runtime`;
- 2026-08-06 — artefactos de publicación/activación preparados sin ejecutar: `infra/k8s/runtime-secret.example.yaml` (plantilla de Secret con `DB_URL`/`JWT_SECRET`), overlay `infra/k8s/overlays/staging/kustomization.yaml` (único punto que des-suspende el CronJob con Mock) y runbook `docs/runbooks/hotels-runtime-activation.md`;
- no prometer delivery externo solo por tener `HotelAlertEvent` persistido.

## 4. Smoke tests hoteleros

### 4.1 Smoke local seguro

El smoke local debe usar H44, una DB aislada y cero red externa:

1. levantar API/frontend con perfil `local_fixture` o `local_demo`;
2. comprobar `GET /health` = 200 y `GET /ready` = 200;
3. autenticar un usuario sintético;
4. abrir `/hoteles`;
5. resolver una ciudad existente desde catálogo interno;
6. ejecutar búsqueda por fechas y ocupación del dataset;
7. seleccionar hotel y consultar rates/detalle/parity;
8. guardar favorito sin crear tracking;
9. crear tracking desde oferta contextualizada;
10. consultar snapshots/histórico y verificar procedencia demo;
11. crear alerta, ejecutar sweep Mock únicamente sobre DB aislada y consultar evento/inbox;
12. comprobar que un deeplink inválido no se convierte en href navegable;
13. repetir con User B y demostrar aislamiento;
14. probar `empty_provider`, `provider_timeout`, `rate_limited_429`, `stale_history` y `partial_batch` con adapters locales cuando H44 los implemente;
15. guardar dataset/profile/commit, requests, consola, screenshots y resultado.

El worker real requiere guardia de DB aislada y flags explícitas, por ejemplo `: "${AISOLATED_DB_URL:?Set an isolated demo DB URL}"` antes de asignar `DB_URL`, tal como exige H44. El runner `backend/scripts/hotel_mock_canary.py` cubre únicamente el tramo offline de Mock, persistencia y kill switch; hasta existir el seed/reset H44 y el flujo navegador completo, el smoke queda `partial`, no `passed` E2E completo.

### 4.2 Smoke de API mínimo actual

Comandos existentes y seguros si el servidor está levantado:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready
```

Estas probes solo prueban API viva. No sustituyen autenticación, búsqueda, tracking, alertas, inbox, provider, worker ni browser QA.

Nota del gate runtime 2026-08-05: `alembic upgrade head --sql` (modo offline) falla en la migración `0006` porque usa `sa.inspect` sobre un `MockConnection`; el Job de migración ejecuta modo **online**, donde se verificó `upgrade head` exit 0 hasta `0041_add_community_trending_snapshots` dentro de la imagen. Usar el modo online o una DB aislada para revisar migraciones.

### 4.3 Smoke frontend

Comandos definidos en `frontend/package.json` (el bloque se excluye del detector de referencias porque se ejecuta desde `frontend/`):

<!-- oma-docs:ignore-start -->
```bash
cd frontend
npm test -- tests/hotels-f56-audit.test.ts tests/hotels-signal-assessment.test.ts
npm run build
npm run lint
```
<!-- oma-docs:ignore-end -->

El script `npm test` existe; el selector de archivos debe confirmarse con `tsx` en la versión instalada. Los scripts de compilación y lint deben ejecutarse desde `frontend/`, no desde `docs/`. Si un script no puede ejecutarse por configuración local, el resultado es `blocked` con causa, no `passed`.

## 5. Canary de release frente a canary hotelero

### 5.1 Release canary genérico

El runbook existente propone:

1. 5% de tráfico;
2. observar p95, 5xx, auth y jobs durante 15 minutos;
3. 25%;
4. 50%;
5. 100% si no hay desviaciones.

En este repositorio, el workflow `infra/github/workflows/release.yml` solo imprime `Deploy canary 5% -> 25% -> 50% -> 100%` y `If SLI degrades, rollback immediately`. Por tanto, H45 lo considera **scaffolding/documentación**, no evidencia de tráfico dividido o rollback ejecutado.

Antes de declarar un release canary real se requiere demostrar el mecanismo de exposición, la métrica consultable, el owner, la ventana y la ruta de reversión. No inventar Istio, ingress, service mesh, traffic split, rollback automático o dashboards no presentes.

### 5.2 Hotel provider canary

Solo después de cerrar H43 P0/P1 y tener provider aprobado por H07/H08/H09/H37:

- provider comercial explícito y allowlisted;
- credencial efímera/rotatable, fuera de logs;
- `max_concurrency=1`, retries y timeout aprobados;
- budget pequeño y ledger correlacionado;
- dataset/consulta sintética permitida por términos del provider;
- una ventana definida y owner de guardia;
- métricas de request, outcome, 429, timeout, coste, rate usable, mapping y duplicados;
- kill switch probado antes de abrir tráfico;
- rollback de configuración sin borrar históricos.

Makcorps no debe considerarse aprobado por el hecho de que el adapter exista: H07/H43 registran riesgo de 429 y el provider sigue experimental/condicionado.

## 6. Criterios de promoción, pausa y bloqueo

### Promote

Promover solo si todos son verdaderos:

- release guard y build/test afectados pasan;
- health/readiness pasan en el artefacto desplegado;
- smoke hotelero H44 produce evidencia completa;
- no hay P0 abiertos en H39/H40/H41/H42/H43/H44;
- migración y rollback de datos son reversibles;
- no hay requests externas con perfil off;
- canary/provider tiene budget, owner, ventana y métricas;
- errores, latencia, empty/partial/stale, duplicados y soporte están dentro de umbrales aprobados;
- comunicación y changelog están preparados si cambia comportamiento visible.

### Pause

Pausar la promoción ante:

- cualquier 5xx/error de auth o regresión crítica del flujo;
- aumento de p95/latencia sin explicación;
- 429/timeout/coste fuera de budget;
- provider response invalid, mapping ambiguo o snapshots incompatibles;
- alertas duplicadas, cross-user o delivery no demostrable;
- divergencia entre API, worker, flags o job directo;
- consola, redaction o PII comprometida;
- migración sin backup/restore o rollback verificable;
- cualquier paso que dependa de infraestructura que solo está descrita, no desplegada.

### Block

Bloquear la release, aunque compile, si:

- el worker de producción sigue siendo placeholder, el CronJob está suspendido o no existe imagen/Secret aprobados, y la release promete tracking automático;
- el workflow canary solo imprime mensajes y se presenta como canary real;
- H44 no puede preparar dataset/DB aislada reproducible;
- `prod_off` no produce cero tráfico externo;
- el rollback borra snapshots, eventos o datos de usuario;
- no existe evidencia de browser para el cambio visible;
- se pretende activar Makcorps sin aprobación, budget o términos claros.

## 7. Rollback

### 7.1 Código/configuración

1. detener promoción y congelar cambios;
2. registrar commit, versión, config revision, correlation IDs y último estado sano;
3. activar `prod_off`: `HOTEL_FEATURE_ENABLED=false`, `HOTEL_SWEEP_ENABLED=false`, `HOTEL_GEOCODER_ENABLED=false` cuando el riesgo incluya geocoder;
4. detener/reiniciar supervisores que retengan flags antiguas;
5. volver al artefacto/imagen estable siguiendo el mecanismo real disponible;
6. comprobar `/health` y `/ready`;
7. ejecutar smoke mínimo y verificar cero nuevas llamadas externas;
8. conservar provider runs, snapshots, tracked offers, alert events y logs redacted;
9. comunicar impacto y abrir postmortem H42;
10. no reactivar sin owner, causa y gate firmado.

La existencia de `infra/k8s/*.yaml` no prueba que haya un cluster o comando de rollback disponible en este entorno. Documentar el mecanismo concreto solo cuando exista.

### 7.2 Datos/migraciones

- no hacer `drop_all`, truncado ni downgrade destructivo como respuesta rápida;
- seguir expand-and-contract y rollback H11;
- verificar counts, FKs, ownership, snapshots y eventos antes/después;
- restaurar backup o snapshot validado si el procedimiento aprobado lo permite;
- preservar evidencia de divergencias y filas rechazadas;
- clasificar cualquier pérdida/corrupción como SEV-0 según H42.

### 7.3 Rollback de provider

- detener únicamente el provider afectado si el resto es seguro;
- cambiar a `prod_off` si no se puede aislar;
- no sustituir error comercial por Mock silenciosamente en producción;
- conservar datos históricos con provenance/provider visible;
- no borrar aliases ni snapshots para “limpiar” el incidente.

## 8. Paquete de evidencia

Cada release/canary/smoke debe producir:

```text
release_id
commit_sha
owner
environment
profile
config_revision
dataset_id / fixture_version
provider_mode
migration_revision
health_result
readiness_result
backend_test_command / result
frontend_test_command / result
build / lint result
browser route / viewport / locale / theme
external_calls_expected / observed
request/outcome/error/latency summary
budget and cost summary
promotion stage
rollback decision
screenshots/traces/log references
known limitations
```

No incluir secretos, cookies, tokens, API keys, URLs firmadas ni raw PII. Los payloads de provider deben ser sanitizados y los artefactos deben tener retención/ownership definidos por H35/H38/H41/H42.

Clasificar el resultado como:

- `passed`: evidencia completa y gates satisfechos;
- `partial`: parte comprobada, pero falta evidencia bloqueante;
- `blocked`: no se pudo ejecutar o existe un P0;
- `failed`: se ejecutó y no cumplió.

## 9. Gates H45

### Gate Q — quality

- [ ] release guard revisado;
- [ ] tests backend afectados y suite hotelera relevante;
- [ ] desde `frontend/`, ejecutar los scripts de test, compilación y lint según alcance; el workflow actual ejecuta la compilación, pero no sustituye automáticamente test/lint hotelero;
- [ ] migraciones/compatibilidad revisadas;
- [ ] ningún artefacto o secreto en el release.

### Gate S — smoke

- [ ] `/health` y `/ready` 200;
- [ ] auth y `/hoteles` cargan;
- [ ] búsqueda, detalle, rates/parity y retorno funcionan;
- [ ] favorito no crea tracking;
- [ ] tracking, snapshot, alerta e inbox contextual funcionan;
- [ ] User A/B aislados;
- [ ] estados empty/partial/stale/error y deeplink inválido son honestos.

### Gate C — canary

- [ ] se distingue release canary de provider canary;
- [ ] mecanismo de tráfico/cohorte real y auditable;
- [ ] provider, budget, retries, concurrency, ventana y owner aprobados;
- [ ] métricas y thresholds consultables;
- [ ] kill switch probado antes de promoción;
- [ ] no se presenta un `echo` del workflow como despliegue real;
- [ ] la imagen se construye en CI sin secretos y el CronJob/Job de migración permanecen suspendidos hasta aprobar imagen, Secret, migración, provider y gates H43/H55.

### Gate R — rollback

- [ ] código/config rollback ejecutable en el entorno real;
- [ ] prod_off verificable y supervisores reiniciados;
- [ ] datos/migraciones reversibles sin borrado destructivo;
- [ ] snapshots/tracking/events conservados;
- [ ] smoke post-rollback y cero nuevas llamadas externas;
- [ ] comunicación/postmortem H42 preparado.

### Gate E — evidence

- [ ] paquete de evidencia completo y redacted;
- [ ] commit/config/dataset/provider identificados;
- [ ] resultados `passed/partial/blocked/failed` honestos;
- [ ] limitaciones y gaps abiertos listados;
- [ ] owner de decisión y fecha de expiración del canary registrados.

## 10. Decisión actual y handoff

**Decisión actual:** H45 es contrato listo para guiar una release, no autorización para lanzar tracking hotelero automático. Mantener `prod_off` para provider/sweep/geocoder externos hasta cerrar H43 y probar H44/H45.

H45 entrega a H46:

- criterios de release y límites de lo que puede prometer la UI;
- smoke principal y estados que deben estar cubiertos antes de optimizar activación;
- evidencia de browser que H46 debe respetar;
- rollback y soporte para cambios visibles.

H45 devuelve a fases anteriores:

- **H39:** P0 de cobertura y clasificación de `partial/blocked`;
- **H40:** evidencia visual/manual y cross-browser;
- **H41:** métricas, SLO, redaction y correlación;
- **H42:** incidentes, comunicación y postmortem;
- **H43:** flags, kill switches y provider canary;
- **H44:** dataset, seed/reset y fault profiles.

**Gate G:** no promover a usuarios reales hasta que Q/S/C/R/E estén aprobados con evidencia reproducible y el alcance visible esté comunicado.
