# Persistencia diaria de tendencias comunitarias e inbox consistente — Mega Plan de Implementación

> **Para el agente ejecutor:** implementar este plan tarea por tarea, manteniendo el orden de dependencias y ejecutando las verificaciones indicadas antes de avanzar.

**Objetivo:** sustituir la caché en memoria de tendencias comunitarias por snapshots diarios persistentes, integrar esas señales correctamente en el inbox privado y conservar compatibilidad con SQLite, PostgreSQL, los estados de lectura existentes y las demás fuentes de notificaciones.

**Arquitectura:** persistir snapshots globales e inmutables de las rutas que están en tendencia. El inbox no guardará una copia por usuario: resolverá la visibilidad mediante un `JOIN` privado con las `FlightWatch` activas del usuario. `UserNotificationState` seguirá almacenando el estado `read/unread` por usuario y fuente, utilizando un identificador determinista por día y ruta. No se reutilizará `NotificationEvent`, porque las tendencias comunitarias no pertenecen a una `AlertRule`.

**Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic, SQLite local, PostgreSQL objetivo, pytest, Ruff, mypy cuando esté disponible, logs JSON existentes y worker `app.worker.notifications`.

**Estado:** implementado y verificado
**Fecha:** 2026-08-04
**Área:** backend, base de datos, notificaciones, comunidad, QA
**Fuente de verdad:** no; este documento conserva el diseño, rollout y evidencia de la implementación. Los contratos vivos y runbooks son la fuente operativa actual.

> Las fases y tareas de las secciones siguientes son el plan original y su registro de decisiones. No representan trabajo pendiente; el estado final se resume en la sección de aceptación marcada como completada.

---

## 0. Resumen ejecutivo

### Problema actual

`backend/app/services/community_trending_notifier.py` calculaba las rutas en tendencia y las guardaba en una caché en memoria. El sistema implementado ahora persiste el resultado en snapshots diarios y el inbox consulta esa persistencia.

El problema original era que el inbox leía memoria, mientras la validación de ownership de `community_trending` intentaba encontrar un `NotificationEvent` persistido que el notifier nunca creaba. Esto provocaba una separación entre:

```text
fuente original que mostraba la señal: memoria del proceso
fuente original que validaba el marcado como leído: NotificationEvent
estado de lectura: UserNotificationState
```

Estado final:

```text
fuente de señal y ownership: community_trending_snapshot + FlightWatch activa
estado de lectura: UserNotificationState
```

### Resultado deseado

```text
quick_search_popularity_daily
        |
        v
cálculo semanal determinista
        |
        v
community_trending_snapshot
        |
        +--> community_trending_snapshot_route
        |
        v
inbox privado
  JOIN FlightWatch activa del usuario
        |
        v
UserNotificationState
  (user_id, community_trending, ct-YYYYMMDD-AAA-BBB)
```

### Principios no negociables

1. No almacenar `user_id`, `watch_id`, email ni datos personales en las tablas comunitarias.
2. Mantener la dirección de la ruta: `MAD → BCN` y `BCN → MAD` son rutas diferentes.
3. No cambiar el contrato de `NotificationEvent` ni hacer `rule_id` nullable.
4. No duplicar una señal por cada Watch del mismo usuario y ruta.
5. No mostrar snapshots `building` o caducados.
6. Mantener privacidad y ownership en `mark-read`.
7. Mantener funcionamiento con SQLite y PostgreSQL.
8. No romper alertas de precio, alertas hoteleras ni actividad de seguridad.
9. No usar `TRENDING_CACHE` como fuente de verdad después del corte.
10. Cada fase debe tener una verificación observable y un rollback claro.

---

## 1. Estado real y superficie afectada

### 1.1 Archivos actuales relevantes

#### Cálculo y worker (estado final)

- `backend/app/services/community_trending_notifier.py`
  - calcula el top 20 %;
  - persiste snapshots publicados y sus rutas hijas;
  - no mantiene una caché de proceso ni señales por usuario.
- `backend/app/worker/notifications.py`
  - ejecuta `notify_trending_routes()` en modo `--trending`;
  - ejecuta la comprobación aproximadamente cada 15 ciclos en `--loop`.

#### Inbox

- `backend/app/services/notification_inbox.py`
  - agrega alertas, hoteles, seguridad y tendencias;
  - consulta estados con `_state_map()`;
  - valida ownership con `_source_belongs_to_user()`;
  - implementa `mark_notification_read()`;
  - implementa `mark_all_notifications_read()`;
  - implementa `count_notification_summary()`.
- `backend/app/services/notification_inbox_sources.py`
  - define `SOURCE_COMMUNITY_TRENDING`;
  - define `READABLE_SOURCES`;
  - define `InboxItem` y `SourceRef`.
- `backend/app/api/v1/notifications.py`
  - expone listado, resumen, marcado individual y `read-all`.
- `backend/app/domain/schemas.py`
  - ya permite `community_trending` como `source_type`;
  - ya permite `community` como categoría;
  - `NotificationInboxSummaryOut` ya tiene `community` con valor por defecto.

#### Persistencia existente

- `backend/app/infrastructure/db/models.py`
  - `FlightWatch`;
  - `NotificationEvent`;
  - `UserNotificationState`;
  - `QuickSearchPopularityDaily`.
- `backend/alembic/versions/0040_add_quick_search_popularity_daily.py`
  - revisión actual que añade el rollup diario de búsquedas.
- `backend/app/api/v1/account.py`
  - borra los `UserNotificationState` del usuario al eliminar su cuenta.
- `backend/app/infrastructure/db/schema_compat.py`
  - contiene compatibilidad para tablas concretas creadas por ORM; no debe utilizarse como sustituto de una migración nueva.

#### Tests y documentación

- `backend/tests/integration/test_notification_inbox.py`
- `backend/tests/integration/test_notification_worker.py`
- `backend/tests/integration/test_community_route_intelligence.py`
- `backend/tests/unit/test_alembic_audit.py`
- `docs/reference/backend/notifications-contract.md`
- `docs/product/notifications.md`
- `docs/runbooks/runbook-notification-worker.md`
- `docs/runbooks/runbook-db-retention.md`
- `docs/reference/backend/community-pricing-contract.md`

### 1.2 Head Alembic confirmado antes del plan (baseline histórico)

El estado leído del repositorio al redactar el plan indicaba:

```text
0040_add_qs_popularity_daily
```

Durante la implementación se debe volver a ejecutar:

```bash
cd backend
uv run alembic heads
```

Si el head ha cambiado, no se debe crear `0041` a ciegas. Se debe usar la siguiente revisión disponible y actualizar las expectativas de tests que dependan del head.

---

## 2. Diseño de datos aprobado

### 2.1 Tabla `community_trending_snapshot`

Crear un modelo SQLAlchemy `CommunityTrendingSnapshot`:

