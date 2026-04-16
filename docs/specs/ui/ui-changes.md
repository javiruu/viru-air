Status: canonical
Scope: active product, UI, or policy specification
Last reviewed: 2026-04-15
Canonical source: docs/specs/ui/ui-changes.md
Related: docs/specs/README.md, docs/INDICE_UNICO.md

---
# 1. Menú de Cuenta (Top-Right User Menu)

### 1.1 Crear Menú de Cuenta
Ubicación: esquina superior derecha del layout principal.

Trigger:
- Avatar circular o iniciales del usuario.
- Hover / click abre dropdown.

Contenido del dropdown:
- Perfil / Cuenta
- Preferencias
- Apariencia (Tema claro / oscuro)
- Idioma
- Ayuda / Feedback (opcional)
- Cerrar sesión

Debe ser accesible por teclado (focus + enter + esc).

### 1.2 Eliminar Cards del Dashboard
Eliminar del grid principal:
- Card “Preferencias”
- Card “Cerrar sesión”

Estas acciones pasan exclusivamente al menú de cuenta.

### 1.3 Estado Técnico
No debe ser card principal.
Mover a:
- Menú de cuenta → “Avanzado”
o
- Icono discreto en footer/topbar

---

## 2. Dashboard — Reestructuración y Jerarquía

### 2.1 KPI Superiores

#### Usuario Activo
Problema: muestra “–”.
Solución:
- Mostrar email o username.
- Mostrar iniciales o avatar.
- Texto secundario: “Conectado”.

#### Vuelos Activos
Problema: “0” frío.
Solución:
- “0 vuelos activos”.
- Texto secundario: “Empieza añadiendo uno en Watchlist”.

#### Estado del Sistema
Problema: semántica débil.
Solución:
- Badge con color + icono.
- Estados: OK / Degradado / Caído.
- Tooltip o texto secundario explicativo.

---

### 2.2 Banner de Error Backend

Problema:
- Demasiado grande.
- Sin acción.
- Visualmente agresivo.

Solución:
- Compactar altura.
- Añadir botón “Reintentar”.
- Añadir link “Ver diagnóstico”.
- Auto-hide si backend vuelve.
- Usar niveles de severidad (info/warn/error).

---

### 2.3 Jerarquía del Grid

Orden visual correcto:

1. Watchlist (mayor elevación)
2. Búsqueda Rápida
3. Alertas
4. Estado del Sistema (compacto)
5. Diagnóstico (secundario / oculto)

Watchlist y Búsqueda Rápida deben dominar visualmente.

---

## 3. Búsqueda Rápida — Correcciones Visuales

### 3.1 Modo Oscuro — Problemas Detectados

- Bajo contraste de placeholders y labels.
- Inputs sin delimitación.
- Falta estado de foco.
- Iconos desalineados.
- Texturas de fondo compitiendo.
- Botones pierden sombra.

### 3.2 Sistema de Tokens Light / Dark

Definir variables:

- `--bg`
- `--surface`
- `--text-primary`
- `--text-secondary`
- `--placeholder`
- `--border-default`
- `--border-focus`
- `--shadow-elevation`
- `--accent`

Modo oscuro:
- Aumentar luminancia de texto.
- Mantener misma familia cromática que modo claro.

---

### 3.3 Estados Interactivos

Implementar:

- `:hover`
- `:focus-visible`
- `:active`
- `:disabled`

Focus visible con outline + glow.

---

### 3.4 Fondo Decorativo

Reducir opacidad de líneas decorativas a 1–2%  
o desactivar bajo áreas con inputs.

---

### 3.5 Alineación y Spacing

- Inputs con misma altura.
- Padding uniforme.
- Iconos centrados verticalmente.
- Cards Origen/Destino con igual altura.

---

## 4. Componentes Compartidos

### 4.1 Botones

Variantes:
- Primary (accent)
- Secondary (outline)
- Danger (logout)

Micro-feedback:
- Scale 0.98 en click.
- Transición 120–180 ms.

Sombra adaptativa por tema.

---

### 4.2 Inputs

- Bordes más visibles en modo oscuro.
- Placeholder token propio.
- Focus ring accesible.
- Mensajes de error consistentes.

---

### 4.3 Tooltips

- Max width definido.
- Sombra suave.
- Aparecen en hover y focus.

---

## 5. UI Técnica / Debug

Problema:
Barra inferior técnica visible para usuarios normales.

Solución:
- Ocultar en producción.
- Mostrar solo con `?debug=1`.
- O colapsar en toggle “Modo diagnóstico”.

---

## 6. Accesibilidad

- Contraste WCAG AA mínimo.
- Focus navegable por teclado.
- Tooltips accesibles.
- No depender solo de color para estados.

---

## 7. Responsive

- Menú de cuenta funciona en móvil.
- Cards reordenables en vertical.
- Inputs mantienen focus visible.
- Banner de error no rompe layout.

---

## 8. Criterios de Aceptación Globales

- Menú de cuenta implementado.
- Preferencias y Logout fuera del dashboard.
- Dashboard enfocado en acciones, no configuración.
- Banner error compacto con CTA.
- Modo oscuro legible.
- Estados interactivos completos.
- Barra debug oculta.
- No elementos vacíos tipo “–”.
- Responsive intacto.
- Lint/tests en verde si existen.

---

## 9. Prioridades de Implementación

1. Menú de cuenta + mover Preferencias/Logout.
2. Banner backend + KPI superiores.
3. Modo oscuro Búsqueda Rápida.
4. Tokens de tema y estados interactivos.
5. Limpieza UI debug.
6. Micro-refinamientos visuales.

---

## 10. Resultado Esperado

El producto debe pasar de:

“UI bonita y ordenada”

a

“UI profesional, jerárquica, accesible y centrada en acción”.





