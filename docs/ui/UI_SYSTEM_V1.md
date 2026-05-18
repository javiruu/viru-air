Status: canonical
Scope: UI system, visual contract
Last reviewed: 2026-05-18
Fuente de verdad: docs/ui/UI_SYSTEM_V1.md

---

# UI System v1 — Freeze oficial (Viru Tracker)

**Estado:** Vigente
**Fecha de freeze:** 2026-03-09

Este documento define los tokens y patrones visuales congelados. Cualquier cambio UI debe respetar este freeze.

## 0) Skill operativo para agentes (frontend estética)
- Skill: `/.codex/skills/taste-skill/SKILL.md`.
- El skill guía criterio visual, pero no autoriza romper naming/tokens congelados.

## 1) Tokens básicos congelados
_Fuente: `frontend/src/styles/tokens.css`_

### Espaciados
- `--space-section-sm`, `--space-section-md`, `--space-section-lg`
- `--space-panel-padding`
- `--space-panel-header-gap`

### Tipografía
- `--text-meta-size`

### Semántica de estados
- `--state-success-bg|border|text|icon`
- `--state-warning-bg|border|text|icon`
- `--state-error-bg|border|text|icon`
- `--state-info-bg|border|text|icon`

### Colores base congelados (tokens reales)
- `--bg`
- `--surface`
- `--surface-2`
- `--ink`
- `--accent`
- `--accent-2`
- `--border`
- `--shadow`

### Valores de referencia para tema dual (documentación visual)
Estos valores alinean la guía dark/light, pero **no se declaran aquí como tokens nuevos congelados**:
- Dark canvas: `#121212`
- Light canvas: `#FFFFFF`
- Dark panels: `#1E1E1E` / `#242424`
- Light panels: `#F5F5F5` / `#FAFAFA` / `#F0F0F0`
- Dark text: `#F5EAD6`
- Light text: `#121212`
- Shared accents: `#FFB000`, `#10B981`, `#50BFE6`, `#FF6464`

## 2) Componentes base congelados
_Fuente: `frontend/src/styles/components.css`_

- `panel`, `panel-soft`
- `page-header`, `panel-header`, `panel-actions`
- `panel-title`, `panel-subtitle`
- `list-row`, `action-row`, `row-actions`
- `section-gap`, `section-gap-sm`, `section-gap-lg`
- `card`, `status-pill`, `notice-compact`, `notice-actions`
- `state-success|state-warning|state-error|state-info`

## 3) Reglas por capa
- `tokens.css`: valores semánticos reutilizables.
- `components.css`: patrones compartidos entre pantallas.
- `screens.css`: ajustes exclusivos por ruta.
- `globals.css`: composición de capas.

## 4) Naming y convención
- Tokens: `--categoria-subcategoria-modificador`.
- Estados: `success|warning|error|info`.
- Patrones: nombres semánticos; evitar nombres ambiguos.

## 5) Glosario UI (ES visible)
- Términos: Panel, Seguimiento, Búsqueda rápida, Alerta, Histórico, Comparativa, Preferencias, Ayuda, Aeropuerto, Vuelo.
- Verbos: Buscar, Actualizar, Guardar, Eliminar, Activar/Desactivar, Reintentar.
- Estados breves: Cargando…, Sin resultados, Error, Listo.

## 6) Evolución controlada
- Crear token nuevo solo si el valor se repite en 2+ módulos o representa semántica estable.
- Crear patrón en `components.css` solo si aparece en 2+ pantallas.
- Mantener en `screens.css` lo exclusivo por ruta.
- Documentar excepciones en PR.

## 7) Elementos en refactor (no congelados aún)
- Composición interna de Quick Search.
- Overrides responsive puntuales en `screens.css`.
- Alias legacy (`/history`, `/preferences`) por compatibilidad.

## 8) Compatibilidad
- Rutas canon: `/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/preferencias`.
- Rutas legacy: `/history`→`/preferencias`, `/suggestions`→en revisión.
- No reintroducir `warn`; usar `warning`.
