# QA Visual `/hoteles` — Fase 9

**Estado:** vivo  
**Última revisión:** 2026-06-03  
**Fuente de verdad:** sí  
**Área:** QA / Visual

## Resumen

Fase 9 de cierre visual y polish final del módulo `/hoteles`. Esta fase se ejecutó después de cerrar las deudas funcionales (paridad backend, anchor robusto, watchlist visible, alertas, feature flag, Makcorps, sweeps, búsqueda con acentos).

## Cambios realizados en Fase 9

### 1. Lista de miembros del Comp Set con botón de eliminar
- Se añadió `deleteHotelCompSetMember` en `frontend/src/modules/hotels/api.ts`.
- Se añadió `handleDeleteMember` en `HotelRadarPage.tsx`.
- Se añadió la sección de lista de miembros en `HotelCompSetPanel.tsx` con:
  - Nombre del hotel miembro y ciudad/país.
  - Botón "Quitar" para eliminar miembros.
  - Estados empty/loading.
- Strings i18n añadidas (ES + EN): `membersTitle`, `membersEmpty`, `removeMember`, `memberRemoved`.

### 2. CSS para la sección de miembros
- Clases nuevas en `screens.css`:
  - `.hotel-comp-set-members-section`
  - `.hotel-comp-set-member-list`
  - `.hotel-comp-set-member-item`
  - `.hotel-comp-set-member-copy`
- Layout grid con gap consistente, alineación centrada, y truncado de nombres largos.

### 3. Polish visual de tarjetas de resultados
- Transiciones suaves en `.hotel-result-card` (border-color, box-shadow, transform).
- Hover: elevación sutil (translateY -1px), borde con acento, sombra.
- Estado activo (`is-active`): sin desplazamiento en hover, sombra inset con acento.
- Anillos de foco visibles (`focus-visible`) en:
  - `.hotel-result-main`
  - `.hotel-comp-set-item`
  - `.hotel-alert-rule-actions .btn-ghost`
  - `.hotel-nearby-actions .btn-ghost`

### 4. Corrección de code smell en backend
- `backend/app/hotels/parity.py`: añadido `import datetime` para anotaciones de tipo.

## Verificaciones

### Build y tests
- ✅ `npm run build` frontend — OK
- ✅ 46/46 tests backend de hoteles — OK

### Verificaciones visuales (código)
- ✅ Jerarquía visual: layout principal + sidebar con secciones agrupadas
- ✅ Spacing consistente con tokens del UI System
- ✅ Focus visible en botones y elementos interactivos
- ✅ Estados: loading, empty, error, success con copy en español
- ✅ Hover states con transiciones suaves
- ✅ Dark/light compatibles vía tokens CSS variables compartidos
- ✅ Responsive: media queries a 980px y 680px para mobile/tablet

### Pendiente de verificación manual en navegador
- [ ] Abrir `/hoteles` en navegador real
- [ ] Revisar dark mode y light mode
- [ ] Revisar responsive (desktop, tablet, móvil)
- [ ] Probar flujo completo: buscar → seleccionar → ver paridad → crear alerta → comp set → añadir/quitar miembros → watchlist
- [ ] Confirmar focus visible en todos los controles interactivos
- [ ] Confirmar que no hay overflow horizontal en viewports estrechos
- [ ] Revisar copy consistente en español sin mezcla ES/EN

## Archivos tocados en Fase 9

| Archivo | Cambio |
|---------|--------|
| `frontend/src/modules/hotels/api.ts` | Añadido `deleteHotelCompSetMember` |
| `frontend/src/modules/hotels/HotelRadarPage.tsx` | Añadido `handleDeleteMember`, import de `deleteHotelCompSetMember` |
| `frontend/src/modules/hotels/components/HotelCompSetPanel.tsx` | Sección de lista de miembros con botón "Quitar", prop `onDeleteMember` |
| `frontend/src/i18n/domains/hotels.ts` | Strings i18n: `membersTitle`, `membersEmpty`, `removeMember`, `memberRemoved` (ES+EN) |
| `frontend/src/styles/screens.css` | CSS para sección de miembros, hover/focus polish en result cards y comp set items |
| `backend/app/hotels/parity.py` | Añadido `import datetime` |
| `docs/qa/hotels-visual-qa.md` | Este documento (creado) |

## Limitaciones conocidas

1. La verificación visual en navegador real queda pendiente (no se pudo levantar el entorno dev en esta sesión).
2. Los nombres de hoteles en la lista de miembros se resuelven desde `results` (búsqueda actual); si un miembro se añadió en una búsqueda anterior que ya no lo incluye, se muestra el `hotel_id` crudo como fallback.
3. No se añadió `deleteHotelCompSet` (eliminar comp set entero) — el backend no expone ese endpoint.
