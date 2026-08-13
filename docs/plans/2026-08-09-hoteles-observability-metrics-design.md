# Diseño H41 — Métricas hoteleras persistentes agregadas

**Fecha:** 2026-08-09
**Estado:** aprobado para implementación
**Área:** backend / observabilidad / H41

## Objetivo

Persistir una vista agregada, segura y de baja cardinalidad del flujo hotelero para que operaciones pueda consultar runs, eventos de alerta y delivery local sin depender de logs en memoria ni registrar identificadores privados.

## Decisión

Crear `HotelDailyMetric`, con una fila por día, métrica, provider y outcome. La clave única será `(metric_date, metric_name, provider, outcome)`.

Métricas iniciales:

- `sweep_run`: estado terminal del `HotelProviderRun` (`completed`, `partial`, `failed`, `skipped`);
- `alert_event`: `created` cuando se generan eventos hoteleros autorizados;
- `hotel_delivery`: `delivered`, `retried` o `failed` para el ledger `HotelNotificationDelivery`.

La tabla no guarda `user_id`, `hotel_id`, `rule_id`, `event_id`, intent browser, email, payload ni URL.

## Actualización y transacciones

Un servicio `record_hotel_daily_metric` normalizará únicamente nombres/outcomes allowlisted y hará upsert atómico con dialectos SQLite/PostgreSQL. El caller decide la transacción; no se hará commit implícito. El sweep registrará su estado terminal; el dispatcher registrará el resultado de cada delivery. Las métricas se publican solo junto con el commit de la operación que representan.

## Consulta operativa

Se añadirá `GET /api/v1/admin/hotels/observability`, protegido por `require_admin`, con una ventana máxima acotada y filtros opcionales de provider/metric/outcome. La respuesta será agregada y no expondrá claves de alta cardinalidad.

## Límites

No se añade un servicio externo, dashboard comercial, tracing distribuido, SLO activo, retención automática ni delivery externo. La retención queda como siguiente tarea operativa explícita.

## Pruebas

- upsert repetido incrementa una sola clave;
- claves no allowlisted se rechazan;
- SQLite y migración quedan alineados;
- delivery local actualiza la métrica en éxito, retry y fallo terminal;
- sweep registra estados terminales;
- endpoint requiere admin, limita ventana y no devuelve PII.
