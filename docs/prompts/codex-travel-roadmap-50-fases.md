# Roadmap de viaje para Codex - 50 fases de mejora de Viru Tracker

**Estado:** vivo
**Ultima revision:** 2026-06-13
**Fuente de verdad:** no; plan operativo para agentes
**Area:** contexto IA / planificacion

## Proposito

Este documento convierte el prompt de viaje del usuario en una hoja de ruta
ejecutable para mejorar Viru Tracker con autonomia responsable. No sustituye a
`AGENTS.md`, `DESIGN.md`, los contratos backend ni las specs vivas: los resume y
ordena para que futuras sesiones puedan trabajar fase a fase sin improvisar.

La regla de mando es sencilla: cada fase debe dejar una pieza mejor, probada,
trazable y publicable desde el repo canonico. Nada de reescrituras opacas, nada
de prometer cobertura falsa, nada de gastar servicios externos sin una decision
explicita del usuario.

## Alcance de autonomia

El usuario ha dado libertad amplia para investigar y trabajar con calma. Eso
autoriza profundidad, criterio y continuidad; no autoriza cambios destructivos,
costes externos, secretos nuevos, migraciones con riesgo de datos ni cambios de
producto irreversibles sin parar y reportar.

Interpretacion practica del presupuesto mencionado:

- invertir tiempo en leer, probar y dejar evidencia;
- priorizar calidad, mantenibilidad y UX real frente a velocidad;
- no contratar servicios, consumir APIs de pago ni activar integraciones con
  coste sin aprobacion explicita.

## Fuentes leidas en Fase 1

Documentacion y reglas:

- `AGENTS.md`
- `README.md`
- `frontend/AGENTS.md`
- `backend/AGENTS.md`
- `DESIGN.md`
- `docs/AGENTS.md`
- `docs/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`
- `docs/overview/project-overview.md`
- `docs/overview/current-state.md`
- `docs/overview/repo-map.md`
- `docs/engineering/backend.md`
- `docs/engineering/frontend.md`
- `docs/engineering/testing.md`
- `docs/reference/codex-operating-contract.md`
- `docs/reference/done-checklist.md`
- `docs/prompts/README.md`

Producto, UI, QA y contratos:

- `docs/ui/UI_SYSTEM_V1.md`
- `docs/ui/UI_CONTRACT_V1.md`
- `docs/ui/estetica.md`
- `docs/product/quick-search.md`
- `docs/product/door-to-door.md`
- `docs/product/watchlist.md`
- `docs/specs/hotels-intelligence-mvp.md`
- `docs/reference/backend/quick-search-contract.md`
- `docs/reference/backend/quick-search-acceptance-checklist.md`
- `docs/reference/backend/provider-integration-guide.md`
- `docs/reference/backend/door-to-door-contract.md`
- `docs/qa/README.md`
- `docs/qa/reports/2026-06-05-watchlist-quick-search-stabilization.md`
- `docs/runbooks/runbook-watchlist-quick-search-stabilization.md`
- `docs/runbooks/runbook-puerta-a-puerta-qa.md`
- `docs/plans/2026-06-08-quick-search-roundtrip-stabilization.md`
- `docs/plans/2026-06-10-quick-search-shared-cache-review-plan.md`

Codigo inspeccionado de forma selectiva:

- `frontend/package.json`
- `backend/pyproject.toml`
- `frontend/src/app/(private)/*`
- `frontend/src/modules/quick-search/*`
- `frontend/src/modules/door-to-door/*`
- `frontend/src/modules/hotels/*`
- `frontend/src/modules/watchlist/*`
- `frontend/tests/*quick-search*`
- `frontend/tests/*watchlist*`
- `backend/app/api/v1/*`
- `backend/app/services/quick_search_*`
- `backend/app/door_to_door/*`
- `backend/app/hotels/*`
- `backend/tests/integration/test_quick_search_dual_reverse_leg.py`
- `backend/tests/unit/test_quick_search_ai_preference.py`
- tests backend de quick-search, puerta a puerta, hoteles, watchlist y alertas listados en `backend/tests/`

## Estado inicial detectado

### Repo y workflow

- Repo canonico confirmado: `C:\Users\javiru\Desktop\viru-tracker`.
- Rama actual: `main`.
- Estado inicial: worktree limpio.
- Workflow vigente: commit directo a `main` y push cuando el usuario pida cambios
  reales completados.
- `_publish_repo` no debe usarse.
- `users_prueba.txt` es intencional y no se toca.

### Arquitectura viva

