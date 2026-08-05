# H42 — Runbook de incidentes y recovery hotelero

**Estado:** COMPLETO como contrato operativo; simulacros, owners de guardia y controles H09/H41/H43 pendientes  
**Fecha:** 2026-08-05  
**Área:** operación / soporte / backend / worker / frontend / seguridad / datos  
**Fuente de verdad:** sí para el procedimiento de respuesta a incidentes de `/hoteles`; los comandos y controles marcados como futuros no existen todavía  
**Depende de:** H09 gateway/sweeps, H28 delivery, H35 legal/privacy/deeplinks, H37 coste/límites, H38 seguridad, H41 observabilidad  
**Relacionado con:** `docs/runbooks/hotels-sweeps.md`, `runbook-canary-rollback.md`, `runbook-provider-degraded.md`, `runbook-db-retention.md`, `runbook-notification-worker.md`, H43 flags/canary y H45 release

> Este runbook permite responder sin depender de la IA que construyó `/hoteles`. No convierte un procedimiento documentado en una capacidad ya desplegada: el worker hotelero actual es V1/manual/Mock, `/health` y `/ready` son probes básicos, el deployment Kubernetes del worker contiene un placeholder y los estados `partial/skipped/rate_limited` de H09 siguen pendientes de implementación.

**Limitación de kill switch:** `HOTEL_SWEEP_ENABLED=false` solo bloquea el entrypoint `app.worker.hotels_sweep`; el job directo `app.hotels.jobs.run_hotel_sweep` puede seguir escribiendo si alguien lo ejecuta. Antes de declarar un provider/sweep detenido, identificar y detener todos los supervisores y entrypoints activos.

---

## 1. Reglas de seguridad antes de tocar nada

1. **Preservar evidencia antes de reiniciar, borrar o migrar.** Guardar timestamp UTC, entorno, release, correlation/request/run ID, provider, síntoma y comandos ejecutados.
2. **No ejecutar SQL destructivo** (`DROP`, `DELETE` o `UPDATE` sin `WHERE`) en producción. Hacer primero dry-run, snapshot/backup verificado y aprobación del owner de datos.
3. **No reintentar a ciegas.** Un timeout, `429`, `invalid_response` o `unavailable` no equivale a `empty`, `sold_out` ni a precio cero.
4. **No activar un provider comercial para “probar”.** H07/H08/H37 mantienen el budget automático en cero hasta que exista plan, cuota, canary y kill switch aprobados.
5. **No saltarse ownership, idempotencia, locks o leases.** Si el control todavía no existe, detener el alcance y marcar el incidente como riesgo de diseño H09/H38, no improvisar una corrección manual.
6. **No pegar secretos en tickets o canales.** Redactar API keys, Authorization, cookies, URLs firmadas, emails, tokens, payloads de ocupación y query strings.
7. **No confundir caída del worker con “sin cambios”.** El producto debe mostrar freshness/stale/unavailable cuando falte una observación.
8. **No borrar snapshots históricos como kill switch.** Pausar la causa; conservar datos y procedencia para investigar.
9. **Si hay sospecha de secreto expuesto, contener primero:** detener el sink afectado, revocar/rotar la credencial según H35/H38 y conservar solo evidencia redacted.
10. **Si una instrucción aquí contradice la infraestructura real, parar y registrar la discrepancia.** Este documento no autoriza comandos de producción no aprobados.

---

## 2. Severidad y activación

