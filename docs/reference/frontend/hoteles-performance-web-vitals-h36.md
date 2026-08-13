# H36 — Rendimiento frontend y Web Vitals de `/hoteles`

**Estado:** baseline lab autenticado obtenido; Gate B/R/M cerrados para las rondas lab declaradas; Gate F lab cerrado para la instrumentación opt-in local; field/RUM de producción y optimización siguen abiertos
**Fecha:** 2026-08-08
**Área:** frontend / performance / backend / QA / observabilidad  
**Fuente de verdad:** sí para los presupuestos, prioridades y criterios de cierre de H36  
**No es:** una medición de producción, una garantía de Web Vitals ni una aprobación de infraestructura

### Actualización 2026-08-08 — cierre del bloque de cancelación y latest-wins

Se implementó el primer bloque accionable de H36 sin cambiar contratos HTTP del backend:

- `apiFetchWithStatus` conserva la `AbortSignal` del llamador y la compone con el timeout opcional;
- `searchHotels`, `areaResolve`, `areaSearch`, `getHotelDetail`, `getHotelRates` y `getHotelParity` aceptan señal de cancelación;
- `useHotelSearch` aborta búsquedas y resoluciones obsoletas, aplica request IDs latest-wins y limpia cancelación al desmontar/cambiar de modo;
- `useHotelDetail` aborta detalle, rates y parity al cambiar de hotel o desmontar, y no deja el loading activo al deseleccionar;
- se añadieron regresiones de transporte, composición caller-signal/timeout y cableado de hooks.

**Validación ejecutada:** 519 tests frontend pasaron antes de la corrección final; tras la corrección final pasaron las 6 regresiones H36/API, `npx tsc --noEmit`, `npm run lint` y `npm run build`. El bloque lab Gate F está cerrado para la instrumentación opt-in local; no se declara cumplimiento de Web Vitals ni field/RUM de producción.

**Siguiente bloque H36:** ejecutar el profiler configurable contra un frontend/backend local levantado y guardar la evidencia del baseline. El runner ya admite `PERF_ROUTES`, `PERF_PROFILES`, Fast 3G y JSON; quedan fuera de este bloque skeletons, dedupe/TTL, fan-out de watchlist y lazy loading de secundarios.

### Actualización 2026-08-08 — profiler configurable preparado

Se extendió `frontend/scripts/perf_profile_playwright.cjs` manteniendo el comportamiento histórico por defecto:

```bash
cd frontend
PERF_ROUTES=/hoteles \
PERF_PROFILES=desktop,mobile,fast3g \
PERF_JSON=1 \
PERF_OUTPUT_DIR=../docs/qa/evidence/hotels-h36-baseline \
PERF_HOTELS_FLOW=1 PERF_HOTELS_CITY=Madrid \
LOGIN_EMAIL='cuenta-de-qa' LOGIN_PASSWORD='secreto-de-qa' \
node scripts/perf_profile_playwright.cjs
```

- `PERF_ROUTES` limita rutas y falla explícitamente si una ruta no existe.
- `PERF_PROFILES` acepta `desktop`, `mobile` y `fast3g`; el último usa emulación CDP y caché desactivada.
- `PERF_JSON=1` activa el JSON; `PERF_OUTPUT_DIR` también lo activa y fija la carpeta de salida relativa a `frontend/`.
- El reporte conserva TTFB, DCL, load, LCP, CLS y TTI aproximado; TTI sigue siendo `networkidle + settle`, no INP.
- Para `/hoteles`, registra `shellInteractiveAt` al encontrar el input principal. Con `PERF_HOTELS_FLOW=1` rellena una ciudad de QA (`PERF_HOTELS_CITY`, por defecto `Madrid`), ejecuta la búsqueda y registra `firstResultRenderedAt` si aparece una card; sin ese flag, el primer resultado queda deliberadamente en `null`.
- Las requests hoteleras se guardan como método + pathname (`GET /api/v1/hotels/...`), nunca query strings.
- Se registran errores de consola truncados y no se guardan credenciales, payloads, tokens ni URLs completas.
- Si no se proporciona login, el baseline mide la respuesta de la ruta/redirect público; no debe interpretarse como baseline autenticado del radar.
- `PERF_HOTELS_FLOW=1` es un recorrido de lectura/búsqueda; usa una cuenta de QA y no crea tracking, watchlist, alertas ni comparativas.
- El waiter de hitos exige un identificador de documento nuevo tras cada navegación para no medir un selector del DOM anterior al reutilizar la página.