| Campo | Tipo | Requerido | Semántica |
|---|---|---:|---|
| `id` | `String(36)` | sí | UUID interno |
| `reporting_date` | `Date` | sí | Día lógico del cálculo |
| `window_start_date` | `Date` | sí | Inicio inclusivo de ventana |
| `window_end_date` | `Date` | sí | Fin inclusivo de ventana |
| `calculated_at_utc` | `DateTime` | sí | Momento de inicio lógico del cálculo |
| `published_at_utc` | `DateTime` | no | Momento en que se publicó |
| `expires_at_utc` | `DateTime` | sí | Límite de lectura |
| `status` | `String(16)` | sí | `building` o `published` |
| `route_count` | `Integer` | sí | Número de rutas hijas |
| `created_at` | `DateTime` | sí | Auditoría |

Índices:

```text
ix_community_trending_snapshot_status_calculated
ix_community_trending_snapshot_status_expires
ix_community_trending_snapshot_reporting_date
```

No añadir una unicidad por `reporting_date`, porque puede haber más de un cálculo válido durante el mismo día. La selección debe resolver cuál es el snapshot más reciente por `calculated_at_utc`.

### 2.2 Tabla `community_trending_snapshot_route`

Crear un modelo SQLAlchemy `CommunityTrendingSnapshotRoute`:

| Campo | Tipo | Requerido | Semántica |
|---|---|---:|---|
| `id` | `String(36)` | sí | UUID interno |
| `snapshot_id` | `String(36)` FK | sí | Snapshot padre |
| `origin_iata` | `String(3)` | sí | Origen normalizado |
| `destination_iata` | `String(3)` | sí | Destino normalizado |
| `rank` | `Integer` | sí | Posición global |
| `search_count` | `Integer` | sí | Suma de búsquedas de la ventana |
| `created_at` | `DateTime` | sí | Auditoría |

Constraints:

```text
UNIQUE(snapshot_id, origin_iata, destination_iata)
FOREIGN KEY(snapshot_id) REFERENCES community_trending_snapshot(id) ON DELETE CASCADE
```

Índices:

```text
ix_community_trending_snapshot_route_snapshot_rank
ix_community_trending_snapshot_route_snapshot_route
```

No crear foreign keys a usuarios, Watches o búsquedas individuales.

### 2.3 Estado del snapshot

Valores iniciales permitidos:

```text
building
published
```

Semántica:

- `building`: cálculo todavía no publicable;
- `published`: snapshot completo y visible si no está caducado;
- cualquier otro valor debe rechazarse desde la capa de servicio o constraint si el patrón del proyecto lo permite.

No utilizar `failed` como estado persistente en esta primera versión. Un cálculo fallido debe hacer rollback. Si se necesita observabilidad del fallo, se usará logging estructurado.

### 2.4 Identificador lógico de fuente de inbox

El `source_id` comunitario será determinista:

```text
ct-YYYYMMDD-AAA-BBB
```

Ejemplo:

```text
ct-20260804-MAD-BCN
```

Características:

- cabe en `UserNotificationState.source_id` (`String(36)`);
- no incluye `user_id`;
- permanece estable durante el día para la misma ruta;
- cambia al cambiar el día lógico;
- permite que una recalculación no parezca una notificación completamente nueva.

Crear helpers puros y testeables:

```text
build_community_trending_source_id(reporting_date, origin_iata, destination_iata)
parse_community_trending_source_id(source_id)
```

El parser debe devolver `None` o un resultado inválido para formatos manipulados. No debe lanzar un error HTTP directamente; la capa de inbox decidirá el `404`.

---

## 3. Política temporal

### 3.1 Ventana de popularidad

Conservar el contrato actual:

```text
hoy y los seis días anteriores
= 7 días inclusivos
```

El snapshot debe guardar explícitamente:

```text
window_start_date = reporting_date - 6 días
window_end_date = reporting_date
```

No usar la fecha de publicación para determinar la ventana.

### 3.2 TTL

Valor inicial recomendado:

```text
TRENDING_SNAPSHOT_TTL_SECONDS = 3600
```

El TTL debe ser al menos dos veces el intervalo normal de cálculo del worker. Si la cadencia cambia, se debe revisar esta relación en el runbook.

La lectura exige:

```text
status == published
AND expires_at_utc > now
```

### 3.3 Snapshot vacío

Si no existen rutas populares o el top 20 % resulta vacío, se debe publicar un snapshot válido con:

```text
status = published
route_count = 0
```

Esto garantiza que las señales anteriores desaparezcan de forma determinista y que el inbox no conserve datos obsoletos por falta de limpieza de una caché.

### 3.4 Zona horaria

No cambiar en esta fase la semántica de fecha del sistema. Usar la misma fecha lógica que `_popularity_by_route()` recibe mediante `today`.

Sí se debe garantizar que:

- todas las consultas de una ejecución reciben el mismo `reporting_date`;
- los tests puedan inyectar una fecha fija;
- `calculated_at_utc`, `published_at_utc` y `expires_at_utc` sean UTC naive siguiendo la convención existente de `utc_now_naive()`.

---

## 4. Flujo de generación del snapshot

### 4.1 Entrada pública del servicio

Mantener una función compatible con el worker:

```text
notify_trending_routes(db, *, today=None) -> int
```

El entero debe conservar la semántica útil actual: devolver el número de señales de usuario visibles o, si se decide cambiarlo a número de rutas persistidas, documentar y testear el cambio. Recomendación: devolver el número de rutas persistidas para que el log no sugiera que se han creado notificaciones individuales.

Antes de implementar, comprobar quién consume el valor y ajustar el nombre del campo del log para no confundir `routes_persisted` con `notifications_created`.

### 4.2 Pasos transaccionales

1. Determinar `reporting_date`.
2. Calcular `window_start_date` y `window_end_date`.
3. Calcular todas las filas de popularidad con `_popularity_rows()` o un helper de dominio equivalente.
4. Determinar `trending_count = ceil(total_routes * TRENDING_SHARE)`.
5. Capturar `calculated_at_utc` una sola vez.
6. Crear `CommunityTrendingSnapshot(status="building")`.
7. Insertar las rutas top con `rank` 1-based.
8. Actualizar `route_count`.
9. Asignar `published_at_utc`.
10. Cambiar `status` a `published`.
11. Hacer `commit()` una sola vez.
12. Emitir log de éxito después del commit.

Si falla cualquier paso antes del commit:

- hacer rollback explícito si el servicio lo necesita;
- no limpiar snapshots anteriores;
- emitir log de error sin PII;
- propagar el error al worker para que el ciclo sea observable.

### 4.3 Orden estable

El ranking debe conservar:

```text
search_count DESC
origin_iata ASC
destination_iata ASC
```

No depender del orden accidental de SQL ni del orden de un `set`.

### 4.4 Concurrencia de workers

La primera versión no necesita lock distribuido adicional si los snapshots son inmutables y la lectura escoge el más reciente por `calculated_at_utc`.

Reglas:

- no borrar el snapshot anterior antes de publicar el nuevo;
- no actualizar rutas de un snapshot ya publicado;
- no considerar `published_at_utc` como criterio principal de frescura lógica;
- seleccionar por `calculated_at_utc DESC, id DESC`;
- conservar una única transacción por snapshot.

