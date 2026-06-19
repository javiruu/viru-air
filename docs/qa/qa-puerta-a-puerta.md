# QA Matrix — `/puerta-a-puerta`

**Estado:** vivo
**Fecha:** 2026-06-09
**Fuente de verdad:** sí
**Área:** qa

## Matriz de modos operativos

Cada modo representa una combinación de providers activos y debe verificarse independientemente.

| Modo | Providers activos | Resultado esperado | Señal de cobertura |
|------|-------------------|-------------------|-------------------|
| **Solo deeplink** | external_deeplink, blablacar_deeplink, goopti_deeplink | Opciones con status `real_deeplink`, acciones externas funcionales, sin precio confirmado | `real_deeplink` badges |
| **Deeplink + Google Routes** | external_deeplink + google_routes | Opciones con `real_deeplink` + duración/distancia real overlay | `real_result` si hay overlay completo |
| **GTFS activo (corredor verificado)** | gtfs_transit (feeds cargados) | Opciones `real_result` con horarios open_data en corredores verificados | `GTFS_CORRIDOR_VERIFIED` |
| **GTFS activo (sin corredor)** | gtfs_transit (feeds cargados, ruta fuera de corredor) | Sin resultados GTFS, fallback a deeplinks | `GTFS_NO_NEARBY_STOPS` o `GTFS_NO_MATCHING_SERVICE` |
| **Sin cobertura real** | Solo mock desactivado | `NO_REAL_PROVIDER_COVERAGE` o `NO_COVERAGE` | Panel de "sin cobertura" |
| **Watch con vuelo guardado** | Cualquiera | Vuelo contextual del watchlist, flight_time_confidence según snapshot | `FLIGHT_TIME_ESTIMATED` si no hay horario real |

## Cierre integral fase 55 (Junio 2026)

Cobertura mínima considerada suficiente para cerrar el módulo tras las fases 49–55:

- Tests frontend de render y honestidad de copy
- Tests frontend de scoring y margen ajustado
- Tests backend de integración door-to-door
- Tests backend GTFS/deeplinks/cache/fallback
- Browser QA real en dark/light y desktop/mobile
- Runbook actualizado con límites y repetición del flujo

## Verificaciones por modo

### Modo: Solo deeplink

- [ ] El formulario acepta origen y destino con coordenadas
- [ ] Al calcular, se generan opciones con status `real_deeplink`
- [ ] Cada opción tiene acciones externas (Google Maps, BlaBlaCar, GoOpti)
- [ ] Las URLs de deeplink son funcionales y bien formadas
- [ ] BlaBlaCar usa `airport_label()` con ciudad ("Aeropuerto de Málaga AGP")
- [ ] Google Maps usa coordenadas cuando están disponibles
- [ ] GoOpti aparece solo si `allow_shuttle=true` y destino != airport_only
- [ ] El badge de completitud muestra `partial_actionable`
- [ ] Sin precio confirmado, se muestra "Precio y disponibilidad se confirman fuera de Viru"

### Modo: Deeplink + Google Routes

- [ ] Google Routes está activo (`GOOGLE_MAPS_API_KEY` configurada)
- [ ] Las opciones deeplink reciben overlay de duración/distancia real
- [ ] `total_duration_minutes` y leg `duration_minutes` reflejan datos de Google
- [ ] `airport_buffer_minutes` se recalcula con datos reales cuando es posible
- [ ] Si Google Routes falla, la búsqueda no se rompe (warning `GOOGLE_ROUTES_UNAVAILABLE`)
- [ ] Las acciones externas se conservan incluso si Google Routes falla

### Modo: GTFS activo (corredor verificado)

- [ ] GTFS está activo con al menos un feed cargado (ej. MOM Treviso)
- [ ] Healthcheck muestra `✅` para feeds cargados con conteo de rutas/paradas
- [ ] Búsqueda en corredor Treviso→TSF produce opciones `real_result` con `source_type=open_data`
- [ ] Las legs GTFS tienen horarios reales (departure_at, arrival_at)
- [ ] Sin precio confirmado (`UNCONFIRMED_PRICE`, `GTFS_PRICE_UNAVAILABLE`)
- [ ] El warning `GTFS_CORRIDOR_VERIFIED` aparece cuando la ruta cae en corredor
- [ ] El warning `GTFS_CORRIDOR_PLANNED` aparece para corredores NAP (Málaga→AGP)
- [ ] `airport_only` omite correctamente el tramo terrestre de llegada

