# Product Language Map (Fase 0)

**Estado:** vivo  
**Ultima revision:** 2026-05-11  
**Fuente de verdad:** si  
**Area:** reference

## Objetivo

Congelar el vocabulario visible de Viru Tracker y su traduccion operativa entre modulo de producto, ruta, API y entidad persistida.

## Mapa canonico

| Label visible | Ruta canonica | API canonica | Entidad principal | Alias legacy | Estado |
|---|---|---|---|---|---|
| Watchlist | `/watchlist` | `/api/v1/watchlist` | `FlightWatch` | `/history` | Activo |
| Historico (integrado en Watchlist) | `/watchlist` | `/api/v1/prices` | `PriceSnapshot` | `/history` | Activo |
| Alertas | `/alerts` | `/api/v1/alerts` | `AlertRule` | - | Activo |
| Eventos de alerta | `/alerts` | `/api/v1/alerts/events` | `NotificationEvent` | - | Activo |
| Quick Search | `/quick-search` | `/api/v1/search` | `UxEvent` (analitica) | - | Activo |
| Oportunidades | `/recomendaciones` | `/api/v1/recommendations` | `RecommendationResponse` | - | Activo |
| Preferencias | `/preferencias` | `/api/v1/preferences` | `UserPreference`, `UserPreferenceAppearance`, `UserPreferenceRegion` | `/preferences` | Activo |
| Feedback de producto | `/soporte/feedback?type=idea` | `/api/v1/support/feedback` | `SupportFeedback` | `/suggestions` | Legacy oculto |

## Nombres legacy no persistidos (UNSPECIFIED)

- `watchlist_item`: no existe como modelo exacto; usar `FlightWatch`.
- `activity_event`: no existe como modelo exacto; usar `UxEvent` o `NotificationEvent` segun contexto.
- `system_status`: no existe como tabla persistida; es estado derivado en `/api/v1/admin/product-health`.

## Regla de uso

Todo copy visible, navegacion y QA de rutas privadas debe usar este mapa como referencia base para evitar duplicidad conceptual.
