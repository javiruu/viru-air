# Runbook: Notification Worker (F3C.2 minimo)

## Objetivo
Ejecutar procesamiento periodico minimo de notificaciones pendientes sin infraestructura pesada.

Comando del worker:

```bash
cd backend
python -m app.worker.notifications --once
```

## Variables de entorno
- `NOTIFICATION_WORKER_ENABLED` (default: `false`)
- `NOTIFICATION_WORKER_BATCH_SIZE` (default: `50`)
- `NOTIFICATION_WORKER_INTERVAL_SECONDS` (default: `60`)

Prerequisito:
- Base de datos migrada al head actual de Alembic (`0041_add_community_trending_snapshots` en esta versión).

Notas:
- El worker **no se activa automaticamente** al levantar la API web.
- `NOTIFICATION_WORKER_ENABLED=false` mantiene modo seguro; el comando sigue ejecutable de forma manual.

## Ejecucion de una pasada
```bash
cd backend
python -m app.worker.notifications --once
```

Para generar un snapshot de tendencias comunitarias persistentes:

```bash
cd backend
python -m app.worker.notifications --trending
```

El ciclo publica un snapshot global de rutas; el inbox solo lo muestra para Watches activas del usuario. Un snapshot vacío es válido y elimina lógicamente las señales anteriores. El evento `notification_trending_cycle` registra `routes_persisted`, no notificaciones individuales. La lectura no depende de caché de proceso y sobrevive al reinicio del worker.

Para inspeccionar el snapshot visible sin generar uno nuevo, ejecutar una consulta equivalente sobre la base configurada:

```sql
SELECT s.id, s.reporting_date, s.calculated_at_utc, s.expires_at_utc,
       r.origin_iata, r.destination_iata, r.rank, r.search_count
FROM community_trending_snapshot AS s
LEFT JOIN community_trending_snapshot_route AS r ON r.snapshot_id = s.id
WHERE s.status = 'published'
  AND s.expires_at_utc > CURRENT_TIMESTAMP
ORDER BY s.calculated_at_utc DESC, r.rank ASC;
```

La retención y el worker no requieren una caché de proceso.

Opcional con limite personalizado:
```bash
python -m app.worker.notifications --once --limit 25
```

## Ejecucion en loop local
```bash
cd backend
python -m app.worker.notifications --loop --limit 50 --sleep-seconds 60
```

## Interpretacion de resultados (logs estructurados)
Evento principal: `notification_worker_cycle`

Campos relevantes:
- `processed`: eventos evaluados en el ciclo
- `delivered`: entregados/enviados correctamente
- `failed`: fallidos sin mas reintento
- `retried`: reprogramados para reintento o quiet hours
- `skipped`: fallidos agotados acumulados en base

El log evita PII sensible:
- no emails completos en payload del log;
- no tokens;
- no payloads sensibles de notificacion.

## Que respeta este worker
- `next_attempt_at` (no procesa eventos no vencidos)
- `max_attempts` y retries
- quiet hours para canal email
- digest/grouping y semantica actual del pipeline

Todo se delega en `notification_service` para evitar logica duplicada.

## Que no hace todavia
- No incluye scheduler distribuido de produccion.
- No incluye proveedor de email real (solo stub actual).
- No despliega infraestructura de colas (Celery/RQ/APScheduler).