Caso esperado:

```text
worker A comienza 10:00
worker B comienza 10:05
worker B publica 10:06
worker A publica 10:08
```

El snapshot B debe seguir ganando si su `calculated_at_utc` es posterior, aunque A haya hecho commit más tarde.

### 4.5 No reutilizar `TRENDING_CACHE` como autoridad

Durante la migración progresiva se mantuvo el símbolo temporalmente; la limpieza legacy ya está completada. Las reglas finales son:

- no debe participar en el resultado del inbox una vez activada la lectura persistente;
- no debe ser la única forma de probar la funcionalidad;
- no debe recibir señales diferentes de las persistidas;
- `TRENDING_CACHE` y `TrendingSignal` ya no existen en producción;
- el inbox no depende de estado global de módulo.

---

## 5. Flujo de lectura del inbox

### 5.1 Nuevo servicio de lectura

Extraer una función específica en `notification_inbox.py` o un módulo cercano, según las convenciones existentes:

```text
list_community_trending_items(
    db,
    *,
    user_id,
    now=None,
    limit=...
) -> list[InboxItem]
```

Responsabilidades:

1. obtener el snapshot publicado más reciente y no expirado;
2. unir rutas con `FlightWatch`;
3. filtrar el `user_id` autenticado;
4. filtrar `WATCH_STATUS_ACTIVE`;
5. deduplicar por ruta;
6. generar `source_id` estable;
7. cargar los estados de lectura;
8. construir `InboxItem`.

### 5.2 Ownership

La visibilidad no se basa en una fila de entrega por usuario. Se basa en:

```text
snapshot.route.origin_iata == watch.origin_iata
snapshot.route.destination_iata == watch.destination_iata
watch.user_id == current_user.id
watch.status == active
```

Nunca devolver:

- `watch_id`;
- `user_id`;
- número de Watches privadas;
- email;
- precio individual.

### 5.3 Deduplificación

Un usuario puede tener varias Watches para una misma ruta en fechas diferentes. El inbox debe producir una sola señal por:

```text
(reporting_date, origin_iata, destination_iata)
```

La deduplicación debe ocurrir en SQL si es sencillo y, en cualquier caso, quedar protegida por una deduplicación final en Python antes de construir la respuesta.

### 5.4 Datos del item

Mantener el contrato actual:

```json
{
  "id": "community_trending:ct-20260804-MAD-BCN",
  "source_type": "community_trending",
  "source_id": "ct-20260804-MAD-BCN",
  "category": "community",
  "tone": "info",
  "title": "Ruta en tendencia en Viru",
  "body": "MAD → BCN es una ruta en tendencia esta semana.",
  "route_label": "MAD → BCN",
  "action_href": "/dashboard",
  "created_at": "2026-08-04T10:00:00",
  "read_at": null,
  "is_read": false
}
```

`created_at` debe derivarse del momento de cálculo/publicación elegido y mantenerse estable para el snapshot. No usar `datetime.now()` al leer, porque eso haría que el orden cambie artificialmente.

### 5.5 Límite

El límite global del inbox sigue siendo responsabilidad de `list_notification_inbox()`. La fuente comunitaria debe tener un límite interno razonable para no multiplicar filas por usuario.

Recomendación inicial:

```text
community_limit = min(bounded_limit, 20)
```

Después se mezclan todas las fuentes, se ordenan por `(created_at, id)` descendente y se aplica el límite final global.

---

## 6. Corrección de marcado como leído

### 6.1 Sustituir la validación actual

Eliminar la dependencia conceptual de:

```text
NotificationEvent.rule_id == ""
NotificationEvent.dedupe_key LIKE ...
```

Para `SOURCE_COMMUNITY_TRENDING`, la validación debe:

1. parsear el `source_id`;
2. verificar que el snapshot correspondiente está visible;
3. verificar que la ruta está en ese snapshot;
4. verificar que el usuario tiene una Watch activa para la ruta;
5. permitir insertar o actualizar `UserNotificationState`.

### 6.2 Repetición idempotente

Repetir:

```http
POST /api/v1/notifications/community_trending/ct-20260804-MAD-BCN/read
```

debe devolver `200` y actualizar `read_at`, no crear una segunda fila.

La constraint existente:

```text
UNIQUE(user_id, source_type, source_id)
```

debe seguir siendo la protección final.

### 6.3 Señal antigua

Si el cliente intenta marcar una señal de un snapshot que ya no está vigente:

```text
404 notification_not_found
```

No se debe permitir escribir estados para señales inexistentes solo porque el identificador tenga un formato válido.

### 6.4 Seguridad entre usuarios

Los siguientes casos deben devolver el mismo `404` genérico:

- ruta inexistente;
- ruta visible para otro usuario;
- ruta sin Watch activa del usuario;
- snapshot inexistente;
- snapshot expirado;
- `source_id` manipulado.

No revelar cuál de estas condiciones falló.

---

## 7. Corrección de `read-all` y resumen

### 7.1 `mark_all_notifications_read`

Como ya parte de `list_notification_inbox()`, deberá incluir automáticamente los items comunitarios después de integrar la nueva lectura.

Verificar explícitamente:

- inserta estados comunitarios;
- actualiza estados comunitarios existentes;
- no duplica estados;
- devuelve el número total de items actualizados;
- mantiene intactas las fuentes no comunitarias.

### 7.2 Resumen del listado

En `backend/app/api/v1/notifications.py`, `_summary()` debe contar explícitamente:

```python
"community": sum(1 for item in items if item.category == "community")
```

El campo ya existe en el schema; no crear otro nombre.

### 7.3 Resumen ligero

En `count_notification_summary()`:

- dejar de consultar `TRENDING_CACHE`;
- derivar la comunidad de la misma función persistente o de una consulta SQL equivalente;
- contar solo snapshots publicados, no expirados y con Watch activa;
- excluir estados antiguos que ya no estén visibles;
- conservar la semántica de `total`, `unread` y `community`.

### 7.4 Consistencia entre endpoints

Debe cumplirse para la misma base de datos y el mismo momento:

```text
GET /notifications.summary.community
== número de items community devueltos por GET /notifications
```

Si los límites hacen imposible la igualdad exacta, documentar explícitamente la diferencia. Recomendación: que ambos cuenten la misma ventana visible y que las pruebas exijan igualdad en escenarios menores al límite.

---

## 8. Migración Alembic

### 8.1 Revisión

Crear la siguiente revisión libre después de confirmar heads:

```text
backend/alembic/versions/0041_add_community_trending_snapshots.py
```

Si el head cambia, usar el identificador siguiente correcto.

### 8.2 Upgrade

La migración debe:

1. crear `community_trending_snapshot`;
2. crear índices de status/calculated/expires/reporting;
3. crear `community_trending_snapshot_route`;
4. crear FK con cascade;
5. crear unique constraint de snapshot y ruta;
6. crear índices de snapshot/rank y snapshot/ruta;
7. no realizar backfill;
8. no modificar `notification_event`;
9. no modificar `user_notification_state`;
10. no insertar tendencias artificiales.

