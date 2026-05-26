# ADR-003 Arquitectura Provider-Agnóstica de Vuelos

- Estado: Aprobado
- Fecha: 2026-05-26

## Contexto

El backend estaba parcialmente desacoplado pero mantenía acoplamientos operativos y semánticos a Ryanair en warnings, estado de provider y rutas de ejecución.

## Decisión

Adoptar arquitectura provider-driven con tres piezas:

1. `FlightProvider`: contrato único para cualquier proveedor de vuelos.
2. `FlightProviderRegistry`: activación y orden de providers por configuración.
3. `FlightSearchOrchestrator`: ejecución centralizada, dedupe y normalización de warnings/estado.

Además:

- conservar `warnings: list[str]` legacy para compatibilidad;
- introducir warnings estructurados (`ProviderWarning`) canónicos;
- mantener compatibilidad de contratos públicos durante transición.

## Consecuencias

- Añadir un nuevo provider requiere implementar una clase y registrarla, sin tocar lógica de negocio de `quick-search`, `watchlist` o `recommendations`.
- Mejor observabilidad multi-provider con estado agregado por provider.
- Transición segura sin breaking changes inmediatos para consumidores legacy.
