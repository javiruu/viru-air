# DESIGN.md — Viru Tracker (Dirección de Diseño)

**Estado:** Vivo
**Última revisión:** 2026-05-18
**Área:** Diseño (UI/UX)

## 1) Principios de marca y tono
- **No es SaaS genérico:** Viru Tracker es un producto aeronáutico sofisticado, no un dashboard genérico.
- **Dirección dual:**
  - **Dark mode:** Aviation Dark-Luxe / Cinematic Flight Intelligence.
  - **Light mode:** contraparte diurna y luminosa de la misma identidad, sin caer en look SaaS blanco genérico.
- **Personalidad compartida en ambos modos:** cues aeronáuticos (IATA, rutas, terminales, radar), jerarquía editorial, ritmo visual y acentos semánticos coherentes.
- **Mejoras incrementales:** priorizar iteraciones progresivas sobre rediseños amplios.

## 2) Paleta y tokens canónicos
**Paleta de referencia dual:**
- **Dark canvas:** `#121212`
- **Light canvas:** `#FFFFFF`
- **Dark panels:** `#1E1E1E` / `#242424`
- **Light panels:** `#F5F5F5` / `#FAFAFA` / `#F0F0F0`
- **Dark text:** `#F5EAD6`
- **Light text:** `#121212`
- **Acentos compartidos:** `#FFB000`, `#10B981`, `#50BFE6`, `#FF6464`

**Reglas:**
- Usar únicamente colores de la paleta aprobada.
- Evitar extremos visuales: negro puro masivo en dark y blanco plano sin jerarquía en light.
- Mantener contraste legible, semántica de estados y cues de vuelo en ambos modos.

## 3) Tipografía y microcopy
- **Titulares:** Playfair Display.
- **Subtítulos/cuerpo:** IBM Plex Sans.
- **Datos de vuelo:** monoespaciada para códigos y horarios cuando aporte claridad.
- **Lenguaje UI:** español consistente y accionable; evitar mezcla ES/EN en texto visible.

## 4) Layout, espaciamiento y composición
- Cabeceras con botón Atrás, título, subtítulo y acciones alineadas.
- Paneles y tarjetas con jerarquía clara, separación por aire y asimetría controlada cuando mejore lectura.
- Mantener una composición editorial sobria tanto en dark como en light.

## 5) Componentes congelados (UI System v1)
Patrones base (`components.css`):
`panel`, `panel-soft`, `page-header`, `panel-header`, `panel-actions`,
`panel-title`, `panel-subtitle`, `list-row`, `action-row`, `row-actions`,
`section-gap` (sm/lg/), `status-pill`, `state-success|warning|error|info`.

*Regla de extensión:* si un patrón se repite en 2+ pantallas, extraer a componente/tokens canónicos.

## 6) Estados y semántica
- `success`: éxito/completado.
- `warning`: parcial/pendiente.
- `error`: falla/validación.
- `info`: contexto neutral.

No usar `warn` en cambios nuevos.

## 7) Interacción y microanimación
- Entrada de secciones: fade + desplazamiento suave (4-8px).
- Hover de tarjetas: elevación mínima + glow tenue contextual.
- Click en botones: compresión leve (1-2px).
- Motion solo para clarificar estado y continuidad.

## 8) QA visual mínimo
Antes de cerrar cambios visuales:
- Validar flujos core (`/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/login`, `/register`).
- Revisar resoluciones desktop/tablet/móvil.
- Confirmar focus visible, sin solapes ni overflow horizontal.
- Validar estados clave (loading, empty, error, success).
- **Probar siempre ambos temas (dark y light)** y verificar que conservan la misma identidad de marca.

## 9) Límites para desarrolladores
- Cambios visuales incrementales, verificables y documentados.
- No tocar lógica de negocio, rutas o API sin aprobación explícita.
- No añadir librerías para retoques estéticos menores.

## 10) Skill de diseño incremental
- Skill: `/.codex/skills/taste-skill/SKILL.md`.
- Uso: jerarquía, ritmo, composición, motion y polish visual.
- Prioridad: `DESIGN.md` y `docs/ui/*` son contrato canónico.
