# ADR-004 Flight Tracking Hub para vuelos

- Estado: Aprobado
- Fecha: 2026-06-30

## Contexto

Quick Search, calendar hints, Watchlist, refresh manual y alertas observan la misma unidad real: una ruta/fecha/provider o una oferta concreta. Si cada flujo decide por separado cuando leer cache, escribir historico o llamar al provider, Viru duplica llamadas y puede convertir datos `warm` o `stale` en precios visibles como si fueran actuales.

La spec viva de Fare Memory prohibe crear una cache paralela y separa memoria operativa de historico visible por usuario.

## Decision

Adoptar el modelo mental **Flight Tracking Hub**:

1. `execute_plan` es el punto operativo unico para tracking de unidades exactas de Quick Search y calendar hints.
2. Fare Memory es la memoria compartida operativa para reutilizar resultados, negativos y frescura.
3. `PriceSnapshot` sigue siendo historico visible de Watchlist por usuario, no la cache compartida.
4. `RevalidationJob` es la cola compartida para refrescar rutas cuando un flujo detecta datos reutilizables pero no frescos.
5. Guardar un resultado en watchlist aplica politica de frescura:
   - `fresh` + precio observado escribe snapshot inmediato;
   - `warm`, `stale`, `expired`, negativos o errores de provider guardan/reusan watch y encolan revalidacion;
   - clientes antiguos sin frescura mantienen compatibilidad y tratan `price_total` como observacion fresca.

## Consecuencias

- Calendar hints, quick-search, refresh manual, boot warmup y alertas pueden compartir memoria sin crear tablas/cache duplicadas.
- Watchlist evita ensuciar el historico visible con precios orientativos o caducados.
- El worker de revalidacion puede convertir una senal warm/stale en snapshots frescos para todas las watches activas de la misma ruta.
- La observabilidad minima queda en eventos estructurados y contadores de cache/job, no en payloads cacheados ni datos privados de usuario.

## Alternativas descartadas

- Crear `PriceSnapshot` automaticamente para cualquier guardado desde quick-search: simple, pero mezcla cache operativa con historico visible.
- Crear una cache nueva para calendario/watchlist: contradice Fare Memory y duplica semantica.
- Redis como solucion inmediata: sigue contemplado como hot layer futuro, pero no sustituye la memoria persistente actual.
