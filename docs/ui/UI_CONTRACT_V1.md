Status: canonical  
Scope: UI system, visual contract  
Last reviewed: 2026-05-15  
Fuente de verdad: docs/ui/UI_CONTRACT_V1.md  

---  

# UI Contract v1 — Viru Tracker

> Referencia de freeze oficial: `docs/ui/UI_SYSTEM_V1.md`

## Objetivo
Reglas mínimas para consistencia visual, coherencia editorial y prevenir regresiones en la interfaz.

## Skill de estética recomendado
- Skill: `/.codex/skills/taste-skill/SKILL.md` (para guiar criterios visuales).  
- Este contrato prevalece ante cualquier sugerencia de estilo.  

## Estructura de archivos CSS
- `base.css`: reseteo y estilos globales básicos.  
- `tokens.css`: variables de diseño (colores, tipografía, espaciamientos, focos, estados).  
- `components.css`: patrones y componentes reutilizables.  
- `screens.css`: estilos específicos para cada pantalla.  

**Reglas de ubicación:**  
1. Un patrón común a 2+ pantallas → `components.css`.  
2. Un valor repetido en varias partes (color, space, radio, tono) → `tokens.css`.  
3. Exclusivo de una ruta/pantalla → `screens.css`.  

## Componentes clave

- **Card:** contenedor genérico. Debe tener padding consistente y opcionales header/footer. No incluir más de una acción primaria en la misma card. (e.g. `.panel`, `.card`)  

- **PanelHeader:** cabecera de sección. Debe incluir título (Playfair Display) + subtítulo (IBM Plex Sans) y una acción a la derecha. Separación clara entre título y acciones. (e.g. `.panel-title`, `.row-between`)  

- **StatusPill:** etiqueta de estado. Colores semánticos consistentes (verde éxito, ámbar advertencia, coral error, azul info). Texto breve (p.ej. “Activo”); tamaño homogéneo. (Clase `.status-pill`)  

- **ActionRow:** fila de acciones. Botón principal a la izquierda, secundarios ordenados después (`.btn-secondary`, `.btn-ghost`). Espacio uniforme entre botones. (e.g. `.row-actions`, `.module-actions`)  

## Semántica de estados
Única en toda la UI: 
- **success:** operación completada.  
- **warning:** proceso en pausa o pendiente.  
- **error:** fallo o validación.  
- **info:** mensaje neutral/contextual.  

Tokens (`tokens.css`):  
- `--state-success-*`, `--state-warning-*`, `--state-error-*`, `--state-info-*`.  

Clases base (`components.css`):  
- `.state-success`, `.state-warning`, `.state-error`, `.state-info`.  

Componentes que usan estos estados: `status-pill`, `notice`, `toast`, campos (`.field-error` feedback).  

**Compatibilidad legacy:** no usar `warn` en nuevo código. Tratar `warn` heredado como `warning` durante migración.  

## Glosario UI (ES)
- **Términos:** Panel, Seguimiento, Búsqueda rápida, Alerta, Histórico, Comparativa, Preferencias, Ayuda, **Vuelo**, **Terminal**.  
- **Verbos:** Buscar, Actualizar, Guardar, Eliminar, Activar / Desactivar, Reintentar.  
- **Estados:** Cargando…, Sin resultados, Error, Listo.  

## Microcopy breve
1. Mensajes operativos de 1-2 frases.  
2. Sin mezclar ES/EN en textos visibles.  
3. Repetir términos del glosario en todas las pantallas.  
4. En caso de error, indicar la acción siguiente (si aplica).  

## Convenciones legacy / Deprecación
- **Rutas canónicas:** `/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/recomendaciones`, `/preferencias`.  
- **Rutas legacy:** `/history`→`/preferencias`, `/suggestions`→en revisión.  
- Usar nombres claros de estado (`warning` en lugar de `warn`).  

## Reglas de regresión (QA)
1. Todo cambio en estilos debe pasar build y pruebas automatizadas.  
2. No introducir cambios visuales no intencionados (UI regressions).  
3. Mantener compatibilidad con modos Dark/Light (contraste legible).  
4. Focus claramente visible en elementos interactivos.