### 8.3 Downgrade

El downgrade debe:

1. eliminar índices de la tabla hija;
2. eliminar tabla hija;
3. eliminar índices de la tabla padre;
4. eliminar tabla padre.

No borrar `UserNotificationState` en el downgrade automáticamente. El plan de rollback operativo debe indicar cómo limpiar estados comunitarios si se vuelve a la versión anterior.

### 8.4 Compatibilidad con tablas preexistentes

No añadir una tabla nueva mediante `Base.metadata.create_all()` fuera de Alembic. La suite debe comprobar que importar `app.main` no crea estas tablas antes de la migración.

Si el repositorio requiere validación defensiva de tablas precreadas, crear un helper de auditoría específico y tests equivalentes a los de `0039`; no debilitar la migración aceptando tablas incompletas.

### 8.5 Auditoría Alembic

Actualizar las expectativas de:

```text
backend/tests/unit/test_alembic_audit.py
backend/tests/unit/test_community_pricing_migration.py
```

Solo después de confirmar que:

```bash
uv run alembic heads
```

devuelve el nuevo head.

---

## 9. Retención y limpieza

### 9.1 Política

Valores iniciales recomendados:

```text
snapshots publicados: 90 días
snapshots building: 1 hora
```

El periodo de 90 días es para auditoría y diagnóstico; la lectura usa solo snapshots publicados y no expirados.

### 9.2 Integración con retención existente

Revisar:

```text
backend/scripts/db_retention.py
backend/ops/db-retention/
docs/runbooks/runbook-db-retention.md
```

Añadir una categoría de retención solo si el script actual admite ampliar tablas sin romper el contrato. Si el script es demasiado específico, crear una función separada y llamarla desde el mismo ciclo, sin duplicar locks ni logging.

### 9.3 Borrado seguro

El borrado debe:

1. ejecutarse en `--dry-run` primero;
2. listar candidatos por tabla;
3. borrar estados de lectura comunitarios cuyos `source_id` pertenecen a snapshots candidatos;
4. borrar snapshots padres;
5. dejar que la FK cascade elimine las rutas hijas;
6. informar cantidad de filas candidatas y eliminadas;
7. respetar mínimos de retención;
8. ejecutarse en batches si el volumen lo exige.

### 9.4 No borrar estados de otras fuentes

El filtro debe incluir siempre:

```text
source_type = 'community_trending'
```

Nunca se debe borrar por `source_id` sin filtrar el tipo.

### 9.5 Recuperación

La retención es destructiva. El runbook debe indicar:

- pausa del timer/cron;
- ejecución en dry-run;
- restauración desde backup si se borró incorrectamente;
- no ejecutar downgrade como mecanismo de recuperación de datos.

---

## 10. Observabilidad

### 10.1 Logs estructurados del worker

Ampliar `notification_trending_cycle` sin PII.

Campos recomendados:

```json
{
  "event": "notification_trending_cycle",
  "reporting_date": "2026-08-04",
  "window_start_date": "2026-07-29",
  "window_end_date": "2026-08-04",
  "candidate_route_count": 42,
  "trending_route_count": 9,
  "snapshot_id": "redacted-or-internal-safe-id",
  "snapshot_status": "published",
  "routes_persisted": 9,
  "duration_ms": 38
}
```

No incluir:

- `user_id`;
- email;
- `watch_id`;
- precios individuales;
- payloads completos.

### 10.2 Errores y estado implementado

El código implementado emite actualmente:

```text
community_trending_snapshot_published
community_trending_snapshot_failed
db_retention.community_trending_completed
```

Los eventos `community_trending_snapshot_started`, `community_trending_snapshot_read_failed` y `community_trending_cleanup_failed` quedan como extensiones operativas futuras; no forman parte del contrato actual. Los logs estructurados existentes son suficientes para esta entrega.

### 10.3 Métricas derivables

Documentar consultas o campos para medir:

- snapshots publicados por día;
- snapshots fallidos;
- rutas persistidas;
- edad del snapshot visible;
- lecturas comunitarias;
- marcados como leídos comunitarios;
- `404` de ownership comunitario;
- filas de retención eliminadas.

---

## 11. Plan de implementación por fases

Cada tarea debe ser pequeña. No avanzar si la verificación de la tarea falla.

### Fase 0 — Baseline y congelación de contratos

#### Tarea 0.1 — Confirmar estado Git y head

**Archivos:** ninguno.

Ejecutar desde la raíz canónica:

```bash
git status --short
cd backend
uv run alembic heads
uv run pytest tests/unit/test_alembic_audit.py -q
```

Verificar:

- documentar cambios previos no relacionados;
- no mezclarlos con la implementación;
- confirmar head actual;
- confirmar que la auditoría actual pasa.

#### Tarea 0.2 — Crear baseline de inbox

Ejecutar:

```bash
cd backend
uv run pytest tests/integration/test_notification_inbox.py tests/integration/test_notification_worker.py -q
```

Registrar:

- número de tests;
- duración;
- cualquier dependencia de estado global `TRENDING_CACHE`;
- si existen fallos previos.

#### Tarea 0.3 — Congelar ejemplos de contrato

Añadir primero tests que describan el contrato deseado:

- `source_type = community_trending`;
- `category = community`;
- `source_id` determinista;
- `summary.community` consistente.

Verificación esperada inicial: los tests nuevos deben fallar por ausencia de persistencia, no por errores de importación o fixture.

---

### Fase 1 — Modelos y migración

#### Tarea 1.1 — Añadir modelos SQLAlchemy

**Modificar:**

- `backend/app/infrastructure/db/models.py`

**Añadir:**

- `CommunityTrendingSnapshot`;
- `CommunityTrendingSnapshotRoute`;
- relaciones padre/hijas con cascade ORM si sigue el patrón del archivo;
- constraints e índices definidos en este plan.

**Verificar:**

```bash
cd backend
uv run pytest tests/unit/test_community_trending_models.py -q
uv run ruff check app/infrastructure/db/models.py tests/unit/test_community_trending_models.py
```

Tests mínimos:

- nombres exactos de tablas;
- columnas y nullability;
- unique constraint;
- FK cascade;
- no FK hacia `users` en snapshots;
- no `user_id` ni `watch_id` en las tablas comunitarias.

#### Tarea 1.2 — Escribir test de migración antes de la migración

**Crear:**

- `backend/tests/unit/test_community_trending_migration.py`

Casos:

1. upgrade desde `0040` crea ambas tablas;
2. upgrade deja índices esperados;
3. downgrade elimina ambas tablas;
4. importar la aplicación no crea tablas futuras;
5. upgrade dos veces no rompe cuando Alembic ya está en head;
6. no se altera `notification_event`;
7. no se altera `user_notification_state`.

Ejecutar el test y confirmar fallos esperados por ausencia de migración/modelos.

#### Tarea 1.3 — Crear migración

**Crear:**

- `backend/alembic/versions/0041_add_community_trending_snapshots.py`

Usar el patrón de `0040_add_quick_search_popularity_daily.py` y respetar la revisión real confirmada en Fase 0.