- Monorepo con backend FastAPI/SQLAlchemy/Alembic y frontend Next.js/React/TypeScript.
- Backend principal en `backend/app/`.
- Frontend privado en `frontend/src/app/(private)/`.
- Documentacion viva en `docs/`; `docs/archive/` solo para contexto historico.
- UI dual por contrato: dark Aviation Dark-Luxe y light con alma, no SaaS blanco.

### Quick Search

Quick Search no esta en cero. Tiene:

- contrato backend canonico v2 con request estructurada;
- cache compartida persistente documentada como V2.1;
- preferencia AI/heuristica ya documentada en `meta.ai_preference`;
- modulos frontend separados (`requestBuilder`, `responseNormalizer`, `filterUtils`,
  `QuickSearchDualWorkspace`, `QuickSearchSidePanel`, `useQuickSearchSide`);
- flujo dual ida/vuelta implementado parcialmente;
- tests backend de reverse leg, calendar hints invertidos, deep links con `date_in`
  y guardado por `group_id`;
- tests frontend abundantes de calendario, pantalla, normalizadores, dual y e2e.

Deuda visible:

- `QuickSearchView.tsx` sigue siendo una superficie grande y cargada;
- el plan original menciona features que ya existen parcialmente y deben auditarse
  antes de reimplementar;
- faltan confirmar o endurecer busquedas recientes en autocomplete y boton de
  invertir origen/destino;
- los gaps diferidos del cierre dual siguen siendo buenos candidatos:
  deep links duales, weather por lado, loading dual mas fino y country-only dual;
- hay posible drift documental: el acceptance checklist antiguo aun menciona cache
  in-memory como riesgo, mientras el contrato v2.1 declara cache persistente.

### Puerta a puerta

Puerta a puerta esta en V1.6, con:

- contrato backend activo bajo `/api/v1/door-to-door`;
- perfiles de activacion por entorno;
- blindaje anti-mock en staging/prod;
- providers reales parciales: deeplinks, Google Routes/Places opcionales, GTFS;
- taxonomia honesta de fuentes, confianza, warnings y capacidades;
- runbook QA especifico;
- UI frontend con timeline, filtros, sticky bar, hub de mapa y estados.

Deuda visible:

- muchos providers son stubs, deeplinks o capacidad parcial;
- el valor de producto depende de no prometer disponibilidad/precio real donde no lo hay;
- la verificacion visual manual dark/light/responsive aparece como pendiente recurrente.

### Radar hotelero

Hoteles no es un MVP pendiente sin base: la spec indica fases 0-9 completadas y
post-cierre A-E aplicado. Existen:

- ruta `/hoteles`;
- dominio backend `backend/app/hotels`;
- endpoints en `backend/app/api/v1/hotels.py`;
- provider mock y Makcorps;
- comp sets, tracked offers, watchlist hotelera, alertas y sweeps;
- tests backend numerosos;
- UI modularizada en hooks y componentes.

Deuda visible:

- verificacion visual manual real sigue pendiente;
- sweeps y provider real requieren cuidado con flags y secretos;
- la planificacion futura debe tratar hoteles como consolidacion y QA, no como
  "construir desde cero".

### Watchlist, alertas e historico

Watchlist es centro operativo con:

- pagina privada `/watchlist`;
- historico integrado;
- mapa/decision panel;
- acciones contextuales;
- tests frontend W0-W9 y runtime guards;
- backend watchlist, prices, alerts y notification worker.

Alertas tienen:

- pagina privada `/alerts`;
- reglas, eventos, quiet hours y digest;
- pruebas frontend y backend.

Deuda visible:

- la campana de estabilizacion de junio dejo pendientes de cierre total:
  mas casos de quick-search degradado/vacio, checklist final de release y decision
  sobre paralelismo adaptativo por provider.

### QA y tooling

Comandos relevantes detectados:

- Frontend:
  - `cd frontend && npm test`
  - `cd frontend && npm run lint`
  - `cd frontend && npm run build`
  - `cd frontend && npm run test:e2e:quick-search`
  - `cd frontend && npm run qa:visual:quick-search`
- Backend:
  - `cd backend && python -m pytest`
  - tests focalizados en `backend/tests/unit` y `backend/tests/integration`
  - `python -m alembic check`
