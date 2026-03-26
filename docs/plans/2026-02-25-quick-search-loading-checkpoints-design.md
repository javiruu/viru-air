# Quick Search Loading V2 - Diseño de Checkpoints y Mensajería por Vuelo

Fecha: 2026-02-25
Ámbito: `/quick-search` (solo UX de loading y percepción de progreso)

## Skills aplicadas
- `brainstorming`: definición de problema, alternativas y decisión recomendada.
- `fullstack-developer`: acople real FE/BE sin romper contratos.
- `writing-plans`: estructura ejecutable fase por fase.

## Evidencia revisada (documentación y logs)
- `docs/estetica.md`
- `docs/qa/frontend-pr-checklist.md`
- `docs/plans/2026-02-19-air-loader-global-design.md`
- `docs/plans/2026-02-23-recomendaciones-quick-search-design.md`
- `logs_ia/sesion_2026-02-17_quick_search_completo.log`
- `logs_ia/sesion_2026-02-17_quick_search_prompt.log`
- `logs_ia/sesion_2026-02-17_21-57-07_quick_search_i18n_tests.md`
- `logs_ia/sesion_2026-02-16_quicksearch_historico_estetica.log`

## Estado actual (mapa técnico real)
Referencia principal: `frontend/src/app/(private)/quick-search/page.tsx`.

- Submit y loading:
  - `setSearchState("loading")`: línea aprox `921`.
  - Hito 30% (`requesting`): línea aprox `924`.
  - `await apiFetchWithStatus(.../search/quick...)`: línea aprox `1026`.
  - Hito 80% (`response_parsed`): línea aprox `1030`.
  - Hito 95% (`client_done`): líneas aprox `1041`, `1053`, `1066`.
  - `success|empty|rate|error`: líneas aprox `1043`, `1056`, `1059`, `1067`.
- Weather ya desacoplado del fin de loading principal:
  - `Promise.allSettled([originWeatherPromise, destinationWeatherPromise])`: línea aprox `1014` (no bloquea resultados).
- Render loading actual:
  - bloque `showLoader || loadingVisualHold`: línea aprox `3262`.
  - loader boarding + skeleton cards: líneas aprox `3264-3326`.
- Mensajes i18n ya existentes para fases:
  - `loadingPhaseRequesting`, `loadingPhaseResponseParsed`, `loadingPhaseClientDone`, `loadingPhaseCommitted`.

## Problema de UX que queremos resolver
1. El usuario ve progreso global, pero no "qué vuelos concretos" se están intentando.
2. Falta granularidad semántica: los hitos existen, pero no comunican fan-out de búsqueda.
3. En cargas de varios segundos, la percepción de avance puede ser plana aunque técnicamente avance.

## Objetivo de V2
- Mantener progreso real por hitos (sin fake progress).
- Añadir una capa narrativa de sub-checkpoints:
  - "Buscando vuelo X"
  - "Buscando vuelo Y"
  - "Buscando vuelo Z"
- Sin tocar contratos backend ni lógica core de ranking/filtros.

## Constraints no negociables
- No cambiar endpoints (`/search/quick`, weather) ni contratos de respuesta.
- No alterar semántica de `searchState` ni rutas de error/rate.
- No bloquear `success/empty` esperando weather.
- No introducir params nuevos de backend.
- No degradar accesibilidad (`role=status`, `aria-live`, keyboard).
- Respetar `prefers-reduced-motion`.

## Alternativas de diseño

### Opción A (recomendada): Sub-checkpoints "estimados por combinaciones" en cliente
Idea:
- Antes del fetch, construir una vista previa de hasta 3 combinaciones candidatas (por ejemplo, origen/destino base + alternativos disponibles en estado local).
- Mostrar secuencia textual durante `loading`: `Buscando vuelo A`, luego `B`, luego `C`.
- La secuencia avanza con hitos reales (30 -> 80 -> 95), no con reloj libre.

Pros:
- No requiere cambios backend.
- Se puede implementar con datos ya presentes en UI.
- Control total de copy e i18n.

Contras:
- Es una representación de "combinaciones evaluadas" en FE, no telemetría exacta por intento real del backend.

### Opción B: Sub-checkpoints por eventos backend (requiere contrato)
Idea:
- Backend devuelve progreso por proveedor/combinación en streaming o meta incremental.

