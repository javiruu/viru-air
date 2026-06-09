# Plan de 10 Fases para Activar `/puerta-a-puerta` de Verdad

**Estado:** activo  
**Fecha:** 2026-06-09  
**Autor:** Codex  
**Area:** plan  
**Fuente de verdad:** no; plan operativo de activacion apoyado en codigo, docs vivas y estado real del modulo

> Este plan complementa y en la practica reemplaza como hoja de ruta principal a `docs/plans/2026-06-08-puerta-a-puerta-plan-aterrizado-real.md` para el siguiente ciclo. El foco aqui no es pulir la UX ni refinar la honestidad general, sino encender capacidades reales una por una hasta que `/puerta-a-puerta` deje de ser una pantalla bien estructurada pero poco util.

## Objetivo real

Pasar de:

- "panel bonito con timeline, badges, fuentes y estimaciones"

a:

- "herramienta que resuelve tramos utiles con datos reales o semireales, y que deja claro que puede y que no puede hacer en cada ruta".

No se busca encender todo a la vez. Se busca activar valor real por capas, sin PR Frankenstein, sin reescritura total y sin vender una cobertura que todavia no existe.

## Diagnostico ejecutivo: donde esta atascado el valor hoy

El modulo ya esta mejor de lo que parece a simple vista:

- existe ruta privada funcional
- existe panel, timeline, comparador, map hub, history, sticky bar y saved places
- existen providers reales parciales
- existe contrato backend
- existen bastantes tests

Pero la utilidad practica sigue baja por cinco razones:

1. El modo por defecto sigue dependiendo mucho de `mock_multimodal`.
2. Los deeplinks ayudan, pero no resuelven horarios ni precio.
3. `google_routes` hoy enciende duracion y distancia, pero no compone la experiencia completa.
4. `gtfs_transit` existe, pero su activacion depende de feeds configurados y cobertura local muy concreta.
5. Hay muchas capacidades en `map_capabilities` y en el hub que visualmente parecen parte del producto, pero funcionalmente siguen en `planned`, `partial` o `fallback`.

La consecuencia es clara: la UX ya parece “producto”, pero la activacion real del motor aun no acompaña.

## Principios para este plan

- Activar primero lo que mas utilidad da al usuario real, no lo que queda mejor en demo.
- Cada fase debe encender una capacidad verificable, no solo dejar preparado un scaffold.
- Toda nueva activacion debe declarar:
  - dependencia tecnica
  - flag/env
  - provider o fuente
  - cobertura esperada
  - fallback honesto
  - criterio de done
- No convertir `/puerta-a-puerta` en un clon de Google Maps.
- No prometer cobertura total; la expansion geografica va despues de la activacion de los flujos base.

## Baseline tecnico confirmado para activar

### Ya disponible en el repo

- `google_maps_deeplink`
- `blablacar_deeplink`
- `goopti_deeplink`
- `external_deeplink`
- `google_routes`
- `google_places`
- `gtfs_transit`
- `nominatim` fallback
- `mock_multimodal`

### Ya visible en frontend

- formulario completo
- resumen/timeline
- resultados por grupos
- panel de fuentes y confianza
- hub de capacidades
- historial
- puntos guardados

### Ya documentado o muy cerca

- `docs/product/door-to-door.md`
- `docs/reference/backend/door-to-door-contract.md`
- `backend/app/door_to_door/providers/registry.py`
- `backend/app/door_to_door/services/search_service.py`

## Los 4 bloques de activacion real

Las 10 fases no van sueltas: se agrupan en 4 bloques.

### Bloque A. Encender el core minimo util

- Fase 1: desactivar la dependencia silenciosa del mock
- Fase 2: activar el modo deeplink util por defecto
- Fase 3: activar Google Routes como enriquecimiento real sistematico

### Bloque B. Encender transporte publico real

- Fase 4: activacion operativa de GTFS por feeds reales
- Fase 5: expansion GTFS por regiones/corredores

### Bloque C. Encender inteligencia de composicion

- Fase 6: composer real de alternativas completas
- Fase 7: seleccion y recomendacion por confianza/cobertura
- Fase 8: historial, guardados y reuso operativo

### Bloque D. Encender ecosistema y salida a produccion

- Fase 9: capacidades auxiliares del map hub que de verdad aportan
- Fase 10: rollout, QA, observabilidad y cierre de claims

## Plan de 10 fases

### Fase 1. Modo “sin mock por defecto” y diagnostico de cobertura real

**Objetivo:** que el producto deje de parecer activo gracias a estimaciones cuando en realidad no hay providers reales suficientes.

**Resultado esperado:**