| Severidad | Cuándo usarla | Respuesta inicial | Escalado |
|---|---|---|---|
| **SEV-0 seguridad/datos** | secreto o PII expuesto, BOLA/IDOR confirmado, SSRF, corrupción o borrado indebido | contener inmediatamente; detener sinks/provider/worker afectado; preservar evidencia | Security + Backend + owner de datos + Legal si aplica |
| **SEV-1 crítico** | `/hoteles` inutilizable para la mayoría, provider activo con coste descontrolado, snapshots/alertas corruptos, delivery global detenido | declarar incidente, activar kill switch seguro, comprobar rollback | Incident Commander + Backend + Infra + Support |
| **SEV-2 mayor** | sweeps detenidos/duplicados, provider degradado sostenido, backlog de alertas, stale generalizado, errores API elevados | mitigar en 15 min, pausar superficie afectada y abrir diagnóstico | Backend/Infra + Support |
| **SEV-3 menor** | un provider parcial, una ruta UI degradada, deeplink individual inválido, logging incompleto sin impacto de datos | registrar ticket, workaround y seguimiento | owner de la fase |

### Criterios que elevan la severidad

Elevar un nivel si hay:

- impacto sobre más de un usuario o más de un provider;
- pérdida de ownership o posibilidad de leer eventos ajenos;
- llamadas externas repetidas sin budget o `429` sostenidos;
- snapshots nuevos que puedan disparar alertas falsas;
- ausencia de evidencia para determinar qué datos fueron live/stale/mock;
- rollback no verificable o migración con estado ambiguo.

### Roles mínimos

- **Incident Commander:** decide severidad, alcance, stop/rollback y cierre.
- **Technical owner:** ejecuta diagnóstico y cambios reversibles.
- **Data/Security owner:** autoriza acciones sobre DB, secretos, PII y migraciones.
- **Support/Comms:** prepara copy de estado y respuestas de usuario.
- **Scribe:** mantiene timeline, IDs, comandos y decisiones.

En el estado actual estos roles no están automatizados ni asignados por guardia; H43/H45 deben convertirlos en ownership de despliegue.

---

## 3. Ciclo universal de respuesta

### 3.1. Detectar y abrir

Registrar en el ticket/canal interno:

```text
incident_id: H42-YYYYMMDD-<opaque>
started_at_utc:
environment: local | staging | production
release_or_commit:
severity:
symptom:
first_observed_by:
route/provider/worker/channel:
correlation_id/request_id/provider_run_id: redacted or opaque
```

Fuentes actuales que sí existen:

- `/health` y `/ready` del backend;
- logs stdout/fichero configurados por `app.core.logging`;
- logs del worker `app.worker.hotels_sweep` y del job `app.hotels.jobs.run_hotel_sweep`;
- filas `HotelProviderRun`, `HotelRateSnapshot`, `HotelAlertEvent`, `HotelTrackedOffer` y estados de inbox;
- `scripts/viru-local-status.ps1` para estado local de puertos 3000/8000;
- `docs/qa/hotels-pending-closeout.md` y `docs/runbooks/hotels-sweeps.md` para baseline V1.

No presentarlos como métricas centralizadas: H41 documenta que dashboards, trazas y SLO persistentes aún están pendientes.

### 3.2. Preservar evidencia

Antes de reiniciar:

1. anotar UTC y release;
2. capturar `/health` y `/ready` sin incluir headers secretos;
3. guardar las últimas líneas de logs del backend/worker en un artefacto con acceso restringido;
4. consultar solo conteos/IDs opacos de los últimos runs, snapshots y eventos;
5. guardar configuración efectiva **sin valores secretos**: provider, flags booleanas, timeout, retries, intervalo;
6. capturar error/correlation ID y outcome normalizado;
7. guardar si el frontend vio `empty`, `partial`, `stale`, `unavailable`, `auth_required` o `error`;
8. registrar si hubo llamada externa, coste/budget observado y número de intentos.

Nunca copiar `MAKCORPS_API_KEY`, JWT, `DATABASE_URL` completa, cookies ni URLs con query params a la evidencia.

### 3.3. Diagnosticar por frontera

Clasificar el fallo en una sola primera frontera, sin asumir que todas fallan:

```text
Browser/UI → API/auth → DB → gateway/provider → worker/scheduler
          → snapshot/tracking → rule evaluator → delivery/inbox
```

Preguntas mínimas:

