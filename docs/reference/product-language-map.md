# Product Language Map (Fase 0)

**Estado:** vivo  
**Ultima revision:** 2026-07-30
**Fuente de verdad:** si  
**Area:** reference

## Objetivo

Congelar el vocabulario visible de Viru Air y su traduccion operativa entre modulo de producto, ruta, API y entidad persistida.

## Mapa canonico

| Label visible | Ruta canonica | API canonica | Entidad principal | Alias legacy | Estado |
|---|---|---|---|---|---|
| Watchlist | `/watchlist` | `/api/v1/watchlist` | `FlightWatch` | `/history` | Activo |
| Historico (integrado en Watchlist) | `/watchlist` | `/api/v1/prices` | `PriceSnapshot` | `/history` | Activo |
| Señales (bandeja) | `/notifications` | `/api/v1/notifications` | `NotificationEvent`, `UserNotificationState` | - | Activo |
| Reglas de señales | `/notifications?view=rules` | `/api/v1/alerts` | `AlertRule` | `/alerts` | Activo |
| Historial de señales | `/notifications?view=rules` | `/api/v1/alerts/events` | `NotificationEvent` | `/alerts` | Activo |
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

## Politica complementaria de lenguaje visible

- Guia operativa: `docs/reference/ui-visible-language-guide.md`
- Este mapa congela labels de producto, rutas y entidades.
- La guia de lenguaje visible gobierna como hablar de estados, filtros, ayudas, mensajes y CTAs.

## Labels de producto congelados

- `Watchlist` se conserva como label visible de producto.
- `Quick Search` se conserva como label visible de producto.
- `Historico` sigue integrado dentro de `Watchlist`.
- `Señales` reune la bandeja y las reglas; `Alertas` deja de ser un modulo visible independiente.
- `Feedback de producto` sigue siendo el destino conceptual del modulo legacy, aunque el copy visible puede humanizarse a `Enviar opinion` segun contexto.