#### Tarea 1.4 — Verificar la migración en SQLite limpio

```bash
cd backend
uv run pytest tests/unit/test_community_trending_migration.py -q
DB_URL=sqlite:///./tmp-community-trending-migration.db uv run alembic upgrade head
DB_URL=sqlite:///./tmp-community-trending-migration.db uv run alembic check
DB_URL=sqlite:///./tmp-community-trending-migration.db uv run python -m app.infrastructure.db.alembic_audit --json
```

Verificar:

- return codes cero;
- head único;
- tablas presentes;
- índices presentes;
- no tablas inesperadas creadas por importación.

#### Tarea 1.5 — Verificar downgrade/upgrade

Sobre una base temporal:

```bash
DB_URL=sqlite:///./tmp-community-trending-migration.db uv run alembic downgrade 0040_add_qs_popularity_daily
DB_URL=sqlite:///./tmp-community-trending-migration.db uv run alembic upgrade head
```

Verificar:

- la tabla desaparece tras downgrade;
- vuelve a aparecer tras upgrade;
- las tablas existentes de fases anteriores permanecen intactas;
- `alembic_version` termina en el head esperado.

---

### Fase 2 — Identidad estable y helpers puros

#### Tarea 2.1 — Añadir helpers de source ID

**Modificar o crear según convención:**

- `backend/app/services/community_trending_notifier.py`, o
- un módulo pequeño `backend/app/services/community_trending_identity.py`.

Recomendación: separar identidad de persistencia para que sea fácilmente testeable.

Implementar:

```text
build_community_trending_source_id(date, origin, destination)
parse_community_trending_source_id(source_id)
```

Normalizar IATA en mayúsculas y validar exactamente tres letras ASCII.

#### Tarea 2.2 — Tests exhaustivos de identidad

**Crear:**

- `backend/tests/unit/test_community_trending_identity.py`

Casos:

- fecha válida;
- IATA minúscula normalizada;
- espacios exteriores rechazados o normalizados según convención;
- IATA numérico rechazado;
- caracteres Unicode rechazados;
- source ID demasiado largo rechazado;
- fecha imposible rechazada;
- origen y destino preservados en dirección;
- `MAD → BCN` distinto de `BCN → MAD`;
- round-trip build → parse;
- source ID de usuario antiguo `trending:{user_id}:...` no se acepta como nuevo ID.

Ejecutar:

```bash
cd backend
uv run pytest tests/unit/test_community_trending_identity.py -q
```

---

### Fase 3 — Servicio persistente de snapshots

#### Tarea 3.1 — Escribir tests de snapshot antes de cambiar el notifier

**Crear:**

- `backend/tests/integration/test_community_trending_persistence.py`

Fixtures:

- SQLite temporal;
- fecha controlada;
- varias filas de `QuickSearchPopularityDaily`;
- usuarios y Watches activas/inactivas;
- session factory independiente cuando sea necesario.

Casos:

1. calcula top 20 % estable;
2. persiste rank y count;
3. publica snapshot completo;
4. publica snapshot vacío;
5. no persiste usuarios;
6. no persiste Watches;
7. no publica `building` incompleto;
8. conserva snapshot anterior si el cálculo falla;
9. ejecuta dos veces sin duplicar rutas dentro de un snapshot;
10. selección del snapshot más reciente usa `calculated_at_utc`, no commit order;
11. snapshots expirados no son visibles;
12. snapshots `building` no son visibles.

#### Tarea 3.2 — Implementar persistencia mínima

**Modificar:**

- `backend/app/services/community_trending_notifier.py`

Cambiar el flujo para:

- crear snapshot `building`;
- insertar rutas top;
- publicar atómicamente;
- devolver un resultado semánticamente claro;
- eliminar escrituras a `TRENDING_CACHE` como fuente de verdad.

No modificar todavía el inbox en esta tarea; primero debe estar probado el almacenamiento.

#### Tarea 3.3 — Verificar el servicio aislado

```bash
cd backend
uv run pytest tests/integration/test_community_trending_persistence.py -q
uv run pytest tests/integration/test_community_route_intelligence.py -q
uv run ruff check app/services/community_trending_notifier.py tests/integration/test_community_trending_persistence.py
```

Confirmar que las rutas públicas existentes no cambiaron de contrato.

---

### Fase 4 — Worker y concurrencia

#### Tarea 4.1 — Actualizar el worker sin cambiar su interfaz CLI

**Modificar:**

- `backend/app/worker/notifications.py`

Conservar:

```bash
python -m app.worker.notifications --trending
python -m app.worker.notifications --loop
```

Actualizar logs para no llamar `created` a notificaciones individuales si ahora se persisten rutas/snapshots.

#### Tarea 4.2 — Tests del worker

**Modificar:**

- `backend/tests/integration/test_notification_worker.py`

Añadir:

- `run_trending()` crea snapshot persistente;
- segunda ejecución crea un nuevo snapshot válido o reutiliza la política decidida, sin duplicar rutas internas;
- fallo controlado deja snapshot anterior visible;
- proceso nuevo puede leer el snapshot creado por otro session factory;
- ejecución con cero popularidad publica snapshot vacío;
- `--trending` devuelve código cero cuando el cálculo es correcto.

#### Tarea 4.3 — Verificación de dos sesiones

Usar dos sesiones SQLite sobre archivo temporal, no `:memory:` compartida:

```python
session_a = TestingSessionLocal()
session_b = TestingSessionLocal()
```

Verificar:

- A publica;
- B lee sin tocar memoria global;
- B no depende de importar el módulo que ejecutó A;
- no hay duplicados dentro del mismo snapshot.

Si se añade un test con threads, evitar afirmar garantías que SQLite no puede dar bajo locks de escritura. El objetivo es probar idempotencia lógica y visibilidad, no simular PostgreSQL con SQLite.

---

### Fase 5 — Lectura persistente del inbox

#### Tarea 5.1 — Tests rojos del inbox comunitario

**Modificar:**

- `backend/tests/integration/test_notification_inbox.py`

Añadir casos:

1. usuario con Watch activa ve una ruta en tendencia;
2. usuario sin Watch no la ve;
3. dos Watches de la misma ruta producen un item;
4. Watch no activa no produce item;
5. snapshot expirado no produce item;
6. snapshot `building` no produce item;
7. snapshot vacío elimina la visibilidad de una señal anterior;
8. ruta inversa no se mezcla;
9. el item contiene `category=community`;
10. el `source_id` es determinista;
11. no aparecen `user_id` ni `watch_id` en el JSON.

#### Tarea 5.2 — Implementar consulta del snapshot visible

**Modificar:**

- `backend/app/services/notification_inbox.py`

Crear la función de lectura comunitaria y reemplazar la lectura de:

```python
get_trending_signals_for_user(user_id)
```

por una consulta persistente.

Mantener el resto de fuentes sin cambios durante esta tarea.

#### Tarea 5.3 — Eliminar dependencia de memoria como fuente de lectura

**Modificar:**

- `backend/app/services/community_trending_notifier.py`
- `backend/app/services/notification_inbox.py`