- ¿Falla `/hoteles` o también `/health`/`/ready`?
- ¿Falla solo el provider o también las lecturas históricas?
- ¿Hay un `HotelProviderRun` nuevo? ¿Está `running`, `completed`, `failed`?
- ¿El timestamp de observación es reciente o solo se actualizó la UI?
- ¿Se generaron snapshots/alert events duplicados?
- ¿La alerta está encolada, entregada, fallida o solo persistida?
- ¿El fallo afecta a una cuenta, hotel, provider, mercado o a todos?
- ¿Hay evidencia de ownership cruzado o secreto expuesto?

### 3.4. Contener antes de reparar

Preferencia de menor blast radius:

1. detener nuevas llamadas del provider afectado;
2. desactivar el worker hotelero, no necesariamente el API completo;
3. pausar solo el canal de delivery afectado;
4. servir histórico/cache elegible con freshness visible;
5. activar banner/estado degradado honesto;
6. rollback de release o migración si la causa es reciente;
7. bloquear toda la superficie solo ante corrupción, fuga o riesgo de coste/datos.

En V1, `HOTEL_SWEEP_ENABLED=false` solo gobierna el proceso `app.worker.hotels_sweep`; no detiene por sí mismo un proceso ya iniciado ni modifica `use_provider` en requests. Verificar el proceso real y no confiar solo en editar `.env`.

### 3.5. Recuperar y verificar

No cerrar porque el proceso arranque. Verificar:

- `/health` responde `200` y `/ready` responde `200`;
- no aparecen nuevos errores en la ventana de observación;
- el worker está detenido/activo exactamente una vez según el plan;
- una pasada Mock controlada no genera duplicados;
- provider comercial permanece apagado hasta canary aprobado;
- no se crean snapshots desde error/timeout/429;
- alertas/inbox conservan ownership y estado correcto;
- el frontend muestra freshness y siguiente acción;
- las métricas/eventos de H41, cuando existan, muestran recovery y no solo ausencia de errores.

### 3.6. Cerrar y aprender

El cierre debe incluir:

```text
resolved_at_utc:
final_severity:
impact_start/end:
users_or_scope_affected:
root_cause:
trigger:
containment:
recovery_or_rollback:
verification_evidence:
remaining_risk:
follow_up_owner/due_date:
```

Para SEV-0/SEV-1, redactar postmortem sin culpas en 48 horas o según la política vigente. H42 exige acciones con owner y fecha, no solo “vigilar”.

---

## 4. Playbook A — Provider degradado, 429, timeout o respuesta inválida

### Síntomas

- aumentan `makcorps_request_failed`, timeouts, 429 o warnings de provider;
- búsqueda devuelve `empty` cuando el provider puede estar caído;
- `HotelProviderRun` pasa a `failed` o no se actualiza;
- precios aparecen stale, parciales o inconsistentes;
- coste/requests supera el canary o budget autorizado.

### Diagnóstico actual

1. comprobar `/health` y `/ready`;
2. identificar `provider` y `provider_run_id` en logs/DB;
3. distinguir `empty` válido de `timeout`, `429`, `unavailable` o `invalid_response`;
4. confirmar `HOTEL_PROVIDER_TIMEOUT_SECONDS` y `HOTEL_PROVIDER_MAX_RETRIES` sin revelar secretos;
5. comprobar si la API key está configurada sin imprimirla;
6. verificar si el adapter está usando alias `provider_hotel_id` o el ID interno; H07/H09 señalan este riesgo;
7. comprobar si el error se repite por una operación concreta (`mapping`, `city`, `hotel`, `revalidation`);
8. guardar error sanitizado y no el payload crudo.

### Contención

