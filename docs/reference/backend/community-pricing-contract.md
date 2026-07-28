# Community Pricing Backend Contract

**Estado:** vivo
**Última revisión:** 2026-07-28
**Fuente de verdad:** sí
**Área:** reference/backend

## Objetivo

Community Pricing recoge el precio final por viajero después de un vuelo
comprado o caducado y publica únicamente estadísticas anónimas de ruta.
No sustituye ni amplía Fare Memory.

## Elegibilidad

Una Watch es elegible cuando:

- tiene estado `purchased`; o
- `travel_date_local` es anterior a la fecha actual.

`GET /api/v1/watchlist` y `GET /api/v1/watchlist/{watch_id}` incluyen:

```json
{
  "community_pricing": {
    "eligible": true,
    "trigger_reason": "purchased",
    "response": null,
    "aggregate": {
      "sample_size": 2,
      "minimum_sample_size": 3,
      "is_public": false,
      "min_price": null,
      "max_price": null,
      "currency": "EUR"
    }
  }
}
```

`response` es siempre la respuesta de la persona autenticada para esa Watch.
No se devuelve ninguna respuesta individual de otras cuentas.

## Mutaciones

Todos los endpoints requieren autenticación y verifican que la Watch pertenece
a `current_user.id`.

### Marcar como comprado

`POST /api/v1/watchlist/{watch_id}/mark-purchased`

- cambia el estado a `purchased`;
- devuelve `watch_id`, `status` y `community_pricing`;
- no crea una respuesta ni presume que la persona voló.

### Crear o corregir una respuesta

`PUT /api/v1/watchlist/{watch_id}/community-price`

Vuelo realizado:

```json
{
  "flew": true,
  "price_per_traveler": 78.5,
  "currency": "EUR"
}
```

Vuelo no realizado:

```json
{
  "flew": false,
  "price_per_traveler": null,
  "currency": "EUR"
}
```

Reglas:

- una única respuesta por Watch;
- `flew=true` exige un precio mayor que 0 y menor o igual que 100000, con
  máximo dos decimales;
- `flew=false` exige `price_per_traveler=null`;
- EUR es la única moneda aceptada;
- una Watch no elegible devuelve `409 community_price_not_eligible`.

### Eliminar una respuesta

`DELETE /api/v1/watchlist/{watch_id}/community-price`

Devuelve `{"status":"ok"}`. Si no existe una respuesta propia, devuelve
`404 community_price_not_found`.

## Agregación pública

La clave de agregación es la ruta direccional exacta
`(origin_iata, destination_iata)`: `MAD → DUB` no se mezcla con `DUB → MAD`.

Se incluyen únicamente:

- respuestas con `flew=true`;
- precios no nulos;
- vuelos cuya fecha está entre hoy menos 365 días y hoy, ambos inclusive.

`sample_size` cuenta viajeros distintos, no respuestas ni Watches. El rango
solo es público con `sample_size >= 3`. Por debajo del umbral:

- `is_public=false`;
- `min_price=null`;
- `max_price=null`.

Con el umbral alcanzado, se exponen únicamente `sample_size`, `min_price`,
`max_price` y `currency`. No se exponen identificadores, precios individuales,
fechas de respuesta ni vuelos concretos.

Una Watch marcada como comprada para una fecha futura puede recoger la respuesta,
pero su precio no entra en el agregado hasta la fecha del viaje.

## Persistencia

La tabla `community_price_report` guarda:

- referencia a la Watch y a su propietario;
- motivo de activación (`purchased` o `expired`);
- si voló;
- precio por viajero opcional;
- moneda y timestamps internos.

Las restricciones de base de datos mantienen una respuesta por Watch y
coherencia entre `flew` y `price_per_traveler`.