- en entornos donde no haya providers reales o feeds activos, el usuario ve una pantalla honesta y accionable, no una pseudo-ruta inventada por defecto
- el equipo puede medir donde hay cobertura real y donde no

**Activaciones concretas:**

- cambiar la estrategia de activacion para que `mock_multimodal` no sea el camino feliz silencioso
- dejar el mock solo como:
  - fallback controlado de desarrollo
  - modo demo explicito
  - fixture de tests
- exponer mejor el estado real de providers activos

**Archivos principales:**

- `backend/app/door_to_door/providers/registry.py`
- `backend/app/door_to_door/services/search_service.py`
- `frontend/src/modules/door-to-door/hooks/useDoorToDoorResults.ts`
- `frontend/src/modules/door-to-door/hooks/useDoorToDoorMapHub.ts`
- `docs/product/door-to-door.md`

**Flags/env a ordenar:**

- `DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER`
- `DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS`
- `DOOR_TO_DOOR_ENABLE_SCRAPERS`

**Done de la fase:**

- si no hay providers reales suficientes, la app no pinta una ruta “usable” basada en mock salvo modo explicito
- el usuario entiende si esta en:
  - cobertura real
  - cobertura parcial
  - sin cobertura real
  - modo estimacion

### Fase 2. Encender deeplinks realmente utiles por tramo

**Objetivo:** que la primera version util del modulo funcione aunque no haya precio ni booking integrado.

**Resultado esperado:**

- cada tramo terrestre puede abrir una accion externa util y bien formada
- la opcion deja de ser “carta bonita” y pasa a ser “plan que me deja continuar ya”

**Activaciones concretas:**

- consolidar `external_deeplink` como capa de acciones por tramo
- asegurar que siempre que haya contexto suficiente se generen URLs operativas para:
  - Google Maps
  - BlaBlaCar
  - GoOpti
- mejorar fallback si faltan `place_id`, ciudades mapeadas o coordenadas
- priorizar el caso:
  - origen usuario -> aeropuerto salida
  - aeropuerto llegada -> destino final

**Archivos principales:**

- `backend/app/door_to_door/providers/deeplink_blablacar.py`
- `backend/app/door_to_door/providers/deeplink_goopti.py`
- `backend/app/door_to_door/providers/deeplink_maps.py`
- `backend/app/door_to_door/providers/deeplink_provider.py`
- `frontend/src/modules/door-to-door/components/DoorToDoorOptionCard.tsx`
- `frontend/src/modules/door-to-door/DoorToDoorPanel.tsx`

**Done de la fase:**

- una ruta sin precio confirmado sigue siendo util porque permite avanzar por acciones reales
- todas las acciones visibles responden a un caso real y no a un CTA decorativo

### Fase 3. Activar Google Routes como enriquecimiento real sistematico

**Objetivo:** pasar de deeplink “ciego” a deeplink enriquecido con duracion y distancia reales de forma estable.

**Resultado esperado:**

- cuando `google_routes` esta activo, las opciones terrestres dejan de depender de duraciones inventadas
- la recomendacion ya puede usar una señal real util

**Activaciones concretas:**

- asegurar que `google_routes` se inyecta como enriquecimiento en todas las rutas compatibles, no solo en casos puntuales
- completar overlay real sobre legs terrestres:
  - `duration_minutes`
  - `distance_meters`
  - posible ventana temporal si aplica
- endurecer el fallback cuando Google falla:
  - warning claro
  - no romper la busqueda
  - conservar acciones externas

**Archivos principales:**

- `backend/app/door_to_door/providers/google_routes.py`
- `backend/app/door_to_door/services/search_service.py`
- `backend/tests/integration/test_door_to_door.py`
- `backend/tests/unit/test_door_to_door_google_routes.py`

**Flags/env:**

- `DOOR_TO_DOOR_ENABLE_GOOGLE_ROUTES`
- `GOOGLE_MAPS_API_KEY`

**Done de la fase:**

- existe un camino estable “deeplink + duracion real” que ya es claramente mas util que el mock

### Fase 4. Activacion operativa de GTFS con feeds reales y pipeline reproducible

**Objetivo:** que `gtfs_transit` deje de ser una capacidad sembrada y pase a ser una integracion operable por entorno.

**Resultado esperado:**

- el equipo puede encender GTFS para un feed real sin trabajo manual confuso
- el producto obtiene horarios reales en regiones donde haya feed cargado

**Activaciones concretas:**

- formalizar el flujo de activacion de feeds:
  - manifest JSON
  - cache dir
  - feed validation
  - healthcheck
- documentar la preparacion del entorno
- endurecer mensajes de fallo por feed, no solo por busqueda

**Archivos principales:**

