# Runbook — Perfiles de activación por entorno (`/puerta-a-puerta`)

**Estado:** vivo  
**Fecha:** 2026-06-09  
**Fuente de verdad:** sí  
**Área:** runbooks  

> Define los 4 perfiles canónicos de activación de providers para `/puerta-a-puerta` y blinda que `mock_multimodal` no reaparezca como camino feliz en entornos que no lo merecen.

## Perfiles canónicos

Cada perfil define una combinación exacta de flags `DOOR_TO_DOOR_*`. No hay valores "por defecto" ambiguos: el perfil activo se declara explícitamente.

| Perfil | Entorno típico | Propósito |
|--------|---------------|-----------|
| `local_demo` | Desarrollo local | Demostración visual sin providers reales. Solo mock. |
| `local_real` | Desarrollo local | Desarrollo diario con providers reales parciales (deeplinks + GTFS open data). Sin APIs que requieran key. |
| `staging_safe` | Staging / pre-producción | Igual que `local_real` pero con Google Routes y Places activos (requiere `GOOGLE_MAPS_API_KEY`). Mock bloqueado. |
| `prod_gradual` | Producción | Rollout controlado. Mismas capacidades que staging. Mock y scrapers bloqueados. Healthcheck y observabilidad adicionales. |

## Matriz de activación por perfil

| Flag | `local_demo` | `local_real` | `staging_safe` | `prod_gradual` |
|------|:---:|:---:|:---:|:---:|
| `DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER` | ✅ true | ❌ false | ❌ false | ❌ false |
| `DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS` | ❌ false | ✅ true | ✅ true | ✅ true |
| `DOOR_TO_DOOR_ENABLE_GTFS_TRANSIT` | ❌ false | ✅ true | ✅ true | ✅ true |
| `DOOR_TO_DOOR_ENABLE_GOOGLE_ROUTES` | ❌ false | ❌ false | ✅ true | ✅ true |
| `DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES` | ❌ false | ❌ false | ✅ true | ✅ true |
| `DOOR_TO_DOOR_ENABLE_SCRAPERS` | ❌ false | ❌ false | ❌ false | ❌ false |
| `DOOR_TO_DOOR_ENABLE_NOMINATIM_SUGGESTIONS` | ✅ true | ✅ true | ✅ true | ✅ true |

### Dependencias externas

| Capacidad | Requiere |
|-----------|----------|
| GTFS transit | `DOOR_TO_DOOR_GTFS_FEEDS_FILE` o `DOOR_TO_DOOR_GTFS_FEEDS_JSON` o fallback al manifest |
| GTFS transit (feeds NAP España) | `GTFS_NAP_API_KEY` (opcional; sin ella los feeds NAP fallan gracefully) |
| Google Routes | `GOOGLE_MAPS_API_KEY` |
| Google Places | `GOOGLE_MAPS_API_KEY` |

## Capacidades resultantes por perfil

Según los providers activos en cada perfil, las capacidades del hub (`map_capabilities`) quedan así:

| Capacidad | `local_demo` | `local_real` | `staging_safe` | `prod_gradual` |
|-----------|:---:|:---:|:---:|:---:|
| `navigation` | planned | available | available | available |
| `traffic` | planned | planned | planned | planned |
| `transit` | planned | partial | partial | partial |
| `alternatives` | planned | available | available | available |
| `street_view_preview` | planned | planned | planned | planned |
| `saved_places` | planned | available | available | available |
| `nearby_pois` | planned | planned | planned | planned |
| `offline` | planned | planned | planned | planned |
| `incidents` | planned | planned | planned | planned |
| `eco_route` | planned | planned | planned | planned |

## Blindaje anti-mock

### Regla

`mock_multimodal` (`DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER=true`) **solo puede activarse en `APP_ENV=local` o `APP_ENV=test`**.

### Comportamiento

- **`APP_ENV=local` o `APP_ENV=test`**: mock se activa/desactiva libremente según la flag.
- **`APP_ENV=staging` o `APP_ENV=production`**: si `DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER=true`, el registry emite un warning severo (`MOCK_ENABLED_IN_NON_LOCAL_ENV`) y fuerza `mock_enabled=false`. El mock no se carga como provider de búsqueda, pero su descriptor de estado sigue apareciendo como `disabled` con el warning en `notes`.
- **`APP_ENV` no definido**: se trata como `local` (comportamiento actual, sin cambios).

### Verificación

Para confirmar que el mock está realmente bloqueado en un entorno:

```bash
# En staging/prod, el healthcheck de providers debe mostrar:
#   mock_multimodal: enabled=false, status=disabled
#   notes incluye "Bloqueado: mock no permitido en APP_ENV=staging"

curl -s http://localhost:8000/api/v1/door-to-door/providers/status | jq '.providers[] | select(.name == "mock_multimodal")'
```

## Cómo cambiar de perfil

1. Identifica el perfil deseado en la matriz de arriba.
2. Ajusta las flags `DOOR_TO_DOOR_*` en tu `.env` para que coincidan exactamente con la columna del perfil.
3. Asegúrate de que `APP_ENV` refleja el entorno real (`local`, `staging`, `production`).
4. Si activas `staging_safe` o `prod_gradual`, configura `GOOGLE_MAPS_API_KEY`.
5. Reinicia el backend.
6. Verifica con `GET /api/v1/door-to-door/providers/status` que los providers esperados están `enabled=true`.

## Relación con otros runbooks

- **GTFS**: `runbook-gtfs-activacion.md` — activación, diagnóstico y mantenimiento de feeds.
- **Provider degradado**: `runbook-provider-degraded.md` — qué hacer cuando un provider real falla en staging/prod.
- **QA**: `docs/qa/qa-puerta-a-puerta.md` — matriz de verificación por modo operativo.
