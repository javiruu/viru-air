# Diseño: intent estable en detalle, rates y parity hoteleros

**Fecha:** 2026-08-08
**Estado:** aprobado para implementación
**Área:** frontend / API / observabilidad H41

## Objetivo

Reutilizar el `client_event_id` opaco de la búsqueda hotelera al cargar el hotel seleccionado y sus lecturas secundarias (`detail`, `rates` y `parity`), sin crear `HotelProviderRun` ni persistencia artificial para endpoints read-only.

## Decisión

La propagación será explícita:

```text
useHotelSearch intentId
  -> HotelRadarPage
  -> useHotelDetail(selectedHotelId, intentId)
  -> getHotelDetail/getHotelRates/getHotelParity
  -> x-client-event-id + x-correlation-id por request
```

Cada llamada conservará su propio `x-correlation-id`; las tres compartirán el mismo `x-client-event-id` de la búsqueda que originó la selección. Si un caller legacy no aporta intent, las funciones API seguirán funcionando sin ese header.

## Límites

- No se crea `HotelProviderRun` para detalle, rates o parity.
- No se escribe una tabla de requests de lectura.
- No se usa el intent como label métrico.
- El backend solo transporta el contexto ya aceptado por el middleware y los logs/error envelopes existentes.
- No se agrupan todavía inbox, delivery ni otras superficies secundarias.

## Flujo y cancelación

`useHotelDetail` conserva el `AbortController` actual. Al cambiar de hotel o desmontar, las tres requests se abortan juntas. La identidad del intent cambia únicamente cuando comienza una nueva búsqueda; seleccionar otro resultado dentro de la misma lista reutiliza el intent de esa búsqueda.

## Errores y privacidad

Los IDs siguen siendo opacos y acotados por la normalización existente. Los errores mantienen `correlation_id` y `client_event_id` devueltos por API. No se incluyen PII, hotel IDs ni preferencias en el intent.

## Pruebas

- Headers reales de las tres funciones API.
- Mismo intent y correlaciones distintas en las tres requests.
- Compatibilidad de callers legacy.
- Cancelación del hook de detalle conserva las tres señales.
- Aislamiento entre dos intents concurrentes.
- Backend conserva respuesta/error y no crea runs para lecturas.