Pros:
- Máxima fidelidad.

Contras:
- Rompe constraint actual (sí cambia contrato).
- Coste alto y riesgo de regresión.

### Opción C: Sub-checkpoints por proveedores (Ryanair/otros)
Idea:
- Mostrar "Consultando proveedor X".

Pros:
- Mensaje claro de arquitectura.

Contras:
- Si quick-search depende principalmente de un origen de tarifas, puede inducir a error.
- No cubre el pedido explícito de "vuelo X/Y/Z".

## Decisión recomendada
Adoptar Opción A.

Razonamiento:
- Cumple constraints actuales.
- Mejora percepción y comprensión sin mentir progreso global.
- Encaja con el flujo de quick-search (fan-out implícito por flex/radio/alternativos) y con la estética definida en `docs/estetica.md`.

## Modelo de checkpoints (V2)

### Capa 1: Checkpoints macro (ya existente, se conserva)
- 30%: `requesting` -> "Consultando tarifas..."
- 80%: `response_parsed` -> "Ordenando resultados..."
- 95%: `client_done` -> "Preparando vista..."
- 100%: `committed` -> "Listo" (solo success/empty)

### Capa 2: Sub-checkpoints por vuelo (nuevo)
Regla:
- Renderizar máximo 3 items.
- Formato recomendado: `Buscando vuelo {ORIGEN}-{DESTINO}`.
- Durante `requesting` se resaltan secuencialmente (1/3, 2/3, 3/3).
- Si no hay suficientes combinaciones confiables, fallback:
  - "Buscando mejor combinación 1/3", etc.

Fuentes de datos permitidas:
- `origin`, `destination`, `originCountryOnly`, `destinationCountryOnly`.
- toggles ya existentes (`includeNearbyOrigins`, `includeNearbyDestinations`, `radius_km`, `flex_days_before/after`).

No permitido:
- Inventar IDs de backend ni claims de proveedores no confirmados.

## i18n y microcopy
Recomendación de claves nuevas en `quickSearchCopy.ts`:
- `loadingSubcheckTitle`: "Comprobaciones en curso"
- `loadingSubcheckFlight`: "Buscando vuelo {route}"
- `loadingSubcheckCombo`: "Buscando mejor combinación {index}/{total}"
- `loadingSubcheckActive`: "en curso"
- `loadingSubcheckDone`: "completado"

EN:
- `Loading checks in progress`
- `Searching flight {route}`
- `Searching best combination {index}/{total}`
- `in progress`
- `done`

## Instrumentación recomendada (sin spam)
Eventos sugeridos:
- `quicksearch_loading_subcheckpoints_shown` (una vez por búsqueda)
- `quicksearch_loading_subcheckpoint_advanced` (máx 3 veces por búsqueda)

Guardrails:
- Emitir solo cuando cambia índice activo.
- No emitir en cada frame de `displayProgress`.

## Accesibilidad
- Lista de sub-checkpoints con texto visible y estado (`aria-live="polite"` ya existente en bloque loader).
- No anunciar 20 cambios por segundo; solo cuando cambia sub-checkpoint activo.
- En reduced motion, mantener cambio textual sin animaciones extra.

## Riesgos y mitigación
1. Riesgo: percepción de inexactitud si el backend termina muy rápido.
- Mitigación: mostrar sub-checkpoints solo cuando `showLoader` ya está activo (threshold 300ms).

2. Riesgo: spam visual con demasiados mensajes.
- Mitigación: límite estricto a 3 sub-checkpoints.

3. Riesgo: contradicción con resultado empty/error.
- Mitigación: no afirmar éxito de sub-checkpoint; usar estado neutral "en curso"/"completado".

## Criterios de aceptación
- El loading muestra macro-fase + 2-3 sub-checkpoints legibles.
- Se ven mensajes tipo "Buscando vuelo X/Y/Z" cuando hay rutas confiables.
- No cambia lógica de búsqueda/ranking/backend.
- Build y responsive OK.
- No se rompe a11y ni reduced motion.

## Decisión pendiente del producto (1 pregunta)
¿Quieres que `X/Y/Z` se construya con rutas reales derivadas del estado (recomendado) o prefieres etiquetas neutrales `combinación 1/2/3` para máxima prudencia semántica?
