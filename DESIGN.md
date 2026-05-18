# DESIGN.md - Viru Tracker (Direccion de Diseno)

**Estado:** Vivo
**Ultima revision:** 2026-05-18
**Area:** Diseno (UI/UX)

## 1) Definicion base de identidad
- **Viru Tracker no es SaaS generico:** es una plataforma de flight intelligence con identidad calida, animada y aeronautica.
- **Impresion deseada:** premium y bien disenada, pero cercana, intuitiva y humana.
- **Direccion dual:**
  - **Dark mode:** Aviation Dark-Luxe cinematografico, nunca lugubre.
  - **Light mode:** contraparte luminosa con alma, nunca blanco corporativo plano.
- **Personalidad compartida en ambos modos:** cues aeronauticos (IATA, rutas, terminales, radar), ritmo visual, acentos semanticos y microcopy vivo.
- **Mejoras incrementales:** priorizar iteraciones progresivas sobre redisenos amplios.

## 2) Principios obligatorios
1. Calidez antes que frialdad.
2. Personalidad antes que neutralidad.
3. Animacion con intencion, no inmovilidad.
4. Claridad sin austeridad.
5. Premium cercano, no premium distante.
6. Aeronautico aesthetic, no corporativo de aerolinea.
7. Light mode con alma, no blanco generico.
8. Dark mode cinematografico, no lugubre.
9. La interfaz debe parecer disenada, viva y cuidada, no ensamblada.
10. Los detalles deben hacer sonreir sin estorbar.

## 2.1) Anti-interpretaciones (bloqueante para agentes)
- No interpretar "claridad" como austeridad visual.
- No interpretar "premium" como distancia emocional.
- No interpretar "orden" como composicion sobria o apagada.
- No interpretar "funcional" como dashboard corporativo frio.
- No interpretar "minimal" como ausencia de personalidad.

## 3) Paleta y tokens canonicos
**Paleta de referencia dual:**
- **Dark canvas:** `#121212`
- **Light canvas:** `#FFFFFF`
- **Dark panels:** `#1E1E1E` / `#242424`
- **Light panels:** `#F5F5F5` / `#FAFAFA` / `#F0F0F0`
- **Dark text:** `#F5EAD6`
- **Light text:** `#121212`
- **Acentos compartidos:** `#FFB000`, `#10B981`, `#50BFE6`, `#FF6464`

**Reglas:**
- Usar unicamente colores de la paleta aprobada.
- Evitar extremos visuales: negro puro masivo en dark y blanco plano sin jerarquia en light.
- Mantener contraste legible, semantica de estados y cues de vuelo en ambos modos.

## 4) Tipografia, microcopy y composicion
- **Titulares:** Playfair Display.
- **Subtitulos/cuerpo:** IBM Plex Sans.
- **Datos de vuelo:** monoespaciada para codigos y horarios cuando aporte claridad.
- **Lenguaje UI:** espanol consistente, accionable y cercano; evitar mezcla ES/EN en texto visible.
- **Composicion:** paneles con ritmo, jerarquia clara, densidad util y asimetria controlada cuando mejora lectura. Debe sentirse cabina viva, no maqueta editorial contenida.
- **Evitar:** grids repetitivas sin ritmo y estetica dominante de "dashboard serio".

## 5) Interaccion y microanimacion
- Motion con intencion: **claridad + delight + continuidad + personalidad**.
- Entrada de secciones: fade + desplazamiento suave (4-8px).
- Hover de tarjetas: elevacion minima + glow contextual tenue.
- Click en botones: compresion leve (1-2px).
- Anadir microinteracciones en hover, seleccion, carga, empty states y confirmaciones.
- Cada estado importante debe incluir senal de acompanamiento (copy/feedback) para transmitir mimo de producto.

**Limites de motion y estilo:**
- Sin ruido visual barato.
- Sin exceso de colores.
- Sin animaciones mareantes.
- Sin estetica cyberpunk, "Awwwards" poco usable o clon corporativo.
- Sin tono sobrio/frio como resultado dominante.

## 6) Componentes congelados (UI System v1)
Patrones base (`components.css`):
`panel`, `panel-soft`, `page-header`, `panel-header`, `panel-actions`,
`panel-title`, `panel-subtitle`, `list-row`, `action-row`, `row-actions`,
`section-gap` (sm/lg), `status-pill`, `state-success|warning|error|info`.

*Regla de extension:* si un patron se repite en 2+ pantallas, extraer a componente/tokens canonicos.

## 7) Estados y semantica
- `success`: exito/completado.
- `warning`: parcial/pendiente.
- `error`: falla/validacion.
- `info`: contexto neutral.

No usar `warn` en cambios nuevos.

## 8) QA visual minimo
Antes de cerrar cambios visuales:
- Validar flujos core (`/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/login`, `/register`).
- Revisar resoluciones desktop/tablet/movil.
- Confirmar focus visible, sin solapes ni overflow horizontal.
- Validar estados clave (loading, empty, error, success) con personalidad y claridad.
- Probar siempre ambos temas (dark y light) y verificar que conservan la misma identidad de marca.

## 9) Limites para desarrolladores
- Cambios visuales incrementales, verificables y documentados.
- No tocar logica de negocio, rutas o API sin aprobacion explicita.
- No anadir librerias para retoques esteticos menores.

## 10) Skill de diseno incremental
- Skill: `/.codex/skills/taste-skill/SKILL.md`.
- Uso: jerarquia, ritmo, composicion, motion y polish visual.
- Prioridad: `DESIGN.md` y `docs/ui/*` son contrato canonico.
