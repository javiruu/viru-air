# Recomendaciones Hierarquia UX Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redisenar `/recomendaciones` para reducir carga cognitiva, dar protagonismo real al IA Score y mejorar control percibido con feedback dinamico, manteniendo compatibilidad con el motor actual.

**Architecture:** Se mantiene la base de `RecommendationsExplorer` pero se separa en capas de interfaz (TopBar, ConfigPanel, ResultsArea, RecommendationCard). Se agregan utilidades de explicacion y de impacto de pesos para desacoplar logica de presentacion. En backend se corrige semantica de filtros estrictos/flexibles y se enriquece metadata de fallback IA.

**Tech Stack:** Next.js 15 + React 19 + TypeScript (`tsx --test`), CSS global del sistema editorial actual, FastAPI + Pydantic + pytest.

---

## Skills usadas y orden

1. `brainstorming`: convertir feedback UX en objetivos tecnicos y decisiones de alcance.
2. `ui-design`: definir jerarquia visual, capas de informacion, estados y microinteracciones.
3. `writing-plans`: convertir decisiones en tareas ejecutables, rutas exactas, pruebas y commits.

## Diagnostico actual (base real del repo)

- UI actual en `frontend/src/modules/recommendations/RecommendationsExplorer.tsx` renderiza:
  - hero,
  - rail izquierda siempre visible con ruta + mezcla + filtros,
  - resultados con tarjetas densas y score pequeno.
- Estilos en `frontend/src/styles/globals.css` (`.reco-grid`, `.reco-rail`, `.reco-score`, `.reco-card`) confirman peso visual parecido entre panel lateral y resultados.
- Mensaje fallback actual solo muestra texto corto: `recommendations.aiFallback` en `frontend/src/i18n/domains/recommendations.ts`.
- Request envia `strict_filters` y `soft_filters_weight`, pero backend no aplica esa semantica de forma real en `backend/app/api/v1/recommendations.py`.

## Design Specification (UI)

1. Purpose Statement:
La pantalla de recomendaciones debe comunicar "IA util y accionable" en menos de 3 segundos. El usuario debe escanear rapido la mejor opcion sin leer un bloque tecnico completo.

2. Aesthetic Direction:
Editorial/magazine con paneles funcionales compactos y tarjetas de resultado protagonistas.

3. Color Palette:
- `#2E6E62` (verde marca principal, score alto)
- `#5C8E84` (verde medio, score medio-alto)
- `#C7A24D` (ambar para score medio)
- `#7F8C8D` (gris para score bajo)
- `#D95D39` (acento acciones)

4. Typography:
- Mantener tipografia actual del sistema global (Playfair Display para titulares + familia base existente del proyecto).

5. Layout Strategy:
- 3 niveles claros:
  - barra superior compacta (resumen + CTA),
  - panel lateral colapsable para configuracion,
  - area principal enfocada en resultados y lectura por capas.

## Cambios funcionales y visuales (mapeo 1:1 con tu feedback)

### 1) Macro-layout en 3 niveles

- Crear top bar inteligente con:
  - Origen, destino, fecha,
  - modo activo (Explorar/Optimizar),
  - CTA principal.
- Mover configuracion avanzada a panel lateral colapsable (default colapsado en desktop y mobile).
- Priorizar area de resultados con ancho dominante.

### 2) IA Score protagonista real

- Redisenar bloque de score en tarjeta:
  - numero 2-3x mas grande,
  - label `IA Score`,
  - color por banda:
    - `>= 70`: verde fuerte,
    - `50-69`: verde suave,
    - `30-49`: ambar,
    - `< 30`: gris.
- Agregar mini animacion de entrada del score (count-up suave, respetando `reduce-motion`).

### 3) Capas de informacion (menos densidad)

- Nivel 1 visible siempre:
  - ruta,
  - precio,
  - IA Score,
  - etiqueta inteligente (`Oportunidad real`, `Estable`, `Sobre media`, etc.).
- Nivel 2 expandible por tarjeta:
  - km,
  - media historica,
  - clima detallado,
  - probabilidad de lluvia.
