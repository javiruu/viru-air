# Watchlist Redesign v1 — Spec

**Estado:** borrador  
**Última revisión:** 2026-06-13  
**Fuente de verdad:** sí  
**Área:** product / ui  
**Basado en:** entrevista con usuario + análisis de código (`frontend/src/modules/watchlist/`)  
**Skills aplicables:** `frontend-design`, `design-taste-frontend`, `make-interfaces-feel-better`, `high-end-visual-design`, `minimalist-ui`

---

## 1. Problema detectado

La página `/watchlist` actual tiene **tres problemas simultáneos** que la hacen poco intuitiva:

1. **Orden de bloques:** La secuencia vertical no refleja la prioridad real de uso.
2. **Demasiada información visible:** 5+ paneles compiten por atención sin jerarquía clara.
3. **Relaciones confusas entre paneles:** No se entiende cómo se conectan lista ↔ detalle ↔ histórico ↔ mapa ↔ comparativa.

---

## 2. Metáfora de producto

**Centro de control editorial** — ni dashboard genérico ni lista simple.

La página debe sentirse como un espacio con personalidad donde el usuario:

- Vigila rutas guardadas
- Entiende cambios de precio
- Revisa señales importantes
- Consulta histórico con contexto
- Decide qué hacer sin perderse

> Premium pero práctico. Con criterio visual, no minimalismo vacío. Con features útiles y bien presentadas: jerarquía visual, contexto, señales, acciones rápidas, estados claros y una composición bonita al estilo Viru.

---

## 3. Inspiración visual

**FlightRadar / aviación** como referencia de tono:

- Códigos IATA como identificadores claros
- Datos precisos con presentación editorial
- Mapa con peso visual pero en su sitio y cuando toca
- Sensación de instrumental de navegación, no de app genérica
- Mantener paleta beige/sobria actual de Viru

---

## 4. Nueva jerarquía de la página (orden de secciones)

| Prioridad | Sección | Rol |
|-----------|---------|-----|
| 1 | **Histórico** | Bloque dominante cuando hay ruta seleccionada. Si no hay, muestra aviso "Selecciona una ruta primero" |
| 2 | **Mis rutas** (antes SmartWatchList) | Lista compacta de rutas vigiladas con filas detalle. Debajo del histórico |
| 3 | **Mapa** | Se mantiene al final. Con peso visual pero en su sitio |
| 4 | **Comparativa** | Se transforma en modal/overlay, no como sección siempre visible |

**Layout general:** scroll narrativo vertical con jerarquía visual fuerte (tamaños, colores, whitespace).

---

## 5. Flujo de usuario

### 5.1 Sin ruta seleccionada
```
[Histórico] → Muestra aviso: "Selecciona una ruta de tu Watchlist para ver su histórico"
[Mis rutas] → Lista completa de todas las rutas vigiladas
[Mapa]     → Estado neutral o vacío
```
El foco inicial está en la lista: el usuario debe elegir una ruta.

### 5.2 Con ruta seleccionada
```
[Histórico] → GRANDE, dominante. Gráfico + KPIs + resumen
[Mis rutas] → La ruta seleccionada aparece expandida inline como "card protagonista"
              Las demás rutas siguen visibles en modo compacto
[Mapa]     → Muestra la ruta seleccionada en foco (o varias si hay comparación)
[Comparativa] → Solo accesible como modal/overlay bajo demanda
```

---

## 6. Rediseño de componentes

### 6.1 SmartWatchList → Mis rutas

**Nuevo nombre:** Mis rutas (i18n: `watchlist.smartList.heading` → `Mis rutas`)

**Filas:** Modo simplificado, sin sparklines por defecto.

Cada fila muestra solo:
- Códigos IATA (origen → destino) + flecha tipográfica
- Fecha del vuelo
- Precio actual (formateado)
- Delta (flecha + valor) — tendencia
- Checkbox para selección múltiple (para bulk actions)
- Botón de acción: **Refresh** (icono + texto)
- Enlace discreto: **Ver histórico** (que selecciona la ruta)

> Los sparklines se eliminan de la lista. Si se necesita contexto visual, se muestran al expandir la ruta.

**Toolbar:**
- Búsqueda por texto (mantener actual)
- Ordenar por (frescura, precio asc, precio desc, delta)
- Bulk toolbar aparece contextualmente al seleccionar (refresh, pausar, reanudar, eliminar)
- Botón "Añadir vuelo"

**Estados:**
- Loading: skeletons (mantener actual)
- Vacío: onboarding actual (3 pasos + CTA)
- Error inline: mensaje + botón reintentar
- Sin resultados de búsqueda: mensaje + "Ver todos"

### 6.2 WatchDetailPanel → Eliminado como panel separado

**El detalle de ruta se integra como expansión inline de la fila.**

Cuando el usuario selecciona una ruta en la lista:

