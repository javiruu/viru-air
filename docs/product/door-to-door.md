# Puerta a puerta

**Estado:** vivo
**Última revisión:** 2026-05-20
**Fuente de verdad:** sí
**Área:** producto

## Resumen

`Puerta a puerta` ayuda a decidir un vuelo guardado con el viaje completo: origen terrestre, aeropuerto de salida, vuelo, aeropuerto de llegada y destino final.

La pregunta que responde no es solo “¿el vuelo es barato?”, sino:

- cuánto cuesta el viaje completo;
- cuánto tarda;
- cuánto margen queda antes del embarque;
- qué riesgo operativo tiene;
- qué fuentes y nivel de confianza sostienen cada dato.

## Entrada principal

La feature vive como apartado privado en `/puerta-a-puerta` y puede recibir un vuelo contextual desde Watchlist con `?watchId=...`.

En `/watchlist`, el detalle de ruta muestra una sugerencia contextual para abrir Puerta a puerta con el vuelo seleccionado.

## Flujo V1

1. El usuario elige un vuelo guardado.
2. Configura origen terrestre y destino final.
3. Ajusta margen, pasajeros, equipaje y filtros esenciales.
4. Calcula ruta completa.
5. Revisa opción recomendada, alternativas, timeline, radar abstracto, fuente y confianza.
6. Puede marcar una opción como elegida.

## Destino final

El destino final puede ser:

- ciudad;
- dirección;
- estación;
- ubicación guardada;
- solo aeropuerto.

Cuando el destino es `solo aeropuerto`, la ruta termina en el aeropuerto de llegada y se omite el tramo terrestre posterior.

## Datos y confianza

V1 usa datos mock normalizados para entregar una experiencia estable sin credenciales externas.

Cada dato debe indicar fuente y confianza:

- `source_type`: `api`, `open_data`, `aggregator`, `deeplink`, `scraper`, `mock`;
- `confidence`: `live`, `cached`, `estimated`, `deeplink`, `unavailable`;
- proveedor;
- fecha de comprobación;
- expiración cuando aplique.

Los scrapers existen solo como arquitectura opt-in y están apagados por defecto.

## Persistencia

V1 persiste:

- ubicación global guardada por usuario, solo con consentimiento;
- historial de cálculos durante 90 días;
- opción elegida por cálculo.

El historial guarda resumen e inputs, no payloads completos de proveedor.

## Identidad visual

La UI debe mantener identidad Viru:

- cálida y premium;
- aeronaútica, no mapa genérico;
- compatible dark/light;
- con radar abstracto, timeline, boarding-pass cues, IATA y panel de decisión;
- con jerarquía clara entre recomendada, alternativas, ruta visual, desglose y fuentes.