- `backend/app/door_to_door/providers/gtfs_transit.py`
- `backend/app/door_to_door/services/gtfs_feed_service.py`
- `backend/app/door_to_door/providers/gtfs_feeds.json`
- `docs/reference/backend/door-to-door-contract.md`
- `docs/runbooks/` nuevo runbook

**Flags/env:**

- `DOOR_TO_DOOR_ENABLE_GTFS_TRANSIT`
- `DOOR_TO_DOOR_GTFS_FEEDS_JSON`
- `DOOR_TO_DOOR_GTFS_FEEDS_FILE`
- `DOOR_TO_DOOR_GTFS_CACHE_DIR`

**Done de la fase:**

- activar GTFS en un entorno es un proceso repetible y documentado
- al menos un feed real puede encender la ruta completa o un tramo real con evidencia

### Fase 5. Expansion GTFS por corredores y cobertura util

**Objetivo:** que GTFS no sea solo “hay un provider”, sino una capacidad realmente usable en rutas concretas.

**Resultado esperado:**

- definir un mapa de corredores/casos con valor
- activar uno o varios conjuntos de feeds que den utilidad real en rutas objetivo

**Activaciones concretas:**

- elegir corredores iniciales de utilidad alta
  - ejemplo: origenes españoles hacia aeropuertos españoles grandes
  - conexiones urbanas o regionales frecuentes
- medir para cada corredor:
  - cobertura de parada cercana
  - servicio por fecha
  - matching con buffer de vuelo
- añadir fixtures y casos QA por corredor

**Archivos principales:**

- `backend/tests/unit/test_door_to_door_gtfs_transit.py`
- `backend/tests/integration/test_door_to_door.py`
- docs de QA y runbook de feeds

**Done de la fase:**

- existen corredores concretos donde `/puerta-a-puerta` ya da transporte publico real repetible
- el producto puede decir “aqui si” y “aqui no” con honestidad geografica

### Fase 6. Composer real de rutas completas

**Objetivo:** pasar de sumar opciones sueltas a construir alternativas completas comparables de puerta a puerta.

**Resultado esperado:**

- la unidad principal del producto ya no es el tramo ni el provider, sino el itinerario completo

**Activaciones concretas:**

- introducir o endurecer un composer de itinerarios que combine:
  - tramo origen -> aeropuerto
  - vuelo
  - tramo llegada -> destino final
- distinguir:
  - opcion completa
  - opcion parcialmente completa pero accionable
  - opcion solo exploratoria
- definir completitud como señal propia

**Archivos principales:**

- `backend/app/door_to_door/services/itinerary_builder.py`
- `backend/app/door_to_door/services/search_service.py`
- `frontend/src/modules/door-to-door/types.ts`
- `frontend/src/modules/door-to-door/decision.ts`

**Done de la fase:**

- el backend devuelve alternativas completas o parcial-completas con estructura consistente
- el frontend deja de forzar comparaciones entre piezas heterogeneas

### Fase 7. Recomendacion real basada en cobertura, confianza y margen

**Objetivo:** que la etiqueta “recomendada” signifique algo mas que score cosmetico.

**Resultado esperado:**

- la recomendacion prioriza utilidad real y riesgo operativo, no solo orden visual

**Activaciones concretas:**

- ampliar scoring con pesos explicitos para:
  - completitud
  - confianza real
  - margen antes del vuelo
  - cambios
  - duracion
  - coste cuando exista
- distinguir “mejor recomendada” de:
  - mas rapida
  - mas barata
  - mas margen
  - mas accionable

**Archivos principales:**

- `backend/app/door_to_door/domain/scoring.py`
- `frontend/src/modules/door-to-door/decision.ts`
- `frontend/src/modules/door-to-door/hooks/useDoorToDoorResults.ts`

**Done de la fase:**

- una ruta parcialmente real pero accionable puede ganar a una muy incompleta
- el usuario ve por que se recomienda esa ruta

### Fase 8. Persistencia operativa: historial, guardados y origen habitual que sí ayudan

**Objetivo:** que el modulo recuerde de forma util y reduzca friccion real entre busquedas.

**Resultado esperado:**

- el usuario puede reutilizar origen, destino y elecciones previas de forma practica

**Activaciones concretas:**

- endurecer `saved-location` para el flujo real de reuso
- revisar si los `saved places` del map hub siguen solo en `localStorage` o merecen backend
- usar historial para:
  - recuperar ultima opcion elegida valida
  - proponer configuracion base del usuario
  - reducir inputs repetidos

**Archivos principales:**

