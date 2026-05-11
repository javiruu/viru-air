# Hero CTA Quick Search Design

**Goal:** Cambiar el CTA principal del Hero del dashboard para orientar acción directa a Quick Search.

**Architecture:** Ajuste de copy y destino del CTA en el Hero; no se modifica la lógica de datos ni backend.

**Tech Stack:** Next.js 15, React 19, i18n existente.

---

## Cambio UI/UX
- Botón principal del Hero:
  - Copy: “Buscar nuevas rutas ahora”.
  - Destino: `/quick-search` siempre.
- Microcopy del Hero se alinea a Quick Search si aplica.
- Se mantiene jerarquía visual y un único CTA principal.

## Criterios de aceptación
- Hero CTA muestra “Buscar nuevas rutas ahora”.
- CTA navega a `/quick-search`.
- No se añaden funcionalidades complejas.