- `ai_reason` se muestra dentro de bloque "Por que esta arriba" con lista de bullets.

### 4) Sliders con impacto en tiempo real

- Bajo cada slider, mostrar impacto calculado:
  - texto tipo `Precio +12 impacto en ranking`.
- Resumen dinamico global:
  - `Ahora priorizas precio 60% mas que clima`.
- Recalculo local inmediato sobre resultados ya cargados (sin pedir backend hasta CTA o auto-refresh configurable).

### 5) Fallback IA explicativo (no gris plano)

- Reemplazar texto fallback corto por bloque explicativo:
  - titulo de estado degradado,
  - explicacion de que ranking se usa (heuristico),
  - indicadores que SI siguen activos (precio, tendencia, clima).
- Mostrar `ai.error` tecnico solo en tooltip/detalle para soporte, no como copy principal.

### 6) Filtros estrictos vs flexibles claros

- Sustituir controles ambiguos por selector de modo:
  - `Estricto (excluye completamente)`,
  - `Flexible (reduce score)`.
- Mantener slider de "fuerza flexible" solo visible en modo flexible.
- Aplicar semantica real en backend:
  - estricto: excluye candidatos que no cumplen;
  - flexible: penaliza score en vez de excluir.

### 7) CTA principal con presencia

- Boton principal ancho completo en top bar y en barra de resultados.
- Microcopy nuevo:
  - `Actualizar radar inteligente`.
- Estado loading mas claro (`Analizando senales...`).

### 8) Modos "Descubrir" vs "Optimizar"

- Toggle de modo de experiencia:
  - Descubrir: menos controles visibles, foco visual y etiquetas.
  - Optimizar: muestra sliders, filtros avanzados y detalles tecnicos.
- Persistencia por sesion para no forzar reconfiguracion continua.

### 9) Branding premium y transparencia del ranking

- Microinteracciones:
  - reordenamiento suave de cards al cambiar pesos/sort,
  - hover con elevacion controlada,
  - entrada escalonada de resultados.
- Bloque "Por que esta arriba":
  - ejemplo de reglas:
    - `Precio 40% bajo media`,
    - `Tendencia bajista`,
    - `Clima inestable` (cuando aplica).

## Cambios por archivo (exactos)

### Frontend

- Modify: `frontend/src/modules/recommendations/RecommendationsExplorer.tsx`
  - Extraer subcomponentes UI internos.
  - Implementar layout 3 niveles, panel colapsable, toggle de modo.
  - Reducir densidad de card y agregar expand/collapse por item.
  - Conectar nuevo copy de fallback + bloque de transparencia.
- Create: `frontend/src/modules/recommendations/scoreBands.ts`
  - Utilidades `getScoreBand`, `getScoreLabel`, `getScoreClass`.
- Create: `frontend/src/modules/recommendations/rankingExplainers.ts`
  - Generacion de bullets de explicacion con `signals`, `avg_price`, `trend`, `weather`.
- Create: `frontend/src/modules/recommendations/weightImpact.ts`
  - Calculo de impacto relativo por slider y resumen comparativo.
- Modify: `frontend/src/i18n/domains/recommendations.ts`
  - Nuevo copy ES/EN para:
    - modo explorar/optimizar,
    - fallback explicativo,
    - CTA nuevo,
    - etiquetas inteligentes,
    - bloque "por que esta arriba".
- Modify: `frontend/src/styles/globals.css`
  - Nuevas clases `reco-topbar`, `reco-config-panel`, `reco-score-lg`, `reco-card-summary`, `reco-card-details`, `reco-impact`, `reco-mode-toggle`.
  - Ajustes responsive para panel colapsable y tarjetas con capa expandible.

### Backend

- Modify: `backend/app/api/v1/recommendations.py`
  - Aplicar semantica real de `strict_filters` vs `soft_filters_weight`.
  - En fallback heuristico, completar `ai.reasoning_mode` y metadata clara para frontend.
  - (Sin cambiar contrato principal de `items`; solo enrich de `ai` y comportamiento de filtrado).
