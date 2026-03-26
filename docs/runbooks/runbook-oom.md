# Runbook OOM

1. Confirmar evento OOMKilled en servicio afectado.
2. Reducir concurrencia de workers y activar backpressure.
3. Priorizar colas critical/normal y pausar low.
4. Escalar horizontalmente si hay capacidad.
5. Analizar diff de release y perfilar memoria.
6. Aplicar rollback por flag o versión si procede.
