# `/puerta-a-puerta` — Siguientes 10 Fases de Activacion Real

**Estado:** completado  
**Fecha:** 2026-06-09  
**Fecha cierre:** 2026-06-09  
**Autor:** Codex  
**Area:** plan  
**Fuente de verdad:** no; roadmap operativo a partir del estado real actual del modulo

> Este documento parte del modulo tal como esta despues de los commits recientes de 2026-06-08 y 2026-06-09. No replantea fases ya ejecutadas; define las siguientes 10 fases para seguir activando capacidades reales sin rehacer lo ya conseguido.

## Que he revisado para construir este plan

### Estructura leida del modulo

- frontend completo de `frontend/src/modules/door-to-door/`
- backend completo de `backend/app/door_to_door/`
- tests relacionados en `frontend/tests/` y `backend/tests/`
- docs vivas:
  - `docs/product/door-to-door.md`
  - `docs/reference/backend/door-to-door-contract.md`
  - `docs/qa/qa-puerta-a-puerta.md`
  - `docs/runbooks/runbook-gtfs-activacion.md`

### Commits recientes revisados

- `ecbc47a` — `feat: activate real providers by default + fix GTFS feed detection + NAP auth support`
- `e7aba06` — `feat: cierre del plan puerta-a-puerta 10 fases — modulo completamente activado`
- `c58b690` — `feat: cierre del plan puerta-a-puerta F1-F10 — honestidad, contrato, composición, UX, GTFS, QA y docs`
- historial reciente adicional del modulo desde `c41faa0` hasta hoy para entender la secuencia real de activacion

## Foto actual: que ya esta activado de verdad

El modulo actual ya no esta en fase de maqueta. A dia 2026-06-09 ya tiene:

- providers reales activados por defecto:
  - `google_maps_deeplink`
  - `blablacar_deeplink`
  - `goopti_deeplink`
  - `external_deeplink`
  - `gtfs_transit`
- `google_routes` y `google_places` listos bajo API key
- `nominatim` como fallback operativo para suggestions
- completitud por opcion:
  - `full`
  - `partial_actionable`
  - `exploratory`
- composer y scoring ampliados
- `map_capabilities` serializado en contrato/backend
- guardados e historial reutilizable
- saved places ya migrados a backend
- GTFS con feeds verificados para Treviso y Venice
- plumbing de autenticacion NAP ya preparado para Malaga y Andalucia
- QA matrix y runbook GTFS ya escritos

## Diagnostico: donde se atasca el siguiente salto de valor

Lo siguiente ya no es “hacerla mas bonita” ni “activar el esqueleto”. Lo que falta ahora es:

1. **Cobertura geografica real**: hoy hay rutas utiles, pero muy concentradas.
2. **Providers terrestres con datos reales adicionales**: seguimos muy apoyados en deeplink + GTFS.
3. **Precios reales de ground transport**: en muchos casos seguimos sin precio confirmado.
4. **Orquestacion avanzada de providers**: ya hay varias fuentes, pero aun falta arbitraje mas inteligente.
5. **Capacidades del hub todavia planned**: traffic, POIs, incidents, eco-route, preview, offline.
6. **Madurez operativa por entorno**: local esta bastante listo, pero staging/prod necesitan perfiles, claims y observabilidad mas finos.

## Principios para las siguientes 10 fases

- No volver a gastar ciclos en UX si no desbloquea capacidad real.
- Expandir por corredores y casos de uso, no por lista abstracta de providers.
- Elegir una sola activacion dura por fase.
- Cada fase debe mover al menos una capacidad de:
  - `planned` -> `partial`
  - `partial` -> `available`
  - `deeplink` -> `real_result`
- No prometer booking o precio donde el backend no lo sostiene.

## Roadmap: siguientes 10 fases

### Fase 1. Perfiles de activacion por entorno

**Objetivo:** dejar de pensar solo en “local activado” y definir modos claros de operacion para local, staging y produccion.

**Problema actual:**

- `backend/.env.example` ya viene bastante encendido para local
- pero no esta completamente formalizado que combinacion de providers debe vivir en cada entorno

**Trabajo concreto:**

- definir perfiles canonicamente:
  - `local_demo`
  - `local_real`
  - `staging_safe`
  - `prod_gradual`
- documentar que flags viven en cada perfil
- añadir una matriz visible de activacion por entorno
- blindar que `mock_multimodal` no reaparezca como camino feliz silencioso en entornos que no lo merecen

**Archivos principales:**

- `backend/.env.example`
- `docs/reference/backend/door-to-door-contract.md`
- `docs/runbooks/`
- `registry.py`

**Resultado de valor:**