**Validación del runner:** `node --check`, typecheck, lint y 9 tests de contrato pasan. Las evidencias de diagnóstico público (`hotels-h36-baseline` y `hotels-h36-baseline-3100`) quedan archivadas como inválidas/no autenticadas y no se usan como métricas.

**Baseline autenticado válido — 2026-08-08:** se construyó un build de producción aislado con Next 15.5.22, se verificó `/hoteles` y un asset `/_next/static` con HTTP 200, y se ejecutó una ronda con una cuenta QA efímera contra backend local. Evidencia: `docs/qa/evidence/hotels-h36-auth-baseline-3400-final/perf_playwright_20260808T153149.{md,json}`. En desktop/mobile/Fast 3G: status 200, cero errores de consola, shell en 417/433/2980 ms, primer resultado en 778/785/3367 ms y 9 requests GET hoteleras por perfil. TTFB fue 4/7/6 ms, LCP 456/400/2656 ms y CLS 0.003/0/0; TTI es aproximado (`networkidle + 500 ms`). Es una medición lab local de una ronda con fixture/backend QA, no un p75 de producción ni un claim de cumplimiento de Web Vitals.

**Resultado del diagnóstico posterior:** el HTTP 500 de `:3000` no era un fallo de `/hoteles`; el puerto estaba ocupado por un proceso Next previo y un arranque paralelo produjo `EADDRINUSE`. La evidencia de `:3000` queda clasificada como inválida por conflicto de entorno. En un servidor sano de producción sobre `:3100`, `/hoteles` respondió `200`, y el navegador confirmó el redirect correcto a `/login?returnUrl=%2Fhoteles` sin sesión y sin errores de consola. La evidencia pública está en `docs/qa/evidence/hotels-h36-baseline-3100/perf_playwright_20260808T151023.{md,json}`.

El reporte `:3100` no es todavía un baseline del radar: `authConfigured=false`, `PERF_HOTELS_FLOW=false`, no hubo shell hotelero ni requests hoteleras y aparecieron respuestas 400 de llamadas auxiliares de la página pública. No se usan sus tiempos como claim de rendimiento del radar.

**Gate R — recorrido real autenticado, 2026-08-08:** se ejecutó el script `frontend/scripts/qa_hotels_gate_r.mjs` en un build de producción aislado sobre `:3500`, con cuenta QA efímera y solo operaciones GET. Evidencia sanitizada: `docs/qa/evidence/hotels-h36-gate-r-3500/gate-r.json`; no se conserva trace autenticado porque puede incluir headers/tokens de sesión. Pasaron: búsqueda Madrid (2 resultados), selección con detalle, autocomplete Madrid + area-search (respuesta 200; `areaCount=0`, empty válido), error 503 controlado con alerta y query conservada, empty controlado sin alerta falsa, error de paridad controlado con badge visible y cancelación por navegación (`ERR_ABORTED`) sin alerta residual. No hubo errores de consola inesperados; los 503 controlados quedan en el registro como esperados. La evidencia JSON no contiene credenciales, tokens, query strings ni UUIDs de hoteles y no ejecutó tracking, watchlist, alertas, comp sets ni ingest. El trace es opt-in mediante `GATE_R_TRACE=1` y no debe persistirse con una sesión autenticada sin auditoría.

**Siguiente acción real:** repetir Gate M en varias rondas y completar el bloque field/RUM de producción: volumen suficiente, p75 por segmento y bundle route-specific. Gate R y Gate M quedan cerrados únicamente para las rondas lab declaradas; no implica cierre de H21 ni cumplimiento de producción.

