# Estado actual

**Estado:** vivo  
**Ultima revision:** 2026-05-12  
**Fuente de verdad:** si  
**Area:** overview

## Rutas privadas canonicas

- `/dashboard`
- `/watchlist`
- `/quick-search`
- `/alerts`
- `/recomendaciones`
- `/preferencias`
- `/soporte/ayuda`

## Alias legacy activos

- `/history` -> `/watchlist`
- `/preferences` -> `/preferencias`
- `/suggestions` -> `/soporte/feedback?type=idea`

## Contratos API base

- `/api/v1/watchlist`
- `/api/v1/prices`
- `/api/v1/search`
- `/api/v1/alerts`
- `/api/v1/recommendations`
- `/api/v1/preferences`
- `/api/v1/support/feedback`

## Estado semantico de Fase 0

- `Quick Search` sigue como modulo de descubrimiento tecnico.
- `Watchlist` sigue como centro operativo con historico integrado.
- `Alertas` mantiene reglas, cooldown e historial.
- `Oportunidades` es la etiqueta visible de `/recomendaciones`.
- `Suggestions` deja de ser modulo core y queda como alias legacy hacia feedback de producto.

## Estado de cierre por fases (2026-05-12)

- F0: done.
- F1: done (producto basico).
- F2: done (producto basico).
- F3A: done.
- F3B: done.
- F3C: done.
- F3C.2: done.
- F3D: done.
- F3 global: partial por alcance (postponed no bloqueante).
