Status: canonical
Scope: UI system, visual contract, or design guidance
Last reviewed: 2026-04-15
Canonical source: docs/ui/UI_CONTRACT_V1.md
Related: docs/ui/UI_SYSTEM_V1.md, docs/specs/README.md

---
# UI Contract v1 (Viru Tracker)

> Referencia de freeze oficial: `docs/ui/UI_SYSTEM_V1.md`

## Objetivo
Establecer reglas mínimas para mantener consistencia visual y reducir regresiones en la interfaz.

## Skill recomendado para cambios visuales por agente
- Skill instalado: `/.codex/skills/taste-skill/SKILL.md`.
- Debe usarse como soporte de criterio visual en tareas de frontend/estetica.
- El contrato de este documento prevalece si existe conflicto.

## Naming y capas de estilos
- `base.css`: fundamentos y reset.
- `tokens.css`: variables de diseño (color, spacing, tipografía, foco, estados).
- `components.css`: componentes y patrones reutilizables.
- `screens.css`: ajustes específicos por pantalla.

Reglas de ubicación:
1. Si el patrón aparece en 2+ pantallas, debe vivir en `components.css`.
2. Si es un valor semántico repetido (espacio, color, radio, tono), debe vivir en `tokens.css`.
3. `screens.css` solo para layout/orden/alineación exclusivos de una ruta.

## Componente: Card
Uso: contenedor visual para bloques de contenido.

Reglas:
- padding consistente por defecto.
- puede tener header y footer opcionales.
- no mezclar acciones primarias en más de una por card.

Ejemplo de clases actuales:
- `.module-card`
- `.panel`

## Componente: PanelHeader
Uso: cabecera de panel o sección.

Debe incluir:
- título claro
- acción opcional alineada a la derecha
- separación visual consistente

Ejemplo de clases actuales:
- `.panel-title`
- `.row-between`
- `.dashboard-section-head`

## Componente: StatusPill
Uso: mostrar estado de entidades y procesos.

Estados estandar:
- `success` (activo/completado)
- `warning` (pausado/pendiente/en espera)
- `error` (fallo)

Reglas:
- color semántico consistente
- tamaño homogéneo
- texto breve y accionable

Ejemplo de clase:
- `.status-pill`

## Componente: ActionRow
Uso: agrupación de acciones de un bloque.

Reglas:
- CTA principal primero
- secundarios en `btn-secondary` o `btn-ghost`
- spacing uniforme

Ejemplo de clases actuales:
- `.row-actions`
- `.module-actions`
- `.alert-actions`

## State Semantics
Semántica única de estados en toda la UI:
- `success`: operación completada o acción confirmada.
- `warning`: estado parcial, reversible o cooldown.
- `error`: fallo, validación o error de API.
- `info`: mensaje neutral o contextual.

Tokens obligatorios (`tokens.css`):
- `--state-success-*`
- `--state-warning-*`
- `--state-error-*`
- `--state-info-*`

Clases base (`components.css`):
- `.state-success`
- `.state-warning`
- `.state-error`
- `.state-info`

Componentes que deben consumir esta semántica:
- `status-pill`
- `notice`
- `toast`
- `field-error` / feedback inline

Compatibilidad legacy:
- No introducir `warn` en nuevos cambios.
- Tratar cualquier `warn` heredado como `warning` hasta su limpieza total.

## Glosario UI (ES)
Términos preferidos en la interfaz visible:
- Panel
- Seguimiento
- Búsqueda rápida
- Alerta
- Histórico
- Comparativa
- Preferencias
- Ayuda

Verbos preferidos:
- Buscar
- Actualizar
- Guardar
- Eliminar
- Activar / Desactivar
- Reintentar

Estados breves:
- Cargando…
- Sin resultados
- Error
- Listo

## Reglas de microcopy breve
1. Mensajes operativos de una o dos frases.
2. Evitar mezcla ES/EN en UI visible.
3. Repetir términos de glosario en todos los módulos.
4. Si hay error, indicar acción siguiente cuando aplique.

## Convenciones legacy / deprecación
- Rutas canonicas: `/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/recomendaciones`, `/preferencias`.
- Puentes legacy permitidos por compatibilidad: `/history`, `/preferences`, `/suggestions` (redirigen a canonica).
- Evitar clases ambiguas de estado legacy (`warn`) en nuevos cambios. Usar `warning`.

## Reglas de regresión
1. Todo refactor de estilos requiere build OK.
2. No introducir cambios visuales no intencionados.
3. Mantener compatibilidad con dark/light.
4. Mantener focus visible en elementos interactivos.










