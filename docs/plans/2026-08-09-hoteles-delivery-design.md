# Diseño: delivery hotelero independiente

**Fecha:** 2026-08-09
**Estado:** aprobado para implementación
**Área:** backend / H28 / H41

## Objetivo

Separar la generación de `HotelAlertEvent` de su delivery, empezando por un canal `in_app` local y verificable, sin mezclar el dominio de vuelos ni activar canales externos.

## Decisión

Se crea un ledger `HotelNotificationDelivery` independiente de `NotificationEvent`:

```text
HotelAlertEvent autorizado
  -> HotelNotificationDelivery queued
  -> worker de notificaciones
  -> in_app materializado
  -> delivered o retryable failure
```

Cada fila conserva `source_event_id`, `recipient_user_id`, canal, versión de plantilla, clave de idempotencia y estado operativo. El contenido no se copia a la cola: se resuelve desde el evento fuente autorizado.

## Ownership y seguridad

- Solo se generan intents para eventos del run actual con `user_id` no nulo.
- Si existe `rule_id`, la regla debe pertenecer al mismo usuario.
- Eventos legacy sin usuario/regla atribuible no generan delivery.
- `hotel_id` nunca es evidencia suficiente de ownership.
- La clave de idempotencia es un hash de evento, usuario, canal y versión; no contiene PII.
- El ledger no se expone en el payload público del inbox en este incremento.

## Canales y estados

- `in_app`: único canal activo; el worker marca la materialización local como `delivered`.
- `email`: no se crea ni se envía; consentimiento, proveedor, sandbox y unsubscribe quedan pendientes.
- Estados implementados: `queued`, `delivered`, `failed`.
- Los fallos se reprograman con el backoff existente y `next_attempt_at`; tras el máximo quedan `failed`.

## Transacciones e idempotencia

Al terminar un `run_hotel_sweep`, los eventos creados por ese `provider_run_id` y sus intents se guardan antes del commit final. La restricción única de idempotencia permite reejecutar la materialización sin duplicar entregas.

El inbox sigue derivándose de `HotelAlertEvent`: delivery y lectura son estados distintos. Un evento puede estar visible en inbox aunque el worker esté desactivado.

## Límites

- No se crean `NotificationEvent` para hoteles.
- No se añade provider externo ni llamada de red.
- No se implementan push, email, digest, dead-letter físico ni dashboard.
- Sweeps globales no heredan `client_event_id`.