1. La fila se expande suavemente (transición)
2. Debajo aparece una **card protagonista** con:

```
┌──────────────────────────────────────────────────┐
│ RUTA SELECCIONADA: MAD → BCN · 2026-07-15       │
│ ┌────────────────────────────────────────────────┐ │
│ │                                                 │ │
│ │  [Mini gráfico de histórico resumido]           │ │
│ │                                                 │ │
│ │  Chips: Activa · Frescura: hace 2h             │ │
│ │                                                 │ │
│ │  Precio objetivo: 45€                           │ │
│ │  Último snapshot: 52€ hace 2h                   │ │
│ │                                                 │ │
│ │  [Refresh]  [Ver análisis completo →]           │ │
│ └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

Características:
- La **card protagonista** es visualmente clara pero no rompe el flujo
- Incluye mini sparkline/resumen histórico
- Chips de estado y frescura
- Botones de acción rápida: Refresh, Pausar/Reanudar
- CTA secundario: "Ver análisis completo" (selecciona la ruta para que el histórico de abajo se actualice)
- No abre panel lateral, no cambia de contexto

### 6.3 HistoryIntegratedPanel → Histórico

**Es el bloque más importante de la página.**

**Cuando hay ruta seleccionada:**
- Ocupa la zona superior de la página con jerarquía dominante
- Muestra: **Gráfico de líneas grande + KPIs (min, max, avg, count, latest, delta) + leyenda**
- View mode: chart por defecto, calendar como alternativa

**Cuando NO hay ruta seleccionada:**
- Espacio dedicado pero en estado de espera
- Mensaje claro: "Selecciona una ruta de tu Watchlist para ver su histórico"
- No ocupa espacio innecesario

**Filtros históricos:**
- Se mantienen dentro del panel de histórico
- Rediseñados para ser más cálidos, compactos y guiados
- Toolbar contextual para: período (7d/14d/30d/90d/todo), punto de consulta, modo gráfico/calendario, rango
- Microcopy amable
- Sin duplicar selección principal de ruta (que se hace en Mis rutas)

**Elementos del histórico:**
| Elemento | Estado default | Notas |
|----------|---------------|-------|
| Gráfico de líneas | Visible con datos | SVG con polyline, hover tooltip, leyenda de series |
| KPIs | Visible siempre | min, max, avg, count, latest, delta |
| Selector de rango | Visible | 7d/14d/30d/90d/All, compact view toggle, reset zoom |
| Selector de punto | Visible (si 1 fecha seleccionada) | Dropdown para ver detalle en fecha concreta |
| Selector modo chart/calendar | Visible | Alternar entre chart SVG y calendario heatmap |
| Leyenda de series | Visible | Chips con color + fecha |
| Disclaimer precio | Colapsable | details/summary |

### 6.4 ComparePanels → Modal/Overlay

**Se transforma en una herramienta que se abre bajo demanda, no una sección permanente.**

- **Trigger:** Botón/flotante "Comparar" visible cuando hay 2+ rutas seleccionadas (checks en lista)
- **Contenido:** Modal/overlay con las dos tabs actuales (Rápida y Multivuelos)
- **Comportamiento:** Al cerrar, vuelve al flujo principal sin perder selección
- **Estados:** Loading, vacío, error, mixed currency warning

### 6.5 WatchlistMapDecisionPanel → Mapa

- Se mantiene al final de la página
- Debe tener más peso visual y presencia
- Tono editorial aviación: rutas trazadas, datos contextuales en marcadores
- Modo foco (ruta seleccionada) vs modo comparación (múltiples rutas)
- Insights contextuales: oportunidad activa, ruta más estable
- Mínimo 1280×720 o similar para sentirse instrumental

---

## 7. Estados y micro-interacciones

### 7.1 Loading
- Skeleton loaders para lista (mantener actual)
- Skeleton para histórico (toolbar + chart area + KPIs) — mantener actual
- Estados de refresco: isRefreshingHistory, isRefreshingBulk

### 7.2 Empty states
- **Watchlist vacía:** mantener onboarding actual (3 pasos + CTA añadir vuelo)
- **Sin resultados de búsqueda:** mensaje + "Ver todos"
- **Histórico sin datos:** "Aún no hay histórico suficiente para resumir esta ruta"

### 7.3 Error states
- **Error al cargar watchlist:** mensaje inline + botón reintentar
- **Error al refrescar:** notificación toast/inline
- **Error en comparativa:** mensaje inline en modal

### 7.4 Animation & motion
- Expansión inline de fila → suave, spring physics
- Staggered reveal de elementos al cargar
- Hover sutil en cards
- Transiciones de estado sin saltos bruscos
- Modal de comparativa → fade + scale

---

## 8. Acciones disponibles

| Acción | Dónde | Tipo |
|--------|-------|------|
| Añadir vuelo | Header + lista vacía | Modal |
| Buscar rutas | Toolbar de Mis rutas | Inline |
| Ordenar rutas | Toolbar de Mis rutas | Select |
| Seleccionar ruta (ver detalle) | Clic en fila de Mis rutas | Inline expand |
| Refresh individual | Botón en fila o en expand | Acción directa |
| Pausar/Reanudar individual | En expansión de ruta | Acción directa |
| Ver histórico | Enlace en expansión o fila | Selecciona ruta, actualiza histórico |
| Selección múltiple | Checkboxes en filas | Bulk mode |
| Bulk refresh | Toolbar bulk | Acción masiva |
| Bulk pausar/reanudar/eliminar | Toolbar bulk | Acción masiva |
| Refresh filtrado | Toolbar histórico | Acción directa |
| Cambiar rango histórico | Toolbar histórico | Select + botones |
| Cambiar modo chart/calendar | Toolbar histórico | Toggle |
| Abrir comparativa | Botón flotante | Modal |
| Ver mapa | Scroll al final | Navegación vertical |

---

## 9. Nombres actualizados (i18n)

| Actual | Nuevo | Clave i18n |
|--------|-------|------------|
| SmartWatchList / "Rutas vigiladas" | **Mis rutas** | `watchlist.smartList.heading` |
| HistoryIntegrated / "Histórico integrado" | **Histórico** | `watchlist.history.title` |
| ComparePanels / "Comparativa" | **Comparativa** (sin cambios) | `watchlist.compare.title` |
| WatchlistMapDecisionPanel / "Mapa de rutas" | **Mapa** | `watchlist.map.title` |
| WatchDetailPanel / "Detalle de ruta" | **(eliminado como panel)** | N/A |

---

## 10. Estética y diseño visual

### 10.1 Paleta
- Mantener paleta actual de Viru (beige/sobria)
- Beige base: `#F7F6F3` / `#FBFBFA`
- Acentos: `#2E6E62` (verde Viru), `#D95D39` (terracota)
- Neutros: zinc/slate suaves
- Texto: off-black, nunca `#000000`

