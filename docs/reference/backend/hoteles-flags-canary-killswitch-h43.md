# H43 — Flags, canary, rollout gradual y kill switches hoteleros

**Estado:** COMPLETA como contrato de rollout; implementación centralizada de flags, canary y kill switches pendiente  
**Fecha:** 2026-08-05  
**Área:** backend / infraestructura / QA  
**Fuente de verdad:** sí para la activación segura de hoteles  
**Depende de:** H09, H35, H37, H38, H41 y H42  
**Siguiente fase:** H44 — seed, demo y fallos reproducibles desde cero

> Este documento define cómo debe activarse y apagarse el dominio hotelero sin llamadas externas, coste inesperado, pérdida de datos ni ambigüedad entre API, worker y jobs manuales. No afirma que el sistema completo esté implementado: separa evidencia V1, contrato objetivo y gaps que deben cerrarse antes de un rollout comercial.

## 1. Objetivo y regla de seguridad

H43 responde a una pregunta operativa concreta: **¿quién puede activar qué capacidad hotelera, en qué entorno, durante qué canary y cómo se apaga de forma verificable?**

Reglas no negociables:

1. **Fail closed:** si falta una flag de seguridad, el valor efectivo es `false`; nunca se activa un provider comercial por una ausencia de configuración.
2. **Off means zero external calls:** con el dominio hotelero apagado no se realizan llamadas al provider, al geocoder externo ni al scheduler por causa hotelera. El delivery tiene un flag separado (`NOTIFICATION_WORKER_ENABLED`) y hoy el adapter de email es un stub; H43 no afirma que el master switch hotelero controle ese pipeline. Si en el futuro se entrega una alerta hotelera por un canal externo, deberá existir una decisión explícita de operación/delivery y su propio kill switch.
3. **No pérdida de datos al apagar:** un kill switch detiene ingestión/sweeps y nuevas escrituras de provider, pero conserva hoteles, aliases, snapshots, tracked offers, reglas y eventos históricos.
4. **Apagado verificable:** cambiar un `.env` no basta para procesos ya arrancados; hay que reiniciar o detener el proceso y comprobar logs, health/readiness y ausencia de requests.
5. **Una sola decisión efectiva:** API, worker y job directo deben resolver la misma configuración, con la misma precedencia y el mismo motivo de bloqueo.
6. **Provider comercial opt-in:** tener `MAKCORPS_API_KEY` no autoriza por sí solo el uso de Makcorps.
7. **Canary reversible:** cada aumento de exposición necesita métricas, ventana de observación, owner y criterio explícito de rollback.

## 2. Baseline comprobado en V1

### 2.1 Flags que existen hoy

| Variable | Default de plantilla | Lectura actual | Alcance real | Limitación |
|---|---:|---|---|---|
| `HOTEL_FEATURE_ENABLED` | `false` | `backend/app/hotels/ingestion.py` | Habilita provider-backed ingestion y resolución de provider | Si falta, el código actual puede auto-habilitar `mock` en `APP_ENV=local/development/dev`; no es fail-closed todavía |
| `HOTEL_SWEEP_ENABLED` | `false` | `backend/app/worker/hotels_sweep.py` | Bloquea el worker `app.worker.hotels_sweep` | No bloquea el job directo ni procesos ya arrancados |
| `HOTEL_PROVIDER` | `mock` | ingestion, worker y job | Selecciona `mock` o `makcorps` | La selección no sustituye a un permiso explícito por provider |
| `HOTEL_MOCK_FIXTURE_PATH` | vacío | adapter mock | Permite fixture del mock cuando se define | No convierte el modo mock en dry-run ni evita mutaciones de DB |
| `HOTEL_GEOCODER_ENABLED` | `true` | `backend/app/hotels/geocoder.py` | Permite fallback de `/area-resolve` a geocoder externo | Su default actual no es fail-closed y no está subordinado a `HOTEL_FEATURE_ENABLED` |
| `MAKCORPS_API_KEY` | vacío | adapter Makcorps | Habilita la credencial del adapter | No debe ser condición suficiente para activar tráfico |
| `NOTIFICATION_WORKER_ENABLED` | `false` | `backend/app/worker/notifications.py` | Controla el worker genérico de notificaciones | No es un kill switch hotelero y el email real sigue siendo stub |
| `HOTEL_PROVIDER_TIMEOUT_SECONDS` | `10` | provider/configuración | Limita espera del provider | No constituye por sí solo un circuit breaker ni un budget ledger |
| `HOTEL_PROVIDER_MAX_RETRIES` | `2` | provider/configuración | Limita reintentos del provider | Debe quedar subordinado a H09/H37 y al perfil activo |