- el equipo sabe exactamente que esta encendido en cada entorno
- se evita el clasico “en local parece funcionar todo”

### Fase 2. Expansion GTFS España desbloqueando NAP

**Objetivo:** convertir Malaga y Andalucia de `planned_blocked` a corredores usables.

**Problema actual:**

- `gtfs_corridors.json` ya define:
  - `malaga_agp_urbano`
  - `almeria_agp_regional`
- pero ambos siguen bloqueados por autenticacion NAP

**Trabajo concreto:**

- conseguir y validar `GTFS_NAP_API_KEY`
- verificar descarga real de:
  - `emt_malaga_nap`
  - `ctan_andalucia_nap`
- ejecutar `gtfs_probe.py` y caracterizar cobertura real
- mover corredores de:
  - `planned_blocked` -> `verified_limited` o `verified`
- añadir tests y evidencia de QA reales con esos feeds

**Archivos principales:**

- `backend/app/door_to_door/providers/gtfs_feeds.json`
- `backend/app/door_to_door/providers/gtfs_corridors.json`
- `backend/app/door_to_door/services/gtfs_feed_service.py`
- `docs/runbooks/runbook-gtfs-activacion.md`

**Resultado de valor:**

- el caso “Almeria -> AGP” que motivaba gran parte del módulo deja de ser teórico

### Fase 3. Cobertura GTFS de llegada, no solo de salida

**Objetivo:** dejar de resolver solo el tramo origen -> aeropuerto y empezar a cerrar mejor el tramo aeropuerto -> destino final.

**Problema actual:**

- los corredores GTFS actuales estan muy sesgados a un solo lado del viaje
- muchas rutas quedan como `partial_actionable`

**Trabajo concreto:**

- seleccionar feeds de ultima milla o area de llegada para:
  - TSF/Treviso
  - VCE/Venice
  - siguientes aeropuertos prioritarios
- medir para cada aeropuerto:
  - nearby stops
  - service by date
  - matching with arrival window
- reforzar inbound GTFS como tramo real

**Archivos principales:**

- `gtfs_corridors.json`
- `gtfs_transit.py`
- tests GTFS

**Resultado de valor:**

- mas opciones pasan de `partial_actionable` a `full`

### Fase 4. Segunda familia de providers reales terrestres

**Objetivo:** salir del binomio `deeplink + GTFS` y activar una segunda familia de datos terrestres reales.

**Problema actual:**

- existen placeholders como:
  - `navitia`
  - `opentripplanner`
  - `distribusion`
  - `omio`
  - `mozio`
  - `amadeus_transfers`
- pero ninguno esta realmente cableado

**Decision recomendada:**

- no activar seis a la vez
- elegir una sola via para el siguiente salto, con esta prioridad:
  1. `opentripplanner` si hay endpoint real controlable por nosotros
  2. `navitia` si encaja legal y tecnicamente con cobertura deseada
  3. `distribusion` o `mozio` si queremos foco shuttle/bus comercial

**Trabajo concreto:**

- elegir proveedor
- crear contrato de integracion real
- añadir factory activa al registry
- devolver `real_result` donde aplique
- preservar fallback a deeplink cuando falle

**Resultado de valor:**

- aumenta cobertura de horarios reales fuera del mundo GTFS puro

### Fase 5. Capa de precio real para ground transport

**Objetivo:** que `/puerta-a-puerta` empiece a confirmar precios en algunos tramos terrestres.

**Problema actual:**

- gran parte del valor sigue sin precio confirmado
- eso limita utilidad comparativa real

**Trabajo concreto:**

- definir taxonomia de pricing por provider:
  - `confirmed`
  - `estimated`
  - `external`
  - `unavailable`
- empezar por el provider que mas retorno dé
- almacenar precio real de tramo sin contaminar el resto
- reflejarlo tanto por leg como por option

**Archivos principales:**

- `schemas.py`
- `search_service.py`
- provider real elegido en fase 4
- frontend option cards / decision logic

**Resultado de valor:**

- el comparador deja de ser principalmente tiempo+margen y empieza a servir para coste real

### Fase 6. Orquestacion avanzada y arbitration entre fuentes

**Objetivo:** que el sistema no solo junte providers, sino que elija mejor fuente por tramo.

**Problema actual:**

- ya hay varias fuentes
- pero el arbitraje todavia es bastante simple

**Trabajo concreto:**

- definir preferencia por tipo de tramo:
  - walking / car directions
  - public transit
  - rideshare / shuttle
- elegir mejor source por:
  - calidad
  - cobertura
  - precio
  - frescura
  - completitud
- permitir opcion compuesta con fuentes mezcladas de forma mas inteligente

**Archivos principales:**

