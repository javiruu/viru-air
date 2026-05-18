Status: canonical
Scope: UI system, visual contract
Last reviewed: 2026-05-18
Fuente de verdad: docs/ui/UI_SYSTEM_V1.md

---

# UI System v1 - Freeze oficial (Viru Tracker)

**Estado:** Vigente
**Fecha de freeze:** 2026-03-09

Este documento define los tokens y patrones visuales congelados. Cualquier cambio UI debe respetar este freeze.

## 0) Skill operativo para agentes (frontend estetica)
- Skill: `/.codex/skills/taste-skill/SKILL.md`.
- El skill guia criterio visual, pero no autoriza romper naming/tokens congelados.

## 1) Principio de intencion visual (sin cambiar freeze)
- La identidad objetivo es calida, animada, cercana y aeronautica.
- El freeze tecnico se mantiene: este documento no habilita cambios de API, rutas o logica.
- Dark + light comparten personalidad; cambia luminancia, no identidad.
- Regla de interpretacion: mantener estructura no significa producir una interfaz sobria o fria.

## 2) Tokens basicos congelados
_Fuente: `frontend/src/styles/tokens.css`_

### Espaciados
- `--space-section-sm`, `--space-section-md`, `--space-section-lg`
- `--space-panel-padding`
- `--space-panel-header-gap`

### Tipografia
- `--text-meta-size`

### Semantica de estados
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

### Valores de referencia para tema dual (documentacion visual)
Estos valores alinean la guia dark/light, pero **no se declaran aqui como tokens nuevos congelados**:
- Dark canvas: `#121212`
- Light canvas: `#FFFFFF`
- Dark panels: `#1E1E1E` / `#242424`
- Light panels: `#F5F5F5` / `#FAFAFA` / `#F0F0F0`
- Dark text: `#F5EAD6`
- Light text: `#121212`
- Shared accents: `#FFB000`, `#10B981`, `#50BFE6`, `#FF6464`

## 3) Componentes base congelados
_Fuente: `frontend/src/styles/components.css`_

- `panel`, `panel-soft`
- `page-header`, `panel-header`, `panel-actions`
- `panel-title`, `panel-subtitle`
- `list-row`, `action-row`, `row-actions`
- `section-gap`, `section-gap-sm`, `section-gap-lg`
- `card`, `status-pill`, `notice-compact`, `notice-actions`
- `state-success|state-warning|state-error|state-info`

## 4) Reglas por capa
- `tokens.css`: valores semanticos reutilizables.
- `components.css`: patrones compartidos entre pantallas.
- `screens.css`: ajustes exclusivos por ruta.
- `globals.css`: composicion de capas.

## 5) Naming y convencion
- Tokens: `--categoria-subcategoria-modificador`.
- Estados: `success|warning|error|info`.
- Patrones: nombres semanticos; evitar nombres ambiguos.

## 6) Glosario UI (ES visible)
- Terminos: Panel, Seguimiento, Busqueda rapida, Alerta, Historico, Comparativa, Preferencias, Ayuda, Aeropuerto, Vuelo.
- Verbos: Buscar, Actualizar, Guardar, Eliminar, Activar/Desactivar, Reintentar.
- Estados breves: Cargando..., Sin resultados, Error, Listo.

## 7) Evolucion controlada
- Crear token nuevo solo si el valor se repite en 2+ modulos o representa semantica estable.
- Crear patron en `components.css` solo si aparece en 2+ pantallas.
- Mantener en `screens.css` lo exclusivo por ruta.
- Documentar excepciones en PR.

## 8) Elementos en refactor (no congelados aun)
- Composicion interna de Quick Search.
- Overrides responsive puntuales en `screens.css`.
- Alias legacy (`/history`, `/preferences`) por compatibilidad.

## 9) Compatibilidad
- Rutas canon: `/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/preferencias`.
- Rutas legacy: `/history`->`/preferencias`, `/suggestions`->en revision.
- No reintroducir `warn`; usar `warning`.