La plantilla canónica es `backend/.env.example`. `backend/.env` está ignorado y puede tener valores locales distintos; nunca se toma como contrato ni se copian sus secretos a documentación, logs, fixtures o commits.

### 2.2 Entry points que deben estar alineados

| Entry point | Situación actual | Riesgo H43 |
|---|---|---|
| `app.worker.hotels_sweep` | Tiene `HOTEL_SWEEP_ENABLED` leído al importar el módulo y soporta `--once`/`--loop` | Un proceso arrancado conserva la configuración anterior hasta reinicio |
| `app.hotels.jobs.run_hotel_sweep` | Ejecuta `run_hotel_sweep` directamente | Actualmente puede saltarse `HOTEL_SWEEP_ENABLED`; el kill switch del worker no basta |
| API `POST /api/v1/hotels/ingest/mock` | Requiere autenticación y delega en ingestión | Debe respetar el master switch y no ser un bypass administrativo |
| API `GET /api/v1/hotels/area-resolve` | Consulta catálogo y, si no encuentra hoteles, puede llamar a `app.hotels.geocoder.geocode_city` | `prod_off` debe bloquear el fallback externo o exigir `HOTEL_GEOCODER_ENABLED=false` |
| API `GET /api/v1/hotels/area-search?use_provider=true` | Puede resolver provider y ejecutar `_fetch_and_store_provider_rates` con llamadas Makcorps | `use_provider=true` no puede saltarse la decisión efectiva, budget ni allowlist |
| API `GET /api/v1/hotels/*` | Permite leer datos existentes | Debe seguir disponible en modo `prod_off` cuando no implique provider externo |
| `run_hotel_sweep` en `hotels_service` | Orquesta ingestión, alertas y tracked offers | Es la barrera común recomendada para la futura decisión efectiva |

**Gate obligatorio:** ningún supervisor, cron, comando manual o endpoint puede invocar una operación de provider sin pasar por la misma resolución de flags y autorización de entorno.

## 3. Perfiles canónicos H43

Los perfiles son contrato objetivo. Mientras no exista un resolver único y una auditoría de configuración, se aplican como checklist manual; no se debe presentar el rollout como automatizado.

| Perfil | Propósito | Provider | Externo | Sweep | Estado |
|---|---|---|---|---|---|
| `local_demo` | UI y flujo feliz sin coste | `mock` | no | manual, sobre DB aislada | Permitido hoy con guardas; no es dry-run |
| `local_fixture` | Tests reproducibles con dataset fijo | `mock` + fixture estricta | no | manual/test | Objetivo H44; requiere fixture y DB efímera |
| `staging_canary` | Validar provider comercial con exposición mínima | provider aprobado por H08/H09 | sí, limitado | ventana explícita | Objetivo; no asumir activo |
| `prod_off` | Lectura segura y apagado de provider/sweep/geocoder | ninguno | no | no | Default recomendado hasta gates H43; exige `HOTEL_GEOCODER_ENABLED=false` |
| `prod_gradual` | Rollout comercial posterior al canary | provider aprobado | sí, limitado por presupuesto | ventana aprobada | Objetivo; requiere H09/H37/H41/H42 |

### Matriz mínima de configuración

| Control | `local_demo` | `local_fixture` | `staging_canary` | `prod_off` | `prod_gradual` |
|---|:---:|:---:|:---:|:---:|:---:|
| `HOTEL_FEATURE_ENABLED` | true | true | true | false | true |
| `HOTEL_GEOCODER_ENABLED` | según prueba | false | solo si el canary lo aprueba | false | solo si el canary lo aprueba |
| `HOTEL_SWEEP_ENABLED` | manual | test/manual | ventana aprobada | false | ventana aprobada |
| Provider comercial | false | false | solo provider aprobado | false | solo provider aprobado |
| Llamadas externas | 0 | 0 | budget/canary | 0 | budget/SLO |
| DB aislada/fixture | obligatoria para pruebas | obligatoria | staging dedicada | no aplica a lectura | controles de producción |
| Kill switch probado | sí | sí | antes de abrir tráfico | siempre disponible | siempre disponible |

