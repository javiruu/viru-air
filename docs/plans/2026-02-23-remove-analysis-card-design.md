# Remove Analysis Card Design

**Goal:** Eliminar la card "Análisis y comparativa" del dashboard para reducir ruido visual.

**Architecture:** Ajustar el layout de la sección "Gestionar tus vuelos" y eliminar textos i18n asociados al módulo de análisis. Sin cambios de backend.

**Tech Stack:** Next.js 15, React 19, i18n existente.

---

## Cambio UI/UX
- Eliminar la card de "Análisis y comparativa".
- La sección "Gestionar tus vuelos" queda con 2 cards: Watchlist + Alertas.
- Remover copy del módulo de análisis en i18n.

## Criterios de aceptación
- No aparece la card de análisis en `/dashboard`.
- No quedan textos i18n huérfanos para el módulo de análisis.
