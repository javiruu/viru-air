# QA - estabilizacion de `/watchlist` y `/quick-search`

**Estado:** vivo  
**Ultima revision:** 2026-06-05  
**Fuente de verdad:** si  
**Area:** QA

## Resumen

Campana de estabilizacion centrada en dos rutas privadas canonicas:

- `/watchlist`
- `/quick-search`

Se valido con:

- tests focalizados frontend y backend;
- ejecucion real con frontend y backend levantados en local;
- sesion limpia creada durante la verificacion;
- inspeccion de consola del navegador y logs backend.

## Inventario reproducible de incidencias

| ID | Ruta | Sintoma | Capa principal | Severidad | Estado |
|---|---|---|---|---|---|
| VT-STAB-001 | `/watchlist` | Se renderizaba la clave cruda `watchlist.noDataLabel` en el detalle sin snapshots | frontend/i18n | alta | corregida |
| VT-STAB-002 | `/watchlist` | Warning de mapa por estilo no cargado (`There is no style added to the map.`) | frontend/runtime | alta | corregida |
| VT-STAB-003 | `/quick-search` | Estado parcial/vacio dificil de interpretar cuando el provider degrada | backend observability + UI state | media | mitigada |
| VT-STAB-004 | `/quick-search` | El pool HTTP de providers se saturaba con concurrencia real (`Connection pool is full`) | backend/provider infra | media | corregida |
| VT-STAB-005 | `/quick-search` | La UI interpretaba degradacion y outage sobre todo con warnings legacy de Ryanair y podia infravalorar senales canonicas (`warnings_structured`, `provider_status`) | frontend/contract resilience | media | corregida |

## Evidencia por incidencia

### VT-STAB-001

Antes:

- en `/watchlist`, con una ruta sin snapshots, el detalle mostraba una clave i18n en bruto.

Despues:

- se renderiza `Sin datos todavia`.

Prueba:

- verificacion runtime con cuenta limpia y ruta creada en local;
- test anadido en `frontend/tests/watchlist-runtime-guards.test.ts`.

### VT-STAB-002

Antes:

- al abrir `/watchlist` con una ruta en foco, el mapa podia avisar que no tenia estilo cargado todavia.

Despues:

- el mapa espera a que el estilo este listo antes de exponer `readyMap`, `fitBounds` y `easeTo`.

Prueba:

- verificacion runtime aislada en contexto limpio;
- guard test en `frontend/tests/watchlist-runtime-guards.test.ts`.

### VT-STAB-003

Observado:

- `POST /api/v1/search/quick` podia devolver `200` con `results=0` y estado parcial visible.
- los logs reales mostraban degradacion de provider, no mismatch de contrato frontend/backend.

Clasificacion:

- fallo funcional externo/de provider, no rotura base de formulario o routing.

Mitigacion:

- log backend enriquecido con `warnings`, `provider_statuses` y `concurrency_limit`.

### VT-STAB-004

Observado:

- logs backend con `Connection pool is full, discarding connection: www.ryanair.com`.

Causa:

- `requests.Session()` con pool por defecto demasiado pequeno frente al paralelismo efectivo de quick-search.

Mitigacion:

- pool HTTP ampliado a `32` en providers `ryanair` y `duffel`;
- test unitario nuevo de configuracion de pool.

### VT-STAB-005

Observado:

- el frontend dependia demasiado de `filters.warnings` y de codigos especificos de Ryanair para marcar degradacion;
- si el backend exponia mejor la capa canonica (`meta.warnings_structured`, `meta.provider_status.overall_status`), la UI podia quedarse corta al clasificar el estado.

Mitigacion:

- fusion y deduplicacion de warning codes desde `filters.warnings` y `meta.warnings_structured`;
- normalizacion defensiva de `provider_status` en frontend;
- estados degradados y copy vacio/outage ahora leen tanto senales legacy como canonicas.

## Matriz sintoma -> capa responsable

| Sintoma | Responsable principal | Comentario |
|---|---|---|
| clave de traduccion visible | frontend/i18n | error de key en consumidor |
| warning de estilo del mapa | frontend/runtime | orden de inicializacion |
| boton Buscar deshabilitado | frontend/form validation | no reproducido en esta campana |
| `200` con cero resultados y avisos de provider | backend/provider | degradacion externa servida correctamente |
| `Connection pool is full` | backend/http infra | saturacion del pool por concurrencia |
| degradacion canonica no reflejada de forma consistente en UI | frontend/contract resilience | el frontend debe leer warnings y `provider_status`, no solo codigos vendor-specific |

## Contrato y rutas auditadas

Contrato backend contrastado:

- `docs/reference/backend/quick-search-contract.md`

Rutas canonicas contrastadas:

- `docs/overview/current-state.md`
- `docs/runbooks/runbook-route-canonicalization.md`

Resultado:

- no se encontro divergencia estructural entre payload canonico frontend/backend en la ruta reproducida;
- si se encontraron problemas de runtime, observabilidad y resiliencia en la lectura frontend del contrato de degradacion.

## Checks ejecutados

### Frontend

```powershell
npm test -- --test-name-pattern="quick-search-screen-state|quick-search-refactor-utils|watchlist runtime guards"
npm run lint
```

Resultado:

- tests focalizados pasando;
- `lint` pasa con warning preexistente en `HotelSearchPanel.tsx`.

### Backend

```powershell
python -m pytest backend\tests\unit\test_provider_session_pooling.py backend\tests\integration\test_watchlist_flow.py backend\tests\integration\test_watchlist_refresh_cooldown.py backend\tests\integration\test_quick_search_returns_results.py backend\tests\integration\test_quick_search_realistic_happy_path.py
```

Resultado:

- suite focalizada pasando.

## Estado actual de cierre parcial

### Hecho

- baseline reproducible levantada;
- incidencias priorizadas y clasificadas;
- fixes aplicados a `watchlist`;
- fix de infraestructura HTTP aplicado a providers de `quick-search`;
- observabilidad de `quick-search` enriquecida;
- lectura frontend endurecida para warnings/provider status canonicos y legacy.

### Pendiente para cierre total de la campana

- ampliar la bateria de casos reales de `quick-search` degradado y vacio;
- dejar checklist final de release con revision manual humana sobre ambas rutas;
- decidir si conviene bajar paralelismo efectivo o introducir estrategia adaptativa por provider.
