# Watchlist W0 Baseline (pre-polish)

**Estado:** vivo  
**Fecha:** 2026-05-12  
**Fuente de verdad:** si  
**Área:** QA / watchlist  
**Commit auditado:** `e360d169050f81fba667870a1420dc11b4c3966d` (`main`, sincronizado con `origin/main`)

## Scope

Fase W0 de baseline para `/watchlist` sin cambios de layout, sin cambios de comportamiento de producto, sin cambios backend y sin features nuevas.  
Objetivo: congelar inventario funcional, baseline UX factual y protección anti-regresión mínima antes de fases W1-W9.

## Component inventory

| Área | Componente | Responsabilidad | Datos/API | Riesgo UX |
|---|---|---|---|---|
| cabecera Watchlist | `frontend/src/app/(private)/watchlist/page.tsx` (header + acciones) | Render de título/subtítulo, botón volver dashboard y alta de vuelo | i18n `watchlist.title/subtitle/addFlight`, navegación `router.push("/dashboard")` | Jerarquía superior compite con bloques de contenido |
| lista de rutas vigiladas | `SmartWatchListPanel.tsx` | Lista operativa, búsqueda, orden, selección, estado por fila, acciones por fila | `items`, `smartListItems`, `watchMeta`, `historyRows`; acciones single/bulk | Título largo sensible a wrap, acciones masivas pueden parecer siempre activas |
| detalle de ruta | `WatchDetailPanel.tsx` | Estado de ruta seleccionada, snapshot más reciente, frescura y acciones directas | `selectedWatch`, `detail`, `summary`; `GET /watchlist/{id}` | Puede quedar relegado frente a histórico por orden de bloques |
| resumen de precios | `WatchDetailPanel.tsx` (`history-summary--kpis`) | KPIs latest/min/max/avg/delta/count | `GET /prices/summary?watch_id=...` | Con `count` bajo transmite confianza excesiva |
| calendario | `WatchDetailPanel.tsx` (tabla Calendario) | Vista agregada por día (mín/máx/media/capturas/señal) | `GET /prices/calendar?watch_id=...` | Puede leerse como concluyente con poca muestra |
| histórico integrado | `HistoryIntegratedPanel.tsx` (inyectado desde `page.tsx`) | Filtros O/D/fechas, gráfico, calendario histórico y zoom/rango | `historyRows` desde `POST /prices/history/batch`, estado de filtros en controller | Posición alta y filtros similares a selector principal generan duplicidad percibida |
| comparativa multi-vuelo | `ComparePanels.tsx` | Selección de 2-4 rutas, comparación y badges de precio/estabilidad | `GET /prices/compare?watch_ids=...` | Menor prominencia antes de selección válida; estados 0/1/2+ sensibles |
| mapa/mesa de decisiones | `WatchlistMapDecisionPanel` (dynamic import en `page.tsx`) | Contexto espacial y foco de rutas | `routes/mode/insight` derivados de controller | Bloque vacío puede ocupar espacio y contradecir actividad de rutas |
| acciones individuales | `SmartWatchListPanel.tsx` + `WatchDetailPanel.tsx` | Actualizar, pausar/reanudar, eliminar por ruta | `POST /watchlist/{id}/refresh-now`, `PUT /watchlist/{id}`, `DELETE /watchlist/{id}` | Redundancia de acciones entre lista y detalle |
| acciones masivas | `SmartWatchListPanel.tsx` + `useWatchlistActions.ts` | Refresh/pausa/reanudar/eliminar de selección | `POST /watchlist/refresh-bulk`, `PUT/DELETE` por lote en cliente | Aparición contextual poco evidente para usuario novato |
| estados vacíos | `SmartWatchListPanel.tsx`, `WatchDetailPanel.tsx`, `ComparePanels.tsx` | Guías vacías y mensajes de falta de datos/selección | Estado local + respuestas de APIs de precios | Inconsistencia potencial de tono entre vacíos operativos y analíticos |
| footer/nav si aparece | shell privada (fuera del módulo específico) | Navegación privada y rutas legacy | rutas privadas canónicas + alias legacy (`/suggestions` -> feedback) | Riesgo de regresión de copy/ruta legacy en vistas privadas |

## Data, contracts and endpoints used indirectly

- `GET /api/v1/watchlist`
- `POST /api/v1/watchlist`
- `PUT /api/v1/watchlist/{id}`
- `DELETE /api/v1/watchlist/{id}`
- `GET /api/v1/watchlist/{id}`
- `POST /api/v1/watchlist/{id}/refresh-now`
- `POST /api/v1/watchlist/refresh-bulk`
- `GET /api/v1/prices/summary?watch_id=...`
- `GET /api/v1/prices/calendar?watch_id=...`
- `GET /api/v1/prices/compare?watch_ids=...`
- `POST /api/v1/prices/history/batch`
- `GET /api/v1/airports/compatible?...`

## Visual states observed

- Header con CTA de alta.
- FTUE notice visible/oculta.
- Notice de última actualización global.
- Notice de mensaje operativo (`success`/`error`).
- Lista vacía (guía 3 pasos).
- Lista filtrada sin resultados.
- Lista con selección activa (acciones bulk visibles).
- Detalle vacío (sin ruta seleccionada).
- Detalle cargando.
- Resumen/KPI con y sin datos.
- Calendario con y sin datos.
- Comparativa rápida (dos fechas) opcional.
- Comparativa multi-vuelo en estados 0/1/<2, loading, 2..4 con datos, sin datos, mixed currency.
- Mapa en loading/operativo (según datos).

## Actions inventory