**Gate F — laboratorio autenticado, 2026-08-08:** se añadió `frontend/src/modules/hotels/HotelRumTracker.tsx`, montado únicamente en `/hoteles`, y el contrato puro `hotelRum.ts`. La activación es opt-in mediante `localStorage` (`viru_hotels_rum_consent=granted`); sin consentimiento no se emiten eventos RUM. El evento first-party `hotel_rum_vitals` usa `/ux/events`, exige autenticación y solo acepta `schema_version`, superficie, métrica, bucket de valor, rating, tipo de navegación y clase de dispositivo. LCP/CLS/TTFB se observan mediante `PerformanceObserver`/Navigation Timing; INP se registra como aproximación de Event Timing y no como INP oficial completo. La evidencia sanitizada del build aislado `:3603` está en `docs/qa/evidence/hotels-h36-gate-f-3603-final/gate-f.json`: consentimiento ausente produjo cero RUM, consentimiento concedido produjo dos RUM válidos, `failedGateFAssertions=0`, sin errores de consola ni violaciones de privacidad. Los eventos no-RUM del canal compartido se registran solo por nombre en la evidencia.

**Gate M — ronda lab autenticada, 2026-08-08:** se ejecutó `frontend/scripts/qa_hotels_gate_m.mjs` en un build de producción aislado sobre `:3602`, con cuenta QA efímera, backend local y operaciones hoteleras solo GET. Evidencia sanitizada: `docs/qa/evidence/hotels-h36-gate-m-3602/gate-m.json`. Los perfiles `desktop` (1440×1200), `tablet` (1024×900), `mobile` (390×844) y `fast3g-cpu4` (390×844, Fast 3G emulado y CPU 4×) pasaron con HTTP 200, autenticación lista, 2 resultados, foco inicial establecido, cero overflow visual, cero fallos de requests hoteleras, cero respuestas 5xx, cero escrituras y cero errores de consola; `failedGateMAssertions=0`. El runner registra LCP/CLS/TTFB y tareas largas como señales observacionales: Fast 3G/CPU4 observó 24 tareas largas, 2.797 ms acumulados y una máxima de 417 ms; no se convierten aún en un gate binario por falta de un umbral reproducible por hardware.

El primer intento de Gate M marcó desktop/tablet por `scrollWidth` bruto con `html { zoom: 75% }`; la medición fue endurecida para comprobar overflow visual mediante rects y registrar layout normalizado. No se modificó el CSS del producto por ese falso positivo. Esta evidencia es una ronda lab local con fixture/backend QA: no demuestra INP, p75 de producción, RUM/field compliance ni latencia real del provider. No se conserva trace autenticado y el JSON valida ausencia de credenciales, tokens, query strings y marcadores de autorización.

**Relacionado con:** H03 arquitectura de información, H04 métricas, H05 freshness/provenance, H09 sweeps, H13 formulario, H15 resultados, H16 cards, H18 detalle, H19 precio, H20 comparación, H21 estados, H31 dirección visual, H32 responsive, H33 accesibilidad, H34 i18n, H35 legal/privacidad, H37 benchmark/coste, H39 tests, H40 browser QA, H41 observabilidad.

> H36 define cuánto debe tardar `/hoteles` en mostrar una interfaz estable, permitir interactuar y producir el primer resultado útil. No confunde la latencia del navegador con la del provider externo: el tiempo de red del provider debe medirse y comunicarse como estado de producto, no ocultarse dentro de una promesa de “instantáneo”.

---

## 1. Objetivo y frontera

Una persona debe poder:

1. ver el shell de `/hoteles` sin una pantalla vacía;
2. identificar el buscador y empezar a escribir sin bloqueo perceptible;
3. recibir feedback estable mientras se resuelve la zona o se buscan hoteles;
4. obtener el primer resultado útil sin esperar a paneles secundarios;
5. interactuar con filtros, autocomplete, selección y CTA sin jank;
6. conservar el contexto cuando una request se cancela, falla o queda obsoleta;
7. usar el flujo en móvil real y en una red degradada sin overflow ni layout inestable.

H36 cubre:

- presupuesto de documento, CSS, JavaScript, fuentes y recursos críticos;
- LCP, INP, CLS, TTFB y tiempo hasta primer resultado útil;
- waterfalls de requests, cancelación, debounce, dedupe y prioridades;
- skeletons estructurales, loading/empty/error y estabilidad de layout;
- carga diferida de comparativas, alertas, watchlist, histórico y paneles secundarios;
- límites de resultados, paginación/virtualización y coste de renderizado;
- imágenes, fuentes, mapas y scripts de terceros;
- lab, browser automation, trace y RUM/field data;
- gates de hardware móvil, red degradada, dark/light, zoom y reduced motion.

H36 no decide por sí sola:

