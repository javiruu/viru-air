# Runbook: DB Retention Automation (Cycle 7)

## Objetivo
Automatizar y operar con seguridad la poda de tablas de crecimiento del backend:
- `price_snapshot`
- `notification_event`
- `security_activity`
- `idempotency_record`
- `community_trending_snapshot` y sus rutas `community_trending_snapshot_route`

Script principal: `backend/scripts/db_retention.py`  
Runner recomendado: `backend/ops/db-retention/run-db-retention.sh`

---

## Guard rails de seguridad (anti-borrado agresivo)
El script valida mínimos de retención antes de tocar datos:
- `price_snapshot_days >= 30`
- `notification_event_days >= 30`
- `security_activity_days >= 30`
- `idempotency_days >= 3`
- `community_trending_days >= 30`
- `community_trending_building_hours > 0`

Si una ventana es menor al mínimo:
1. termina con exit code `1`
2. registra `db_retention.run_failed`
3. escribe alerta JSON en `DB_RETENTION_ALERT_FILE` (por defecto `backend/logs/alerts/db-retention-failure.json`)

Además existe `--dry-run` para inspeccionar candidatos sin borrar.

---

## Observabilidad y logging
Se genera JSONL en stdout + archivo `DB_RETENTION_LOG_FILE` (por defecto `backend/logs/db-retention.log`), con:
- estado (`run_started`, `table_completed`, `run_completed`, `run_failed`)
- duración (`duration_ms`)
- candidatos y eliminados por tabla
- batches
- modo `dry_run`

### Señal explícita de fallo
- **archivo alerta**: `DB_RETENTION_ALERT_FILE`
- **webhook opcional**: `DB_RETENTION_ALERT_WEBHOOK` (POST JSON)
- **exit code no-cero** para cron/systemd

---

## Runner operativo
`backend/ops/db-retention/run-db-retention.sh` incluye:
- lock con `flock` (`db-retention.lock`) para evitar ejecuciones solapadas
- validación de runtime Python (`DB_RETENTION_PYTHON`, por defecto `.venv/bin/python`)
- export de rutas de logs/alertas por defecto

Ejecución manual:

```bash
cd backend
ops/db-retention/run-db-retention.sh --dry-run
ops/db-retention/run-db-retention.sh
```

La limpieza comunitaria usa dos políticas independientes:

- snapshots `published`: se conservan por defecto 90 días, controlados por `--community-trending-days`;
- snapshots `building`: se eliminan si tienen más de 1 hora, controlados por `--community-trending-building-hours`.

En `--dry-run` se informa de candidatos, rutas y estados `community_trending` sin borrar nada. En modo apply se eliminan primero los estados comunitarios que ya no pueden ser representados por ninguna snapshot retenida, después las rutas y finalmente las snapshots. Los estados de otras fuentes nunca se eliminan aunque compartan `source_id`.

La limpieza comunitaria emite `db_retention.community_trending_completed` con candidatos, eliminados, batches y duración; no incluye usuarios, emails ni payloads privados.

---

## Instalación recomendada (systemd timer)
Archivos plantilla:
- `backend/ops/db-retention/db-retention.service`
- `backend/ops/db-retention/db-retention.timer`

### Pasos
```bash
sudo cp backend/ops/db-retention/db-retention.service /etc/systemd/system/
sudo cp backend/ops/db-retention/db-retention.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now db-retention.timer
sudo systemctl status db-retention.timer
```

Ver próximos runs:
```bash
systemctl list-timers db-retention.timer
```

Ejecutar ahora (prueba controlada):
```bash
sudo systemctl start db-retention.service
sudo journalctl -u db-retention.service -n 100 --no-pager
```

---

## Opción alternativa (cron)
Plantilla: `backend/ops/db-retention/db-retention.cron`

Instalar:
```bash
crontab backend/ops/db-retention/db-retention.cron
crontab -l | grep db-retention
```

---

## Operación diaria
1. Revisar último run:
   - `tail -n 50 backend/logs/db-retention.log`
2. Confirmar no hay alerta:
   - `test ! -f backend/logs/alerts/db-retention-failure.json`
3. Si hay fallo, revisar:
   - evento `db_retention.run_failed`
   - payload del archivo de alerta

---

## Rollback
Si hay comportamiento inesperado:

### 1) Pausar automatización
**systemd**
```bash
sudo systemctl disable --now db-retention.timer
```

**cron**
```bash
crontab -l > /tmp/cron.bak
crontab -l | grep -v db-retention | crontab -
```

### 2) Volver a modo seguro (sin borrado)
Ejecutar únicamente en `dry-run` hasta validar:
```bash
cd backend
ops/db-retention/run-db-retention.sh --dry-run
```

### 3) Recuperación de datos (si aplica)
La poda es destructiva; recuperar desde backup/snapshot de DB según política del entorno.

### 4) Rehabilitar tras validación
Reactivar timer o cron cuando se confirme estabilidad.

---

## Variables útiles
- `DB_URL`
- `DB_RETENTION_PYTHON`
- `DB_RETENTION_LOG_DIR`
- `DB_RETENTION_LOG_FILE`
- `DB_RETENTION_ALERT_FILE`
- `DB_RETENTION_ALERT_WEBHOOK`