- no lanzar reintentos manuales repetidos;
- mantener `HOTEL_SWEEP_ENABLED=false` para impedir nuevas pasadas automáticas;
- si el proceso ya está corriendo, detenerlo por el mecanismo de supervisor del entorno;
- no activar otro provider como fallback sin H08/H35/H37/H41 aprobados;
- dejar disponibles snapshots históricos solo con estado `stale`/edad visible;
- deshabilitar deeplinks del provider si su validez es dudosa;
- si hay API key en logs/URLs, pasar a SEV-0 y rotar.

El runbook genérico `runbook-provider-degraded.md` menciona circuit breaker de vuelos; no se debe afirmar que exista el mismo breaker hotelero.

### Recuperación

1. corregir configuración/credencial o esperar cooldown del provider;
2. validar primero con fixture Mock aislado, sin salir a red. La pasada escribe `HotelProviderRun`, snapshots, `current_price` y potencialmente `HotelAlertEvent`: usar una `DB_URL` de staging/fixture separada, backup verificado o rollback aprobado; no ejecutarla contra producción por defecto;
3. ejecutar una única pasada controlada en esa DB aislada:

```bash
cd backend
# Define AISOLATED_DB_URL antes; el comando falla si falta.
DB_URL="${AISOLATED_DB_URL:?define una DB aislada}" HOTEL_SWEEP_ENABLED=true python -m app.worker.hotels_sweep --once --provider mock
```

4. verificar `HotelProviderRun`, snapshots y ausencia de duplicados;
5. reabrir el provider real solo mediante canary H09/H43, con budget explícito;
6. observar outcomes y coste antes de activar loop.

### No hacer

- no traducir 429/timeout a “sin disponibilidad”;
- no cambiar `MAKCORPS_BASE_URL` para apuntar a un host de prueba desde un input de usuario;
- no ejecutar `--loop` como prueba de recuperación;
- no borrar históricos para ocultar stale.

---

## 5. Playbook B — Worker parado, duplicado, bloqueado o ventana perdida

### Síntomas

- no hay `HotelProviderRun` nuevo en la ventana esperada;
- existen dos runs solapados o snapshots duplicados;
- el worker consume CPU/requests sin terminar;
- una pasada permanece `running` sin finalizar;
- la UI sigue mostrando datos como si el sweep hubiera ocurrido.

### Hechos actuales

- el API no arranca el scheduler hotelero;
- `HOTEL_SWEEP_ENABLED=false` es default seguro;
- `--once` y `--loop` existen;
- no existe lease distribuido hotelero ni estado `partial/skipped` completo;
- `infra/k8s/worker.yaml` contiene `python -c "print('worker placeholder')"`, no el worker hotelero productivo.

### Diagnóstico

1. comprobar proceso y logs del supervisor real;
2. en local, usar:

```powershell
scripts/viru-local-status.ps1
```

3. consultar últimos runs:

```sql
SELECT id, provider, status, items_processed, error_message, started_at, finished_at
FROM hotel_provider_run
ORDER BY started_at DESC
LIMIT 10;
```

4. comprobar si hay más de un `--loop`/cron/systemd ejecutando la misma operación;
5. comparar `provider_run_id`, timestamps y conteos de snapshots;
6. no marcar un run atascado como `completed` manualmente sin evidencia de qué unidades terminaron.

### Contención

- detener el worker duplicado o el proceso runaway usando el supervisor del entorno;
- localmente, si se confirma que solo son los procesos de Viru, puede usarse:

```powershell
scripts/viru-local-stop.ps1
```

Este script detiene los listeners de 3000/8000 y **no sustituye** a un stop seguro del worker de producción.

- mantener el provider real apagado mientras se resuelve el solapamiento;
- conservar los runs y snapshots para reconciliación;
- no borrar filas `running` sin decidir primero si representan trabajo potencialmente activo.

### Recuperación

1. comprobar que solo existe una instancia autorizada;
2. ejecutar Mock `--once`;
3. revisar run, snapshots, alert events y tracking;
4. actualizar el estado de freshness/UI como stale si se perdió la ventana;
5. abrir H09/H41 gap si la causa fue ausencia de lease, budget u outcome;
6. no habilitar `--loop` hasta que H09/H43 prueben dedupe y recovery.