- Modify: `backend/app/domain/schemas.py`
  - Tipar metadata `ai` mas explicitamente (modelo opcional recomendado) para evitar `dict` opaco.

### Tests

- Create: `frontend/tests/recommendations-score-bands.test.ts`
- Create: `frontend/tests/recommendations-ranking-explainers.test.ts`
- Create: `frontend/tests/recommendations-weight-impact.test.ts`
- Create: `backend/tests/integration/test_recommendations_filter_modes.py`

## Criterios de aceptacion

1. El panel lateral puede colapsarse y el area de resultados gana foco visual sin romper mobile.
2. IA Score es claramente dominante y colorizado por rango.
3. Cada tarjeta muestra solo nivel 1 por defecto; nivel 2 aparece al expandir.
4. Sliders muestran impacto textual inmediato y resumen de prioridad relativa.
5. Fallback IA explica heuristico de forma transparente y confiable.
6. Modo Estricto/Flexible es entendible y altera realmente el filtrado/ranking.
7. CTA principal tiene copy nuevo y mayor protagonismo visual.
8. Toggle Descubrir/Optimizar cambia densidad de controles sin perder funcionalidad.
9. Cada tarjeta muestra razones de ranking comprensibles.

## Riesgos y mitigaciones

- Riesgo: demasiada animacion reduce legibilidad.
  - Mitigacion: respetar `prefers-reduced-motion` y usar duraciones cortas.
- Riesgo: refactor grande en un solo archivo TSX.
  - Mitigacion: extraer utilidades puras + pruebas unitarias primero.
- Riesgo: cambio de filtros afecta resultados esperados.
  - Mitigacion: tests de integracion backend por modo y dataset controlado.

## Plan de implementacion por tareas (TDD, pasos pequenos)

### Task 1: Utilidades de bandas de score

**Files:**
- Create: `frontend/src/modules/recommendations/scoreBands.ts`
- Test: `frontend/tests/recommendations-score-bands.test.ts`

**Step 1: Write the failing test**

```ts
import assert from "node:assert/strict";
import test from "node:test";
import { getScoreBand } from "../src/modules/recommendations/scoreBands";

test("getScoreBand maps score ranges", () => {
  assert.equal(getScoreBand(75), "high");
  assert.equal(getScoreBand(55), "midHigh");
  assert.equal(getScoreBand(40), "midLow");
  assert.equal(getScoreBand(20), "low");
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- frontend/tests/recommendations-score-bands.test.ts`
Expected: FAIL (`Cannot find module .../scoreBands`)

**Step 3: Write minimal implementation**

Implement `getScoreBand` + classes de estilo asociadas.

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- frontend/tests/recommendations-score-bands.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/modules/recommendations/scoreBands.ts frontend/tests/recommendations-score-bands.test.ts
git commit -m "feat(recommendations): add IA score band helpers"
```

### Task 2: Explainers de ranking por tarjeta

**Files:**
- Create: `frontend/src/modules/recommendations/rankingExplainers.ts`
- Test: `frontend/tests/recommendations-ranking-explainers.test.ts`

**Step 1: Write the failing test**

Probar que devuelve bullets positivos/negativos segun precio vs media, tendencia y clima.

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- frontend/tests/recommendations-ranking-explainers.test.ts`
Expected: FAIL

**Step 3: Write minimal implementation**

Crear generador de razones corto, deterministico y localizable por clave.

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- frontend/tests/recommendations-ranking-explainers.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/modules/recommendations/rankingExplainers.ts frontend/tests/recommendations-ranking-explainers.test.ts
git commit -m "feat(recommendations): add ranking explainers"
```

### Task 3: Impacto dinamico de sliders

**Files:**
- Create: `frontend/src/modules/recommendations/weightImpact.ts`
- Test: `frontend/tests/recommendations-weight-impact.test.ts`

**Step 1: Write the failing test**

Validar deltas de peso y copy comparativo (`precio 60% mas que clima`).

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- frontend/tests/recommendations-weight-impact.test.ts`
Expected: FAIL

**Step 3: Write minimal implementation**