- qué proveedor hotelero se integra ni cuánto tarda su API (H07/H08);
- el scheduler o coste máximo de sweeps (H09/H37);
- la forma final del envelope V2 de resultados (H15);
- una compra de servicio de RUM, analítica o monitorización. Cualquier servicio externo requiere investigación, privacidad y aprobación H35/H41;
- una garantía contractual de Web Vitals para todo el producto.

---

## 2. Estado real V1: evidencia observada

### 2.1. Lo que existe

| Superficie | Evidencia V1 | Lectura correcta |
|---|---|---|
| Ruta | `/hoteles` renderiza `HotelRadarPage`, un Client Component | La página depende de hidratación y requests de cliente para poblar datos |
| Refresh inicial | Al montar se llaman `refreshCompSets`, `refreshWatchlist`, `refreshAlertRules` y `refreshTrackedOffers` | Hay varias cargas secundarias concurrentes, pero no existe un presupuesto ni prioridad documentada |
| Detalle seleccionado | `useHotelDetail` ejecuta en paralelo detalle, rates y parity con `Promise.allSettled` | Evita una cascada interna y ahora aborta HTTP al cambiar de selección; sigue pendiente medir su coste |
| Watchlist | La hidratación de hoteles faltantes hace `Promise.allSettled` sobre un request por hotel | Puede crear un fan-out proporcional al tamaño de la lista; necesita límite, dedupe, cache TTL o endpoint batch |
| Comparativa | `useHotelCompSets` carga lista y, al seleccionar, detalle del comp set, anchor y nearby suggestions | Es una superficie secundaria que no debe bloquear el primer resultado |
| Autocomplete | `HotelSearchPanel` aplica debounce de 350 ms para `areaResolve` | Existe debounce local, cancelación HTTP y latest-wins; dedupe y medición de coste siguen pendientes |
| Requests | `frontend/src/modules/hotels/api.ts` usa `apiFetchWithStatus` y las operaciones principales aceptan `AbortSignal` | La cancelación de búsqueda, resolve y selección ya está cableada; dedupe, prioridades y métricas siguen pendientes |
| Resultados | La card principal hace `.map()` sobre la lista y el search V1 pide `limit: 30` | Hay un límite inicial, pero no existe paginación/virtualización contractual para crecimiento posterior |
| Loading | La página muestra textos de loading y estados vacíos; no hay skeleton hotelero estructural completo | El espacio puede cambiar cuando llegan resultados o paneles secundarios |
| Cache | Existen caches en memoria para algunos detalles de watchlist/comp set | No hay TTL, invalidación ni límite de memoria documentado |
| Fuentes | `globals.css` importa Google Fonts mediante `@import` | Puede afectar la ruta crítica y requiere medir bloqueo, fallback y consentimiento H35 |
| Instrumentación | No se encontró instrumentación hotelera específica de LCP/INP/CLS/TTFB/RUM | No puede afirmarse cumplimiento ni regresión controlada antes de medir |

### 2.2. Riesgos concretos

- El primer paint puede incluir un shell client-side antes de que exista resultado; no debe llamarse “resultado rápido” solo por mostrar un loader.
- Los refreshes secundarios de montaje compiten por red, CPU y autenticación con la primera interacción.
- Seleccionar un hotel dispara tres requests; ahora el transporte se aborta al cambiar de selección, aunque el coste y la prioridad de esos requests siguen pendientes de medir.
- La hidratación de watchlist puede disparar muchas llamadas de detalle en paralelo.
- `Promise.allSettled` evita que una petición secundaria mate todo el panel, pero no reduce coste ni prioriza el camino principal.
- El autocomplete resuelve después de 350 ms y ahora cancela la request previa con latest-wins; todavía no existe dedupe de intenciones idénticas.
- El resultado de área construye una lista derivada y cada card formatea precio en render; su coste debe medirse con resultados grandes.
- No hay evidencia de dimensiones reservadas para recursos hoteleros futuros ni de un skeleton con alturas equivalentes.
- La importación global de fuentes externas y CSS de MapLibre debe auditarse en el bundle de `/hoteles`, aunque no todos sus estilos se usen en la pantalla.

**Estado de lanzamiento:** H36 no declara “rápido”, “instantáneo”, “sin layout shift” ni “cumple Core Web Vitals” hasta aportar medición lab y field suficiente.

---

