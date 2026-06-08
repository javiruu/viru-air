# Plan Aterrizado Real para `/puerta-a-puerta`

**Estado:** activo  
**Fecha:** 2026-06-08  
**Autor:** Codex  
**Area:** plan  
**Fuente de verdad:** no; plan operativo apoyado en codigo, tests y docs vivas

> **Para Codex/Claude:** REQUIRED SUB-SKILL: usa `writing-plans` como marco base. Para ejecutar fases UI, usar tambien `Browser` para evidencia de apoyo y pedir revision manual del usuario antes de cerrar visualmente.

## Objetivo

Convertir `/puerta-a-puerta` de una feature hibrida ya sembrada en una herramienta honestamente util, incremental y publicable, sin rehacer lo existente ni romper contratos ya consumidos por frontend, backend, tests o Watchlist.

La meta no es "hacerla perfecta". La meta es que cada fase aumente utilidad real, claridad de fuentes y accionabilidad para el usuario final.

Este documento complementa `docs/plans/2026-06-04-puerta-a-puerta-mejoras-frontend.md` y pasa a ser la referencia operativa mas util para las siguientes iteraciones, porque ya incorpora backend, contrato, warnings, providers y verificacion real del repo actual.

## Baseline real confirmado hoy

Estos puntos salen de codigo y docs vivas revisadas hoy, no del brief:

- La ruta existe en `frontend/src/app/(private)/puerta-a-puerta/page.tsx` y monta `DoorToDoorPanel`.
- El modulo frontend ya no es maqueta vacia: existe `frontend/src/modules/door-to-door/` con panel, filtros, timeline, route visual, sticky bar, map hub, history y hooks dedicados.
- El frontend ya consume endpoints reales definidos en `frontend/src/modules/door-to-door/api.ts`:
  - `POST /door-to-door/search`
  - `GET /door-to-door/suggestions`
  - `GET|PUT|DELETE /door-to-door/saved-location`
  - `GET /door-to-door/history`
  - `POST /door-to-door/history/{history_id}/chosen`
  - `GET /door-to-door/providers/status`
- La documentacion viva del dominio ya existe:
  - `docs/product/door-to-door.md`
  - `docs/reference/backend/door-to-door-contract.md`
- El backend real vive en `backend/app/door_to_door/` con:
  - endpoints en `backend/app/door_to_door/api/routes.py`
  - schemas en `backend/app/door_to_door/schemas.py`
  - scoring en `backend/app/door_to_door/domain/scoring.py`
  - search service en `backend/app/door_to_door/services/search_service.py`
  - registry en `backend/app/door_to_door/providers/registry.py`
- El registry ya distingue providers y estados funcionales. Hoy existen piezas reales o parcialmente reales para:
  - `mock_multimodal`
  - `google_maps_deeplink`
  - `google_routes`
  - `blablacar_deeplink`
  - `goopti_deeplink`
  - `external_deeplink`
  - `gtfs_transit`
  - `google_places`
  - `nominatim` como fallback de suggestions
- Ya hay cobertura de tests relevante:
  - `frontend/tests/door-to-door-v1.test.tsx`
  - `backend/tests/integration/test_door_to_door.py`
  - `backend/tests/unit/test_door_to_door_deeplinks.py`
  - `backend/tests/unit/test_door_to_door_gtfs_transit.py`
  - `backend/tests/unit/test_door_to_door_google_routes.py`
  - `backend/tests/unit/test_door_to_door_google_places.py`

## Hallazgos concretos que el plan debe asumir

### Honestidad ya conseguida y que hay que preservar

- `DoorToDoorOptionCard.tsx` ya evita inventar precio en varias ramas:
  - deeplink sin precio confirmado
  - API real sin precio
  - GTFS/open data sin precio
- El backend ya emite warnings de honestidad como `UNCONFIRMED_PRICE`, `NO_REAL_PROVIDER_COVERAGE`, `NO_COVERAGE`, `GTFS_PRICE_UNAVAILABLE`, `BLABLACAR_DEEPLINK_PARTIAL` o `GOOGLE_ROUTES_UNAVAILABLE`.
- `docs/product/door-to-door.md` ya define el producto como "hibrido honesto", no como cobertura total.

### Grietas reales detectadas ahora mismo