- Release guard:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\release_guard.ps1 -AllowDirtyWorktree`

Observacion local:

- `rg` no estuvo disponible en esta sesion; se uso `Get-ChildItem` y
  `Select-String` como fallback.
- Hay artefactos locales visibles (`frontend-dev*.log`, `viru.db`, `%TEMP%/npm-cache`)
  que no deben tratarse como documentacion ni como scope de limpieza salvo pedido
  explicito.

## Areas de producto

1. **Quick Search:** descubrimiento de vuelos, comparacion, calendario, filtros,
   resultados, guardado y recomendacion.
2. **Watchlist:** centro operativo de rutas guardadas, historico, mapas y decision.
3. **Alertas:** reglas, eventos, digest, quiet hours y entregabilidad.
4. **Puerta a puerta:** viaje completo con fuentes, confianza, rutas terrestres y
   accion externa honesta.
5. **Radar hotelero:** inteligencia hotelera, comp sets, tracked offers, paridad,
   watchlist y alertas.
6. **Preferencias:** busqueda, region, apariencia, puerta a puerta y futuras
   preferencias de recomendacion.
7. **Recomendaciones:** ranking, explicaciones y perfiles de decision.
8. **UI global:** identidad calida, dual-theme, accesibilidad, motion y coherencia
   visual.
9. **Backend/providers:** integraciones, cache, observabilidad, contratos y
   resiliencia.
10. **QA/documentacion:** comandos fiables, evidencia y trazabilidad.

## Deuda tecnica visible

- `frontend/src/modules/quick-search/QuickSearchView.tsx` concentra demasiada
  responsabilidad: formulario, calendario, hints, dual mode, render de resultados,
  modales, guardado y tracking.
- El estado dual de quick-search existe, pero requiere una auditoria de gaps antes
  de nuevas features.
- Algunos docs vivos estan desincronizados en detalles historicos, especialmente
  quick-search cache.
- Puerta a puerta tiene muchos providers semivivos; hay que clasificar real,
  parcial, stub y planificado antes de prometer valor.
- Hoteles tiene cierre tecnico fuerte, pero validacion visual/manual marcada como
  pendiente.
- `docs/DOCS_INVENTORY.md` tiene entradas historicas y texto con encoding irregular;
  no corregir de forma masiva salvo fase documental dedicada.
- Hay logs y artefactos locales en raiz; no limpiarlos sin objetivo y permiso
  explicitos.
- Dependencia de providers externos: una busqueda puede estar sana y devolver cero
  resultados por degradacion real.

## Riesgos transversales

- **Contrato vs UI:** quick-search y puerta a puerta dependen de payloads complejos;
  cualquier mismatch debe tratarse como causa raiz, no taparse con copy.
- **Falsa precision:** puerta a puerta y hoteles no deben mostrar precios,
  horarios o disponibilidad como confirmados si no lo estan.
- **Coste externo:** APIs reales, providers hoteleros y mapas pueden requerir keys
  o coste. No activar sin aprobacion.
- **Datos:** migraciones y sweeps deben ser aditivos, reversibles o cuidadosamente
  verificados.
- **Visual:** light mode no puede derivar a blanco generico; dark no puede volverse
  lugubre ni cyberpunk.
- **Autonomia:** mejorar mucho no significa mezclar cinco areas en un commit.
- **QA:** browser/build passing no sustituye tests de contrato ni evidencia de UI
  cuando el cambio sea visible.

## Gates de trabajo por fase

Cada fase debe cerrar con este minimo:

1. Objetivo de fase escrito antes de tocar codigo.
2. Archivos leidos y archivos probables.
3. Reproduccion, auditoria o baseline del estado actual.
4. Cambio minimo viable.
5. Tests o checks adecuados al riesgo.
6. Si hay UI: desktop/mobile cuando aplique, dark/light, focus y consola.
7. `git diff` revisado.
8. Commit Conventional Commit en `main`.
9. Push si el cambio real queda completado.
10. Informe corto con evidencia.

## Plan de 50 fases actualizado

### Bloque A - Base, auditoria y mapa del terreno

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 1 | Crear este roadmap con estado real, deudas, riesgos y plan revisado. | `git status`, lectura documental/codigo, diff solo docs. |
| 2 | Auditar drift documental vivo: quick-search cache, rutas legacy, planes completados y docs pendientes. | Lista de conflictos con fuente preferida; no corregir sin evidencia. |
| 3 | Consolidar comandos QA fiables por area en una matriz viva. | Ejecutar checks pequenos y documentar bloqueos reales. |
| 4 | Revisar `docs/reference/done-checklist.md` para fases largas. | Diff breve, sin duplicar `AGENTS.md`. |
| 5 | Clasificar deuda tecnica visible sin borrar nada. | Checklist: eliminar seguro, requiere test, requiere usuario, no tocar. |

### Bloque B - Quick Search como prioridad

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 6 | Auditoria profunda de `/quick-search` actual. | Tests existentes, mapa de estado, gaps duales confirmados. |
| 7 | Boton accesible para invertir origen/destino. | Test de estado/form, teclado, mobile, sin reset de filtros. |
| 8 | Busquedas recientes en autocomplete. | Helper localStorage testeado, dedupe, limite 5-10, fallback sin storage. |
| 9 | Endurecer estado independiente ida/vuelta ya existente. | Tests `quick-search-dual-regression` y backend reverse leg. |
| 10 | Completar filtros/orden/paginacion propios por lado. | Cambiar ida no altera vuelta; filtrar vuelta no altera ida. |
| 11 | Mejorar loading/empty/error por lado. | Estados por side, copy ES, no solapes, dark/light. |
| 12 | Completar seleccion individual y resumen de combinacion. | Test de total, precio faltante, limpiar seleccion. |
| 13 | Deep links duales coherentes. | `date_in` correcto, ida/vuelta no mezcladas. |
| 14 | Weather por side o decision explicita de no mostrarlo. | Contrato claro: alimentado o oculto honestamente. |
| 15 | Country-only dual audit y soporte seguro si procede. | E2E o tests de request builder con IATA invertidos. |
| 16 | Recomendacion Viru v0: auditar AI actual y fallback heuristico. | Tests de unico recomendado y fallback. |
| 17 | UI de recomendacion con explicacion honesta. | Badge no agresivo, no oculta resultados, screenshots. |
| 18 | Refactor acotado de `QuickSearchView.tsx` por responsabilidad. | Tests existentes pasan; sin cambio visual accidental. |
| 19 | QA completo de Quick Search. | Frontend targeted tests, backend targeted tests, browser/manual review. |

### Bloque C - Puerta a puerta

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 20 | Auditoria de providers puerta a puerta: real, parcial, stub, mock, scraper. | Tabla por provider + status del contrato. |
| 21 | Revisar modelo de tramo y campos falsos (`--:--`, `0,00`). | Tests render/formateo + runbook QA. |
| 22 | Estados honestos de cobertura y proveedor. | `NO_REAL_PROVIDER_COVERAGE`, `NO_COVERAGE`, warnings visibles. |
| 23 | Acciones externas fiables por tramo. | URL builders, `target=_blank`, `rel=noreferrer`, copy sin "comprar". |
| 24 | Buffers y riesgo de conexion. | Unit tests de margen ajustado y scoring. |
| 25 | GTFS/open data: cobertura, feeds, cache y errores. | Tests GTFS + `runbook-gtfs-activacion`. |
| 26 | UX visual puerta a puerta. | Browser dark/light, desktop/mobile, timeline y sticky bar. |
| 27 | QA integral puerta a puerta. | Comandos del runbook + revision manual propuesta. |

### Bloque D - Radar hotelero

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 28 | Auditoria post-cierre de `/hoteles`. | Contrastar spec, code, tests y pendientes reales. |
| 29 | Cerrar verificacion visual pendiente de hoteles. | Browser dark/light/responsive, screenshots si procede. |
| 30 | Revisar sweeps hoteleros y ausencia/presencia de scheduler. | Runbook, worker, flags y tests sin secretos. |
| 31 | Reforzar copy honesto de provider real/mock/cache. | No prometer disponibilidad falsa; tests i18n si cambia. |
| 32 | Pulido responsive de comp sets, sugerencias cercanas y tracked offers. | Browser + build/typecheck frontend. |
| 33 | Scoring/recomendacion hotelera: auditar antes de ampliar. | Tests de scoring y caso sin datos suficientes. |

### Bloque E - Watchlist, alertas e historico

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 34 | Auditoria watchlist actual tras W0-W9. | Tests existentes + mapa de estado. |
| 35 | Claridad de diferencia de precio e historico insuficiente. | Tests de formateo y screenshots con 1/muchos snapshots. |
| 36 | Historial mas util: min, max, media, tendencia, freshness. | Tests de calculo y responsive. |
| 37 | Alertas claras y accionables. | Form tests, quiet hours/digest tests, browser flow. |
| 38 | Backend alertas/historico: paginacion, cooldown, N+1 obvio. | Tests integration alerts/prices/watchlist. |
| 39 | QA integral watchlist-alertas-historico. | Crear ruta, ver historico, regla, evento, borrar/pausar. |

### Bloque F - Backend, providers y contratos

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 40 | Auditoria providers de vuelos. | Registry, env vars, errores, rate limits y tests. |
| 41 | Normalizacion de errores providers. | Tests de timeout/error/empty y warnings canonicos. |
| 42 | Revisar cache compartida quick-search antes de prod. | Ejecutar plan R1-R9 o subset justificado. |
| 43 | Preparar Redis hot layer solo si procede. | Flag off por defecto, tests, rollback claro. |
| 44 | Contratos frontend-backend de busqueda. | Typecheck + backend contract tests. |
| 45 | Observabilidad util sin ruido ni secretos. | Logs con trace/correlation, revision manual. |

### Bloque G - Preferencias y personalizacion

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 46 | Auditoria de preferencias actuales. | Paginas, persistence, opciones que hacen algo vs placeholders. |
| 47 | Preferencias de busqueda conectadas a quick-search. | Tests de persistencia + payload real. |
| 48 | Preferencias puerta a puerta alineadas con backend. | Contrato allow_* y flags reales. |
| 49 | Preferencias de recomendacion si el scoring esta listo. | Perfiles no expuestos a medias; tests de pesos. |

### Bloque H - Pulido global y cierre

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 50 | Consolidacion final: regresion, bitacora y handoff al usuario. | Suites razonables, browser core, `HISTORY.md` si aplica, push limpio. |

## Verificacion por familias

### Documentacion

- Revisar que los links existen.
- Revisar que `docs/DOCS_INVENTORY.md` coincide con archivos nuevos.
- No actualizar `HISTORY.md` salvo cambio de comportamiento/workflow.

### Backend

- Unit tests focalizados primero.
- Integration tests de endpoint cuando cambie contrato o flujo real.
- `python -m alembic check` si hay migraciones/modelos.
- Confirmar logs sin secretos.

### Frontend

- Tests de componente/logica cercanos.
- `npm run lint` o `npm run build` segun impacto.
- Browser real o Playwright/TestSprite para cambios visibles.
- Dark/light y mobile cuando toque layout, copy o estados.

### Quick Search

Comandos base candidatos:

```powershell
cd C:\Users\javiru\Desktop\viru-tracker\frontend
npm test -- --test-name-pattern="quick-search-screen-state|quick-search-refactor-utils|quick-search-dual-regression|quick-search-response-normalizer"
```

```powershell
cd C:\Users\javiru\Desktop\viru-tracker
python -m pytest backend\tests\integration\test_quick_search_dual_reverse_leg.py backend\tests\integration\test_quick_search_provider_degradation.py backend\tests\unit\test_quick_search_ai_preference.py
```

### Puerta a puerta

Usar el runbook:

```powershell
cd C:\Users\javiru\Desktop\viru-tracker\frontend
node --import tsx --test tests/door-to-door-v1.test.tsx
```

```powershell
cd C:\Users\javiru\Desktop\viru-tracker\backend
python -m pytest tests/integration/test_door_to_door.py tests/unit/test_door_to_door_gtfs_transit.py tests/unit/test_door_to_door_deeplinks.py -q
```

### Hoteles

- Backend hotels unit/integration tests cercanos.
- `npx tsc --noEmit` si se tocan hooks/componentes.
- Browser visual pendiente como gate importante.

## Decisiones seguras sin preguntar

- Corregir bugs claros con tests.
- Endurecer fallbacks y mensajes honestos.
- Mejorar microcopy ES sin cambiar contrato.
- Agregar tests focalizados.
- Dividir archivos grandes en piezas locales si preserva comportamiento y tests.
- Actualizar docs cuando reflejen un cambio real o un drift comprobado.
- Desactivar o esconder promesas visuales incompletas si el backend no las respalda.
- Mantener mock solo en local/demo y documentarlo.

## Decisiones que deben esperar al usuario

- Activar APIs con coste o claves reales.
- Cambiar modelo de negocio, reservas, pagos, scraping activo o compra de billetes.
- Borrar datos, migraciones destructivas o cambios irreversibles.
- Eliminar archivos intencionales o historicos.
- Cambiar identidad visual global o paleta canonica.
- Sustituir providers principales.
- Crear PR/branch en vez de commit directo a `main`.
- Publicar un roadmap externo o promesa de producto.

## Fase 1 completada

### Que cambio

- Se creo este documento como entregable inicial de viaje.
- Se ajusto el plan original de 50 fases al estado real detectado el 2026-06-13.
- Se marco expresamente que muchas piezas ya existen y deben auditarse antes de
  reconstruirse.

### Archivos tocados previstos

- `docs/prompts/codex-travel-roadmap-50-fases.md`
- `docs/prompts/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

### Verificacion prevista de esta fase

- `git status`
- revision de diff documental
- comprobacion de rutas de docs referenciadas
- sin cambios de logica

### Siguiente fase recomendada

Fase 2: auditar drift documental vivo, empezando por Quick Search cache y los
planes ya cerrados que todavia pueden leerse como pendientes.
