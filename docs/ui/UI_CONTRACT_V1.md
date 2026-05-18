Status: canonical
Scope: UI system, visual contract
Last reviewed: 2026-05-18
Fuente de verdad: docs/ui/UI_CONTRACT_V1.md

---

# UI Contract v1 — Viru Tracker

> Referencia de freeze oficial: `docs/ui/UI_SYSTEM_V1.md`

## Objetivo
Reglas mínimas para mantener consistencia visual, coherencia de identidad cálida y prevenir regresiones.

## Skill de estética recomendado
- Skill: `/.codex/skills/taste-skill/SKILL.md`.
- Este contrato prevalece ante cualquier sugerencia de estilo.

## Estructura de archivos CSS
- `base.css`: base y reset.
- `tokens.css`: colores, tipografía, spacing, foco y estados.
- `components.css`: patrones reutilizables.
- `screens.css`: ajustes específicos por pantalla.

**Reglas de ubicación:**
1. Patrón en 2+ pantallas -> `components.css`.
2. Valor semántico repetido -> `tokens.css`.
3. Exclusivo de una ruta -> `screens.css`.

## Componentes clave
- **Card:** padding consistente; no más de una acción primaria por card.
- **PanelHeader:** título, subtítulo y acción clara.
- **StatusPill:** tamaño homogéneo y color semántico consistente.
- **ActionRow:** CTA principal primero, secundarios ordenados.

## Semántica de estados
Semántica única en toda la UI:
- `success`
- `warning`
- `error`
- `info`

Tokens obligatorios: `--state-success-*`, `--state-warning-*`, `--state-error-*`, `--state-info-*`.
Clases base: `.state-success`, `.state-warning`, `.state-error`, `.state-info`.

**Regla clave:** la semántica de estados es compartida entre dark y light; cambia la superficie, no el significado.

Compatibilidad legacy:
- No introducir `warn` en cambios nuevos.
- Tratar `warn` heredado como `warning` hasta limpieza total.

## Consistencia entre temas (obligatoria)
Todo componente debe mantener en **dark y light**:
- legibilidad,
- foco visible,
- jerarquía visual,
- semántica de estado,
- consistencia de interacción,
- calidez y personalidad sin ruido visual.

## Motion y microinteracción
- Motion con intención: claridad, delight, continuidad y personalidad.
- Incluir microinteracciones en hover, selección, carga, empty states y confirmaciones cuando aporten comprensión.
- Evitar animaciones mareantes, ornamentales o que afecten la usabilidad.

## Microcopy breve
1. Mensajes operativos de 1-2 frases.
2. Sin mezcla ES/EN visible.
3. Repetir términos del glosario.
4. En errores, indicar siguiente acción cuando aplique.
5. Tono cercano y humano, no infantil.

## Glosario UI (ES)
- Términos: Panel, Seguimiento, Búsqueda rápida, Alerta, Histórico, Comparativa, Preferencias, Ayuda, Vuelo, Terminal.
- Verbos: Buscar, Actualizar, Guardar, Eliminar, Activar / Desactivar, Reintentar.
- Estados: Cargando..., Sin resultados, Error, Listo.

## Convenciones legacy / Deprecación
- Rutas canónicas: `/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/recomendaciones`, `/preferencias`.
- Rutas legacy: `/history`->`/preferencias`, `/suggestions`->en revisión.
- Naming de estado: usar `warning`, no `warn`.

## Reglas de regresión (QA)
1. Todo cambio de estilos pasa build y pruebas automatizadas.
2. No introducir regresiones visuales no intencionadas.
3. Mantener compatibilidad de contraste en dark y light.
4. Focus claramente visible en elementos interactivos.
5. Evitar salida visual “dashboard serio” o “SaaS plano” como estética dominante.