- `frontend/src/modules/door-to-door/DoorToDoorPanel.tsx` sigue renderizando `--:--` desde `formatClock()` cuando no hay horario.
- `frontend/src/modules/door-to-door/components/DoorToDoorTimeline.tsx` sigue usando placeholders tipo `--` para hora y duracion.
- `DoorToDoorPanel.tsx` y el historial siguen mostrando rangos como `-- - -- EUR`, que no es tan grave como `0,00 EUR` pero tampoco es copy honesto final.
- Hay inconsistencia de warning entre capas:
  - backend emite `PARTIAL_PROVIDER_COVERAGE`
  - `useDoorToDoorResults.ts` mira `PROVIDER_PARTIAL_COVERAGE`
  - el contrato vivo documenta `PROVIDER_PARTIAL_COVERAGE`
- `docs/reference/backend/door-to-door-contract.md` documenta `map_capabilities`, y el frontend lo soporta como opcional, pero `backend/app/door_to_door/schemas.py` no lo expone todavia en `DoorToDoorSearchResponse`.
- `useDoorToDoorMapHub.ts` hoy compensa esa ausencia construyendo fallback desde `providers/status`, asi que el panel de capacidades es util pero parcialmente sintetico.
- `DoorToDoorPanel.tsx` mezcla copy localizado con cadenas hardcodeadas como `Desde {price} EUR` o `Ver ruta en Maps`; eso complica la fase de honestidad y consistencia ES/EN.

## Reglas operativas para ejecutar este plan

- No rehacer `DoorToDoorPanel` ni la arquitectura de providers desde cero.
- No cambiar contratos existentes sin antes alinear:
  - backend schemas
  - docs/reference/backend/door-to-door-contract.md
  - frontend types
  - tests existentes
- No borrar stubs, scrapers base o providers placeholder en estas fases salvo prueba fuerte de que sobran y el usuario lo pida.
- Las fases UI deben cerrar con:
  - tests en terminal
  - Browser como evidencia de apoyo
  - revision manual del usuario en dark y light, porque asi lo piden `frontend/AGENTS.md` y `tests/AGENTS.md`
- Los cambios deben vivir en el repo canonico actual; no usar mirrors ni `_publish_repo`.

## Skills y herramientas recomendadas por fase

| Fase | Skill / herramienta principal | Uso real |
|---|---|---|
| F1 auditoria | `viru-tracker-context`, `writing-plans`, `code-reviewer` | Reentrada rapida, mapa de codigo, hallazgos, severidad |
| F2 honestidad UI | `web-bug-fixer`, `Browser`, `Viru Tracker UI` | Quitar placeholders falsos y validar estados |
| F3 contrato | `fullstack-developer`, `code-reviewer` | Alinear schemas, types, warnings y serializacion |
| F4 vuelo bloqueado | `fullstack-developer`, `Browser` | Mejorar caso core con watch seleccionado |
| F5 acciones externas | `web-bug-fixer`, `Browser` | Deep links, CTAs visibles y fallback por tramo |
| F6 registry/fuentes | `fullstack-developer`, `code-reviewer` | Capacidades, notas, warnings canonicos |
| F7 GTFS/open data | `fullstack-developer` | Cobertura parcial honesta sin promesas falsas |
| F8 ranking/composer | `fullstack-developer` | Scoring, etiquetas y explicacion de recomendacion |
| F9 utilidad UX | `Viru Tracker UI`, `design-taste-frontend`, `Browser` | Jerarquia, timeline y comparacion mas utiles |
| F10 cierre | `code-reviewer`, `Browser` | QA, docs, runbook y rollout |

## Mapa de archivos que realmente gobiernan el modulo

### Frontend core

- `frontend/src/app/(private)/puerta-a-puerta/page.tsx`
- `frontend/src/modules/door-to-door/DoorToDoorPanel.tsx`
- `frontend/src/modules/door-to-door/types.ts`
- `frontend/src/modules/door-to-door/api.ts`
- `frontend/src/modules/door-to-door/decision.ts`
- `frontend/src/modules/door-to-door/mapHub.ts`
- `frontend/src/modules/door-to-door/hooks/useDoorToDoorSearch.ts`
- `frontend/src/modules/door-to-door/hooks/useDoorToDoorResults.ts`
- `frontend/src/modules/door-to-door/hooks/useDoorToDoorHistory.ts`
- `frontend/src/modules/door-to-door/hooks/useDoorToDoorMapHub.ts`
- `frontend/src/modules/door-to-door/components/DoorToDoorOptionCard.tsx`
- `frontend/src/modules/door-to-door/components/DoorToDoorTimeline.tsx`
- `frontend/src/modules/door-to-door/components/DoorToDoorRouteVisual.tsx`
- `frontend/src/i18n/domains/doorToDoor.ts`
- `frontend/src/styles/screens.css`

