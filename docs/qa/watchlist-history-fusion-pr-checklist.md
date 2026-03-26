# PR Checklist Ejecutable - Fusión Watchlist + Histórico

Fecha: 2026-02-18

## Gate
- [ ] `npm run test` pasa en `frontend/`.
- [ ] `npm run lint` pasa en `frontend/`.
- [ ] Sin enlaces activos de producto a `/history` en dashboard.

## Navegación
- [ ] `/history` redirige a `/watchlist`.
- [ ] Dashboard abre análisis desde `/watchlist`.

## UX Unificada
- [ ] Existe cabecera de control general con CTA de añadir vuelo.
- [ ] Lista de vuelos es seleccionable y usable.
- [ ] Hay filtros/orden para lista inteligente.
- [ ] Bloque de análisis principal domina visualmente.

## Funcionalidad preservada
- [ ] Refresh individual por vuelo.
- [ ] Refresh por filtros.
- [ ] Gráfico + tooltip + rango temporal + zoom/reset.
- [ ] KPIs (media, mínimo, máximo, puntos).
- [ ] Comparativa 2 fechas.
- [ ] Comparativa multi-vuelo (<=3).
- [ ] Calendario/heatmap.

## Calidad visual y UX
- [ ] Estados selected/hover/focus claros.
- [ ] Copy consistente en español.
- [ ] Diseño usable en desktop y mobile.

## Evidencia
- [ ] Capturas antes/después de watchlist.
- [ ] Salida de test/lint adjunta.
- [ ] Log en `logs_ia` con resumen técnico.