`HOTEL_PROVIDER=mock` no equivale a “sin efectos”: el mock puede crear runs, snapshots, precios actuales y eventos en la DB configurada. Toda verificación Mock debe usar `AISOLATED_DB_URL` o un mecanismo equivalente de fixture/dry-run aprobado.

## 4. Precedencia de configuración efectiva

La implementación futura debe exponer una única función de resolución, por ejemplo `resolve_hotel_activation()`, usada por API, worker y job. La precedencia propuesta, de mayor a menor autoridad, es:

1. **Bloqueo de seguridad del entorno** (`prod_off`, secret leak, provider no aprobado, budget agotado, canary vencido).
2. **Kill switch global** (`HOTEL_FEATURE_ENABLED=false`).
3. **Kill switch de operación** (`HOTEL_SWEEP_ENABLED=false` para sweeps; no debe apagar lecturas locales).
4. **Allowlist de provider y operación** (`HOTEL_PROVIDER_<ID>_ENABLED`, `..._SWEEP_ENABLED`, cuando se implementen).
5. **Perfil explícito del entorno** (`local_demo`, `local_fixture`, `staging_canary`, `prod_off`, `prod_gradual`).
6. **Valores de entorno declarados** (`HOTEL_PROVIDER`, timeout, retries, budget).
7. **Defaults fail-closed**.

No se aceptan como autoridad:

- inferir activación porque `APP_ENV=local`;
- inferir permiso porque existe una API key;
- un valor congelado al importar un módulo si el supervisor cambió la configuración;
- flags legacy de otros dominios;
- una CLI que no pasa por la decisión efectiva común.

La resolución debe devolver, como mínimo: `enabled`, `profile`, `provider`, `operation`, `reason_code`, `config_revision` y `external_calls_allowed`. El `reason_code` debe aparecer en logs estructurados sin incluir secretos.

## 5. Kill switches

### 5.1 Niveles

| Nivel | Acción | Debe detener | No debe borrar |
|---|---|---|---|
| Global | `HOTEL_FEATURE_ENABLED=false` | ingestion, provider search/sweep y nuevas operaciones externas | hoteles, aliases, snapshots, tracking y eventos |
| Sweep | `HOTEL_SWEEP_ENABLED=false` | worker y scheduling de sweep | lecturas y datos ya persistidos |
| Provider | provider no permitido o `..._ENABLED=false` | tráfico al provider concreto | datos históricos de otros providers |
| Geocoder | `HOTEL_GEOCODER_ENABLED=false` o geocoder no permitido | fallback externo de resolución de área | catálogo y coordenadas ya persistidos |
| Operación | search, tracking, alerts o delivery aislados | solo la operación afectada | el resto del dominio |
| Seguridad/coste | breaker, budget agotado, credencial revocada | toda llamada externa relacionada | evidencia, runs y estado de recuperación |

### 5.2 Limitaciones actuales que bloquean declarar H43 implementada

1. `HOTEL_SWEEP_ENABLED=false` solo se aplica al worker `app.worker.hotels_sweep`; no bloquea automáticamente `app.hotels.jobs.run_hotel_sweep`.
2. `HOTEL_FEATURE_ENABLED` tiene fallback local para `mock` cuando falta la variable; debe eliminarse o quedar restringido a un perfil de test explícito.
3. `HOTEL_GEOCODER_ENABLED` puede permitir el fallback externo de `/area-resolve` aunque el master switch de ingestión esté off; debe quedar subordinado a la decisión efectiva de área/geocoder.
4. `/area-search?use_provider=true` puede invocar Makcorps desde una lectura; `use_provider` debe pasar por provider allowlist, budget y kill switch.
5. Las flags se leen en momentos distintos; cambiar el entorno no reconfigura procesos ya arrancados.
6. No existe un sistema central de cohortes, porcentaje, región, usuario interno, lease global ni auditoría de cambios.
7. No existe todavía una garantía automática de “cero requests” para cada operación de hoteles.
8. La API key de Makcorps y el provider comercial requieren aprobación, budget y canary; no se debe activar por conveniencia local.