- `frontend/src/modules/door-to-door/hooks/useDoorToDoorHistory.ts`
- `frontend/src/modules/door-to-door/hooks/useDoorToDoorMapHub.ts`
- `backend/app/door_to_door/api/routes.py`
- modelos de DB relacionados

**Done de la fase:**

- el segundo uso del modulo es sensiblemente mejor que el primero
- guardados e historial dejan de ser apendices y pasan a ser ayuda real

### Fase 9. Activar capacidades auxiliares del hub que aportan de verdad

**Objetivo:** que el map hub deje de listar ambiciones y empiece a enseñar capacidades auxiliares con valor real.

**Resultado esperado:**

- al menos varias tarjetas del hub dejan de ser `planned` o `partial` vacio y pasan a significar algo tangible

**Activaciones concretas:**

- priorizar solo capacidades con retorno real cercano:
  - `navigation`
  - `transit`
  - `alternatives`
  - `saved_places`
- no tocar aun o mantener como planned si no hay backend real:
  - `offline`
  - `street_view_preview`
  - `incidents`
  - `eco_route`
  - `nearby_pois`
  - `traffic` si no hay fuente real suficiente
- hacer que cada capacidad explique:
  - de donde sale
  - que cubre
  - que no cubre

**Archivos principales:**

- `frontend/src/modules/door-to-door/mapHub.ts`
- `frontend/src/modules/door-to-door/hooks/useDoorToDoorMapHub.ts`
- `backend/app/door_to_door/providers/registry.py`
- contrato backend si se serializa `map_capabilities`

**Done de la fase:**

- el hub deja de inflar expectativas y empieza a servir como panel de capacidades reales del entorno

### Fase 10. Rollout serio: observabilidad, QA, claims y paso a “feature util”

**Objetivo:** cerrar el ciclo para que la feature pueda crecer sin autoengañarse.

**Resultado esperado:**

- existe una ruta clara para operar, medir y comunicar el estado real de `/puerta-a-puerta`

**Activaciones concretas:**

- definir matriz de QA por modos:
  - solo deeplink
  - deeplink + google routes
  - GTFS activo
  - sin cobertura real
  - watch con vuelo guardado
- introducir observabilidad minima:
  - provider activado
  - warnings dominantes
  - cobertura por ruta/corredor
  - ratio de busquedas con opcion completa
- endurecer claims de producto y docs para que solo hablen de lo realmente activado

**Archivos principales:**

- `docs/product/door-to-door.md`
- `docs/reference/backend/door-to-door-contract.md`
- `docs/qa/` nuevo material
- `docs/runbooks/` nuevo runbook de activacion/operacion

**Done de la fase:**

- el equipo sabe exactamente que capacidades estan activas en cada entorno
- el usuario no recibe promesas que el backend no sostenga

## Orden de ejecucion recomendado

Si el objetivo es utilidad real cuanto antes, el orden no deberia ser por “complejidad tecnica”, sino por “valor activado”:

1. Fase 1
2. Fase 2
3. Fase 3
4. Fase 6
5. Fase 7
6. Fase 4
7. Fase 5
8. Fase 8
9. Fase 9
10. Fase 10

Motivo:

- primero quitamos la ilusion del mock
- luego activamos acciones externas utiles
- luego metemos señal real con Google Routes
- despues mejoramos composer y recomendacion
- y solo entonces escalamos GTFS y capacidades auxiliares

## Corte de trabajo recomendado para ya

Si hay que empezar mañana sin perder meses, el primer bloque deberia ser:

### Sprint A

- Fase 1 completa
- Fase 2 completa
- Fase 3 completa

**Que deja encendido:**

- modulo honesto
- acciones externas utiles
- duraciones reales cuando Google Routes este activo

### Sprint B

- Fase 6 completa
- Fase 7 completa

**Que deja encendido:**

- alternativas completas comparables
- recomendacion realmente util

### Sprint C

- Fase 4 completa
- Fase 5 parcial o completa

**Que deja encendido:**

- transporte publico real por feeds/corredores concretos

## Que no haria ahora

- scraper real agresivo
- login en terceros
- intentar “activar todo el hub”
- vender cobertura europea
- introducir cinco providers nuevos a la vez
- rediseñar otra vez la UI antes de encender el motor

## Definicion de done global

`/puerta-a-puerta` estara realmente activado cuando cumpla estas cinco cosas:

1. Resuelve el caso principal con un vuelo guardado y al menos una salida accionable real.
2. Usa providers reales parciales como camino principal cuando existan.
3. Muestra cobertura y limites por fuente sin depender del mock silencioso.
4. Puede operar con uno o varios corredores reales de GTFS ya verificados.
5. La recomendacion final ya se basa en completitud, margen y confianza, no solo en presentacion.