---

## 6. Playbook C — Alertas, delivery o inbox atrasado

### Síntomas

- `HotelAlertEvent` existe pero no aparece en inbox;
- inbox muestra un evento de otro usuario;
- notificaciones quedan `queued`, `failed` o se reintentan indefinidamente;
- alertas duplicadas por cada sweep;
- el usuario recibe alerta sin snapshot comparable.

### Diagnóstico

1. separar creación de evento, ownership, estado read/unread y delivery;
2. comprobar `rule_id`, `tracked_offer_id`, `provider_run_id`, snapshot base/current y dedupe key;
3. verificar que `HotelAlertEvent` no se esté resolviendo solo por `hotel_id`;
4. comprobar dos cuentas con el mismo hotel en fixture seguro, nunca con datos reales en un ticket;
5. revisar el worker de notificaciones solo si el canal afectado corresponde a él:

```bash
cd backend
python -m app.worker.notifications --once
```

6. no inferir “entregado” porque exista una fila en DB; H28 exige estados de delivery separados. `python -m app.worker.notifications --once` procesa el pipeline genérico y el email real sigue siendo stub según su runbook: solo puede declararse delivery hotelero cuando se verifique la fuente hotelera, el estado terminal y el canal real.

### Contención

- pausar el canal fallido, no borrar eventos;
- detener reintentos si hay storm o si el payload contiene secretos;
- mantener inbox privado solo para fuentes con ownership verificable;
- poner en cuarentena eventos legacy sin relación determinista;
- comunicar “alerta en revisión” en vez de afirmar entrega.

### Recuperación

1. corregir ownership/dedupe antes de reemitir;
2. ejecutar una pasada de notificaciones con batch pequeño en una base/entorno seguro, sin asumir que el worker genérico prueba delivery externo;
3. comprobar `queued → terminal` y que no se duplica el evento;
4. validar deep link con reautorización y estado not-found prudente;
5. reabrir canal gradualmente y revisar backlog/failed/retry;
6. registrar como P0/P1 H38/H41 si hubo fuga o si no se pudo determinar el alcance.

---

## 7. Playbook D — Snapshots, tracking o datos hoteleros sospechosos

### Síntomas

- precios cero/negativos, moneda incorrecta o fechas cruzadas;
- snapshots duplicados o vinculados al hotel equivocado;
- `current_price` cambia tras timeout/429;
- `HotelProviderRun` dice `completed` aunque parte del trabajo falló;
- tracking o alertas mezclan ofertas, usuarios o condiciones.

### Diagnóstico seguro

- detener nuevas escrituras del provider/sweep;
- consultar conteos y muestras mínimas por `provider_run_id`, sin exportar PII;
- comparar `HotelProperty.id` con `provider_hotel_id`/alias;
- verificar fechas, guests, currency, room, meal y cancellation;
- revisar si el snapshot tiene `tracked_offer_id` y ownership relacional;
- comparar con fixture conocido y migración/schema version;
- preservar DB/logs y no “limpiar” antes de tener un plan.

### Contención y reparación

- marcar superficie como stale/unavailable si no se puede probar elegibilidad;
- pausar alert evaluation para datos afectados;
- no ejecutar `UPDATE` masivo manual;
- preparar script idempotente de cuarentena/backfill con dry-run, revisión DB y backup verificado;
- si hay migración reciente, detener promoción y usar rollback documentado, no downgrade improvisado;
- revalidar con H11/H23/H26/H38 antes de reabrir tracking.

### Verificación

- cero snapshots nuevos desde outcomes inválidos;
- no quedan relaciones privadas legibles por otra cuenta;
- reglas no disparan por datos cuarentenados;
- históricos válidos siguen disponibles con procedencia;
- una fixture de dos usuarios y dos ofertas pasa H39/H41.

---