## 6. Canary y rollout

### 6.1 Preflight obligatorio

Antes de cualquier `staging_canary` o `prod_gradual`:

- confirmar scope, provider y base URL aprobados por H07/H08/H09;
- confirmar credencial efímera o rotatable y que no aparece en logs;
- confirmar timeout, retries, rate limit, budget y concurrencia de H37;
- confirmar ownership/SSRF/PII de H38;
- confirmar correlación y redaction de H41;
- confirmar runbook y owner de incidente de H42;
- confirmar kill switch probado en el mismo artefacto y entorno;
- en `prod_off`, fijar explícitamente `HOTEL_FEATURE_ENABLED=false`, `HOTEL_SWEEP_ENABLED=false` y `HOTEL_GEOCODER_ENABLED=false`;
- ejecutar tests de flag-off con transporte bloqueado;
- registrar `config_revision`, provider, ventana, owner y ticket de cambio.

### 6.2 Rampas propuestas

La rampa debe ser una secuencia explícita, no una promesa de infraestructura existente:

1. **Fixture local:** mock + fixture + DB aislada, cero red externa.
2. **Staging apagado:** API y worker desplegados con `prod_off`, verificar lecturas y cero requests.
3. **Canary interno:** un usuario/tenant/escenario sintético, provider aprobado, `max_concurrency=1`, retries 0–1 y budget pequeño.
4. **Canary ampliado:** cohorte interna limitada o porcentaje si existe soporte real; observar provider, coste, latencia, errores, duplicados, alertas y delivery.
5. **Producción gradual:** solo con evidencia de H09/H37/H41/H42 y aprobación explícita.
6. **Promoción total:** únicamente tras cerrar los gaps P0/P1 y documentar el resultado del canary.

No se debe escribir “5% de tráfico” como capacidad actual de hoteles: el runbook genérico `runbook-canary-rollback.md` lo propone para releases, pero el dominio hotelero aún no tiene selector de cohortes documentado ni instrumentación completa.

### 6.3 Criterios de pausa y rollback

Pausar o apagar inmediatamente ante:

- cualquier request cuando el perfil declara `external_calls_allowed=false`;
- secreto, URL con credencial o PII en logs;
- 429/5xx/timeout por encima del umbral aprobado;
- coste o consumo sin ledger, presupuesto o correlación;
- duplicación de snapshots/runs o pérdida de idempotencia;
- cross-user event/inbox o fallo de ownership;
- alertas que se encolan pero no pueden probar delivery;
- divergencia entre API, worker y job directo;
- migración o deploy sin rollback verificable.

Rollback operativo:

1. detener la promoción;
2. aplicar el kill switch del nivel mínimo que contenga el riesgo y el global si la causa no está aislada;
3. detener/reiniciar supervisores para que no conserven flags antiguas;
4. comprobar `/health` y `/ready` donde estén disponibles;
5. confirmar que no hay llamadas externas nuevas y preservar runs/logs/evidencia;
6. volver a la configuración o imagen estable previa siguiendo H42;
7. no borrar snapshots ni hacer rollback destructivo de esquema sin procedimiento H11;
8. comunicar impacto, ventana y owner;
9. abrir postmortem y no reactivar sin gate firmado.

## 7. Contrato de pruebas

### P0 — bloqueo antes de canary

- ausencia de flags ⇒ provider y sweeps apagados;
- global off ⇒ cero llamadas externas desde API, worker y job directo;
- `prod_off` exige `HOTEL_GEOCODER_ENABLED=false` ⇒ `/area-resolve` no llama al geocoder y conserva el fallback interno;
- `prod_off` + `use_provider=true` ⇒ `/area-search` no llama a Makcorps ni persiste rates externos;
- sweep off ⇒ worker y job supervisado no ejecutan trabajo;
- API key presente con provider no aprobado ⇒ cero llamadas;
- valor de provider desconocido o combinación contradictoria ⇒ bloqueo fail-closed;
- excepción del provider ⇒ no filtra secreto/query en log;
- kill switch durante una ventana ⇒ no se inicia el siguiente ciclo;
- datos históricos siguen legibles tras apagar;
- `NOTIFICATION_WORKER_ENABLED` se prueba por separado: H43 no lo confunde con el kill switch hotelero.