- Crear watch.
- Seleccionar watch.
- Buscar y ordenar lista.
- Refrescar watch individual.
- Pausar/reanudar watch individual.
- Eliminar watch individual.
- Refrescar filtrados del histórico.
- Bulk refresh / bulk pause / bulk resume / bulk delete.
- Toggle de selección para comparativa.
- Filtros de histórico (origen/destino/fechas/punto/rango/mes).

## Current test coverage map

| Bloque | Tests actuales |
|---|---|
| Endpoints F2 consumidos en watchlist | `frontend/tests/watchlist-f2-integration.test.ts` |
| Histórico avanzado (calendar/compare, límites 2..4) | `frontend/tests/watchlist-f3b-advanced-history.test.ts` |
| Resumen refresh-bulk | `frontend/tests/watchlist-refresh-bulk-summary.test.ts` |
| Utilidades de fechas watchlist | `frontend/tests/watchlist-date-utils.test.ts` |
| Catálogo de estados compartido | `frontend/tests/status-catalog.test.ts` |
| Anti-regresión copy privada ES (incluye watchlist y legacy) | `frontend/tests/private-visible-copy-es.test.ts` |
| Baseline anti-regresión W0 de presencia de bloques y guardas copy/ruta | `frontend/tests/watchlist-w0-baseline.test.ts` |

## UX findings before polish

| Finding | Severidad W0 | Evidencia factual | Estado W0 |
|---|---|---|---|
| Histórico demasiado arriba en la lectura del flujo | major | `HistoryIntegratedPanel` se renderiza antes de lista+detalle+mapa en `page.tsx` | accepted for W0 |
| Duplicidad aparente entre selector de ruta y filtros del histórico | major | Lista elige ruta activa y filtros histórico vuelven a mostrar O/D/fechas | accepted for W0 |
| “Lista inteligente de vuelos” susceptible de romperse visualmente | minor | Título largo en panel y densidad alta de herramientas en cabecera del bloque | accepted for W0 |
| Acciones repetidas/masivas poco contextuales | major | Acciones por fila + acciones bulk en mismo panel, con cambio visual condicionado a selección | accepted for W0 |
| Mapa vacío o contradictorio con rutas activas | major | Panel de mapa dedicado puede ocupar espacio con señal limitada si no hay rutas útiles | accepted for W0 |
| KPIs con 1 snapshot parecen concluyentes | minor | KPI summary renderiza métricas aunque `count` bajo (si `count > 0`) | accepted for W0 |
| Frescura “En observación” poco accionable sin tiempo concreto | major | Etiquetas de frescura presentes, pero acción temporal concreta no priorizada en layout | accepted for W0 |
| Comparativa poco prominente antes de selección suficiente | major | Bloque compare visible pero valor real aparece desde 2 selecciones | accepted for W0 |

### Duplicidad actual detectada

| Punto | Estado actual W0 | Corrección planificada |
|---|---|---|
| Lista selecciona ruta activa | Sí | W2 selección única de ruta |
| Filtros histórico muestran origen/destino/fecha | Sí | W2 convergencia de selector/filtros |
| Sensación de “doble selector” | Sí | W2 claridad de modelo mental |

## Baseline visual capture

- Screenshot guardada en: `docs/qa/screenshots/watchlist-w0-baseline.png`.
- Evidencia técnica de ejecución:
  - `GET http://127.0.0.1:3010/watchlist` responde `200` (frontend arriba).
  - En browser (Playwright headless), navegación final: `http://127.0.0.1:3010/login?returnUrl=%2Fwatchlist`.
  - `h1` final renderizado: `Acceso`.
- Conclusión W0 de captura:
  - Se capturó el estado real del entrypoint de `/watchlist` en entorno local sin sesión autenticada persistida.
  - No se aplicó hack de auth ni mock nuevo (restricción W0).
  - Baseline funcional autenticada de contenido interno `/watchlist` queda dependiente de sesión de prueba válida existente en fases siguientes.

## Watchlist polish risk matrix

| Riesgo | Probabilidad | Impacto | Mitigación en fases W1-W9 |
|---|---|---|---|
| romper selección de ruta | media | alta | W2 con tests de selección única y fallback claro |
| romper refresh bulk | media | alta | W3 preservar contrato `refresh-bulk` + tests resumen |
| romper compare | media | alta | W8 sobre base de límites 2..4 y estados vacíos actuales |
| romper histórico | media | alta | W1/W2 cambios jerárquicos sin tocar contratos de datos |
| romper mapa cleanup | baja | media | W7 colapsado progresivo sin eliminar integración |
| duplicar estado local | media | media | consolidar ownership de estado por fase y test por bloque |
| introducir copy EN | media | media | mantener guardas `private-visible-copy-es` + tests W0 |
| empeorar responsive | media | alta | validación browser en desktop + narrow viewport por fase |
| tocar backend por error | baja | alta | scope lock frontend-only y revisión de diff por ruta |

## Plan W1-W9 (referencia, no implementado en W0)

1. W1 jerarquía visual  
2. W2 selección única de ruta  
3. W3 acciones contextuales  
4. W4 renombre “Rutas vigiladas”  
5. W5 confianza histórica  
6. W6 frescura accionable  
7. W7 mapa plegado  
8. W8 comparativa reactiva  
9. W9 pulido visual final

## Verification executed in W0

- `npm test` (en `frontend`) -> pass `91`, fail `0`, skipped `15`.
- `npm run build` (en `frontend`) -> OK.
- `npm run lint` (en `frontend`) -> OK con warning preexistente de `react-hooks/exhaustive-deps` en `preferencias/busqueda/page.tsx:60`.