### 10.2 Tipografía
- Mantener tipografía actual del proyecto
- Jerarquía clara: H1 (título página), H2 (título sección), body
- Códigos IATA en weight semibold o bold para identificación rápida

### 10.3 Espaciado
- Scroll narrativo: secciones con padding vertical generoso (`py-16`+)
- Whitespace como herramienta de jerarquía
- Cards con padding interno amplio

### 10.4 Toques editoriales
- Flecha tipográfica `→` para rutas (ya implementado)
- Códigos IATA como identificadores primarios
- Fechas en formato legible
- Precios con moneda, tabular-nums
- Badges semánticos con color

### 10.5 Lo que NO cambiar
- No oscurecer la interfaz
- No añadir gradientes ni glassmorphism
- No cambiar el sistema de tokens actual
- No añadir dependencias nuevas sin verificar en package.json

---

## 11. Skills de diseño aplicables

Skills cargadas que guiarán la implementación:

| Skill | Aportación |
|-------|------------|
| `frontend-design` | Crear interfaz distintiva y de grado de producción, evitar estética AI genérica |
| `design-taste-frontend` | Baseline: DESIGN_VARIANCE=8, MOTION_INTENSITY=6, VISUAL_DENSITY=4. Anti-patrones: no Inter, no purple, no cards-overuse |
| `make-interfaces-feel-better` | Micro-interacciones: concentric border radius, scale on press, tabular-nums, interruptible animations, staggered reveals |
| `high-end-visual-design` | Double-bezel architecture para cards premium, button-in-button, spatial rhythm |
| `minimalist-ui` | Bento grids tipográficos, ultra-flat components, muted pastel accents |

---

## 12. No incluido en este spec (fuera de scope)

- Backend: no se tocan APIs, no se añaden endpoints
- Nuevas features de producto (alertas avanzadas, recomendaciones, etc.)
- Dashboard: es otra página con su propio spec
- Quick search: es otro módulo independiente
- Mobile responsive: se menciona pero no se detalla (aplica UI_VISUAL_QA_CHECKLIST)

---

## 13. Definition of Done (DoD)

- [ ] Histórico es el bloque dominante arriba cuando hay ruta seleccionada
- [ ] Sin ruta seleccionada → aviso claro en lugar de histórico vacío
- [ ] Mis rutas usa filas simplificadas sin sparklines
- [ ] Detalle de ruta es expansión inline (no panel separado)
- [ ] Comparativa es modal/overlay, no sección permanente
- [ ] Mapa se mantiene al final con más peso visual
- [ ] Nombres actualizados en i18n (SmartWatchList → Mis rutas)
- [ ] Flujo scroll narrativo con jerarquía clara
- [ ] Build frontend OK
- [ ] TypeScript typecheck OK
- [ ] Tests existentes siguen pasando
- [ ] QA visual en desktop 1440×900 y tablet 768×1024
