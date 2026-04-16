Status: canonical
Scope: active product, UI, or policy specification
Last reviewed: 2026-04-15
Canonical source: docs/specs/product/dashboard-redesign-v2.md
Related: docs/specs/README.md, docs/INDICE_UNICO.md

---
# 2. Nueva arquitectura del dashboard

### ZONA 1 — BLOQUE PRINCIPAL (full width)
Reemplazar las tres tarjetas superiores por un bloque dominante.

**Componente:** `DashboardHeroState`

**Contenido:**
- Título dinámico: “Hoy en Viru”
- Subtexto: “2 vuelos vigilados · Última búsqueda hace 5d”
- Oportunidad destacada (si existe):
  - Ruta
  - Precio actual
  - Delta (% o €)
- CTA principal: “Revisar oportunidad”
- Si no hay oportunidades:
  - “Nada urgente hoy.”
  - CTA: “Explorar nuevas rutas”
- Si 0 vuelos activos: estado onboarding con copy breve y CTA “Explorar nuevas rutas”.

**Estilo:**
- Card más ancha
- Sombra ligeramente más fuerte
- Badge verde/rojo según oportunidad
- Punto focal visual

### ZONA 2 — OPERATIVA PRINCIPAL
Sección con título: “Gestionar tus vuelos”.

Contiene:
- Watchlist
- Alertas
- Análisis

**Reglas:**
- 1 botón principal por card
- Acciones secundarias como link pequeño
- Mismo tamaño para las 3 cards
- Espaciado consistente

Ejemplo Watchlist:
- Botón: “Abrir watchlist”
- Link discreto: “Ver análisis”

### ZONA 3 — DESCUBRIMIENTO
Fusionar Recomendaciones + Sugerencias en una nueva tarjeta: “Oportunidades”.

**Contenido interno:**
- 1 highlight principal
- CTA único: “Ver oportunidades”

Eliminar duplicidad conceptual.

### ZONA 4 — SECUNDARIO (compacto)
Reducir peso visual de:

**Actividad reciente**
- Timeline compacto: icono + texto corto
- Menor padding
- Más discreto

**Notas**
- Colapsable dentro del dashboard
- No compite con funcionalidades core

---

## 3. Reducción de fricción

### 3.1 Botones
Regla global:
- Máximo 1 botón sólido por tarjeta
- Secundarios en estilo link
- Eliminar redundantes

### 3.2 Microcopy orientado a acción
Textos dinámicos sin nuevas features:
- “Última actividad hace 5 días”
- “Sin cambios en las últimas 24h”
- “1 oportunidad detectada”

---

## 4. Mejora visual (sin cambiar identidad)

### 4.1 Jerarquía
- Hero state → H2 dominante
- Sección → H3
- Card title → H4

### 4.2 Espaciado
- Sistema 8 / 16 / 24
- Más aire arriba y abajo de secciones

### 4.3 Contraste
- Mantener estética beige
- Badges con color semántico
- Botón primario consistente
- Cards secundarias más planas

---

## 5. Comportamiento inteligente (sin nueva lógica)
- Si 0 vuelos activos → Hero muestra onboarding
- Si no hay oportunidades → Hero muestra “Nada urgente hoy” + CTA explorar

No añadir backend nuevo, solo condicional UI.

---

## 6. Qué eliminar
- Separación rígida en 3 columnas iguales
- Duplicidad Recomendaciones/Sugerencias
- Botones secundarios grandes
- Notas como bloque dominante

---

## 7. Resultado esperado
El usuario entra y:
- Ve un bloque claro que le dice qué pasa hoy.
- Entiende dónde gestionar sus vuelos.
- Tiene una sección clara para descubrir.
- No se siente abrumado.
- Percibe producto premium y organizado.

---

## 8. Definition of Done
- Existe un bloque Hero dominante arriba.
- Recomendaciones y Sugerencias fusionadas.
- Solo 1 botón principal por tarjeta.
- Actividad convertida en timeline compacto.
- Notas reducidas o colapsables.
- Jerarquía visual clara.
- Espaciado coherente.
- Dashboard más limpio y menos plano.

---

## 9. Prompt directo para Codex
“Aplica DASHBOARD_REDESIGN_V2.md.
Reestructura el dashboard priorizando jerarquía y claridad.
Crea un bloque Hero dominante.
Fusiona Recomendaciones y Sugerencias en Oportunidades.
Reduce botones secundarios.
Compacta Actividad y Notas.
No añadas nuevas funcionalidades complejas.
Mantén el estilo Viru actual pero mejora jerarquía y foco.”