## 3. Modelo de rendimiento: cuatro tiempos distintos

H36 exige separar:

```text
T0 request document
  → T1 shell interactivo
  → T2 buscador listo para escribir
  → T3 primer resultado útil
  → T4 resultado completo/secondary hydration
  → T5 interacción estable después de filtrar o seleccionar
```

| Tiempo | Definición | No debe confundirse con |
|---|---|---|
| TTFB | Inicio de respuesta del documento/endpoint medido | tiempo total del provider |
| LCP | Render del elemento de mayor contenido visible | llegada de todos los hoteles |
| Shell interactivo | controles principales aceptan foco/teclado | datos secundarios cargados |
| Primer resultado útil | primera card o mensaje accionable con contexto suficiente | lista completa, parity o histórico |
| Completo | carga de datos prioritarios y secundarios definidos | “reserva confirmada” |
| INP | latencia de la interacción relevante hasta el siguiente paint | tiempo de respuesta HTTP aislado |

Para búsquedas con provider externo, H36 debe guardar al menos:

- `client_started_at`;
- `request_sent_at`;
- `server_response_at`;
- `provider_started_at`/`provider_finished_at` si existe;
- `first_result_rendered_at`;
- `complete_rendered_at`;
- estado `success/empty/partial/stale/unavailable/error/cancelled`.

Los timestamps no deben incluir `user_id`, query privada completa ni payload externo en telemetría, según H35.

---

## 4. Presupuesto objetivo

Los valores siguientes son objetivos de release para la superficie hotelera, no evidencia de que V1 ya los cumpla. Deben medirse en un entorno reproducible y revisarse cuando cambien shell, provider, hardware o tráfico.

### 4.1. Core Web Vitals y servidor

| Métrica | Objetivo p75 | Degradación que obliga a investigar | Contexto |
|---|---:|---:|---|
| TTFB documento | ≤ 0,8 s | > 1,8 s | lab y field; separar backend de provider |
| LCP | ≤ 2,5 s | > 4,0 s | lab móvil y field; identificar elemento LCP |
| INP | ≤ 200 ms | > 500 ms | principalmente field; lab con interacciones reproducibles |
| CLS | ≤ 0,10 | > 0,25 | lab y field; incluir cambios de resultados/paneles |

La evaluación de release usa p75 por viewport/dispositivo cuando exista volumen suficiente. Un único Lighthouse verde no demuestra field compliance. INP no debe declararse conforme usando solo una carga estática sin interacción.

### 4.2. Presupuesto de producto

| Señal | Target inicial | Gate |
|---|---:|---|
| Shell visible | ≤ 1,5 s en móvil de laboratorio | no pantalla blanca ni salto de header |
| Buscador interactivo | ≤ 2,0 s | input y modo de búsqueda reciben foco/teclado |
| Primer resultado útil | ≤ 4,0 s con Fast 3G y fixture estable | si provider tarda más, mostrar estado honesto y timestamp/acción |
| Feedback local de interacción | ≤ 100 ms | toggle, focus, loading y validación se perciben inmediatos |
| Main-thread blocking de carga | ≤ 300 ms acumulados en tareas >50 ms | investigar tareas largas causadas por hotel UI |
| Lista inicial | máximo 30 cards V1 | paginar/virtualizar antes de aumentar el límite |
| JavaScript inicial de ruta | ≤ 200 KB comprimidos como objetivo de calibración | medir con build real; no contar solo el archivo principal |
| Peso inicial total | ≤ 1,5 MB como objetivo de calibración | incluye CSS, fonts, scripts y recursos críticos |

El target de primer resultado es válido únicamente para fixture/mock o backend controlado; en provider real se reportan por separado latencia del provider, latencia del backend y render del cliente. No se permite “cumplir” ocultando el resultado detrás de un spinner o descartando estados parciales.

### 4.3. Presupuestos de interacción

- autocomplete: debounce entre 250–400 ms, latest-wins y cancelación de requests obsoletas;
- selección de hotel: no más de una operación de detalle activa por selección vigente;
- filtro/orden: feedback local ≤100 ms y no más de una request válida por intención establecida;
- búsqueda duplicada: la misma intención no debe generar requests concurrentes innecesarias;
- panel secundario: no bloquea el foco, submit ni primer resultado;
- tareas de render: dividir listas grandes, memoizar solo cuando la medición lo justifique y evitar trabajo por card no visible;
- navegación/teclado: ningún loader o transición debe robar foco o introducir un bloqueo >200 ms.

