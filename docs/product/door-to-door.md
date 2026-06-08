# Puerta a puerta

**Estado:** vivo
**Última revisión:** 2026-05-21
**Fuente de verdad:** sí
**Área:** producto

## Resumen

`Puerta a puerta` ayuda a decidir un vuelo guardado con el viaje completo: origen terrestre, aeropuerto de salida, vuelo, aeropuerto de llegada y destino final.

La pregunta que responde no es solo “¿el vuelo es barato?”, sino:

- cuánto cuesta el viaje completo;
- cuánto tarda;
- cuánto margen queda antes del embarque;
- cuántos cambios requiere;
- qué fuentes y nivel de confianza sostienen cada dato.

## Entrada principal

La feature vive como apartado privado en `/puerta-a-puerta` y puede recibir un vuelo contextual desde Watchlist con `?watchId=...`.

En `/watchlist`, el detalle de ruta muestra una sugerencia contextual para abrir Puerta a puerta con el vuelo seleccionado.

## Flujo V1.1

1. El usuario elige un vuelo guardado.
2. Configura origen terrestre y destino final.
3. Ajusta margen, pasajeros, equipaje, precio máximo y filtros esenciales.
4. Calcula ruta completa.
5. Revisa opción recomendada, alternativas, timeline, radar abstracto, fuente y confianza.
6. Puede marcar una opción como elegida; al volver a calcular, Viru la recupera si sigue disponible.

## Destino final

El destino final puede ser:

- ciudad;
- dirección;
- estación;
- ubicación guardada;
- solo aeropuerto.

Cuando el destino es `solo aeropuerto`, la ruta termina en el aeropuerto de llegada y se omite el tramo terrestre posterior.

## Datos, filtros y confianza

V1.2 queda en estado híbrido honesto:

- mock normalizado para UX estable;
- primer paso real parcial con providers deeplink (`blablacar_deeplink`, `goopti_deeplink`);
- primer provider API real parcial (`google_routes`) para duración/distancia sin precio confirmado;
- primer provider open_data parcial (`gtfs_transit`) para horarios reales de transporte público sin precio confirmado;
- suggestions reales opcionales (`google_places`) bajo API key y flags;
- sin scraping real activo por defecto.

Cada dato debe indicar fuente y confianza:

- `source_type`: `api`, `open_data`, `aggregator`, `deeplink`, `scraper`, `mock`;
- `confidence`: `live`, `cached`, `estimated`, `deeplink`, `unavailable`;
- proveedor;
- fecha de comprobación;
- expiración cuando aplique.

Los filtros de transporte y `max_price` pueden ocultar opciones:
- `allow_rideshare=false` oculta opciones de BlaBlaCar.
- `allow_shuttle=false` oculta opciones de GoOpti.
- `airport_only` oculta opciones de GoOpti (tramo terrestre de llegada).
- `public_transport_only` prioriza transporte público (GTFS) y oculta opciones de rideshare/shuttle.
- `allow_bus=false` oculta opciones GTFS con `mode=bus`.
- `allow_train=false` oculta opciones GTFS con `mode=train` o `mode=metro`.
- `max_price` no filtra deeplinks ni opciones open_data sin precio confirmado; los mantiene con warning `UNCONFIRMED_PRICE`.

Si no queda ninguna opción válida, la UI muestra `NO_COVERAGE` con ajustes sugeridos: subir margen, permitir shuttle/coche compartido o terminar solo en aeropuerto.

Si no hay providers reales activos y el mock está desactivado, la UI debe mostrar explícitamente “Sin cobertura real todavía” (`NO_REAL_PROVIDER_COVERAGE`), evitando rutas inventadas.

Los scrapers existen solo como arquitectura opt-in y están apagados por defecto.

## Persistencia

V1.1 persiste:

- ubicación global guardada por usuario, solo con consentimiento;
- historial de cálculos durante 90 días;
- opción elegida por cálculo.

El historial guarda resumen e inputs, no payloads completos de proveedor.

## Identidad visual

La UI debe mantener identidad Viru:

- cálida y premium;
- aeronáutica, no mapa genérico;
- compatible dark/light;
- con radar abstracto, timeline, boarding-pass cues, IATA y panel de decisión;
- con jerarquía clara entre recomendada, alternativas, ruta visual, desglose y fuentes.

## Base parcial inspirada en Google Maps

V1.3 incorpora un "Hub de capas y herramientas" dentro de `/puerta-a-puerta` para mantener una base completa parcial sin romper el foco actual de timeline + decision.

El hub organiza capacidades por bloques:

- capas del mapa;
- rutas alternativas;
- explorar zona de llegada;
- verificacion visual;
- guardados.

Cada capacidad declara estado y transparencia operacional:

- `available` (real);
- `partial` (parcial funcional);
- `planned` (sembrado para fases siguientes);
- `unavailable` (no disponible en entorno actual).

La implementacion mantiene el enfoque hibrido honesto:

- reutiliza providers reales existentes (`google_routes`, `google_places`, `gtfs_transit`, deeplinks externos);
- evita simular cobertura total;
- muestra limites y pendientes de forma explicita por capacidad.
