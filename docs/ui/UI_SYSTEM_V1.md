Status: canonical
Scope: UI system, visual contract, or design guidance
Last reviewed: 2026-04-15
Canonical source: docs/ui/UI_SYSTEM_V1.md
Related: docs/ui/UI_SYSTEM_V1.md, docs/specs/README.md

---
# UI System v1 — Freeze oficial (Viru-Tracker)

Estado: **Vigente**
Fecha de freeze: 2026-03-09

Este documento es la referencia oficial para evitar deriva del sistema visual.

## 1) Tokens congelados (canon)
Fuente: `frontend/src/styles/tokens.css`

### Spacing y layout base
- `--space-section-sm`
- `--space-section-md`
- `--space-section-lg`
- `--space-panel-padding`
- `--space-panel-header-gap`

### Tipografía auxiliar
- `--text-meta-size`

### Tokens de estado (semántica)
- `--state-success-bg|border|text|icon`
- `--state-warning-bg|border|text|icon`
- `--state-error-bg|border|text|icon`
- `--state-info-bg|border|text|icon`

### Tokens de apoyo dashboard (congelados v1)
- `--dashboard-section-gap`
- `--dashboard-block-gap`
- `--dashboard-muted-size`
- `--dashboard-muted-tone`

## 2) Componentes/patrones base congelados
Fuente: `frontend/src/styles/components.css`

- `panel`, `panel-soft`
- `panel-title`, `panel-subtitle`, `panel-note`
- `page-header`
- `panel-header`, `panel-actions`
- `list-row`
- `action-row`, `row-actions`
- `section-gap`, `section-gap-sm`, `section-gap-lg`
- `notice-compact`, `notice-actions`
- `card`
- `status-pill` (`success|warning|error|info`)
- `state-success|warning|error|info`

## 3) Reglas congeladas por capa
- `tokens.css`: semántica reutilizable (colores, spacing, estados, jerarquías base).
- `components.css`: patrones reutilizables, no dependientes de una ruta concreta.
- `screens.css`: solo reglas de pantalla (layout/orden/overrides específicos).
- `globals.css`: agregación de capas.

## 4) Naming congelado
### Tokens
- `--categoria-subcategoria-modificador`
- Ejemplo: `--state-error-border`

### Clases de estado
- `state-success|warning|error|info`
- `status-pill success|warning|error|info`

### Patrones
- nombres semánticos (`panel-*`, `notice-*`, `action-row`, `list-row`)
- prohibidos nombres ambiguos (`misc`, `tmp`, `box2`, `wrapFix`, etc.)

## 5) Glosario UI congelado (ES visible)
Términos:
- Panel, Seguimiento, Búsqueda rápida, Alerta, Histórico, Comparativa, Preferencias, Ayuda

Verbos:
- Buscar, Actualizar, Guardar, Eliminar, Activar/Desactivar, Reintentar

Estados breves:
- Cargando…, Sin resultados, Error, Listo

## 6) Evolución controlada (cómo extender sin degradar)
Crear token nuevo **solo si**:
1) el valor se repite en 2+ módulos, o
2) representa semántica estable (estado, jerarquía, spacing de sistema).

Crear patrón en `components.css` **solo si**:
1) aparece en 2+ pantallas, y
2) no depende del orden/layout de una ruta específica.

Mantener en `screens.css` **solo si**:
1) el comportamiento es exclusivo de una pantalla, o
2) la abstracción generaría acoplamiento artificial.

Toda excepción debe documentarse en PR (sección UI visual checklist).

## 7) Elementos no congelados aún (deliberado)
- `quick-search` a nivel de composición interna (sigue en refactor progresivo).
- ciertos overrides responsive puntuales en `screens.css` pendientes de consolidación.
- alias legacy de rutas (`/history`, `/preferences`) se mantienen por compatibilidad.

## 8) Compatibilidad y deprecación
- Rutas canónicas: `/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/preferencias`.
- Puentes compatibles: `/history`, `/preferences` (redirigen a canónicas).
- Evitar reintroducir `warn` como naming activo; usar `warning`.





