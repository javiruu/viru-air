# DESIGN.md — Viru Tracker

Estado: vivo
Fuente de verdad: si
Ultima revision: 2026-05-14
Area: diseno/agentes

## 1) Principios de marca y tono
- Viru Tracker no es un dashboard SaaS generico.
- La interfaz debe sentirse clara, controlada, sobria, editorial y cercana.
- Mantener jerarquia fuerte, ritmo visual y densidad util.
- Priorizar mejoras incrementales sobre redisenos amplios.

## 2) Paleta y tokens canonicos
Base semantica (alineada a docs/ui/estetica.md y frontend tokens):
- `--bg`: base del lienzo.
- `--surface`: panel principal.
- `--surface-2`: subpanel/tarjeta secundaria.
- `--ink`: texto principal.
- `--accent`: accion principal.
- `--accent-2`: accion/estado secundario.
- `--border`: linea sutil.
- `--shadow`: profundidad suave.

Reglas:
- No introducir colores fuera de paleta base.
- Evitar fondos saturados y sombras agresivas.
- Mantener coherencia dark/light con contraste legible.

## 3) Tipografia y microcopy
- Titulares: Playfair Display.
- Subtitulos y cuerpo UI: IBM Plex Sans.
- Mantener glosario UI en espanol (Panel, Seguimiento, Busqueda rapida, Alerta, Historico, Comparativa, Preferencias, Ayuda).
- Mensajes breves y accionables; evitar mezcla ES/EN en UI visible.

## 4) Layout, spacing y composicion
- Cabeceras con boton Atras, titulo, subtitulo y acciones alineadas.
- Paneles con borde fino, radio consistente y sombra suave.
- Separacion por aire antes que divisores duros.
- Preservar asimetria controlada cuando mejore la lectura.

## 5) Componentes y patrones congelados
Patrones base (UI system v1):
- `panel`, `panel-soft`, `page-header`, `panel-header`, `panel-actions`
- `panel-title`, `panel-subtitle`, `list-row`, `action-row`, `row-actions`
- `section-gap`, `section-gap-sm`, `section-gap-lg`
- `status-pill` + clases de estado `success|warning|error|info`
- `state-success|state-warning|state-error|state-info`

Regla de extension:
- Si un patron se repite en 2+ pantallas, llevarlo a componentes/tokens canonicos.

## 6) Estados y semantica
Semantica unica permitida:
- `success`: accion confirmada/completada.
- `warning`: estado parcial, pausa o pendiente.
- `error`: fallo o validacion.
- `info`: mensaje neutral/contextual.

No usar naming legacy `warn` en cambios nuevos.

## 7) Interaccion y microanimacion
- Entrada de bloques: fade + desplazamiento suave (4-8px).
- Cambios de filtro: 80-120ms.
- Hover de tarjeta: elevacion minima (1px) + glow tenue.
- Press de boton: compresion 1-2px.
- Motion solo para clarificar estado o continuidad, nunca decorativo excesivo.

## 8) QA visual minimo
Antes de cerrar cambios UI:
- Validar rutas core: `/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/login`, `/register`.
- Verificar desktop/tablet/mobile (`1440x900`, `768x1024`, `375x812`, `320x780`).
- Confirmar: sin scroll horizontal accidental, sin solapes, focus visible, CTA principal claro.
- Validar estados clave: loading, empty, error, success cuando aplique.

## 9) Limites de implementacion para agentes
- Realizar cambios incrementales y verificables.
- No cambiar logica de negocio, contratos API ni rutas sin peticion explicita.
- No introducir librerias nuevas para ajustes visuales menores.
- Mantener consistencia con `AGENTS.md`, `frontend/AGENTS.md` y docs UI canonicos.

## 10) Skill de ejecucion visual recomendado
- Skill instalado: `/.codex/skills/taste-skill/SKILL.md`.
- Uso esperado: decisiones de frontend estetica (jerarquia, ritmo, composicion, motion y polish).
- Regla de prioridad: este documento y `docs/ui/*` siguen siendo el contrato canonico.