Implementar calculos de impacto por peso actual vs baseline.

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- frontend/tests/recommendations-weight-impact.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/modules/recommendations/weightImpact.ts frontend/tests/recommendations-weight-impact.test.ts
git commit -m "feat(recommendations): add dynamic slider impact model"
```

### Task 4: Refactor UI a layout 3 niveles + panel colapsable

**Files:**
- Modify: `frontend/src/modules/recommendations/RecommendationsExplorer.tsx`
- Modify: `frontend/src/styles/globals.css`

**Step 1: Write the failing test**

Agregar test de render semantico (si existe harness) o test de utilidades de estado del panel.

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL por nuevos estados no implementados.

**Step 3: Write minimal implementation**

Introducir:
- top bar compacta,
- panel colapsable,
- foco visual en resultados,
- CTA principal ancho completo.

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/modules/recommendations/RecommendationsExplorer.tsx frontend/src/styles/globals.css
git commit -m "feat(recommendations): add 3-level layout with collapsible config panel"
```

### Task 5: Tarjetas por capas + score dominante + transparencia ranking

**Files:**
- Modify: `frontend/src/modules/recommendations/RecommendationsExplorer.tsx`
- Modify: `frontend/src/styles/globals.css`

**Step 1: Write the failing test**

Tests de helpers para estado expandido por tarjeta y mapeo de etiquetas inteligentes.

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL

**Step 3: Write minimal implementation**

Implementar:
- summary vs details,
- score grande con color por banda,
- bloque `Por que esta arriba`.

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/modules/recommendations/RecommendationsExplorer.tsx frontend/src/styles/globals.css
git commit -m "feat(recommendations): redesign cards with layered info and score prominence"
```

### Task 6: Copy ES/EN y mensajes IA fallback enriquecidos

**Files:**
- Modify: `frontend/src/i18n/domains/recommendations.ts`

**Step 1: Write the failing test**

Agregar test de copy minimo para nuevas claves criticas.

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL por claves faltantes.

**Step 3: Write minimal implementation**

Agregar claves para:
- modo explorar/optimizar,
- fallback explicativo,
- CTA `Actualizar radar inteligente`,
- etiquetas de estado.

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/i18n/domains/recommendations.ts
git commit -m "feat(i18n): expand recommendations copy for hierarchy refresh"
```

### Task 7: Semantica backend strict/flexible

**Files:**
- Modify: `backend/app/api/v1/recommendations.py`
- Modify: `backend/app/domain/schemas.py`
- Test: `backend/tests/integration/test_recommendations_filter_modes.py`

**Step 1: Write the failing test**

Caso A: modo estricto excluye item por filtro.
Caso B: modo flexible conserva item pero penaliza score.

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/integration/test_recommendations_filter_modes.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Aplicar rama de comportamiento segun `strict_filters` y `soft_filters_weight`.

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/integration/test_recommendations_filter_modes.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/v1/recommendations.py backend/app/domain/schemas.py backend/tests/integration/test_recommendations_filter_modes.py
git commit -m "feat(recommendations-api): implement strict vs flexible filter behavior"
```

### Task 8: QA final y smoke manual cross-device

**Files:**
- Modify: `docs/qa/watchlist-history-fusion-pr-checklist.md` (opcional, o nuevo checklist de recomendaciones)
- Create: `docs/qa/recommendations-hierarchy-refresh-checklist.md`

**Step 1: Write the failing test**

No aplica unitario; preparar checklist QA reproducible.

**Step 2: Run verification**

- `cd frontend && npm run lint`
- `cd frontend && npm test`
- `cd backend && pytest -q`

Expected: PASS y sin regresiones en rutas privadas.

**Step 3: Commit**

```bash
git add docs/qa/recommendations-hierarchy-refresh-checklist.md
git commit -m "docs(qa): add recommendations hierarchy refresh checklist"
```

## Entregables finales

1. UX de `/recomendaciones` claramente jerarquizada.
2. Plano de informacion por capas (scan first, deep dive later).
3. Transparencia del ranking IA/heuristico.
4. Semantica de filtros corregida end-to-end.
5. Suite minima de pruebas para utilidades nuevas y modo de filtros backend.
