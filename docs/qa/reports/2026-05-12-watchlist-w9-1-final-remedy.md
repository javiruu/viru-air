# Watchlist W9.1 Final Remedy

**Estado:** vivo  
**Fecha:** 2026-05-13  
**Fuente de verdad:** si  
**Area:** QA / watchlist  
**Commit base:** `dd02d901f70fe172d5ef9204c28eb4aae5ffb4cb`

## Problemas corregidos

- Separador de rutas inconsistente con `?` en múltiples superficies de `/watchlist`.
- Bloque de confianza histórica del detalle con lectura demasiado fragmentada.
- Duplicidad visual en histórico integrado (`Rango` repetido en cabecera y selector).
- Salto poco legible en frescura dentro de cards.
- Calendario tabular dentro del detalle de ruta, duplicando el histórico integrado.

## Decisión W9.1

Se elimina por completo el calendario tabular del panel **Detalle de ruta** (`WatchDetailPanel`) para reducir sobrecarga visual y evitar duplicidad con el histórico integrado.

Aclaración explícita:

> No se elimina `/prices/calendar` ni histórico backend; solo se elimina la tabla del detalle porque duplicaba el histórico integrado.

## Archivos tocados

- `frontend/src/modules/watchlist/components/WatchDetailPanel.tsx`
- `frontend/src/modules/watchlist/components/ComparePanels.tsx`
- `frontend/src/modules/watchlist/components/HistoryIntegratedPanel.tsx`
- `frontend/src/modules/watchlist/components/SmartWatchListPanel.tsx`
- `frontend/src/i18n/domains/watchlist.ts`
- `frontend/src/styles/screens.css`
- `frontend/tests/watchlist-f3b-advanced-history.test.ts`
- `frontend/tests/watchlist-w6-actionable-freshness.test.ts`
- `frontend/tests/watchlist-w9-1-final-remedy.test.ts`
- `docs/qa/reports/2026-05-12-watchlist-w9-1-final-remedy.md`
- `docs/DOCS_INVENTORY.md`

## Verificaciones ejecutadas

En `frontend`:

- `npm test`
- `npm run build`
- `npm run lint`

## Caveats

- Ningún cambio de backend, endpoints o migraciones.
- Si aparece warning preexistente de `react-hooks/exhaustive-deps` fuera de este alcance, se documenta y no se modifica en W9.1.