### Backend core

- `backend/app/door_to_door/api/routes.py`
- `backend/app/door_to_door/schemas.py`
- `backend/app/door_to_door/services/search_service.py`
- `backend/app/door_to_door/services/itinerary_builder.py`
- `backend/app/door_to_door/domain/scoring.py`
- `backend/app/door_to_door/providers/registry.py`
- `backend/app/door_to_door/providers/deeplink_blablacar.py`
- `backend/app/door_to_door/providers/deeplink_goopti.py`
- `backend/app/door_to_door/providers/deeplink_maps.py`
- `backend/app/door_to_door/providers/google_routes.py`
- `backend/app/door_to_door/providers/google_places.py`
- `backend/app/door_to_door/providers/gtfs_transit.py`
- `backend/app/door_to_door/providers/nominatim.py`

### Tests y contratos

- `frontend/tests/door-to-door-v1.test.tsx`
- `backend/tests/integration/test_door_to_door.py`
- `backend/tests/unit/test_door_to_door_deeplinks.py`
- `backend/tests/unit/test_door_to_door_gtfs_transit.py`
- `docs/product/door-to-door.md`
- `docs/reference/backend/door-to-door-contract.md`

## Fases aterrizadas

### Fase 1. Auditoria quirurgica y mapa de verdad

**Objetivo:** salir con una matriz exacta de que es real, que es parcial, que es estimacion, que es deeplink y donde se esta presentando mal en UI.

**Tocar:** solo docs y, si hace falta, tests de caracterizacion; no cambiar comportamiento productivo.

**Trabajo concreto:**

1. Leer y resumir:
   - `docs/product/door-to-door.md`
   - `docs/reference/backend/door-to-door-contract.md`
   - `frontend/AGENTS.md`
   - `backend/AGENTS.md`
   - `tests/AGENTS.md`
2. Inventariar providers del registry con esta taxonomia fija:
   - `real_api`
   - `real_open_data`
   - `real_maps_deeplink`
   - `external_deeplink`
   - `estimate`
   - `stub_planned`
3. Confirmar en codigo quien decide:
   - source type
   - confidence
   - status de opcion
   - warnings
   - ranking
4. Marcar las grietas de contrato ya detectadas:
   - `PARTIAL_PROVIDER_COVERAGE` vs `PROVIDER_PARTIAL_COVERAGE`
   - `map_capabilities` documentado pero no serializado
5. Revisar que los tests existentes cubren comportamiento real y no solo strings.

**Salida exigida:**

- lista de hallazgos por severidad
- lista de contratos a no romper
- lista de huecos honestos visibles
- propuesta cerrada para Fase 2

**Verificacion minima:**

- `cd frontend && npm test -- tests/door-to-door-v1.test.tsx`
- `cd backend && pytest tests/integration/test_door_to_door.py -q`

### Fase 2. Honestidad visual y estados no falsos

**Objetivo:** que la pantalla deje de parecer una simulacion engañosa aunque siga habiendo datos parciales.

**Archivos candidatos:**

- `frontend/src/modules/door-to-door/DoorToDoorPanel.tsx`
- `frontend/src/modules/door-to-door/components/DoorToDoorTimeline.tsx`
- `frontend/src/modules/door-to-door/components/DoorToDoorOptionCard.tsx`
- `frontend/src/i18n/domains/doorToDoor.ts`
- `frontend/src/styles/screens.css`
- `frontend/tests/door-to-door-v1.test.tsx`

**Trabajo concreto:**

1. Sustituir `--:--` y `--` horarios por copy honesto:
   - `Horario no confirmado`
   - `Hora no confirmada`
   - ocultar bloque horario si visualmente suma mas ruido que claridad
2. Sustituir rangos falsos o vacios del historial y trust panel por copy explicito:
   - `Sin precio confirmado`
   - `Precio externo`
3. Hacer que cada tramo pueda expresar claramente una de estas situaciones:
   - horario real
   - horario publico/open data
   - horario estimado
   - horario no confirmado
   - precio confirmado
   - precio no confirmado
   - consulta externa
4. Etiquetar deeplinks como externos en CTA y badges, no como resultado real.
5. Mantener la separacion actual de grupos:
   - `real_result`
   - `real_deeplink`
   - `estimate_only`
   pero reforzarla con copy y badges mas honestos.

**Tests que deben quedar o ampliarse:**

- null price no pinta `0,00 EUR`
- null departure/arrival no pinta `--:--`
- deeplink pinta disclosure externo
- GTFS/open data no promete compra ni precio

