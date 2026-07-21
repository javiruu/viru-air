# ADR-006 Fallback operacional multi-proveedor sin coste inesperado

- Estado: Aprobado
- Fecha: 2026-07-21
- Relacionado: `ADR-005-live-operational-flight-tracking.md`

## Contexto

El primer corte de seguimiento operacional ocultó Aviationstack tras un contrato reemplazable, pero solo registró ese adapter. Una Watch próxima puede necesitar dos clases de datos distintas:

- horarios, estado, retrasos, terminales y puertas;
- posición, altitud, velocidad, rumbo y estado en tierra.

Los proveedores no cubren ambas clases por igual y sus cuotas no comparten unidad ni ventana. OpenSky usa créditos diarios; Aviationstack usa solicitudes mensuales; AeroDataBox usa unidades mensuales con coste por endpoint; Amadeus conserva cuota gratuita por cuenta pero puede facturar el exceso en producción; FlightAware factura por consulta con un pequeño crédito gratuito; ADS-B Exchange requiere suscripción. El requisito principal es que Viru no produzca un cargo por agotar una cuota.

## Restricciones y atributos de calidad

- cero coste inesperado por defecto;
- degradación parcial: estado sin posición y posición sin puerta siguen siendo útiles;
- identidad exacta: no mezclar observaciones de vuelos ambiguos;
- consumo mínimo: no consultar seis proveedores cuando uno ya cubre el dato;
- estado de cuota persistente entre procesos y reinicios;
- adapters reemplazables, sin credenciales en logs, DB o respuestas;
- compatibilidad con el contrato público de ADR-005 y con SQLite/PostgreSQL.

No es objetivo crear una verdad aeronáutica certificada, prometer cobertura global ni eludir licencias o límites de terceros.

## Opciones consideradas

### A. Fallback secuencial de fuentes completas

Cada proveedor intenta devolver una observación completa y el primero que responde gana.

Ventajas: implementación pequeña y un único origen por snapshot. Inconvenientes: OpenSky y ADS-B Exchange nunca pueden ganar por no aportar puertas/horarios; una buena observación de estado sin posición impide enriquecer el mapa; el orden mezcla capacidad, coste y calidad en una sola dimensión.

### B. Carrera paralela de todos los proveedores

Se lanzan todos y se fusiona el resultado más completo.

Ventajas: menor latencia y cobertura máxima por petición. Inconvenientes: quema todas las cuotas, multiplica llamadas duplicadas, complica cancelación y hace imposible garantizar coste cero. Se descarta.

### C. Orquestador secuencial por capacidades y presupuesto

Primero busca estado/horarios. Solo si la observación elegida carece de posición activa busca enriquecimiento ADS-B. Cada intento reserva su coste en un ledger persistente antes de salir a red; un límite local, un `429`, un `402` o un bloqueo remoto abre el circuito hasta la siguiente ventana o `Retry-After`.

Ventajas: usa el mínimo de cuota, permite combinar Amadeus con OpenSky, conserva fallback real y hace visible por qué se saltó un proveedor. Inconvenientes: añade un ledger y reglas explícitas de fusión. Es la opción elegida.

## Decisión

1. Mantener `OperationalFlightProvider` como frontera de cada adapter y añadir metadatos de capacidad: `status_schedule` y `position`.
2. Registrar los seis adapters solicitados:
   - Amadeus: estado/horarios mediante OAuth2;
   - OpenSky: posición ADS-B, preferentemente por ICAO24;
   - Aviationstack: estado/horarios y posición cuando exista;
   - AeroDataBox: estado/horarios y posición;
   - FlightAware AeroAPI: estado/horarios y última posición;
   - ADS-B Exchange: posición por ICAO24.