### Modo: Sin cobertura real

- [ ] Sin providers reales activos → `NO_REAL_PROVIDER_COVERAGE`
- [ ] Sin opciones tras filtros → `NO_COVERAGE` con sugerencias
- [ ] La UI muestra el panel de "sin cobertura" con acciones sugeridas
- [ ] No se muestran rutas inventadas (mock desactivado)

### Modo: Watch con vuelo guardado

- [ ] El watch se selecciona correctamente del watchlist
- [ ] `flight_time_confidence` es `live` si hay snapshot con horario
- [ ] `flight_time_confidence` es `estimated` si no hay horario completo
- [ ] El formulario muestra IATA del watch seleccionado
- [ ] `airport_only` usa el IATA de destino del watch

## Limitaciones que QA debe recordar

- `real_deeplink` no equivale a booking integrado ni a precio confirmado.
- GTFS `open_data` puede aportar horario real sin aportar precio real.
- `NO_COVERAGE` puede ser una respuesta correcta si el entorno no tiene providers suficientes.
- En móvil, la sticky bar puede requerir scroll horizontal para recorrer las siete secciones.
- La evidencia visual automática depende del binario local de Playwright/Chromium.

## Observabilidad mínima

Indicadores a monitorizar por entorno:

| Indicador | Fuente | Umbral de atención |
|-----------|--------|-------------------|
| Providers reales activos | `GET /providers/status` | < 2 → cobertura insuficiente |
| Warnings dominantes | `warnings[].code` en responses | `NO_COVERAGE` > 50% → revisar configuración |
| Ratio de opciones completas | `options[].completeness == "full"` | < 10% → pocos datos reales |
| Corredores GTFS cargados | Healthcheck `gtfs_transit` | 0 → sin transporte público |
| Google Routes funcional | Healthcheck `google_routes` | `unavailable` → revisar API key |
| Feeds GTFS expirados | `GTFS_NO_SERVICE_FOR_DATE` | Frecuente → renovar feeds |

## Claims de producto (qué decir y qué no)

### Lo que SÍ puede decir el producto (Junio 2026)

- "Calcula la ruta completa puerta a puerta con tu vuelo guardado"
- "Abre Google Maps, BlaBlaCar y GoOpti con un clic desde cada tramo"
- "Duración y distancia reales con Google Routes cuando está activo"
- "Horarios de transporte público real en Treviso (MOM) y Venecia (ACTV)"
- "Guarda tu origen habitual y reutiliza búsquedas anteriores"
- "Compara alternativas por precio, tiempo, margen y cambios"
- "Cada dato muestra su fuente y nivel de confianza"

### Lo que NO debe decir el producto

- "Cobertura europea completa" → solo corredores verificados
- "Precios confirmados" → los deeplinks y GTFS no confirman precio
- "Reserva integrada" → no hay booking
- "Transporte público en toda España" → solo feeds configurados
- "Tráfico en tiempo real" → no cableado
- "Street View preview" → no implementado
- "Rutas ecológicas" → no implementado

## Criterios de aceptación por fase

Ver `docs/plans/2026-06-09-puerta-a-puerta-plan-10-fases-activacion-real.md` para los criterios de done de cada fase.

| Fase | Criterio de done | Verificado |
|------|-----------------|-----------|
| F1 | Sin mock silencioso; usuario ve cobertura real/parcial/sin cobertura | ✅ |
| F2 | Deeplinks operativos por tramo (Google Maps, BlaBlaCar, GoOpti) | ✅ |
| F3 | Google Routes overlay estable con duración/distancia real | ✅ |
| F4 | GTFS operable por entorno con runbook documentado | ✅ |
| F5 | Corredores definidos; producto dice "aquí sí" y "aquí no" | ✅ |
| F6 | Composer de itinerarios con completitud (full/partial/exploratory) | ✅ |
| F7 | Scoring con completitud, buffer graduado, recomendación real | ✅ |
| F8 | Historial reutilizable, saved places en backend, pre-llenado automático | ✅ |
| F9 | Hub de capacidades honesto: 4 reales, 6 planned | ✅ |
| F10 | QA matrix, observabilidad, claims alineados | ✅ |