- `search_service.py`
- `itinerary_builder.py`
- `domain/scoring.py`

**Resultado de valor:**

- mejores recomendaciones sin necesidad de añadir mas frontend

### Fase 7. Activar 2 capacidades nuevas del hub con backend real

**Objetivo:** mover al menos dos capacidades del hub de `planned` a algo genuinamente util.

**Estado actual del hub:**

- reales o casi reales:
  - `navigation`
  - `transit`
  - `alternatives`
  - `saved_places`
- planned:
  - `traffic`
  - `street_view_preview`
  - `nearby_pois`
  - `offline`
  - `incidents`
  - `eco_route`

**Recomendacion:**

- priorizar dos de estas tres:
  - `nearby_pois`
  - `traffic`
  - `incidents`

**Trabajo concreto:**

- conectar fuente real o semirreal
- propagarla a `map_capabilities`
- mostrar por que pasa a `available` o `partial`

**Resultado de valor:**

- el hub deja de ser solo “panel honesto” y gana utilidad operativa real

### Fase 8. Persistencia de itinerarios reutilizables

**Objetivo:** ir mas alla de historial y saved places, y permitir que un plan compuesto se convierta en artefacto reutilizable.

**Problema actual:**

- ya hay historial reutilizable
- pero aun no existe una nocion fuerte de “plan puerta a puerta guardado”

**Trabajo concreto:**

- definir entidad de plan guardado o snapshot util
- guardar:
  - origen
  - destino
  - watch asociado
  - opcion elegida
  - fuentes usadas
  - fecha de validez
- permitir rehidratar y recalcular desde ahi

**Archivos principales:**

- modelos DB
- `routes.py`
- hooks frontend de history/search/results

**Resultado de valor:**

- el modulo se vuelve mas cercano a herramienta de decision real y menos a consulta puntual

### Fase 9. Observabilidad operacional por corredor/provider

**Objetivo:** medir de verdad que esta funcionando y donde.

**Problema actual:**

- hay QA matrix y criterios
- pero falta observabilidad mas util para operar cobertura real

**Trabajo concreto:**

- exponer indicadores por entorno:
  - ratio `full`
  - ratio `partial_actionable`
  - warnings dominantes
  - corredores verificados mas usados
  - providers con mayor tasa de fallo
- log estructurado por busqueda y provider
- tablero minimo o endpoint de health agregado

**Resultado de valor:**

- el equipo puede decidir donde invertir siguiente activacion

### Fase 10. Rollout progresivo por mercados y claims de producto

**Objetivo:** convertir activaciones tecnicas en rollout de producto real por pais/corredor/entorno.

**Problema actual:**

- ya hay claims bastante honestos
- pero falta un “go to market” tecnico por cobertura

**Trabajo concreto:**

- definir niveles de rollout:
  - piloto interno
  - beta corredores verificados
  - beta regional
  - apertura parcial
- ligar claims de UI a cobertura real
- introducir gating por corredor o pais si hace falta
- revisar Watchlist y Quick Search como puertas de entrada al modulo

**Resultado de valor:**

- `/puerta-a-puerta` deja de ser “modulo activado en el repo” y pasa a ser “capacidad de producto con rollout controlado”

## Orden recomendado de ejecucion

No ejecutaria esto en orden lineal sin pensar. Haría:

1. Fase 2
2. Fase 3
3. Fase 4
4. Fase 6
5. Fase 5
6. Fase 7
7. Fase 8
8. Fase 9
9. Fase 10
10. Fase 1 si hace falta endurecer perfiles antes del despliegue, o moverla al inicio si vamos a tocar staging/prod ya

### Prioridad real

Si lo que quieres es “que sirva más” cuanto antes, el mayor retorno está aquí:

- desbloquear NAP España
- cerrar mejor inbound GTFS
- activar un segundo provider terrestre real
- meter pricing real donde sea posible

## Lo que ya no hace falta volver a planear

No hace falta replanear otra vez como si estuviera pendiente:

- honestidad visual base
- serializacion de `map_capabilities`
- completitud de opciones
- migracion de saved places a backend
- QA matrix base
- runbook GTFS inicial

Eso ya existe. Ahora toca expandir y endurecer.

## Definicion de done para este siguiente ciclo

Este siguiente roadmap habra valido la pena si al final conseguimos tres cosas:

1. El caso España -> aeropuerto -> vuelo -> llegada ya tiene mas de un corredor con datos reales sostenibles.
2. Algunas rutas muestran ya precio real de ground transport, no solo duracion y deeplink.
3. El hub y la recomendacion pasan de “buenos contenedores” a “motor que refleja cobertura real por zona y fuente”.

