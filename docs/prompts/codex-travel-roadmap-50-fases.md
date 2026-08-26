# Roadmap de viaje para Codex - 50 fases de mejora de Viru Air

**Estado:** vivo
**Ultima revision:** 2026-06-13
**Fuente de verdad:** no; plan operativo para agentes
**Area:** contexto IA / planificacion

## Proposito

Este documento convierte el prompt de viaje del usuario en una hoja de ruta
ejecutable para mejorar Viru Air con autonomia responsable. No sustituye a
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

- `DESIGN.md`
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

- Repo canonico confirmado: `C:\Users\javiru\Desktop\viru-air`.
- Rama actual: `main`.
- Estado inicial de esta iteracion: repo valido en `main`, con cambios locales
  documentales ya presentes en `docs/prompts/codex-travel-roadmap-50-fases.md`
  antes de cerrar las Fases 1-5.
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
- modulos frontend separados (`api/buildQuickSearchRequest`, `api/normalizeQuickSearchResponse`, `filterUtils`,
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

#### Desarrollo ampliado de las Fases 1-5

Las fases 1-5 forman el arranque operativo del viaje. No buscan "hacer producto"
todavia: buscan ordenar el terreno, separar hechos de ruido y dejar una base que
permita ejecutar despues cambios pequenos, verificables y publicables sin volver
a improvisar el contexto en cada sesion.

### Fase 1 - Baseline del viaje y estado real del repo

**Objetivo real**

Dejar una foto util del estado actual de Viru Air para futuras sesiones:
repositorio canonico, areas de producto activas, deuda visible, riesgos
transversales, comandos de verificacion relevantes y limites de autonomia.

**Por que existe ahora**

El repo ya no esta en fase de arranque. Tiene Quick Search, Watchlist, Alertas,
Puerta a puerta y Hoteles con distintos niveles de madurez. Sin un baseline
actualizado, un agente nuevo puede tratar piezas consolidadas como si hubiera que
rehacerlas desde cero o puede leer planes viejos como si siguieran pendientes.

**Incluye**

- lectura selectiva de `AGENTS.md`, `docs/`, contratos vivos y areas de producto;
- comprobacion del repo canonico y del workflow real de commit/push;
- mapa resumido de superficies activas, deuda visible y riesgos.

**No incluye**

- ejecutar cambios de producto;
- normalizar toda la documentacion historica;
- corregir contradicciones no verificadas en caliente.

**Entregables esperados**

- este roadmap actualizado como baseline de viaje;
- inventario narrativo de producto, arquitectura, deuda y riesgos;
- siguiente fase recomendada ya priorizada.

**Fuentes y dependencias a revisar**

- `AGENTS.md`
- `DESIGN.md`
- `docs/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`
- `docs/reference/codex-operating-contract.md`
- docs vivas por dominio segun el area que aparezca como activa

**Cierre y verificacion minima**

- `git status` desde la raiz canonica;
- lectura/documentacion suficiente para sostener el mapa del repo sin suposiciones
  mayores;
- diff documental acotado;
- evidencia explicita de que no se tocaron contratos ni codigo.

### Fase 2 - Auditoria de drift documental vivo

**Objetivo real**

Localizar contradicciones entre documentacion viva, planes cerrados y estado real
del codigo antes de seguir implementando sobre premisas antiguas.

**Por que existe ahora**

Quick Search, cache compartida, planes de puerta a puerta y cierres de hoteles ya
tienen varias capas de documentacion. Algunas fueron escritas en momentos
distintos y pueden seguir describiendo riesgos ya cerrados o estados intermedios
que hoy inducen a error.

**Incluye**

- comparar contratos vivos con checklists y planes recientes;
- buscar docs que sigan llamando pendiente a algo ya completado;
- identificar rutas legacy, referencias duplicadas o fuentes movidas;
- preferir siempre la fuente viva sobre historicos o prompts viejos.

**No incluye**

- reescritura masiva de `docs/`;
- limpiar el inventario entero por estilo o encoding;
- usar archivos historicos no presentes en el workspace como fuente primaria.

**Entregables esperados**

- lista corta de conflictos documentales con fuente preferida;
- clasificacion por severidad: bloquea implementacion, confunde QA o solo requiere
  saneamiento futuro;
- recomendacion de que conflictos corregir primero y cuales dejar para una fase
  documental dedicada.

**Fuentes y dependencias a revisar**

- `docs/reference/backend/quick-search-contract.md`
- `docs/reference/backend/quick-search-acceptance-checklist.md`
- `docs/plans/2026-06-08-quick-search-roundtrip-stabilization.md`
- `docs/plans/2026-06-10-quick-search-shared-cache-review-plan.md`
- `docs/specs/hotels-intelligence-mvp.md`
- `docs/qa/hotels-pending-closeout.md`
- `docs/DOCS_INVENTORY.md`

**Cierre y verificacion minima**

- tabla o lista de conflictos con fuente preferida claramente indicada;
- ningun cambio documental correctivo sin evidencia local suficiente;
- reporte expreso de rutas historicas fantasma o referencias no resolubles si
  aparecen.

**Conflictos confirmados en esta iteracion**

| Conflicto | Fuente preferida | Severidad | Decision |
|---|---|---|---|
| `docs/reference/backend/quick-search-acceptance-checklist.md` seguia declarando cache solo en memoria | `docs/reference/backend/quick-search-contract.md` V2.1 | bloquea implementacion | corregir ahora |
| `docs/qa/hotels-pending-closeout.md` seguia listando `DELETE /comp-sets/{id}` como deuda abierta en una seccion ya superada | `docs/qa/hotels-pending-closeout.md` seccion 2026-06-05 Fase E | confunde QA | corregir ahora |
| `docs/specs/hotels-intelligence-mvp.md` seguia proponiendo documentar sweeps manuales como siguiente paso pese a quedar ya cerrados en runbook y closeout | `docs/runbooks/hotels-sweeps.md` y `docs/qa/hotels-pending-closeout.md` | confunde QA | corregir ahora |
| texto con encoding irregular en `docs/DOCS_INVENTORY.md` y algunos runbooks heredados | fuente viva puntual por documento | saneamiento futuro | no corregir en masa en estas fases |

### Fase 3 - Matriz QA fiable por area

**Objetivo real**

Consolidar una matriz minima de comandos y checks que sirva para verificar cambios
por superficie sin depender de memoria de sesion ni de comandos heredados dudosos.

**Por que existe ahora**

El repo mezcla frontend, backend, flows visibles y runbooks por dominio. Hay
comandos historicos, wrappers rotos o pruebas muy especificas; sin una matriz
fiable, el riesgo es validar mal o perder tiempo con checks que ya no representan
la realidad.

**Incluye**

- distinguir comandos canonicos de comandos heredados o rotos;
- asociar cada area con una salida minima verificable;
- dejar claro cuando un flujo visible requiere browser/manual review ademas de
  tests de terminal.

**No incluye**

- crear una infraestructura nueva de test;
- prometer cobertura total de todas las rutas privadas;
- marcar build/lint como prueba suficiente de una correccion visible.

**Entregables esperados**

- matriz por area: frontend, backend, Quick Search, puerta a puerta, hoteles,
  watchlist/alertas y documentacion;
- nota de bloqueos reales del entorno, por ejemplo wrappers o binarios ausentes;
- criterio operativo de "comando canónico", "comando heredado" y "requiere
  validacion humana".

**Fuentes y dependencias a revisar**

- `docs/qa/README.md`
- `docs/runbooks/runbook-watchlist-quick-search-stabilization.md`
- `docs/runbooks/runbook-puerta-a-puerta-qa.md`
- `frontend/package.json`
- `backend/pyproject.toml`
- scripts de guard o release si entran en el cierre real

**Cierre y verificacion minima**

- ejecutar o contrastar al menos un subconjunto pequeno de comandos por familia;
- documentar bloqueos del entorno en vez de ocultarlos;
- dejar por escrito que evidencia minima debe quedar para cambios de UI, contrato o
  backend.

**Matriz resultante de esta fase**

- Fuente viva creada: `docs/qa/qa-command-matrix.md`.
- Checks contrastados en esta iteracion:
  - `cd frontend && npm run lint`
  - `cd C:\Users\javiru\Desktop\viru-air && python -m pytest backend\tests\unit\test_quick_search_cache_models.py -q`
  - `cd backend && python -m pytest tests/unit/test_door_to_door_deeplinks.py -q`
- Hallazgos reales:
  - `npm run lint` funciona, pero arroja warnings preexistentes en hoteles y
    quick-search.
  - los tests focalizados de cache quick-search y deeplinks de puerta a puerta
    pasan.
  - `rg` no estuvo disponible en esta sesion; se uso PowerShell como fallback.

### Fase 4 - Revisar `done-checklist` para fases largas

**Objetivo real**

Ajustar la checklist de cierre para que sirva en tareas largas o multipaso sin
duplicar reglas ya presentes en `AGENTS.md` ni rebajar el umbral de evidencia.

**Por que existe ahora**

La checklist actual es util para cierres de codigo, pero las fases largas del
roadmap necesitan separar mejor investigacion, implementacion, validacion humana y
publicacion final. Si no se hace, es facil confundir "analizado" con "terminado".

**Incluye**

- revisar si la checklist distingue bien investigado, verificado y publicado;
- decidir que evidencia minima exigir para UI, backend y tareas documentales;
- aclarar cuando una fase puede cerrarse localmente y cuando debe esperar
  validacion humana o push real.

**No incluye**

- reescribir `AGENTS.md`;
- crear un proceso burocratico nuevo;
- obligar a que toda fase larga termine en commit si su objetivo era solo auditoria.

**Entregables esperados**

- diff breve y justificado en `docs/reference/done-checklist.md` si realmente hace
  falta;
- criterio claro para separar "investigado", "parchado", "verificado" y
  "publicado";
- recomendacion de uso de la checklist dentro de este roadmap.

**Fuentes y dependencias a revisar**

- `docs/reference/done-checklist.md`
- `AGENTS.md`
- `docs/reference/codex-operating-contract.md`
- `docs/qa/README.md`

**Cierre y verificacion minima**

- checklist revisada contra las reglas del repo, sin contradicciones nuevas;
- diff pequeno si hay cambio, o decision explicita de no tocarla si ya cumple;
- explicacion de cuando pedir validacion humana en flujos visibles o sensibles.

**Decision aplicada en esta iteracion**

- `docs/reference/done-checklist.md` se ajusta para separar `investigado`,
  `parchado`, `verificado` y `publicado`.
- La validacion humana en navegador sigue siendo obligatoria para cambios UI
  visibles, pero no se exige como gate de cierre para estas cinco fases porque el
  alcance aqui es documental/procesal.

### Fase 5 - Clasificar deuda tecnica visible sin borrar nada

**Objetivo real**

Transformar la deuda visible detectada en un backlog operativo corto y accionable,
separando lo que puede atacarse ya de lo que requiere contrato, QA previo o
permiso explicito del usuario.

**Por que existe ahora**

La deuda ya esta a la vista, pero mezclada: archivos grandes, drift documental,
providers parciales, QA visual pendiente, logs locales y riesgos de coste externo.
Sin clasificacion, todo parece igual de urgente y se mezclan arreglos seguros con
cambios que podrian abrir mas frente del necesario.

**Incluye**

- agrupar deuda por categoria operativa;
- identificar deudas seguras para parches pequenos;
- marcar dependencias duras: contrato, provider real, secretos, browser QA, aprobacion
  del usuario.

**No incluye**

- borrar archivos heredados por limpieza estetica;
- meter refactors grandes en nombre de la deuda;
- asumir que todo warning o TODO debe resolverse ya.

**Entregables esperados**

- clasificacion con categorias minimas:
  - seguro atacar;
  - requiere contrato;
  - requiere QA primero;
  - requiere permiso del usuario;
  - no tocar todavia;
- priorizacion inicial para las siguientes fases de ejecucion.

**Fuentes y dependencias a revisar**

- secciones de deuda y riesgos de este mismo roadmap;
- `docs/product/*` y `docs/specs/*` en las areas con mayor gap;
- superficies grandes o sensibles ya detectadas, como `QuickSearchView.tsx`,
  providers de puerta a puerta y QA visual de hoteles.

**Cierre y verificacion minima**

- clasificacion trazable a archivos, contratos o flujos reales;
- ninguna accion destructiva ejecutada durante la clasificacion;
- backlog resultante pequeno y util, no una lista enciclopedica.

**Clasificacion inicial resultante**

### Seguro atacar

- `frontend/src/modules/quick-search/QuickSearchView.tsx`: deuda de tamano y
  responsabilidades, apta para refactor acotado con tests existentes.
- drift documental puntual de quick-search cuando exista fuente viva clara.

### Requiere contrato

- providers parciales de `/puerta-a-puerta` y cualquier ajuste que cambie
  semantica de cobertura, confianza, precio o booking.

### Requiere QA primero

- verificacion visual pendiente de `/hoteles` en dark/light/responsive/focus/copy.
- pulidos visibles de quick-search, watchlist y puerta a puerta.

### Requiere permiso del usuario

- activacion de APIs con coste, providers reales adicionales, scheduler real de
  sweeps o cambios que impliquen claves/consumo externo.

### No tocar todavia

- warnings/lint preexistentes ajenos al alcance de una fase documental.
- logs y artefactos locales visibles en raiz o entorno cuando no formen parte del
  problema.
- saneamiento masivo de encoding en `docs/DOCS_INVENTORY.md` y archivos historicos.

### Bloque B - Quick Search como prioridad

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 6 | Auditoria profunda de `/quick-search` actual. | Tests existentes, mapa de estado, gaps duales confirmados. |
| 7 | Boton accesible para invertir origen/destino. | Test de estado/form, teclado, mobile, sin reset de filtros. |
| 8 | Busquedas recientes en autocomplete. | Helper localStorage testeado, dedupe, limite 6, fallback sin storage. |
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

#### Desarrollo ampliado de las Fases 6-10

Estas fases se ejecutan de forma literal sobre `/quick-search`, no como reescritura
teorica. El principio operativo es aprovechar lo ya construido, auditar de verdad que
sirve y cerrar los huecos concretos que seguian abiertos en round-trip y dual mode.
El resultado esperado no era "rediseñar Quick Search", sino dejar un bloque 6-10
cerrado con evidencia real de codigo, tests y decisiones documentadas.

### Fase 6 - Auditoria profunda de `/quick-search`

**Objetivo real**

Inspeccionar contrato, tests y estado actual antes de tocar UX. Esta fase sirve para
decidir que partes del dual mode estaban realmente listas, cuales eran parciales y que
quedaba vivo en 7-10.

**Fuentes contrastadas**

- `docs/product/quick-search.md`
- `docs/reference/backend/quick-search-contract.md`
- `docs/reference/backend/quick-search-acceptance-checklist.md`
- `docs/plans/2026-06-08-quick-search-roundtrip-stabilization.md`
- `docs/plans/2026-06-10-quick-search-shared-cache-review-plan.md`
- `frontend/src/modules/quick-search/QuickSearchView.tsx`
- `frontend/src/modules/quick-search/state/useQuickSearchScreenState.ts`
- `frontend/src/modules/quick-search/state/useQuickSearchSide.ts`
- componentes duales y tests `frontend/tests/*quick-search*`
- guards backend `backend/tests/integration/test_quick_search_dual_reverse_leg.py`
- guards backend `backend/tests/unit/test_quick_search_execution.py`

**Hallazgos concretos**

- La Fase 7 seguia pendiente: no existia un control explicito para invertir origen y
  destino en el bloque principal.
- La Fase 8 estaba parcial: `recentAirports` existia como persistencia para picker
  modal, pero no alimentaba el autocomplete inline principal.
- La Fase 9 estaba parcial: el backend y `useQuickSearchSide` ya ofrecian estado por
  lado, pero `QuickSearchView.tsx` seguia mezclando demasiado estado monolitico y
  derivaciones globales incluso en render dual.
- La Fase 10 estaba parcial: la paginacion backend por lado ya existia, pero los
  filtros y el orden visible seguian anclados al estado simple/global.

**Decision de ejecucion**

Se adopta ejecucion literal: cerrar 6-10 sobre lo existente, sin borrar dual mode ni
rehacer contrato backend. Se permiten helpers y componentes locales si reducen
acoplamiento y mejoran verificabilidad.

**Cierre de fase**

La auditoria se considera cerrada porque produjo un mapa de gaps accionable y porque
los hallazgos se ejecutaron inmediatamente en las Fases 7-10 de esta misma iteracion.

**Comandos realmente ejecutados para esta fase**

```powershell
git status --short
```

```powershell
cd C:\Users\javiru\Desktop\viru-air\frontend
npm test -- tests/quick-search-dual-regression.test.tsx tests/quick-search-screen-state.test.tsx
```

```powershell
cd C:\Users\javiru\Desktop\viru-air\backend
python -m pytest tests/integration/test_quick_search_dual_reverse_leg.py tests/unit/test_quick_search_execution.py -q
```

### Fase 7 - Boton accesible para invertir origen/destino

**Implementacion real**

- Se reemplazo el adorno central de ruta por un boton real de swap en
  `QuickSearchView.tsx`.
- El swap intercambia:
  - `origin` y `destination`
  - `originCountryOnly` y `destinationCountryOnly`
  - `originSelectedCountryCode` y `destinationSelectedCountryCode`
- No resetea fechas, adultos, filtros visibles ni modo ida/vuelta.
- Limpia estado efimero de autocomplete, touched y errores de origen/destino.
- No dispara auto-submit: deja la pantalla en estado de cambios pendientes, igual que
  una edicion manual.
- Se anadio copy ES/EN y `aria-label` especificos para la accion.

**Verificacion minima cerrada**

- tests focalizados de quick-search frontend en verde;
- lint frontend sin errores nuevos;
- control accesible presente en el markup y visible tambien en viewport estrecho.

### Fase 8 - Busquedas recientes en autocomplete

**Implementacion real**

- Se extrajo la persistencia de recientes a `recentAirports.ts`, con lectura/escritura
  segura frente a ausencia o error de `localStorage`.
- Se mantuvo dedupe y limite en `6`, alineado con el picker modal existente.
- El autocomplete inline de origen y destino ahora muestra recientes cuando:
  - el input esta enfocado y vacio;
  - el texto actual coincide con recientes guardados.
- Los recientes se enriquecen con nombre/IATA usando `airportsByIata`; si no existe
  metadata, se muestra al menos el codigo IATA.
- Picker modal e inline comparten la misma fuente de recientes; no quedan dos
  implementaciones separadas.

**Verificacion minima cerrada**

- helper testeado para dedupe, limite, persistencia, fallback y enriquecimiento;
- regresiones frontend en verde;
- sin cambios de contrato backend.

### Fase 9 - Endurecer estado independiente ida/vuelta

**Implementacion real**

- Se mantuvo `useQuickSearchSide` como nucleo del estado remoto por lado.
- Se redujo la dependencia del render dual respecto al estado compartido de
  `QuickSearchView`.
- Se cablearon estados derivados por lado para:
  - resultados visibles;
  - metadata de busqueda;
  - warnings;
  - paginacion actual;
  - seleccion y resumen de combinacion en modo dual.
- Se reforzo la limpieza al salir de dual mode para evitar residuos cruzados de filtros
  visibles y estado de panel ida/vuelta.

**Verificacion minima cerrada**

- `tests/quick-search-dual-regression.test.tsx` actualizado y en verde;
- `backend/tests/integration/test_quick_search_dual_reverse_leg.py` en verde;
- `backend/tests/unit/test_quick_search_execution.py` en verde.

### Fase 10 - Filtros, orden y paginacion propios por lado

**Implementacion real**

- Se anadio estado de vista por lado para:
  - `priceMin`
  - `priceMax`
  - `durationMax`
  - `sortBy`
- Ese estado vive en frontend y no cambia el payload de `/api/v1/search/quick`.
- Se extrajo la logica derivada de filtrado/orden a
  `state/quickSearchVisibleResults.ts`.
- Se creo un componente local `QuickSearchSideViewControls` y se renderiza dentro de
  cada `QuickSearchSidePanel`.
- En dual mode, cada panel aplica sus filtros, orden y paginacion visibles de forma
  independiente. Cambiar ida no altera vuelta y viceversa.

**Verificacion minima cerrada**

- tests del helper de resultados visibles en verde;
- regresiones duales en verde;
- lint frontend sin errores nuevos.

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
cd C:\Users\javiru\Desktop\viru-air\frontend
npm test -- --test-name-pattern="quick-search-screen-state|quick-search-refactor-utils|quick-search-dual-regression|quick-search-response-normalizer"
```

```powershell
cd C:\Users\javiru\Desktop\viru-air
python -m pytest backend\tests\integration\test_quick_search_dual_reverse_leg.py backend\tests\integration\test_quick_search_provider_degradation.py backend\tests\unit\test_quick_search_ai_preference.py
```

### Puerta a puerta

Usar el runbook:

```powershell
cd C:\Users\javiru\Desktop\viru-air\frontend
node --import tsx --test tests/door-to-door-v1.test.tsx
```

```powershell
cd C:\Users\javiru\Desktop\viru-air\backend
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

## Fases 1-5 completadas

### Que cambio

- Se creo este documento como entregable inicial de viaje.
- Se ajusto el plan original de 50 fases al estado real detectado el 2026-06-13.
- Se marco expresamente que muchas piezas ya existen y deben auditarse antes de
  reconstruirse.
- Se cerraron las Fases 2-5 con correcciones documentales puntuales, matriz QA
  viva, checklist de cierre endurecida y clasificacion operativa de deuda.

### Archivos tocados

- `docs/prompts/codex-travel-roadmap-50-fases.md`
- `docs/reference/backend/quick-search-acceptance-checklist.md`
- `docs/specs/hotels-intelligence-mvp.md`
- `docs/qa/hotels-pending-closeout.md`
- `docs/qa/qa-command-matrix.md`
- `docs/reference/done-checklist.md`
- `docs/qa/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`

### Verificacion ejecutada

- `git status`
- revision de diff documental acotado a docs y checklists
- comprobacion de rutas de docs referenciadas
- `cd frontend && npm run lint`
- `cd C:\Users\javiru\Desktop\viru-air && python -m pytest backend\tests\unit\test_quick_search_cache_models.py -q`
- `cd backend && python -m pytest tests/unit/test_door_to_door_deeplinks.py -q`
- sin cambios de logica ni de contrato runtime

## Fases 6-10 completadas

### Que cambio

- Se ejecuto la auditoria real de `/quick-search` y se documento la decision de
  completar literalmente las Fases 6-10 sobre la implementacion existente.
- Se incorporo un boton accesible para invertir origen/destino sin resetear fechas,
  adultos ni filtros visibles.
- Se unifico la fuente de aeropuertos recientes para picker modal y autocomplete
  inline, con helper seguro de persistencia.
- Se endurecio el render dual para depender de estado y resultados visibles por lado,
  reduciendo acoplamientos de `QuickSearchView.tsx`.
- Se completaron controles de filtros/orden por panel en dual mode sin cambiar el
  contrato backend de quick-search.

### Archivos tocados

- `docs/prompts/codex-travel-roadmap-50-fases.md`
- `frontend/src/modules/quick-search/QuickSearchView.tsx`
- `frontend/src/modules/quick-search/recentAirports.ts`
- `frontend/src/modules/quick-search/types.ts`
- `frontend/src/modules/quick-search/state/quickSearchVisibleResults.ts`
- `frontend/src/modules/quick-search/state/useQuickSearchScreenState.ts`
- `frontend/src/modules/quick-search/components/QuickSearchSideViewControls.tsx`
- `frontend/src/modules/shared/quickSearchCopy.ts`
- `frontend/src/styles/screens.css`
- `frontend/src/styles/quick-search-dual.css`
- `frontend/tests/quick-search-copy.test.ts`
- `frontend/tests/quick-search-dual-regression.test.tsx`
- `frontend/tests/quick-search-recent-airports.test.ts`
- `frontend/tests/quick-search-visible-results.test.ts`

### Verificacion ejecutada

- `cd frontend && npm test -- tests/quick-search-dual-regression.test.tsx tests/quick-search-screen-state.test.tsx tests/quick-search-copy.test.ts tests/quick-search-recent-airports.test.ts tests/quick-search-visible-results.test.ts`
- `cd frontend && npm run lint`
- `cd backend && python -m pytest tests/integration/test_quick_search_dual_reverse_leg.py tests/unit/test_quick_search_execution.py -q`

**Hallazgos de verificacion**

- Los tests frontend focalizados de quick-search pasan.
- Los guards backend de quick-search dual pasan.
- `npm run lint` queda limpio de errores; persisten warnings preexistentes en hoteles.

### Siguiente fase recomendada

Fase 21: revisar modelo de tramo y campos falsos (`--:--`, `0,00`) en puerta a puerta.

## Fases 18-19 completadas

### Que cambio

- Extraccion de `weatherUtils.ts` (weatherLabel, WeatherFetchError, isWeatherRangeSupported,
  fetchWeather) y `airportSuggestions.ts` (normalizeText, buildAirportSuggestions,
  mergeAirportSuggestions) desde `QuickSearchView.tsx`.
- Eliminacion de funciones inline duplicadas y codigo huérfano de
  mergeAirportSuggestions.
- Fix de bug preexistente TDZ: `const { locale, localeTag, t, tWarn } = copy` donde
  `copy` nunca se declaro → `const { ... } = getQuickSearchCopy()`.
- Fix de bug preexistente TDZ: `useEffect` referenciando `isDualMode` antes de su
  declaracion → movido `useEffect` despues de la declaracion.

### Archivos tocados

- `frontend/src/modules/quick-search/QuickSearchView.tsx`
- `frontend/src/modules/quick-search/airportSuggestions.ts` (nuevo)
- `frontend/src/modules/quick-search/weatherUtils.ts` (nuevo)

### Verificacion ejecutada

- 66 quick-search tests pasan sin regresiones
- 0 errores lint nuevos
- Build tiene errores TDZ preexistentes (airportsByCountry, airportsByIata,
  logQuickSearchApiError, debugLog) no introducidos por estos cambios

## Fase 20 completada

### Que cambio

- Auditoria completa de providers puerta a puerta desde el registry:
  - 5 providers reales (google_routes, gtfs_transit, navitia, google_maps_deeplink, google_places)
  - 3 providers deeplink (blablacar, goopti, external unified)
  - 6 stubs puros (opentripplanner, amadeus_transfers, mozio, omio, distribusion, rome2rio)
  - 1 mock (mock_multimodal, bloqueado en staging/prod)
  - 4 scrapers base-only sin parser (blablacar, goopti, alsa, renfe)
- Tests: 21 source-code assertions en `quick-search-d2d-provider-audit.test.ts`
  cubriendo registry structure, mock blocking, feature flags, API keys,
  classification, base provider contract y frontend contract awareness.

### Archivos tocados

- `frontend/tests/quick-search-d2d-provider-audit.test.ts` (nuevo)

### Verificacion ejecutada

- 21/21 tests de auditoria D2D pasan
- 37 tests de regresion pasan sin fallos
- 0 errores lint nuevos

## Fases 11-15 completadas

### Que cambio

- Per-side `emptyCausesExpanded` state con toggle y reset al salir de dual mode.
- `handleDualRelaxAction` con early return para `increase_duration` (view-only) y
  params deduplicados con `sideOrigin`/`sideDest`/`sideDate`.
- Precio combinado retorna `null` (no `0`) cuando falta precio de un lado.
- `buildReturnFallbackUrl` con ruta invertida (destination→origin, returnDate).
- `fetchDeepLink` acepta `dateIn` opcional para deep links duales correctos.
- Weather explícitamente `null` en modo dual (no fetch per-side, contract explícito).
- Tests: 22 source-code assertions en `quick-search-dual-phases-11-15.test.ts`.

### Archivos tocados

- `frontend/src/modules/quick-search/QuickSearchView.tsx`
- `frontend/src/modules/quick-search/state/useQuickSearchSide.ts`
- `frontend/tests/quick-search-dual-phases-11-15.test.ts`

### Verificacion ejecutada

- 22/22 tests nuevos pasan
- 66 quick-search tests pasan sin regresiones
- 0 errores lint nuevos

## Fases 16-17 completadas

### Que cambio

- Auditoría del sistema AI de recomendación: badge inline (no overlay),
  razón solo cuando no está vacía, aria-label para accesibilidad,
  `qs-result-row-ai` CSS class para distinción visual.
- Verificación de que solo un resultado es preferido (`min()` en heuristic).
- Tests de scoring heurístico (price, duration, distance, stale penalty).
- Tests de fallback chain (missing key, OpenAI error, invalid ID).
- Tests de i18n keys ES/EN (`aiPreferredPrice`, `aiPreferredAria`, `aiPreferredReasonLabel`).

### Archivos tocados

- `frontend/tests/quick-search-ai-recommendation-audit.test.ts`

### Verificacion ejecutada

- 15/15 tests de auditoría AI pasan
- 66 quick-search tests pasan sin regresiones
- 0 errores lint nuevos

### Siguiente fase recomendada

Fase 18: refactor acotado de `QuickSearchView.tsx` por responsabilidad, manteniendo
tests existentes pasando y sin cambio visual accidental.
