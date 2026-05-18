# DESIGN.md — Viru Tracker (Dirección de Diseño)

**Estado:** Vivo
**Última revisión:** 2026-05-18
**Área:** Diseño (UI/UX)

## 1) Definición base de identidad
- **Viru Tracker no es SaaS genérico:** es una plataforma de flight intelligence con identidad cálida, animada y aeronáutica.
- **Impresión deseada:** premium y bien diseñada, pero cercana, intuitiva y humana.
- **Dirección dual:**
  - **Dark mode:** Aviation Dark-Luxe cinematográfico, nunca lúgubre.
  - **Light mode:** contraparte luminosa con alma, nunca blanco corporativo plano.
- **Personalidad compartida en ambos modos:** cues aeronáuticos (IATA, rutas, terminales, radar), ritmo visual, acentos semánticos y microcopy vivo.
- **Mejoras incrementales:** priorizar iteraciones progresivas sobre rediseños amplios.

## 2) Principios obligatorios
1. Calidez antes que frialdad.
2. Personalidad antes que neutralidad.
3. Animación con intención, no inmovilidad.
4. Claridad sin austeridad.
5. Premium cercano, no premium distante.
6. Aeronáutico aesthetic, no corporativo de aerolínea.
7. Light mode con alma, no blanco genérico.
8. Dark mode cinematográfico, no lúgubre.
9. La interfaz debe parecer diseñada, no ensamblada.
10. Los detalles deben hacer sonreír sin estorbar.

## 3) Paleta y tokens canónicos
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

## 4) Tipografía, microcopy y composición
- **Titulares:** Playfair Display.
- **Subtítulos/cuerpo:** IBM Plex Sans.
- **Datos de vuelo:** monoespaciada para códigos y horarios cuando aporte claridad.
- **Lenguaje UI:** español consistente, accionable y cercano; evitar mezcla ES/EN en texto visible.
- **Composición:** paneles con ritmo, jerarquía clara, densidad útil y asimetría controlada cuando mejora lectura.
- **Evitar:** grids repetitivas sin ritmo y estética dominante de “dashboard serio”.

## 5) Interacción y microanimación
- Motion con intención: **claridad + delight + continuidad + personalidad**.
- Entrada de secciones: fade + desplazamiento suave (4-8px).
- Hover de tarjetas: elevación mínima + glow contextual tenue.
- Click en botones: compresión leve (1-2px).
- Añadir microinteracciones en hover, selección, carga, empty states y confirmaciones.

**Límites de motion y estilo:**
- Sin ruido visual barato.
- Sin exceso de colores.
- Sin animaciones mareantes.
- Sin estética cyberpunk, “Awwwards” poco usable o clon corporativo.

## 6) Componentes congelados (UI System v1)
Patrones base (`components.css`):
`panel`, `panel-soft`, `page-header`, `panel-header`, `panel-actions`,
`panel-title`, `panel-subtitle`, `list-row`, `action-row`, `row-actions`,
`section-gap` (sm/lg), `status-pill`, `state-success|warning|error|info`.

*Regla de extensión:* si un patrón se repite en 2+ pantallas, extraer a componente/tokens canónicos.

## 7) Estados y semántica
- `success`: éxito/completado.
- `warning`: parcial/pendiente.
- `error`: falla/validación.
- `info`: contexto neutral.

No usar `warn` en cambios nuevos.

## 8) QA visual mínimo
Antes de cerrar cambios visuales:
- Validar flujos core (`/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/login`, `/register`).
- Revisar resoluciones desktop/tablet/móvil.
- Confirmar focus visible, sin solapes ni overflow horizontal.
- Validar estados clave (loading, empty, error, success) con personalidad y claridad.
- Probar siempre ambos temas (dark y light) y verificar que conservan la misma identidad de marca.

## 9) Límites para desarrolladores
- Cambios visuales incrementales, verificables y documentados.
- No tocar lógica de negocio, rutas o API sin aprobación explícita.
- No añadir librerías para retoques estéticos menores.

## 10) Skill de diseño incremental
- Skill: `/.codex/skills/taste-skill/SKILL.md`.
- Uso: jerarquía, ritmo, composición, motion y polish visual.
- Prioridad: `DESIGN.md` y `docs/ui/*` son contrato canónico.