Eliminar o aislar:

- `TRENDING_CACHE`;
- `TrendingSignal` si ya no tiene consumidores válidos;
- imports locales que solo servían a la caché.

Antes de eliminar símbolos exportados, ejecutar búsqueda de referencias en todo el backend y tests.

#### Tarea 5.4 — Verificar el inbox completo

```bash
cd backend
uv run pytest tests/integration/test_notification_inbox.py -q
uv run pytest tests/integration/test_notification_pipeline.py tests/integration/test_notification_worker.py -q
uv run ruff check app/services/notification_inbox.py app/services/community_trending_notifier.py tests/integration/test_notification_inbox.py
```

Verificar que las fuentes existentes siguen mezclándose y ordenándose correctamente.

---

### Fase 6 — Ownership y marcado como leído

#### Tarea 6.1 — Tests de seguridad del source ID

**Modificar:**

- `backend/tests/integration/test_notification_inbox.py`

Casos:

- `POST .../community_trending/{source_id}/read` válido devuelve 200;
- repetir devuelve 200;
- usuario sin Watch devuelve 404;
- ruta de otro usuario devuelve 404;
- source ID inválido devuelve 404;
- snapshot expirado devuelve 404;
- snapshot viejo devuelve 404;
- no se crea estado para una señal no visible.

#### Tarea 6.2 — Implementar `_source_belongs_to_user` comunitario

**Modificar:**

- `backend/app/services/notification_inbox.py`

Para `SOURCE_COMMUNITY_TRENDING`:

1. parsear source ID;
2. buscar snapshot visible;
3. buscar ruta del snapshot;
4. comprobar Watch activa del usuario;
5. devolver booleano.

No lanzar detalles diferenciados al cliente.

#### Tarea 6.3 — Verificar persistencia de estados

Consultar directamente:

```python
select(UserNotificationState).where(
    UserNotificationState.user_id == user_id,
    UserNotificationState.source_type == "community_trending",
)
```

Confirmar:

- una fila por usuario/fuente;
- `read_at` no nulo;
- no hay duplicados;
- otros usuarios no comparten el estado.

---

### Fase 7 — `read-all` y summaries

#### Tarea 7.1 — Test de read-all comunitario

**Modificar:**

- `backend/tests/integration/test_notification_inbox.py`

Escenario:

- crear una alerta de precio;
- crear una señal comunitaria;
- dejar ambas sin leer;
- ejecutar `/api/v1/notifications/read-all`;
- comprobar que ambas están leídas;
- repetir y comprobar que `updated=0` o la semántica existente establecida por el endpoint se conserva.

#### Tarea 7.2 — Actualizar resumen HTTP

**Modificar:**

- `backend/app/api/v1/notifications.py`

Añadir el conteo explícito de `community` en `_summary()`.

#### Tarea 7.3 — Actualizar resumen SQL

**Modificar:**

- `backend/app/services/notification_inbox.py`

Eliminar lectura de `TRENDING_CACHE` y calcular comunidad desde snapshots visibles y Watches activas.

#### Tarea 7.4 — Verificar igualdad de summaries

Para una base con menos de 200 items:

```text
GET /notifications -> body.summary
GET /notifications/summary -> body
```

Comparar:

- total;
- unread;
- community;
- categorías existentes.

Si existe una diferencia intencionada por límites, escribirla en el contrato y en el test.

---

### Fase 8 — Retención

#### Tarea 8.1 — Test de candidatos en dry-run

**Modificar o crear:**

- tests del script de retención existente;
- `backend/tests/unit/test_community_trending_retention.py` si el script no tiene cobertura adecuada.

Casos:

- snapshot de 91 días es candidato;
- snapshot de 89 días no es candidato;
- `building` de más de una hora es candidato;
- snapshot actual no se borra;
- rutas hijas se eliminan por cascade;
- solo se eliminan `UserNotificationState` de tipo `community_trending`;
- un estado `alert_event` con el mismo `source_id` no se elimina.

#### Tarea 8.2 — Integrar la limpieza

**Modificar según resultado de la inspección:**

- `backend/scripts/db_retention.py`, o
- un servicio dedicado llamado por el runner existente.

Respetar:

- guard rails;
- batches;
- dry-run;
- logs JSONL;
- lock existente;
- alert file y exit codes.

#### Tarea 8.3 — Verificar operación manual

```bash
cd backend
ops/db-retention/run-db-retention.sh --dry-run
```

Verificar que:

- no borra filas;
- informa candidatos comunitarios;
- no exige infraestructura nueva;
- no rompe las categorías existentes.

---

### Fase 9 — Eliminación de cuenta y datos

#### Tarea 9.1 — Test de account deletion

**Modificar:**

- `backend/tests/integration/test_notification_inbox.py` o suite de account.

Escenario:

1. crear Watch activa;
2. crear snapshot global;
3. marcar señal como leída;
4. eliminar cuenta;
5. comprobar que se borra el `UserNotificationState` del usuario;
6. comprobar que el snapshot global permanece;
7. comprobar que otro usuario no recibe acceso a una Watch eliminada.

#### Tarea 9.2 — Revisar dependencias

No añadir FK de snapshots a usuarios. Confirmar que la eliminación de cuenta no intenta borrar tablas globales de comunidad.

---

### Fase 10 — Observabilidad y runbook

#### Tarea 10.1 — Tests de logs

**Crear o modificar:**

- `backend/tests/unit/test_community_trending_logging.py`.

Verificar que el evento de éxito contiene:

- reporting date;
- window dates;
- route counts;
- status;
- duration.

Verificar que no contiene:

- email;
- user ID;
- watch ID;
- precio individual.

#### Tarea 10.2 — Actualizar runbook

**Modificar:**

- `docs/runbooks/runbook-notification-worker.md`

Documentar:

- nuevo snapshot persistente;
- comando `--trending`;
- TTL;
- cómo comprobar el último snapshot;
- cómo interpretar un snapshot vacío;
- cómo diagnosticar `snapshot_failed`;
- qué hacer si el snapshot está caducado;
- cómo pausar el worker;
- rollback de lectura.

#### Tarea 10.3 — Actualizar retención

**Modificar:**

- `docs/runbooks/runbook-db-retention.md`

Añadir:

- tablas comunitarias;
- mínimos;
- dry-run;
- orden de borrado;
- recuperación desde backup;
- no usar downgrade para recuperar datos.

---

### Fase 11 — Contratos y documentación viva

#### Tarea 11.1 — Actualizar contrato de notificaciones

**Modificar:**

- `docs/reference/backend/notifications-contract.md`

Añadir:

- `community_trending` como fuente permitida de marcado leído;
- formato de `source_id`;
- ownership mediante Watch activa;
- snapshot publicado/no expirado;
- ausencia de `NotificationEvent` para estas señales;
- privacidad;
- comportamiento `404`;
- `community` en summaries;
- retención de snapshots y estados.

Corregir el documento actual, que lista solo tres fuentes permitidas para `mark-read` aunque el schema ya incluye `community_trending`.

#### Tarea 11.2 — Actualizar documento de producto

