# Estado actual

**Estado:** vivo  
**Ultima revision:** 2026-07-30
**Fuente de verdad:** si  
**Area:** overview

## Rutas privadas canonicas

- `/dashboard`
- `/watchlist`
- `/quick-search`
- `/notifications`
- `/recomendaciones`
- `/preferencias`
- `/soporte/ayuda`
- `/puerta-a-puerta` — modulo activo de transporte terrestre multi-proveedor
- `/hoteles` — exploracion hotelera con comp-sets

## Alias legacy activos

- `/history` -> `/watchlist`
- `/alerts` -> `/notifications?view=rules`
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
- `/api/v1/door-to-door` — busqueda multi-proveedor (GTFS, APIs REST)
- `/api/v1/airports` — seeds, sugerencias, paises
- `/api/v1/search/quick` — busqueda rapida con cache L1/L2/Provider
- `/api/v1/search/quick/calendar-hints` — precios estimados por mes
- `/api/v1/search/deeplink` — generacion de enlaces a aerolineas
- `/api/v1/watchlist/{watch_id}/live` — estado operacional por vuelo exacto, autenticado por owner

## Publicacion

- **Cloudflare Tunnel** como via principal de exposicion publica
- **Tailscale Funnel** como failover/bypass
- Panel unificado `VIRU_PANEL.bat` con estado, inicio/parada de ambos túneles
- Sin dependencia de DuckDNS ni Caddy

## Modulos activos

La revalidacion se despliega como proceso separado del API y consume `RevalidationJob`; el API no depende de tareas en proceso cuando `ENABLE_IN_PROCESS_WORKERS=false`.

### Quick Search (estabilizado)

- Busqueda rapida de vuelos con cache compartida persistente (L1 local + L2 DB + provider)
- Calendar hints con precios estimados por mes
- Proveedores: Ryanair, Vueling, Wizz Air, easyJet, Duffel (API)
- Indicador visual de estado por proveedor durante la busqueda
- Logging en tiempo real de actividad por provider
- Cesta comparable por viajeros con equipaje, seguro, Fast Track y otros extras introducidos por el usuario
- Persistencia de la cesta al guardar un resultado en Watchlist

### Watchlist (estable)

- Centro operativo con historico de precios integrado
- Refresco automatico y manual de precios
- Watchlist unificada con migracion de rutas
- Enlace opcional a vuelos exactos guardados desde Quick Search
- Estado operacional, horarios, puertas y posicion observada con degradacion segura si falta cobertura
- Snapshots operacionales compartidos, cooldown de fallos y polling pausado en pestanas ocultas
- Precio comparable editable, con desglose base/extras y estado honesto cuando faltan importes

### Puerta a puerta (activo)

- Transporte terrestre multi-proveedor (datos GTFS + APIs REST)
- Perfiles de activacion (local_demo, local_real, staging_safe, prod_gradual)
- Blindaje anti-mock en entornos productivos
- Metricas de cobertura real

### Hoteles (en cierre)

- Exploracion con comparativa de comp-sets
- Fases A-E de correcciones post-cierre en progreso

## Estado de arquitectura reciente

### Backend

- Providers ejecutados en paralelo via ThreadPoolExecutor (antes secuencial)
- Wizz Air: locks por ruta en vez de lock global (elimina serializacion entre rutas)
- Caché quick-search: L1 en memoria + L2 en DB compartida + anti-stampede
- Door-to-door: GTFS corridors + providers Ors/OpenTripPlanner con fallback

### Frontend

- SVGs de aerolineas centralizados en `src/icons/` como componentes reutilizables
- Indicador visual de estado por proveedor durante busqueda
- Humanizacion de lenguaje visible (microcopys mas cercanos y claros)
- Migracion a iconos corporativos reales (Simple Icons)

### Infraestructura

- Cloudflare Tunnel como via principal de exposicion
- Tailscale Funnel como failover
- Sin dependencia de DuckDNS/Caddy