**Verificacion:**

- `cd frontend && npm test -- tests/door-to-door-v1.test.tsx`
- `cd frontend && npx tsc --noEmit`
- `cd frontend && npm run build`
- Browser sobre `/puerta-a-puerta`
- revision manual del usuario:
  - dark
  - light
  - desktop
  - viewport movil

### Fase 3. Consolidacion real del contrato

**Objetivo:** alinear schemas, types, docs y warning codes antes de crecer en funcionalidades.

**Archivos candidatos:**

- `backend/app/door_to_door/schemas.py`
- `backend/app/door_to_door/services/search_service.py`
- `frontend/src/modules/door-to-door/types.ts`
- `frontend/src/modules/door-to-door/hooks/useDoorToDoorResults.ts`
- `docs/reference/backend/door-to-door-contract.md`
- tests frontend y backend relacionados

**Trabajo concreto:**

1. Unificar warning de cobertura parcial.
2. Decidir si `map_capabilities` entra ya en payload backend o si se documenta formalmente como fallback frontend.
3. Reducir ambiguedad entre `mock`, `estimate`, `maps`, `external_deeplink` y `deeplink`.
4. Alinear `source_type`, `confidence` y `status` entre frontend y backend.
5. Añadir test de serializacion para el payload alineado.

**No hacer en esta fase:**

- reescribir todos los providers
- cambiar scoring
- rediseñar UI

### Fase 4. Caso core: vuelo bloqueado de Watchlist

**Objetivo:** optimizar el caso mas util de producto: usuario ya tiene un vuelo y quiere resolver origen real y llegada real.

**Trabajo concreto:**

1. Priorizar la recomendacion para:
   - origen del usuario -> aeropuerto salida
   - vuelo
   - aeropuerto llegada -> destino final
2. Hacer visible el margen antes del vuelo y el riesgo si es bajo.
3. Mantener acciones externas por tramo incluso cuando no haya booking nativo.
4. Verificar `?watchId=` y persistencia de opcion elegida.

**Archivos clave:**

- `useDoorToDoorSearch.ts`
- `useDoorToDoorResults.ts`
- `decision.ts`
- `search_service.py`
- `backend/tests/integration/test_door_to_door.py`

### Fase 5. Acciones externas utiles de verdad

**Objetivo:** que incluso sin integracion completa el usuario pueda avanzar de inmediato.

**Trabajo concreto:**

1. Auditar builders de deeplink:
   - `deeplink_blablacar.py`
   - `deeplink_goopti.py`
   - `deeplink_maps.py`
2. Asegurar que cada CTA dice la verdad:
   - `Abrir Google Maps`
   - `Buscar en BlaBlaCar`
   - `Buscar traslado en GoOpti`
   - `Abrir proveedor`
3. No llamar `Reservar` a algo que solo abre una busqueda externa.
4. Hacer visibles acciones clave tambien en movil.

### Fase 6. Registry y fuentes explicables

**Objetivo:** que el usuario y el equipo entiendan de donde sale cada opcion.

**Trabajo concreto:**

1. Refinar `providers/status` con capacidades legibles:
   - horario
   - precio
   - duracion
   - booking
   - external search
   - api key requerida
   - cobertura parcial
2. Convertir las notas del registry en copy mas consistente entre backend y frontend.
3. Hacer que el panel de cobertura explique por que una capacidad esta en `available`, `partial`, `planned` o `unavailable`.

### Fase 7. GTFS/open data util sin humo

**Objetivo:** exprimir GTFS donde ya aporta valor sin vender cobertura universal.

**Trabajo concreto:**

1. Reforzar warnings ya soportados por tests:
   - `GTFS_FEED_UNAVAILABLE`
   - `GTFS_NO_NEARBY_STOPS`
   - `GTFS_NO_SERVICE_FOR_DATE`
   - `GTFS_NO_MATCHING_SERVICE`
   - `GTFS_PARTIAL_COVERAGE`
   - `GTFS_PRICE_UNAVAILABLE`
2. Mejorar fixtures y copy de UI para diferenciar:
   - horario publico real
   - precio no disponible
   - cobertura parcial
3. No bloquear toda la busqueda por fallo GTFS.

### Fase 8. Composer y alternativas comparables

**Objetivo:** dejar de mostrar piezas sueltas y ofrecer opciones completas comparables.

**Trabajo concreto:**

1. Revisar `decision.ts` y `domain/scoring.py`.
2. Añadir ranking visible por:
   - duracion
   - margen
   - cambios
   - coste
   - confianza
   - completitud
