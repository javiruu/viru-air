# Runbook QA — `/puerta-a-puerta`

**Estado:** vivo
**Última revisión:** 2026-06-08
**Fuente de verdad:** sí
**Área:** QA / runbooks

## Objetivo

Verificar que el módulo `/puerta-a-puerta` funciona correctamente tras cambios, sin romper contratos ni introducir regresiones.

## Comandos de verificación rápida

```bash
# Frontend (suite estructural + render)
cd frontend && node --import tsx --test tests/door-to-door-v1.test.tsx

# Backend (integración + unitarios GTFS + deeplinks)
cd backend && python -m pytest \
  tests/integration/test_door_to_door.py \
  tests/unit/test_door_to_door_gtfs_transit.py \
  tests/unit/test_door_to_door_deeplinks.py \
  -q

# Typecheck frontend
cd frontend && npx tsc --noEmit
```

## Checklist de estados por fase (F1–F9)

### F2 — Honestidad visual
- [ ] `null price` no pinta `0,00 EUR`
- [ ] `null departure/arrival` no pinta `--:--`
- [ ] Deeplink pinta disclosure externo (`Búsqueda externa`)
- [ ] GTFS/open data no promete precio ni compra
- [ ] i18n incluye fallbacks honestos (`scheduleUnconfirmed`, `durationUnconfirmed`, `deltaUnavailable`)

### F3 — Contrato
- [ ] `map_capabilities` se serializa desde backend con 10 claves canónicas
- [ ] Warning codes alineados entre backend (`PROVIDER_PARTIAL_COVERAGE`) y frontend

### F4 — Watchlist
- [ ] Opción con margen < 90 min muestra pill "Margen ajustado"
- [ ] `?watchId=` persiste y preselecciona vuelo
- [ ] Acciones por tramo (`leg.actions[]`) se renderizan como links externos con `target=_blank`

### F5 — Acciones externas
- [ ] Ningún CTA contiene "Reservar" o "Comprar"
- [ ] Verbos honestos: "Abrir", "Buscar", "Ver"
- [ ] Links externos usan `target=_blank` y `rel=noreferrer`

### F6 — Registry y fuentes
- [ ] 16 claves `whyMissing` existen en i18n (ES + EN)
- [ ] Capability cards muestran `d2d-capability-reason` con copy i18n cuando `state !== "available"`

### F7 — GTFS/open data
- [ ] 6 flags GTFS expuestos en `useDoorToDoorResults`
- [ ] Sección `d2d-gtfs-notice` renderiza warnings GTFS con i18n
- [ ] Badge "horario público" / "public schedule" en OptionCard para tramos GTFS
- [ ] Tests backend cubren los 6 warning codes GTFS
- [ ] `GtfsFeedService` reutiliza cache en memoria dentro del TTL
- [ ] Si la descarga falla pero existe ZIP local, se usa cache rancio sin romper la búsqueda
- [ ] ZIP inválido o feed sin ficheros requeridos no se trata como resultado válido
- [ ] Feeds con auth (`api_key_env`, `auth_header_name`, `response_format=json_presigned`) tienen caso cubierto en tests

## GTFS: cache, feeds y errores

### Variables y rutas que conviene comprobar

```bash
# Cache local de feeds GTFS
echo %DOOR_TO_DOOR_GTFS_CACHE_DIR%

# TTL de cache (segundos)
echo %DOOR_TO_DOOR_GTFS_CACHE_TTL_SECONDS%

# Manifest inline o por fichero
echo %DOOR_TO_DOOR_GTFS_FEEDS_JSON%
echo %DOOR_TO_DOOR_GTFS_FEEDS_FILE%

# Feeds con autenticación tipo NAP
echo %GTFS_NAP_API_KEY%
```

### Qué debe verificarse cuando tocamos GTFS

1. Si el feed descarga bien, el proveedor devuelve horarios `open_data` sin inventar compra.
2. Si el feed falla pero hay ZIP previo en cache, la búsqueda no cae y se usa el fallback local.
3. Si el ZIP está corrupto o le faltan ficheros GTFS mínimos, el feed se rechaza.
4. Si no hay paradas cercanas o no hay servicio en fecha, el warning debe ser específico.
5. Si el corredor está `planned_blocked`, debe salir `GTFS_CORRIDOR_PLANNED` y no aparentar cobertura real.

### Comandos útiles para iterar solo GTFS

```bash
# Solo unitarios GTFS
cd backend && python -m pytest tests/unit/test_door_to_door_gtfs_transit.py -q

# Subgrupo de cache / fallback / auth
cd backend && python -m pytest tests/unit/test_door_to_door_gtfs_transit.py -k "cache or stale or auth or presigned" -q
```

### F8 — Composer
- [ ] `getCompletenessScore` puntúa opciones por fuentes confirmadas
- [ ] Badge `most_complete` se asigna con threshold >= 2
- [ ] Razón `completeness` aparece cuando la recomendada tiene más datos confirmados

### F9 — UX
- [ ] Orden de secciones: timeline → recomendada → comparador → fuentes/confianza → deeplinks → historial
- [ ] StickyBar incluye 7 items de navegación
- [ ] Section IDs existen: `d2d-section-sources`, `d2d-section-deeplinks`, `d2d-section-history`

## Taxonomía de fuentes

| Tipo | `source_type` | `confidence` | ¿Precio? | ¿Horario? | ¿Booking? |
|------|--------------|-------------|----------|-----------|-----------|
| **API real** | `api`, `maps` | `live`, `cached` | Parcial | Sí | No |
| **Open data** | `open_data` | `cached` | No | Sí (feed público) | No |
| **Deeplink** | `deeplink` | `deeplink` | No (externo) | No (estimado) | URL externa |
| **Estimación** | `estimate`, `mock` | `estimated` | Estimado | Estimado | No |
| **Scraper** | `scraper` | — | — | — | — |

### Lo que `/puerta-a-puerta` NO hace hoy

- No confirma precios en nombre del usuario
- No hace scraping activo por defecto
- No reserva ni compra billetes
- No tiene cobertura geográfica "Europa completa"
- No sustituye a Google Maps, BlaBlaCar, GoOpti ni operadores de transporte
- GTFS/open data solo funciona con feeds configurados explícitamente

## Impacto cruzado

| Módulo | Relación | Archivo |
|--------|---------|---------|
| **Watchlist** | `WatchDetailPanel` importa `DoorToDoorWatchlistSuggestion` para sugerir apertura con `?watchId=` | `frontend/src/modules/watchlist/components/WatchDetailPanel.tsx` |
| **Quick Search** | Sin impacto directo | — |
| **Dashboard** | Sin impacto directo | — |

## Verificación visual (manual)

Para cambios de UI, validar en navegador real:

1. Abrir `/puerta-a-puerta`
2. Seleccionar un vuelo del watchlist
3. Configurar origen y destino
4. Calcular ruta
5. Verificar en **dark** y **light**
6. Verificar en **desktop** y **viewport móvil** (max-width: 980px)
7. Confirmar:
   - Jerarquía visual clara (recomendada > timeline > alternativas > fuentes > deeplinks > historial)
   - Sin placeholders falsos (`--:--`, `0,00 EUR`)
   - Badges y pills legibles
   - CTAs externos con target=_blank
   - GTFS warnings visibles si aplica
