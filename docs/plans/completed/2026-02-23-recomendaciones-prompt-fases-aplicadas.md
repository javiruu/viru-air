# Recomendaciones Prompt - Aplicacion Fase por Fase

Fecha: 2026-02-23
Ruta objetivo: `/recomendaciones`
Prompt fuente: `prompts/prompt recomendaciones.txt`

## Skills aplicadas
- `brainstorming`: cierre de alcance y decisiones previas de diseno.
- `writing-plans`: ejecucion por fases con foco en entregables verificables.
- `ui-design`: refinado visual premium, jerarquia y microinteracciones.

## Fase 1 - Estructura (claridad + ritmo visual)
Estado: Aplicada

Cambios implementados:
- Header ultra limpio con titulo, subtitulo y selector `Descubrir/Optimizar`.
- Linea horizontal de estado con `Origen | Destino | Fecha | Sistema`.
- Macro layout en 2 columnas con asimetria 30/70 (panel tecnico + resultados protagonistas).
- Panel izquierdo colapsable para reducir ruido visual.
- CTA unico y sticky: `Actualizar radar inteligente`.

Archivos:
- `frontend/src/modules/recommendations/RecommendationsExplorer.tsx`
- `frontend/src/styles/globals.css`

## Fase 2 - Tarjetas pro (score hero + profundidad)
Estado: Aplicada

Cambios implementados:
- Tarjetas con tension horizontal: bloque principal + score box premium.
- Score IA dominante (tamano grande, estilo encapsulado, color por banda).
- Microconfianza bajo score: `Top {percent}% de oportunidades hoy`.
- Tooltip en score: explicacion de senales de calculo.
- Insight `Top por` truncado para lectura rapida.

Archivos:
- `frontend/src/modules/recommendations/RecommendationsExplorer.tsx`
- `frontend/src/styles/globals.css`
- `frontend/src/modules/recommendations/scoreBands.ts`

## Fase 3 - Claridad cognitiva
Estado: Aplicada

Cambios implementados:
- Capas de informacion por tarjeta:
  - Nivel 1 siempre visible (ruta, precio, score, etiqueta, insight).
  - Nivel 2 expandible (distancia, media historica, clima, tags, razon IA).
- Contraste visual intencional:
  - resultados mas luminosos,
  - panel tecnico mas sobrio,
  - fondo neutral con maximo tres niveles.
- Sliders refinados (track fino + thumb compacto) y feedback inmediato.

Archivos:
- `frontend/src/modules/recommendations/RecommendationsExplorer.tsx`
- `frontend/src/styles/globals.css`

## Fase 4 - Conversion invisible
Estado: Aplicada

Cambios implementados:
- CTA unico con presencia controlada (ancho completo, hover, sombra ligera).
- Microcopy final definido: `Actualizar radar inteligente`.
- Flujo de carga claro: `Analizando senales...`.

Archivos:
- `frontend/src/modules/recommendations/RecommendationsExplorer.tsx`
- `frontend/src/i18n/domains/recommendations.ts`

## Fase 5 - Sensacion de IA potente
Estado: Aplicada

Cambios implementados:
- Reordenamiento vivo de resultados segun pesos (feedback inmediato local).
- Animacion de entrada y score count-up suave (respeta reduced motion).
- Bloque fallback IA mejorado:
  - que esta pasando,
  - modo heuristico,
  - senales activas.
- Transparencia por tarjeta con `Por que esta arriba`.

Archivos:
- `frontend/src/modules/recommendations/RecommendationsExplorer.tsx`
- `frontend/src/modules/recommendations/rankingExplainers.ts`
- `frontend/src/modules/recommendations/weightImpact.ts`
- `frontend/src/i18n/domains/recommendations.ts`

## Fase 6 - Validacion anti-feo
Estado: Aplicada y validada

Checklist final:
- [x] Layout 2 columnas con contraste real.
- [x] Score visualmente dominante.
- [x] Tarjetas como foco principal con sombra destacada.
- [x] Maximo 3 niveles de fondo.
- [x] Espaciado generoso entre secciones.
- [x] CTA unico.
- [x] Sliders finos y elegantes.
- [x] Sin apariencia de documento plano.

## Validacion tecnica
Frontend:
- `npm run lint -- --file src/modules/recommendations/RecommendationsExplorer.tsx --file src/i18n/domains/recommendations.ts`
- `npm test -- tests/recommendations-score-bands.test.ts tests/recommendations-ranking-explainers.test.ts tests/recommendations-weight-impact.test.ts`

Backend:
- `python -m pytest tests/integration/test_recommendations_filter_modes.py -q`

Resultado:
- Lint OK.
- Tests de recomendaciones frontend OK.
- Test de filtros strict/flexible backend OK.