---

## 5. Requisitos de arquitectura y UI

### 5.1. Prioridad de cargas

Orden recomendado:

1. shell, navegación privada y buscador;
2. validación y resolución de destino;
3. resultados principales;
4. detalle del resultado seleccionado;
5. tracking/watchlist asociado a la decisión;
6. alertas, parity, comp set, nearby e histórico cuando sean visibles o solicitados.

La implementación puede mantener llamadas concurrentes, pero debe demostrar que las secundarias no consumen el presupuesto del camino principal. Si el backend no soporta un endpoint agregado, la UI debe limitar fan-out y degradar con honestidad.

### 5.2. Loading y estabilidad visual

- Usar skeletons con la misma estructura aproximada que la primera card, heading, count y panel visible.
- Reservar altura para contenido que llegará async; no insertar bloques grandes encima del foco actual.
- Mantener estable el ancho/alto del autocomplete y sus sugerencias.
- No mostrar `0` como resultado definitivo mientras una búsqueda está cargando.
- Diferenciar loading inicial, refresh, partial, stale y error.
- Mantener acciones primarias disponibles cuando una superficie secundaria está cargando.
- Respetar reduced motion y no usar animaciones como sustituto de feedback semántico.

### 5.3. Requests y cache

- Aceptar `AbortSignal` desde hooks hasta `apiFetchWithStatus` para búsqueda, resolve, detalle, parity y snapshots.
- Aplicar latest-wins a destino, búsqueda y selección de hotel.
- Deduplicar peticiones idénticas durante una ventana breve.
- Definir TTL, clave, invalidación y límite de memoria para caches de detalles; una cache sin TTL no es un contrato de freshness.
- No cachear respuestas privadas fuera del scope de usuario ni reutilizarlas entre cuentas.
- Mantener cancelación lógica incluso cuando el transporte no pueda abortarse.
- Evitar un request por hotel en watchlist cuando pueda existir batch o límite explícito.
- No reintentar automáticamente provider calls costosas sin backoff y budget H09/H37.

### 5.4. Assets y terceros

- Medir impacto real de Google Fonts y decidir self-host, preload, `font-display` y consentimiento según H34/H35.
- No cargar mapas, librerías o CSS de paneles no visibles en la ruta crítica sin evidencia.
- Cualquier imagen hotelera debe tener dimensiones, lazy loading, procedencia/licencia y fallback.
- Cualquier script de analítica debe cargarse fuera del camino crítico y no enviar PII.
- Revisar bundle route-specific de Next, no solo el tamaño total del proyecto.

---

## 6. V1 frente a V2

### V1 — mínimo de rendimiento necesario

- medir baseline de `/hoteles` en desktop, móvil y red Fast 3G;
- añadir eventos/telemetría de T1–T5 sin PII;
- skeletons estructurales y estados estables;
- cancelación y latest-wins para requests obsoletas;
- prioridad del primer resultado sobre paneles secundarios;
- límite V1 de 30 resultados y protección ante fan-out de watchlist;
- TTL explícito para caches introducidas o documentación de no-cache;
- gates LCP/INP/CLS/TTFB y primer resultado en CI/lab y field cuando haya volumen.

### V2 — optimización posterior

- streaming o server/client split si el benchmark demuestra beneficio real;
- endpoint agregado para watchlist/details y envelope de resultados V2;
- paginación/virtualización para catálogos grandes;
- prefetch de detalle solo con evidencia de intención y budget;
- Web Worker para procesamiento pesado únicamente si un trace lo justifica;
- RUM segmentado por provider, dispositivo, locale y estado de red;
- budgets adaptativos por mercado sin relajar el p75 global sin decisión registrada.

H36 no exige Web Workers, prefetch agresivo ni streaming por moda. Cada optimización debe tener benchmark antes/después y no empeorar privacidad, accesibilidad o claridad de estados.

---

## 7. Prioridades de remediación

### P0 — camino principal bloqueado

- Medición reproducible de shell, buscador, primer resultado, LCP, INP y CLS.
- Separar carga prioritaria de refreshes secundarios de montaje.
- Evitar que una búsqueda o selección obsoleta pueda sobrescribir la vigente.
- Skeleton/estado estable para que loading no produzca layout engañoso.
- Presupuesto móvil y Fast 3G con evidencia versionada.