## 8. Playbook E — Retención, migración o borrado accidental

### Retención

El runbook existente `runbook-db-retention.md` sí tiene `--dry-run`, mínimos, lock `flock`, logs JSONL, archivo de alerta y rollback operativo. Para cualquier tabla hotelera nueva:

1. ejecutar primero:

```bash
cd backend
ops/db-retention/run-db-retention.sh --dry-run
```

2. revisar candidatos, tablas y ventana;
3. verificar backup/snapshot según el entorno;
4. aplicar solo con owner DB;
5. revisar `backend/logs/db-retention.log` y ausencia/presencia de `backend/logs/alerts/db-retention-failure.json`;
6. si hay anomalía, pausar timer/cron y volver a dry-run según el runbook existente.

La política actual no demuestra que todas las tablas hoteleras estén incluidas ni que exportación/retención H35 esté cerrada.

### Migración

Ante fallo de Alembic/backfill:

- detener nuevas escrituras de la fase afectada;
- registrar revisión, versión de esquema y batch;
- no borrar columnas legacy durante expand-and-contract;
- comprobar FKs/huérfanos y divergencia dual-read/write;
- ejecutar rollback solo si H11 define que es reversible;
- restaurar desde backup si la operación fue destructiva;
- repetir dry-run y tests antes de reanudar.

No existe un comando universal de rollback de datos en este runbook: depende del entorno y de H11.

---

## 9. Playbook F — Seguridad, secreto, SSRF o ownership

Activar **SEV-0** si aparece cualquiera de estos indicios:

- API key en logs, URL, trace, error o ticket;
- evento hotelero visible para la cuenta incorrecta;
- `tracked_offer_id`/`rule_id` cruzado entre usuarios;
- geocoder/provider dirigido a loopback, RFC1918, metadata o host no permitido;
- deeplink/open redirect sin allowlist;
- raw provider payload con PII o token.

### Primeros 15 minutos

1. detener el sink o worker que sigue generando exposición;
2. desactivar provider/sweep/canal afectado;
3. conservar evidencia redacted y anotar ventana de exposición;
4. revocar/rotar credenciales si un secreto pudo salir del proceso;
5. bloquear el destino/egress sospechoso según infraestructura disponible;
6. no borrar logs que puedan probar el alcance, pero restringir su acceso;
7. revisar H35/H38 y avisar a Security/Legal/owner de datos;
8. no reabrir hasta tener prueba de contención y test adversarial.

### Verificación de cierre

- secreto revocado y no reutilizable;
- sinks redacted y logs posteriores sin exposición;
- dos usuarios no pueden leer/modificar recursos cruzados;
- provider/geocoder solo alcanza destinos allowlisted;
- deeplink vuelve a validar y usa disclosure;
- se documenta si hubo notificación legal o de usuarios.

---

## 10. Playbook G — API/frontend caído, OOM o release defectuoso

### Diagnóstico