3. Explicar "por que esta ruta" con razones honestas, no solo decorativas.
4. Tratar una opcion parcial pero accionable como valida, no como fallo binario.

### Fase 9. UX de utilidad sin rediseño total

**Objetivo:** mejorar jerarquia y lectura sin tirar el trabajo ya hecho.

**Trabajo concreto:**

1. Mantener identidad Viru ya existente en:
   - timeline
   - route visual
   - sticky bar
   - map hub
2. Reordenar la pantalla segun utilidad real:
   - recomendada
   - timeline completo
   - alternativas
   - fuentes/confianza
   - acciones externas
   - historial/guardados
3. No convertirlo en dashboard generico.
4. Verificar dark y light con la misma intencion visual.

### Fase 10. QA, docs y rollout

**Objetivo:** cerrar el modulo como producto serio, no como experimento eterno.

**Trabajo concreto:**

1. Crear runbook QA especifico de `/puerta-a-puerta`.
2. Documentar claramente:
   - que es real
   - que es open data
   - que es deeplink
   - que es estimacion
3. Revisar impacto cruzado sobre:
   - Watchlist
   - Quick Search
   - Dashboard
4. Evitar claims de cobertura geografica que el repo no sostiene aun.

## Corte inicial recomendado: Fase 1 + Fase 2 pequeña

Este es el primer bloque que si deberia ejecutarse ya. Es el corte mas rentable y menos destructivo.

### Paso 1. Caracterizacion antes de tocar UI

- ejecutar tests actuales de frontend y backend del modulo
- sacar lista de warnings reales emitidos hoy
- confirmar exactamente donde salen:
  - `--:--`
  - `--`
  - copy duro no localizado
  - rangos de precio vacios

### Paso 2. Corregir solo los casos visibles de deshonestidad

- no tocar scoring ni arquitectura de providers
- no mover layout salvo lo necesario para que el mensaje honesto sea legible
- priorizar:
  - `DoorToDoorPanel.tsx`
  - `DoorToDoorTimeline.tsx`
  - `DoorToDoorOptionCard.tsx`
  - `doorToDoor.ts`

### Paso 3. Añadir regresion

- ampliar `frontend/tests/door-to-door-v1.test.tsx` con asserts para:
  - no `--:--`
  - no precio falso
  - disclosure externo para deeplink
  - GTFS sin precio confirmado

### Paso 4. Verificar por capas

- frontend:
  - `cd frontend && npm test -- tests/door-to-door-v1.test.tsx`
  - `cd frontend && npx tsc --noEmit`
  - `cd frontend && npm run build`
- backend:
  - `cd backend && pytest tests/integration/test_door_to_door.py -q`
  - `cd backend && pytest tests/unit/test_door_to_door_deeplinks.py tests/unit/test_door_to_door_gtfs_transit.py -q`
- browser:
  - abrir `/puerta-a-puerta`
  - probar vuelo con watch seleccionado
  - revisar dark y light
  - pedir feedback manual del usuario

### Criterio de salida del corte inicial

- la pantalla puede seguir siendo parcial
- ya no debe parecer que inventa horarios o precios
- el usuario entiende que puede confirmar fuera de Viru
- el estado de la fuente queda mas claro por opcion y por tramo
- no se rompe Watchlist ni la navegacion hacia `/puerta-a-puerta`

## Riesgos reales de ejecucion

- El warning de cobertura parcial esta desalineado entre backend, frontend y docs; si no se corrige pronto, la UI puede ocultar estado parcial real.
- `map_capabilities` esta a medio camino entre contrato y fallback frontend; si se toca sin disciplina, se crea deuda de serializacion.
- El modulo ya tiene bastante copy ES/EN; cualquier arreglo rapido con cadenas hardcodeadas empeora i18n.
- Hay trabajo local no relacionado en el repo; las fases futuras deben stagear solo los archivos del modulo y docs asociadas.

## Lo que explicitamente no se toca en el corte inicial

- rediseño total del layout
- eliminacion de stubs o scrapers base
- ampliacion geografica
- nuevo proveedor externo
- cambios profundos en scoring
- claims de cobertura "Europa completa"

## Definicion de done por fase

Una fase solo se cierra si cumple todo esto:

- cambio pequeño y trazable
- tests dirigidos ejecutados
- contrato no roto o actualizado con evidencia
- Browser usado cuando el cambio es visible
- feedback manual del usuario recogido cuando el cierre es visual
- doc actualizada si cambia contrato, warning canonico o regla operativa