### P1 — eficiencia y escalabilidad

- `AbortSignal` real en API/hook y latest-wins del autocomplete. **Cerrado el 2026-08-08 para búsqueda, resolve y selección de hotel.**
- TTL/dedupe/límites para caches y fan-out de watchlist.
- Lazy/deferred loading de alertas, parity, comp sets, nearby e histórico cuando no estén visibles.
- Bundle y fuentes route-specific medidos; CSS/terceros fuera de la ruta crítica si procede.
- Límite, paginación o virtualización antes de superar 30 resultados.

### P2 — optimización avanzada

- Prefetch selectivo, streaming, Web Worker o RUM segmentado si el benchmark lo justifica.
- Budget automático de regresión por PR y dashboard histórico.
- Adaptación por capacidad de dispositivo/red sin cambiar semántica de estados.
- Tuning de animaciones, memoización y render solo tras trace.

---

## 8. Evidencia y gates de cierre

### Gate B — baseline lab

- Build de producción con versión de Node/Next registrada.
- Lighthouse o herramienta equivalente en móvil simulado y desktop.
- Trace de Chrome con CPU throttling y Fast 3G.
- Waterfall de documento, JS, CSS, fonts y requests hoteleras.
- Identificación explícita del elemento LCP, tareas largas y shifts de CLS.

### Gate R — recorrido real

- Browser flow: abrir `/hoteles`, enfocar buscador, resolver área, buscar, seleccionar resultado, abrir tracking/watchlist y plegar paneles.
- Medir al menos primer resultado, interacción de autocomplete, selección y refresh.
- Probar respuesta obsoleta, cancelación, error, empty, partial y provider lento.
- Verificar que el foco y el contexto no se pierden durante loading.

### Gate M — móvil y red degradada

- Viewports estrecho, intermedio y desktop.
- Dispositivo/CPU representativo de gama media, no únicamente ordenador de desarrollo.
- Fast 3G o perfil acordado, con fixture estable y provider separado.
- Dark/light, ES/EN, zoom/reflow, teclado y reduced motion.
- Sin overflow, CLS grave ni bloqueo de CTA principal.

### Gate F — field/RUM

- Instrumentación compatible con `onLCP`, `onINP`, `onCLS` y `onTTFB` o equivalente.
- Redaction y consentimiento conforme H35; no activar analítica sensible por defecto.
- Segmentación por ruta, viewport, conexión, locale, provider y estado sin identificar personas.
- **Lab cerrado:** la implementación opt-in y el contrato sanitizado pasan la evidencia `hotels-h36-gate-f-3603-final`; el runner intercepta `/ux/events` y no persiste telemetría de QA.
- **Field pendiente:** la implementación local no demuestra volumen, p75 de producción ni cumplimiento; sin una ventana de datos suficiente se debe marcar “no concluyente” y no “cumple”.

### Gate Q — regresión

- Presupuesto de bundle route-specific y total inicial.
- Tests de no duplicación/cancelación y renders grandes.
- Comparativa antes/después de cualquier optimización.
- `git diff --check`, typecheck/build y tests hoteleros relevantes.

**Criterio final:** no quedan P0, los budgets lab pasan en el recorrido definido, existe evidencia de field suficiente o se declara explícitamente no concluyente, y ninguna optimización degrada H21 (estados), H33 (a11y), H34 (i18n) o H35 (privacidad).

---

## 9. Claims que H36 no autoriza

Mientras el gate no esté cerrado, no se puede afirmar que `/hoteles` sea:

- instantáneo o en tiempo real;
- rápido en cualquier dispositivo, país o red;
- compliant con Core Web Vitals en producción;
- libre de layout shifts;
- independiente de la latencia del provider;
- optimizado por streaming, cache, virtualización o cancelación si no hay evidencia del mecanismo;
- medido por RUM si solo existe Lighthouse o un navegador local;
- “ligero” por el tamaño de un único bundle sin contar CSS, fuentes, terceros y chunks de ruta.

H36 sí autoriza como contrato que el equipo mida, priorice el primer resultado, cancele trabajo obsoleto, reserve espacio visual, difiera secundarios y publique solo claims respaldados por datos.
