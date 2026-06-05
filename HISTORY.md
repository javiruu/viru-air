# History

## 2026-06-05 — Post-closeout hotel polish (Fases A-E)

Tras el cierre de las 10 fases originales del módulo `/hoteles`, se ejecutaron 5 fases adicionales de correcciones y polish. El plan maestro está documentado en `docs/plans/2026-06-04-hoteles-correcciones-post-cierre.md` y en `cabinalimpia.txt`.

### Cambios

- **Fase A — DELETE comp-set endpoint**: Ya existía en backend con tests de ownership (184/184 tests pasan).
- **Fase B — Refactor hooks**: Ya completado. Los 6 hooks (`useHotelSearch`, `useHotelDetail`, `useHotelWatchlist`, `useHotelCompSets`, `useHotelAlerts`, `useTrackedOffers`) ya estaban extraídos de `HotelRadarPage.tsx`.
- **Fase C — Unificar tracking UI**: Ya completado. `initial_price` visible en `HotelTrackedOffersPanel`, componente `HotelTrackedOfferSnapshots` con historial de precios, watchlist vs tracked-offers diferenciados en i18n.
- **Fase D — CSS area-search**: Añadidas 165 líneas de CSS en `screens.css` para el buscador por área: tabs de modo (nombre/zona), grid responsivo (2-4 columnas), autocomplete con dropdown posicionado, spinner animado con `@keyframes hotel-spin`, badge de zona resuelta, y lista de resultados de área.
- **Fase E — Polish final**: `parity_break` ya relegado a toggle "Avanzada" en `HotelAlertsPanel`. Conectado `deleteHotelCompSet` en hook (`handleDeleteCompSet`), componente (botón "Eliminar comparativa"), y página. Añadidas 4 claves i18n (`compSetDeleted`/`deleteCompSet` ES+EN).

### Archivos modificados

- `frontend/src/styles/screens.css` (+165 líneas)
- `frontend/src/modules/hotels/hooks/useHotelCompSets.ts` (+17 líneas)
- `frontend/src/modules/hotels/components/HotelCompSetPanel.tsx` (+9 líneas)
- `frontend/src/i18n/domains/hotels.ts` (+4 líneas)
- `frontend/src/modules/hotels/HotelRadarPage.tsx` (+1 línea)
- `cabinalimpia.txt` (nuevo, plan consolidado)
- `docs/plans/2026-06-04-hoteles-correcciones-post-cierre.md` (nuevo)
- `hoteles.txt`, `hoteles_2.txt`, `hoteles_3.txt` (eliminados)

### Verificación

- Backend: 184/184 tests pasan
- Frontend: `npx tsc --noEmit` sin errores de hoteles
- Commit: `2db8b25` en `main`, pushed a GitHub