3. Ejecutar estado/horarios en orden configurable y detenerse en la primera coincidencia exacta. Ejecutar posición solo si falta y existe identidad segura suficiente.
4. Fusionar únicamente campos ausentes. Una fuente de enriquecimiento nunca sobrescribe horarios, estado o identidad ya observados por la fuente primaria. `provider` conserva la procedencia combinada.
5. Persistir por proveedor y ventana el consumo reservado, el bloqueo hasta y su motivo. El límite efectivo permanece en configuración versionada. Reservar antes de la llamada evita que procesos concurrentes rebasen el techo local; una llamada fallida puede consumir reserva, favoreciendo seguridad económica sobre aprovechamiento total.
6. Activar `LIVE_FLIGHT_ZERO_COST_ONLY=true` por defecto. En este modo:
   - OpenSky puede operar sin credenciales dentro de su presupuesto diario conservador;
   - Aviationstack y AeroDataBox operan solo con key y techo local inferior a su cuota gratuita;
   - Amadeus requiere credenciales y un techo mensual explícito obtenido del dashboard de la cuenta;
   - los adapters FlightAware y ADS-B Exchange existen, pero el registro los excluye porque no existe un número de llamadas universal que garantice coste cero.
7. Los proveedores de pago solo pueden activarse con una opt-in explícita separada; añadir una key no basta.
8. Tratar `401/403` como configuración inválida, `402` como proveedor de pago bloqueado, `429` según `Retry-After`, `5xx/timeout` como indisponibilidad transitoria y cero coincidencias como falta de cobertura. Ninguno rompe Watchlist.
9. Conservar snapshots y cooldowns de ADR-005. El ledger protege presupuesto; el refresh lock evita trabajo duplicado. Son responsabilidades distintas.

## Consecuencias

- Viru obtiene fallback útil sin convertir cada refresco en seis consultas.
- La cobertura puede ser compuesta, por ejemplo `amadeus+opensky`.
- Agotar una cuota degrada al siguiente proveedor en lugar de fallar toda la feature.
- La garantía económica depende de límites locales conservadores y del modo zero-cost. Cambiar esos límites o activar proveedores de pago es una decisión operativa explícita.
- Los adapters sin credenciales se prueban con contratos HTTP locales; una prueba real requiere cuentas del usuario y no forma parte del arranque normal.

## Riesgos y mitigaciones

- **Cuota compartida fuera de Viru:** el ledger local no conoce llamadas hechas desde otras apps. Mitigación: reservar margen y honrar headers de saldo cuando existan.
- **Identidad ADS-B ambigua:** un número IATA no siempre coincide con callsign ICAO. Mitigación: preferir ICAO24/callsign entregado por una fuente exacta y no elegir coincidencias múltiples.
- **Cambios de planes:** precios y cuotas pueden variar. Mitigación: límites configurables, documentación fechada y respuestas remotas como fuente de verdad.
- **Fusión incoherente:** dos fuentes pueden observar instantes distintos. Mitigación: no sobrescribir el primario y rechazar posición futura, parcial o fuera de límites.

## Validación posterior

- prueba roja/verde de reserva concurrente, rotación de ventana, `429`, `402` y agotamiento local;
- pruebas contractuales de los seis adapters con servidor HTTP local y payloads oficiales mínimos;
- prueba de orquestación: fallback de estado, enriquecimiento de posición y no llamada cuando el primario ya tiene posición;
- upgrade de Alembic limpio y recuperación de tablas ORM huérfanas en 0034;
- smoke autenticado del endpoint con providers simulados y arranque real mediante `VIRU_PANEL.bat`;
- revisión periódica de cuotas/licencias antes de cambiar límites por defecto.

## Fuentes oficiales consultadas

- [Amadeus On-Demand Flight Status](https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/resources/flights/)
- [Amadeus test data y cuotas](https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/test-data/)
- [OpenSky REST API](https://openskynetwork.github.io/opensky-api/rest.html)
- [Aviationstack pricing](https://aviationstack.com/pricing)
- [AeroDataBox pricing](https://aerodatabox.com/pricing/)
- [AeroDataBox RapidAPI OpenAPI](https://doc.aerodatabox.com/rapidapi.html)
- [FlightAware AeroAPI](https://www.flightaware.com/commercial/aeroapi/)
- [ADS-B Exchange Developer Hub](https://www.adsbexchange.com/community/developer-hub/)
