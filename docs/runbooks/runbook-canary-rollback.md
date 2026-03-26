# Runbook Canary y Rollback

## Canary
1. Desplegar backend al 5% de trafico.
2. Verificar p95, 5xx, errores de auth y jobs 15 min.
3. Subir a 25%, repetir validacion.
4. Subir a 50%, repetir validacion.
5. Si no hay desviaciones, subir a 100%.

## Rollback
1. Detener promoción de canary.
2. Volver a imagen estable previa.
3. Desactivar feature flags de release.
4. Validar salud (`/health`, `/ready`) y errores p95/5xx.
5. Ejecutar postmortem corto con causa y acción preventiva.
