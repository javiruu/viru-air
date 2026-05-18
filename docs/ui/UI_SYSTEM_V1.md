Status: canonical  
Scope: UI system, visual contract  
Last reviewed: 2026-05-15  
Fuente de verdad: docs/ui/UI_SYSTEM_V1.md  

---  

# UI System v1 — Freeze oficial (Viru Tracker)

**Estado:** Vigente  
**Fecha de freeze:** 2026-03-09  

Este documento define los tokens y patrones visuales _congelados_ para Viru Tracker. Cualquier propuesta de cambio UI debe respetar las convenciones aquí establecidas.

## 0) Skill operativo para agentes (frontend estética)
- Skill: `/.codex/skills/taste-skill/SKILL.md` (usar para orientación estética).
- No sustituir tokens/patrones de este documento sin aprobación. El Skill sugiere mejoras (jerarquía, ritmo, motion) pero _no modifica_ los nombres ni tokens congelados aquí listados.

## 1) Tokens básicos congelados  
_Fuente: `frontend/src/styles/tokens.css`_

### Espaciados
- `--space-section-sm`, `--space-section-md`, `--space-section-lg` (tamaños de sección).
- `--space-panel-padding` (padding interno de panel).
- `--space-panel-header-gap` (gap en cabecera de panel).

### Tipografía
- `--text-meta-size` (tamaño de texto auxiliar/meta, e.g. fechas, códigos).

### Semántica de estados
- `--state-success-bg/border/text/icon` (éxito).
- `--state-warning-bg/border/text/icon` (advertencia; usamos ámbar suave).
- `--state-error-bg/border/text/icon` (error; usamos coral suave).
- `--state-info-bg/border/text/icon` (información; usamos hielo azul).

### Colores base congelados
- `--bg` (fondo base: #121212).
- `--surface` (panel principal: #1E1E1E).
- `--surface-2` (panel secundario: #242424).
- `--ink` (texto principal: #F5EAD6).
- `--accent` (acción primaria: #FFB000, luz de pista).
- `--accent-2` (acción/estado secundario: #10B981, verde radar).
- `--border` (borde sutil: #242424).
- `--shadow` (sombra ligera, e.g. rgba(0,0,0,0.6)).

## 2) Componentes base congelados  
_Fuente: `frontend/src/styles/components.css`_

- `panel`, `panel-soft` (contenedores).
- `page-header`, `panel-header`, `panel-actions`.
- `panel-title`, `panel-subtitle`.
- `list-row`, `action-row`, `row-actions`.
- `section-gap`, `section-gap-sm`, `section-gap-lg`.
- `card`, `status-pill`, `notice-compact`, `notice-actions`.
- Clases de estado aplicables: `state-success`, `state-warning`, `state-error`, `state-info`.

## 3) Reglas por capa
- `tokens.css`: definiciones semánticas (colores, spacing, estados).  
- `components.css`: patrones reutilizables, independientes de rutas.  
- `screens.css`: ajustes exclusivos de una pantalla.  
- `globals.css`: importación de las capas anteriores.  

## 4) Naming y convención
- **Tokens:** `--categoria-subcategoria-modificador` (e.g. `--state-error-border`).  
- **Estados:** `state-success|warning|error|info`; `status-pill.success|warning|error|info`.  
- **Clases de patrones:** nombres semánticos (`panel-*`, `notice-*`, `action-row`, `list-row`). No usar nombres ambiguos (`misc`, `tmp`, `box2`, etc.).  

## 5) Glosario UI (texto visible ES)
- **Términos:** Panel, Seguimiento, Búsqueda rápida, Alerta, Histórico, Comparativa, Preferencias, Ayuda, **Aeropuerto, Vuelo**.  
- **Verbos:** Buscar, Actualizar, Guardar, Eliminar, Activar/Desactivar, Reintentar.  
- **Estados breves:** Cargando…, Sin resultados, Error, Listo.  

## 6) Evolución controlada
- **Nuevos tokens:** crear _solo si_ valor repetido en 2+ módulos (espacio, color, radio, semántica).  
- **Nuevos patrones:** crear en `components.css` _solo si_ aparece en 2+ pantallas.  
- **Mantener en `screens.css`** lo exclusivo de una ruta.  
- Cualquier excepción debe documentarse en el PR (ui visual checklist).

## 7) Elementos en refactor (no congelados aún)
- Composición interna de Quick Search.  
- Overrides responsive puntuales en `screens.css`.  
- Alias legacy de rutas (`/history`, `/preferences`) aún redirigen por compatibilidad.  

## 8) Compatibilidad
- **Rutas canon:** `/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/preferencias`.  
- **Rutas legacy:** `/history`→`/preferencias`, `/suggestions`→en revisión.  
- **Naming legacy:** nunca usar `warn` en nuevos cambios (usar `warning`).
