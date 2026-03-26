# Dashboard Redesign V2 Design

**Goal:** Rediseñar el dashboard para mejorar jerarquía, foco en acción y limpieza visual sin añadir funcionalidades complejas.

**Architecture:** Reorganización por zonas con un bloque Hero dominante, sección operativa principal con tres cards equivalentes, bloque de descubrimiento unificado, y secundarios compactos. Solo condicional UI; sin backend nuevo.

**Tech Stack:** Next.js (frontend actual), React, Tailwind/CSS existente del proyecto.

---

## Contexto y referencia
- Estado actual: dashboard del PDF `C:\Users\javiru\Downloads\dashboard.pdf`.
- Problemas detectados: tarjetas con mismo peso, duplicidad Recomendaciones/Sugerencias, falta de foco, exceso de botones secundarios, notas sobredimensionadas.

## Decisiones clave
- Hero dominante `DashboardHeroState` full width con CTA principal único.
- Sección “Gestionar tus vuelos” con 3 cards iguales: Watchlist, Alertas, Análisis.
- Fusión Recomendaciones + Sugerencias en “Oportunidades” (1 highlight + CTA único).
- Actividad reciente pasa a timeline compacto.
- Notas se mantienen en dashboard pero colapsables.

## Estructura propuesta
### ZONA 1 — Hero
- Título “Hoy en Viru”.
- Subtexto de estado (vuelos vigilados, última búsqueda).
- Oportunidad destacada (ruta, precio, delta) con badge semántico.
- CTA principal “Revisar oportunidad”.
- Estados alternos:
  - Sin oportunidades: “Nada urgente hoy” + CTA “Explorar nuevas rutas”.
  - 0 vuelos activos: estado onboarding con CTA “Explorar nuevas rutas”.

### ZONA 2 — Operativa principal
- Sección titulada “Gestionar tus vuelos”.
- Cards: Watchlist, Alertas, Análisis.
- Regla de botones: 1 sólido por card, secundarios como link.
- Microcopy de contexto bajo título (ej. “Última actividad hace 5 días”).

### ZONA 3 — Descubrimiento
- Tarjeta única “Oportunidades” con 1 highlight.
- CTA “Ver oportunidades”.

### ZONA 4 — Secundario
- Actividad reciente en timeline compacto (icono + texto corto).
- Notas colapsables, visualmente discretas.

## Jerarquía visual
- H2 para Hero, H3 para secciones, H4 para títulos de card.
- Espaciado consistente 8/16/24.
- Hero con sombra ligeramente más fuerte.
- Cards secundarias más planas.
- Badges de color semántico (verde/rojo).

## Sin cambios de lógica compleja
- Solo condicional UI en Hero para estados vacíos.
- Sin backend nuevo ni rutas adicionales.

## Criterios de aceptación
- Hero dominante visible al entrar.
- Recomendaciones y Sugerencias fusionadas.
- 1 botón principal por tarjeta.
- Actividad en timeline compacto.
- Notas colapsables.
- Jerarquía tipográfica y espaciado coherentes.

---

## Riesgos y mitigaciones
- Riesgo: pérdida de accesos rápidos si se ocultan acciones secundarias.
  - Mitigación: links secundarios visibles y consistentes.
- Riesgo: Hero demasiado pesado en móvil.
  - Mitigación: comportamiento responsive con stacking y reducción de padding.

## Pruebas sugeridas
- Visual QA en `/dashboard` desktop y mobile.
- Verificar que no hay más de 1 botón sólido por card.
- Verificar estados: con oportunidades, sin oportunidades, 0 vuelos activos.