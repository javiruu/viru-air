# ADR-005 Seguimiento operacional de vuelos desde Watchlist

- Estado: Aprobado
- Fecha: 2026-07-21
- Relacionado: `ADR-004-flight-tracking-hub.md`
- Enmendado por: `ADR-006-zero-cost-operational-provider-fallback.md`

## Contexto

Watchlist representa hoy una ruta y una fecha, y conserva historico de precios por usuario. Fare Memory ya conoce ofertas y, cuando el proveedor lo entrega, una identidad de vuelo con numero, horario y `flight_instance_fingerprint`. Sin embargo, la Watch no conserva esa identidad y el producto no dispone de un contrato para estado operacional, retrasos, terminales, puertas o posicion.

La expresion "tracking" de ADR-004 se refiere a frescura de busqueda, cache y revalidacion de precios. El seguimiento operacional necesita otra memoria y otra cadencia, pero debe integrarse en el mismo hub sin crear una segunda Watchlist ni degradar clientes existentes.

## Decision

1. `FlightWatch` sigue siendo la entidad de usuario y mantiene su unicidad por usuario, ruta y fecha.
2. Una Watch puede tener cero o varias piernas exactas en `WatchTrackedFlightLeg`. Quick Search es la fuente preferente de esa identidad; una Watch creada manualmente permanece valida aunque no tenga piernas.
3. Cada pierna usa un `flight_instance_fingerprint` compatible con Fare Memory. No se infiere una identidad cuando hay mas de un vuelo plausible.
4. `FlightOperationalSnapshot` conserva observaciones compartidas por identidad de vuelo. No pertenece a un usuario y no almacena payloads crudos del proveedor.
5. El proveedor operacional se oculta tras un contrato propio. La primera integracion es Aviationstack, activada solo con configuracion de entorno. OpenSky no es el proveedor primario porque no ofrece horarios, retrasos, terminales o puertas y limita el uso comercial de su API publica.
6. `GET /api/v1/watchlist/{watch_id}/live` autoriza mediante la Watch, reutiliza snapshots frescos y solo consulta al proveedor cuando la politica de frescura lo permite.
7. La respuesta siempre distingue `coverage`, `freshness`, `provider_status` y el estado operacional. Ausencia de clave, identidad, cobertura o posicion no se presenta como error general de Watchlist.
8. El frontend consulta solo la Watch seleccionada, pausa polling con la pestaña oculta, conserva el ultimo dato valido durante errores transitorios y no anima una posicion estimada como si fuera real.

## Alternativas consideradas

### Polling del proveedor desde el navegador

Descartado: expone credenciales, duplica consumo por pestaña, rompe el control de cuota y acopla la UI a un proveedor.

### Endpoint sin persistencia de identidad

Descartado: una ruta/fecha puede contener varias salidas y conexiones. Resolver por ruta en cada llamada produciria coincidencias ambiguas y cambios de vuelo invisibles.

### Extender `PriceSnapshot` con campos operacionales

Descartado: mezcla historico privado de precio con telemetria compartida, cadencias distintas y politicas de retencion incompatibles.

### OpenSky como unica fuente

Descartado como fuente primaria: es util para ADS-B y posicion, pero no cubre el contrato completo y su API publica no esta orientada a uso comercial. Puede incorporarse despues como enriquecimiento de posicion bajo licencia adecuada.

## Consecuencias

- Las Watches antiguas y las creadas manualmente siguen funcionando sin migracion de datos obligatoria.
- Guardar desde Quick Search gana identidad operacional sin cambiar la semantica de precio.
- Los itinerarios con conexiones se modelan como piernas ordenadas.
- La cuota del proveedor se controla en backend con TTL, cooldown y cache compartida.
- El producto puede mostrar estado y horario aunque una posicion no este disponible.
- Se introduce una migracion y un nuevo contrato API; requieren pruebas de upgrade/downgrade, autorizacion, cuotas, polling e i18n.

## Validacion posterior

- Probar migracion sobre SQLite de test y PostgreSQL de desarrollo cuando este disponible.
- Probar Watches antiguas, manuales, directas, con varias piernas y con identidad incompleta.
- Verificar contrato con proveedor simulado y, si existe clave local, una consulta real sin registrar la clave ni el payload.
- Verificar `/watchlist` en temas claro/oscuro y 375, 768 y 1440 px.
- Auditar que ninguna respuesta expone datos de otros usuarios ni payloads crudos.