### P1 — antes de staging canary

- misma decisión efectiva en API/worker/job;
- perfil inválido o combinación contradictoria ⇒ error fail-closed;
- cambio de config exige restart/reload explícito y deja evidencia;
- canary no supera budget, concurrencia, retries ni ventana;
- rollback conserva runs, snapshots, tracking y eventos;
- provider alternativo no recibe tráfico cuando está off;
- smoke de `/health` y `/ready` no declara sano un worker hotelero inexistente.

### P2 — endurecimiento

- auditoría de cambios de configuración;
- cohortes deterministas por usuario/tenant/región;
- métricas H41 para activación, requests, coste, sweep, delivery y rollback;
- dashboard y alertas con SLO aprobado por H09/H43;
- prueba periódica del kill switch y simulacro H42;
- documentación de compatibilidad para clientes durante migraciones.

Tests de referencia actuales: `backend/tests/unit/test_hotels_ingestion.py`, `backend/tests/unit/test_hotels_sweep.py`, `backend/tests/unit/test_hotels_sweep_worker.py` y `backend/tests/integration/test_hotels_api_flow.py`. Deben ampliarse para probar la decisión unificada y cero red, no solo el happy path.

## 8. Gates de cierre H43

### Gate F — flags

- [ ] nombres, defaults y tipos están en una fuente ejecutable;
- [ ] ausencia = off para todos los providers comerciales;
- [ ] no existe fallback accidental por entorno local;
- [ ] cada operación declara si requiere provider externo.

### Gate K — kill switch

- [ ] global, sweep, provider y operación tienen alcance definido;
- [ ] worker, API y job directo obedecen la misma decisión;
- [ ] restart/reload está incluido en el procedimiento;
- [ ] el apagado no elimina datos.

### Gate C — canary

- [ ] provider, budget, concurrencia, retries y ventana aprobados;
- [ ] cohorte o mecanismo de exposición es real y auditable;
- [ ] no se confunde el canary genérico de release con canary hotelero;
- [ ] promoción y rollback tienen owner y evidencia.

### Gate Z — cero llamadas externas

- [ ] transporte bloqueado en tests para Makcorps y geocoder;
- [ ] `/area-resolve` y `/area-search?use_provider=true` tienen pruebas explícitas con `prod_off`;
- [ ] evidencia de cero requests con flags off;
- [ ] ausencia de key no es la única protección;
- [ ] provider desconocido y allowlist ausente fallan closed;
- [ ] `/ingest/mock` bloqueado no muta la DB;
- [ ] Mock usa DB aislada y no se presenta como dry-run;
- [ ] delivery queda fuera del master switch hasta que exista un contrato de operación/delivery hotelero.

### Gate R — recuperación

- [ ] H42 cubre la severidad y comunicación;
- [ ] H41 cubre correlación, redaction y métricas;
- [ ] H09/H37 cubren leases, retries, budget y provider health;
- [ ] H11 cubre rollback de migración y retención;
- [ ] el gate queda firmado antes de `prod_gradual`.

## 9. Handoff

H43 entrega a H44:

- perfiles `local_demo` y `local_fixture` para datasets reproducibles;
- requisitos de fixture, DB aislada y fallos 429/timeout/vacío;
- tests de zero external calls;
- la obligación de no usar datos sintéticos sin etiqueta.

H43 devuelve a fases anteriores los gaps que bloquean activación:

- **H09:** gateway/scheduler/leases y kill switch de ejecución;
- **H35:** readiness del dominio y contrato de estado;
- **H37:** budget, rate limits, retries, locks y coste;
- **H38:** secretos, SSRF, BOLA/IDOR y PII;
- **H41:** métricas, correlación y redaction;
- **H42:** incidentes, recovery y rollback.

**Decisión de rollout actual:** mantener `prod_off` como perfil seguro. No se declara `staging_canary` ni `prod_gradual` activos hasta que los gates P0/P1 estén implementados y verificados.