**Modificar:**

- `docs/product/notifications.md`

Añadir la señal comunitaria como fuente real de la bandeja y aclarar:

- solo aparece para una Watch activa;
- no es una alerta personalizada de precio;
- no identifica a otros viajeros;
- desaparece al caducar o cambiar el snapshot.

#### Tarea 11.3 — Actualizar plan relacionado

**Modificar solo si sigue siendo coherente:**

- `docs/plans/2026-08-01-community-route-intelligence.md`

Añadir una referencia a este plan para que la implementación de la inteligencia comunitaria no vuelva a asumir una caché en memoria.

#### Tarea 11.4 — Actualizar inventario

**Modificar:**

- `docs/DOCS_INVENTORY.md`

Añadir el nuevo plan bajo una sección de actualización manual con:

```text
Ruta: docs/plans/2026-08-04-community-trending-persistence-inbox.md
Tipo: plan
Estado: vivo
Acción: conservar
Fuente de verdad: este plan mientras esté pendiente; después, contrato/runbook actualizados
```

No actualizar `HISTORY.md` por crear un plan pendiente. Solo hacerlo cuando el cambio de comportamiento esté implementado y publicado.

---

## 12. Estrategia de rollout y rollback

### 12.1 Rollout recomendado

#### Release A — migración y escritura

- aplicar migración;
- persistir snapshots;
- conservar temporalmente el código legacy solo si hace falta para comparar;
- no cambiar aún la lectura pública sin evidencia.

Verificar:

- snapshots publicados;
- counts iguales al cálculo directo;
- ningún dato personal;
- logs correctos.

#### Release B — lectura persistente

- cambiar inbox a DB;
- corregir ownership;
- habilitar read/read-all/summary persistentes;
- ejecutar suites completas.

Verificar:

- señales después de reinicio;
- dos session factories ven lo mismo;
- estado de lectura independiente por usuario.

#### Release C — limpieza legacy

- eliminar `TRENDING_CACHE`;
- eliminar `TrendingSignal` si queda sin referencias;
- eliminar validación antigua de `NotificationEvent` para comunidad;
- actualizar docs y retención.

### 12.2 Feature flag

No introducir una infraestructura nueva de flags si el proyecto ya tiene una convención existente. Antes de implementar, revisar `docs/reference/feature-flags.md`.

Si se necesita rollout reversible, utilizar una sola configuración explícita siguiendo la convención del repositorio, con estados:

```text
legacy
shadow
persistent
```

Semántica:

- `legacy`: inbox usa memoria; persistencia puede apagarse;
- `shadow`: persistencia calcula y registra diferencias, pero inbox todavía usa legacy;
- `persistent`: inbox usa DB.

No mantener `shadow` indefinidamente.

### 12.3 Rollback de aplicación

Si falla la lectura persistente:

1. pausar el worker si está generando errores;
2. volver temporalmente a `legacy` solo si la caché sigue presente en esa versión;
3. mantener las tablas y snapshots sin borrarlos;
4. investigar discrepancias;
5. no hacer downgrade de base de datos como primera reacción.

### 12.4 Rollback de migración

Solo hacer downgrade si:

- no hay código desplegado que consulte las tablas nuevas;
- se ha realizado backup;
- se acepta perder snapshots comunitarios persistidos;
- se han limpiado o preservado los `UserNotificationState` comunitarios según el procedimiento.

La recomendación operativa es preferir rollback de aplicación manteniendo la migración.

---

## 13. Matriz completa de verificaciones

### 13.1 Verificación estática

```bash
cd backend
uv run ruff check app tests
uv run ruff format --check app tests
```

Si el repositorio tiene configuración mypy aplicable:

```bash
uv run mypy app
```

Revisar manualmente:

- imports muertos;
- referencias a `TRENDING_CACHE`;
- referencias a `TrendingSignal`;
- referencias al patrón `NotificationEvent.rule_id == ""`;
- SQL con filtros de `source_type` ausentes;
- tipos de fechas timezone-aware/naive mezclados.

### 13.2 Migraciones

```bash
cd backend
uv run alembic heads
uv run alembic check
uv run pytest tests/unit/test_alembic_audit.py tests/unit/test_community_trending_migration.py -q
```

Además:

- base SQLite vacía;
- upgrade hasta head;
- downgrade a `0040`;
- upgrade de nuevo;
- inspección de tablas, indexes y FKs con SQLite;
- PostgreSQL temporal si el entorno está disponible.

### 13.3 Unit tests

```bash
cd backend
uv run pytest \
  tests/unit/test_community_trending_identity.py \
  tests/unit/test_community_trending_models.py \
  tests/unit/test_community_trending_migration.py \
  tests/unit/test_community_trending_logging.py \
  -q
```

### 13.4 Integration tests de comunidad

```bash
cd backend
uv run pytest \
  tests/integration/test_community_trending_persistence.py \
  tests/integration/test_community_route_intelligence.py \
  tests/integration/test_community_pricing.py \
  -q
```

### 13.5 Integration tests de inbox/worker

```bash
cd backend
uv run pytest \
  tests/integration/test_notification_inbox.py \
  tests/integration/test_notification_pipeline.py \
  tests/integration/test_notification_worker.py \
  -q
```

### 13.6 Suite de regresión backend

```bash
cd backend
uv run pytest -q
```

Si la suite completa falla por una causa previa no relacionada:

- registrar el test y traceback exactos;
- ejecutar la suite focalizada en verde;
- no ocultar el fallo global en el informe final.

### 13.7 Verificación de proceso separado

1. Crear snapshot con un proceso/session factory.
2. Cerrar sesión y limpiar cualquier caché de módulo.
3. Crear una nueva sesión/proceso.
4. Llamar `GET /api/v1/notifications`.
5. Confirmar que la señal persiste.

La prueba no debe importar la misma instancia de `TRENDING_CACHE` como ayuda.

### 13.8 Verificación multiusuario

Crear:

```text
usuario A con MAD → BCN
usuario B con MAD → BCN
usuario C sin MAD → BCN
```

Verificar:

- A ve la señal;
- B ve la señal;
- C no la ve;
- A puede marcarla leída;
- B sigue viéndola como no leída;
- el estado de A no cambia el de B.

### 13.9 Verificación de reinicio

1. Ejecutar `--trending`.
2. Consultar inbox.
3. Terminar el proceso worker.
4. Iniciar otro proceso.
5. Consultar inbox.
6. Marcar leído.
7. Reiniciar de nuevo.
8. Confirmar que sigue leído mientras el source ID siga visible.

### 13.10 Verificación de caducidad

Con tiempo controlado o timestamps manuales:

- snapshot `expires_at_utc` pasado no aparece;
- snapshot vigente sí aparece;
- si solo existe snapshot caducado, no hay señal comunitaria;
- summary no lo cuenta;
- read endpoint devuelve 404.

### 13.11 Verificación de snapshot vacío

1. Publicar snapshot con una ruta.
2. Confirmar señal visible.
3. Publicar snapshot vacío más reciente.
4. Confirmar que desaparece del inbox.
5. Confirmar que el estado antiguo no se transforma en una señal visible fantasma.

