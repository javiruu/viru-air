# Watchlist

**Estado:** vivo  
**Última revisión:** 2026-07-21
**Fuente de verdad:** si  
**Área:** product

## Resumen

Watchlist es el centro operativo de Viru Air y absorbe el historico como parte de la misma experiencia de decision.

## Seguimiento operacional del vuelo

Una Watch guardada desde un resultado exacto de Quick Search puede enlazar una o varias piernas y mostrar, sin desplazar la lectura de precio:

- estado normalizado, número y ruta;
- salida/llegada programada, estimada o real;
- retraso, terminal y puerta cuando la fuente los entrega;
- posición en el mapa solo cuando ha sido observada y validada;
- frescura y estados honestos de falta de identidad, cobertura o proveedor.

Las Watches manuales o antiguas mantienen precio e histórico. No se asigna un vuelo por ruta/fecha: la UI ofrece volver a Quick Search para guardar uno exacto. En multi-leg, solo el primer tramo queda expandido y los siguientes se consultan bajo demanda.

Contrato y operación:

- [Live flight tracking desde Watchlist](../reference/backend/live-flight-tracking-contract.md)
- [Runbook live flight tracking](../runbooks/runbook-live-flight-tracking.md)

## Contenido principal

- Presencia funcional confirmada en:
  - [Overview del proyecto](../overview/project-overview.md)
  - [Estado actual](../overview/current-state.md)
- Mapa de lenguaje y entidades:
  - [Product language map](../reference/product-language-map.md)
- Material operativo relacionado:
  - [Runbook watchlist uniqueness migration](../runbooks/runbook-watchlist-uniqueness-migration.md)

## Relacionado

- [Backend](../engineering/backend.md)
- [Frontend](../engineering/frontend.md)
