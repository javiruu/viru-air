Status: draft  
Scope: quick-search regression diagnostics (browser-visible)  
Date: 2026-04-23  
Owner: Codex session (user request)

# Quick Search (`/quick-search`) - TestSprite Strict Report

## 1) Objetivo

Validar con pruebas nuevas y estrictas que `/quick-search` muestre resultados visibles y correctos para rutas concretas, evitando falsos positivos.

Regla de éxito usada:
- No basta con `HTTP 200`.
- Debe existir render real de `.qs-results-list`.
- Debe haber al menos un `.qs-result-row`.
- El texto de ruta visible debe contener los IATA esperados del caso.

## 2) Suite nueva creada

- Test E2E nuevo: `frontend/tests/quick-search-testsprite-strict.e2e.test.ts`
- Plan TestSprite nuevo: `testsprite_tests/quick_search_strict_results_test_plan.json`

Casos ejecutados:
- `QS201`: `MAD -> BCN`
- `QS202`: `VLC -> LIS`

## 3) Entorno y comando de ejecución

Entorno observado durante la ejecución:
- Frontend: `http://127.0.0.1:3000` (activo)
- Backend: `http://127.0.0.1:8000` (activo)
- Fecha/hora de evidencia principal (UTC): `2026-04-23T16:04:36Z`

Comando usado:

```powershell
cd frontend
npm run test -- tests/quick-search-testsprite-strict.e2e.test.ts
```

## 4) Resultado global

Resultado: **FAIL (2/2 casos)**.

### Evidencia directa

Archivo de evidencia estructurada:
- `testsprite_tests/tmp/quick_search_strict_results_report.json`

Capturas de navegador:
- `testsprite_tests/tmp/qs201_strict.png`
- `testsprite_tests/tmp/qs202_strict.png`

En ambas capturas se observa estado visual degradado de quick-search con:
- mensaje de búsqueda parcial,
- contador de resultados en `0`,
- ausencia de lista `.qs-results-list`.

## 5) Qué sí funciona y qué no

### Sí funciona

- El submit de búsqueda se ejecuta.
- El endpoint `/api/v1/search/quick` responde `HTTP 200`.
- La respuesta contiene estructura JSON válida con claves `query`, `meta`, `filters`, `results`.

### No funciona

- Para ambos casos, `results` llega vacío (`resultsLength: 0`).
- La UI no renderiza `.qs-results-list` ni filas de resultados.
- Por tanto, la experiencia "ver resultados correctamente" falla en ambos casos.

## 6) Por qué esto NO es un falso positivo

El check está diseñado para bloquear el caso típico de falso positivo (`200` sin datos útiles):

1. Se verifica la respuesta de red.
2. Se verifica render real en DOM.
3. Se exige contenido mínimo visible (al menos 1 fila).
4. Se valida consistencia de ruta visible (IATA origen/destino).

Conclusión: el fallo es real y reproducible; no es un fallo de test superficial.

## 7) Hipótesis técnicas priorizadas (para desarrollador externo)

### H1 - Búsqueda en modo degradado/estricto devuelve 0 resultados para esas rutas-fecha

Síntomas que apoyan H1:
- Respuesta `200` pero `results: []`.
- UI muestra mensaje de búsqueda parcial/degradada.

Qué revisar:
- Lógica backend de ensamblado de `results` cuando proveedores están parciales.
- Si el modo estricto descarta todo cuando falta un proveedor clave.
- Fallback y relajación automática antes de devolver vacío.

### H2 - Contrato backend/frontend no aprovecha `meta` cuando `results` llega vacío

Síntomas:
- Hay metadata y estado de búsqueda, pero la experiencia final es "sin resultados".
- El usuario ve panel de degradación, pero no una estrategia efectiva de recuperación.

Qué revisar:
- `normalizeQuickSearchResponse` en frontend.
- Reglas de render de `QuickSearchResultsList` versus `QuickSearchStatePanels`.
- Condiciones para auto-relajar filtros en estado degradado.

### H3 - Criterios por defecto demasiado restrictivos para la ventana de búsqueda

Síntomas observados en query resumen:
- `strict_filters: true`
- `include_stops: false`
- `max_stops: 0`
- ventana de salida limitada (`07:00`-`22:00`)

Qué revisar:
- Defaults de filtros estrictos en `QuickSearchView`.
- Si estos defaults deberían cambiar cuando backend responde parcial o vacío.

## 8) Plan de arreglo recomendado (secuencia concreta)

1. Instrumentar backend `/api/v1/search/quick` con logs por etapa:
   - total itinerarios brutos por proveedor,
   - descartes por cada filtro,
   - motivo final de `results: []`.
2. Reproducir local con los dos casos (`MAD->BCN`, `VLC->LIS`) y misma fecha seleccionada por UI.
3. Confirmar si el vacío nace en:
   - proveedor sin datos,
   - filtros de negocio,
   - normalización/merge final.
4. Si el vacío viene por filtros estrictos + degradación:
   - aplicar fallback gradual automático,
   - o devolver acciones de relajación ya aplicadas al menos una vez.
5. Ajustar frontend para mostrar claramente:
   - "sin resultados reales" vs "degradado recuperable",
   - CTA que realmente rehaga búsqueda con fallback efectivo.
6. Re-ejecutar esta suite estricta y exigir:
   - `resultsLength > 0`
   - `.qs-results-list` visible
   - `.qs-result-row > 0`
   - ruta correcta en primera fila.

## 9) Criterio de cierre recomendado

No cerrar el bug con solo `200`.

Cerrar únicamente cuando para cada caso objetivo:
- hay resultados visibles reales en UI,
- hay al menos una fila válida,
- la ruta mostrada coincide con la búsqueda,
- y las capturas lo demuestran.
