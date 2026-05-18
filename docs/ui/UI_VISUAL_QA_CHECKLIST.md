Status: canonical
Scope: UI system, visual contract, or design guidance
Last reviewed: 2026-05-18
Canonical source: docs/ui/UI_VISUAL_QA_CHECKLIST.md
Related: docs/ui/UI_SYSTEM_V1.md, docs/specs/README.md

---
# UI Visual QA Checklist (Core Routes)

Checklist obligatorio para PRs con cambios de interfaz.

Referencia operativa para agentes:
- `/.codex/skills/taste-skill/SKILL.md` para direccion visual.
- Este checklist manda para validar salida final.

## Rutas core
- `/dashboard`
- `/watchlist`
- `/quick-search`
- `/alerts`
- `/login`
- `/register`

Rutas recomendadas adicionales:
- `/ayuda`
- `/policies`

## Resoluciones minimas
- Desktop estandar: `1440x900`
- Tablet: `768x1024`
- Mobile: `375x812`
- Mobile compacto: `320x780`

## Verificaciones transversales (todas las rutas)
- [ ] Jerarquia visual clara (titulo, contenido, acciones)
- [ ] Spacing y alineacion consistentes
- [ ] CTA principal visible y sin competir con secundarios
- [ ] Focus visible en botones/inputs/enlaces
- [ ] Sin scroll horizontal no intencional
- [ ] Sin solapes de componentes en mobile
- [ ] Contraste aceptable en dark/light
- [ ] Microinteracciones suaves y utiles en elementos interactivos clave
- [ ] Microcopy cercano, vivo y con tono humano
- [ ] La pantalla no transmite tono sobrio/frio/corporativo como resultado dominante

## Estados minimos por pantalla

### /dashboard
- [ ] Estado normal con datos
- [ ] Estado con notice/banner
- [ ] Estado minimo (sin actividad/sin oportunidades)

### /watchlist
- [ ] Lista con vuelos
- [ ] Estado vacio
- [ ] Estado de actualizacion visible (feedback de accion)

### /quick-search
- [ ] Loading
- [ ] Empty (sin resultados)
- [ ] Error
- [ ] Resultados presentes con acciones visibles

### /alerts
- [ ] Lista con alertas
- [ ] Sin alertas
- [ ] Toggle activar/pausar
- [ ] Historial legible

### /login y /register
- [ ] Formulario normal
- [ ] Error de validacion visible cerca del campo
- [ ] Feedback de error general claro

### /ayuda y /policies (recomendado)
- [ ] Legibilidad de bloques de texto
- [ ] Indice/estructura visible
- [ ] No roturas de maquetacion en mobile

## Evidencia minima en PR
- [ ] Capturas desktop de rutas core
- [ ] Capturas mobile 375 de rutas privadas core
- [ ] Capturas mobile 320 de rutas privadas core
- [ ] Build frontend OK

Ruta de snapshots sugerida:
- `docs/qa/snapshots/`
