Status: canonical
Scope: UI system, visual contract, or design guidance
Last reviewed: 2026-04-15
Canonical source: docs/ui/UI_VISUAL_QA_CHECKLIST.md
Related: docs/ui/UI_SYSTEM_V1.md, docs/specs/README.md

---
# UI Visual QA Checklist (Core Routes)

Checklist obligatorio para PRs con cambios de interfaz.

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

## Resoluciones mínimas
- Desktop estándar: `1440x900`
- Tablet: `768x1024`
- Mobile: `375x812`
- Mobile compacto: `320x780`

## Verificaciones transversales (todas las rutas)
- [ ] Jerarquía visual clara (título, contenido, acciones)
- [ ] Spacing y alineación consistentes
- [ ] CTA principal visible y sin competir con secundarios
- [ ] Focus visible en botones/inputs/enlaces
- [ ] Sin scroll horizontal no intencional
- [ ] Sin solapes de componentes en mobile
- [ ] Contraste aceptable en dark/light

## Estados mínimos por pantalla

### /dashboard
- [ ] Estado normal con datos
- [ ] Estado con notice/banner
- [ ] Estado mínimo (sin actividad/sin oportunidades)

### /watchlist
- [ ] Lista con vuelos
- [ ] Estado vacío
- [ ] Estado de actualización visible (feedback de acción)

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
- [ ] Error de validación visible cerca del campo
- [ ] Feedback de error general claro

### /ayuda y /policies (recomendado)
- [ ] Legibilidad de bloques de texto
- [ ] Índice/estructura visible
- [ ] No roturas de maquetación en mobile

## Evidencia mínima en PR
- [ ] Capturas desktop de rutas core
- [ ] Capturas mobile 375 de rutas privadas core
- [ ] Capturas mobile 320 de rutas privadas core
- [ ] Build frontend OK

Ruta de snapshots sugerida:
- `docs/qa/snapshots/`





