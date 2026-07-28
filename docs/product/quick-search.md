# Quick Search

**Estado:** vivo  
**Última revisión:** 2026-07-28
**Fuente de verdad:** sí  
**Área:** product

## Resumen

Quick Search es una de las áreas más documentadas del proyecto y cuenta con contrato backend, checklist técnico, política de weather y guías de QA visual/manual.

## Precio comparable

La cesta de precio comparable permite aplicar el mismo criterio a todos los resultados:

- número de viajeros;
- equipaje de cabina de 10 kg y maleta facturada de 20 kg;
- seguro, Fast Track, embarque prioritario, selección de asiento y cambios flexibles;
- selección de extras sin introducir importes manuales.

Cada resultado mantiene visible el precio base y calcula automáticamente el
total o rango comparable con las tarifas públicas de la aerolínea, respetando
si cada servicio se cobra por vuelo o por reserva. Cuando una tarifa es
dinámica o no publica un máximo, Viru muestra
`Desde`; cuando no existe una cifra pública calculable, conserva el total
parcial y señala el extra pendiente sin inventar un precio. La fuente oficial
queda enlazada junto a la estimación. Al guardar un resultado, la cesta y la
aerolínea identificada viajan con la Watch para conservar la comparación.

## Contenido principal

- Contrato técnico:
  - [Quick Search contract](../reference/backend/quick-search-contract.md)
- Criterios técnicos:
  - [Quick Search acceptance checklist](../reference/backend/quick-search-acceptance-checklist.md)
- Comportamiento auxiliar:
  - [Quick Search weather policy](../reference/quick-search-weather-policy.md)
- QA y capturas:
  - [Runbook UI captures](../runbooks/runbook-ui-captures.md)
  - [Reportes QA](../qa/reports/)

## Relacionado

- [Backend](../engineering/backend.md)
- [Testing](../engineering/testing.md)