### 13.12 Verificación de carrera lógica

Simular:

```text
snapshot S1 calculado con datos antiguos
snapshot S2 calculado con datos nuevos
publicar S2
publicar S1 después
```

Confirmar que el lector escoge S2 por `calculated_at_utc`.

### 13.13 Verificación de privacidad

Serializar respuestas y buscar:

```text
user_id
watch_id
email
price_per_traveler
```

Confirmar que no aparecen en items comunitarios ni en snapshots públicos.

### 13.14 Verificación de las demás fuentes

En una misma bandeja mezclar:

- alert event;
- hotel alert event;
- security activity;
- community trending.

Verificar:

- categorías correctas;
- orden global correcto;
- marcado individual aislado;
- `read-all` marca todo;
- resumen mantiene counts anteriores;
- ninguna fuente depende de la nueva tabla.

### 13.15 Verificación de retención

```bash
cd backend
ops/db-retention/run-db-retention.sh --dry-run
```

Después, sobre base temporal controlada:

- ejecutar limpieza real;
- contar antes/después;
- validar cascades;
- validar que otras fuentes permanecen;
- comprobar logs y exit code.

### 13.16 Verificación de documentación

Comprobar:

```bash
git diff --check
```

Y revisar manualmente:

- todos los paths citados existen;
- el head mencionado es correcto;
- el contrato no afirma que las tendencias sean `NotificationEvent`;
- la lista de fuentes de `mark-read` incluye comunidad;
- el inventario incluye el nuevo plan;
- no se han copiado secretos ni datos privados.

---

## 14. Criterios de aceptación funcional

La entrega no se considera terminada hasta cumplir todos estos puntos:

- [x] `TRENDING_CACHE` no es fuente de verdad y la proyección legacy fue eliminada.
- [x] Los snapshots se almacenan en DB.
- [x] Las rutas hijas tienen rank y count correctos.
- [x] Los snapshots `building` nunca se muestran.
- [x] Los snapshots expirados nunca se muestran.
- [x] Un snapshot vacío limpia lógicamente las señales anteriores.
- [x] El inbox solo muestra rutas de Watches activas del usuario.
- [x] Varias Watches de la misma ruta producen un solo item.
- [x] `source_id` es determinista por día y ruta.
- [x] `mark-read` funciona para comunidad.
- [x] `mark-read` de otro usuario devuelve 404.
- [x] `read-all` incluye comunidad.
- [x] `summary.community` es correcto.
- [x] El estado de lectura es independiente por usuario.
- [x] Las señales sobreviven a reinicios.
- [x] Dos procesos pueden leer el mismo snapshot.
- [x] SQLite pasa las migraciones y la suite focalizada.
- [x] PostgreSQL no recibe SQL específico innecesario; la conexión real queda pendiente de un entorno PostgreSQL disponible.
- [x] No se modifica `NotificationEvent` para forzar compatibilidad.
- [x] No se almacenan datos personales comunitarios.
- [x] Retención y dry-run están documentados.
- [x] Los logs no contienen PII.
- [x] Los documentos vivos se actualizan.
- [x] `git diff --check` pasa.

---

## 15. Criterios de aceptación no funcional

### Rendimiento

- la lectura comunitaria debe resolverse en una consulta agregada o un número pequeño y estable de consultas;
- no debe existir N+1 por Watch;
- el listado de inbox no debe hacer una consulta por cada señal;
- la generación del snapshot debe usar una sola transacción de escritura;
- las rutas deben estar cubiertas por índices útiles.

### Seguridad

- ownership verificado en el servidor;
- source ID validado estrictamente;
- respuestas homogéneas `404` para no filtrar existencia;
- no confiar en `user_id` enviado por cliente;
- no incluir datos personales en logs o payloads.

### Operación

- worker manual ejecutable;
- fallo de cálculo observable;
- snapshot anterior usable durante un fallo si no ha caducado;
- retención con dry-run;
- rollback documentado;
- no dependencia obligatoria de Redis ni de una cola nueva.

### Compatibilidad

- API pública de notificaciones mantiene envelope;
- `source_type` y `category` existentes permanecen;
- alertas y hoteles no cambian su persistencia;
- SQLite local continúa siendo válido;
- migración lineal desde el head actual.

---

## 16. Orden de commits recomendado

No hacer un commit gigante. Crear commits atómicos, después de sus verificaciones:

1. `test: define community trending persistence contracts`
2. `feat: persist community trending snapshots`
3. `test: cover persistent trending worker cycles`
4. `fix: read community trends from persisted snapshots`
5. `fix: validate community notification ownership`
6. `fix: include community trends in notification summaries`
7. `feat: retain community trending snapshots safely`
8. `docs: document persistent community trending inbox`
9. `test: verify community trending rollback and retention`

Antes de cada commit:

```bash
git status --short
git diff --check
git diff --stat
```

No incluir en esos commits los cambios iniciales no relacionados del árbol de trabajo.

---

## 17. Cierre y revisión final

Antes de declarar la implementación terminada:

1. Ejecutar revisión de diff completo.
2. Buscar referencias residuales a `TRENDING_CACHE`.
3. Buscar validaciones residuales contra `NotificationEvent` para `community_trending`.
4. Ejecutar auditoría Alembic.
5. Ejecutar tests unitarios y de integración focalizados.
6. Ejecutar suite backend completa.
7. Ejecutar Ruff y `git diff --check`.
8. Probar el worker en modo `--trending` sobre una base temporal.
9. Probar reinicio y lectura desde una segunda sesión.
10. Probar `read`, `read-all` y summary.
11. Probar retención en dry-run.
12. Revisar documentación, inventario y paths.
13. Confirmar que no se modificó `NotificationEvent` innecesariamente.
14. Confirmar que no se persiste ninguna identidad personal en la comunidad.
15. Registrar limitaciones reales, especialmente si PostgreSQL no pudo ejecutarse localmente.

### Evidencia mínima que debe acompañar el cierre

```text
- salida de alembic heads/check
- resultado de tests de migración
- resultado de tests de persistencia
- resultado de tests de inbox/worker
- resultado de suite backend
- resultado de ruff
- evidencia de reinicio/multi-sesión
- evidencia de read/read-all/summary
- evidencia de dry-run de retención
- diff --check
```

No usar “parece correcto” como evidencia. Cada criterio debe quedar respaldado por un test, comando, inspección SQL o verificación operativa concreta.

---

## 18. Fuera de alcance

Esta entrega no implementa:

- follows explícitos de rutas;
- notificaciones por email de tendencias;
- perfiles sociales;
- comentarios o chat;
- reputación de usuarios;
- gamificación;
- Redis obligatorio;
- microservicio de comunidad;
- ML de recomendaciones;
- mediana de precios;
- popularidad ponderada por Watches/follows;
- migración de SQLite a PostgreSQL;
- cambios visuales en frontend.

Estas funcionalidades pueden planificarse después de que la persistencia y el inbox sean deterministas, privados y verificables.