En el backend:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready
```

En local Windows:

```powershell
scripts/viru-local-status.ps1
```

En Kubernetes, los manifests existentes usan `/health` y `/ready` para backend; el manifest de worker actual es placeholder y no debe tomarse como prueba de worker hotelero.

Comprobar:

- release/commit y cambios recientes;
- errores 5xx, auth, DB y frontend hydration/fetch;
- memoria/OOMKilled y reinicios;
- si el API funciona pero el worker no;
- si el provider es la única dependencia degradada.

### Contención

- si el problema es release reciente, detener promoción y seguir `runbook-canary-rollback.md`;
- desactivar flags de la release, provider/sweep y delivery si son la causa;
- para OOM, reducir concurrencia/fan-out y seguir `runbook-oom.md`;
- no subir límites de memoria sin conservar evidencia y revisar causa;
- mantener `/health`/`/ready` como probes, no como prueba de funcionalidad hotelera.

### Recuperación

1. volver a la última versión estable aprobada;
2. validar `/health` y `/ready`;
3. ejecutar smoke de búsqueda Mock y lectura de históricos;
4. comprobar que no se habilitó el provider real por accidente;
5. revisar snapshots/alertas/inbox y errores de consola;
6. promover gradualmente solo con H41/H43/H45.

---

## 11. Comunicación y soporte

### Mensajes internos

Cada actualización debe decir:

```text
Severidad / impacto / superficie afectada
Qué sabemos y qué no sabemos
Contención aplicada
Si los precios son live, stale, mock o unavailable
Siguiente verificación y hora de la próxima actualización
```

### Copy de soporte

| Caso | Respuesta segura |
|---|---|
| precio cambió | “El precio observado puede cambiar en el partner; estamos comprobando la última captura y sus condiciones.” |
| alerta no recibida | “La regla puede estar guardada aunque la entrega esté pendiente; revisamos el estado del canal.” |
| no hay resultados | “No podemos confirmar disponibilidad ahora; prueba otra fecha/zona o vuelve cuando el proveedor esté disponible.” |
| deeplink roto | “El enlace externo ya no es válido o ha cambiado; no vamos a sustituirlo por un destino no verificado.” |
| hotel duplicado | “Estamos revisando la identidad del hotel; no crees otro seguimiento hasta confirmar la oferta.” |
| datos antiguos | “Esta información es histórica/stale y no confirma disponibilidad actual.” |

No prometer reembolso, disponibilidad, precio final ni frecuencia diaria si H09/H19/H28 no lo garantizan.

### Datos que Support no debe pedir

- API keys, JWT, cookies, contraseñas;
- query strings completas o URLs firmadas;
- export completo de la cuenta;
- datos de otros usuarios;
- payload crudo de provider.

Usar correlation/request/support code opaco y mínimo.

---

## 12. Simulacros y evidencia de cierre

H42 no se considera implementada solo por existir este documento. Deben ejecutarse simulacros controlados, primero con Mock/fixtures:

| Simulacro | Resultado esperado |
|---|---|
| provider Mock success/empty | run verificable, sin duplicados, copy correcto |
| provider timeout/429 fixture | no `sold_out`, cooldown/estado explícito, recovery reversible |
| worker stopped/missed window | stale/skipped visible; no timestamp falso |
| dos workers/duplicado | un solo owner o gap H09 claramente bloqueante |
| alert delivery failed/retry | evento no se pierde ni se marca sent automáticamente |
| dos usuarios mismo hotel | ningún evento privado cruzado |
| snapshot inválido | cuarentena sin alertas falsas |
| retention dry-run | cero borrado no autorizado y alerta verificable |
| secret/SSRF fixture | contención, redaction y no egress peligroso |
| release rollback | `/health`, `/ready`, smoke Mock y flags correctos |

### Paquete de evidencia

- comando exacto y entorno;
- fixture/payload sanitizado;
- timestamp y versión;
- logs redacted;
- consultas de conteo, nunca dump privado;
- outcome antes/después;
- owner y aprobación;
- limitaciones y gaps abiertos;
- fecha de caducidad del simulacro.

### Gate H42

H42 podrá considerarse operativamente cerrada cuando:

1. otra persona ejecute los playbooks sin asistencia de la IA;
2. cada incidente común tenga señal, severidad, contención, recuperación y verificación;
3. los comandos citados existan y los futuros estén marcados;
4. exista al menos un simulacro de provider, worker, delivery, datos y seguridad;
5. H41 aporte correlación/evidencia y H43 aporte flags/kill switch;
6. no haya comandos destructivos sin dry-run/backup/owner;
7. soporte tenga copy honesto para precio, stale, alerta y deeplink;
8. cada gap residual tenga owner y siguiente fase.

**Resultado H42:** runbook contractual aprobado. La operación hotelera productiva, los leases distribuidos, los SLO, el delivery real y el worker Kubernetes siguen condicionados a H09/H28/H41/H43/H45.
