# QA Checklist - Fase 0 Limpieza conceptual

**Estado:** vivo  
**Ultima revision:** 2026-05-11  
**Fuente de verdad:** si  
**Area:** qa

## Objetivo

Validar que la Fase 0 elimina ambiguedad de lenguaje, rutas y estados sin introducir cambios de contrato.

## Checklist manual

1. Navegacion privada muestra: Dashboard, Watchlist, Quick Search, Alertas, Oportunidades, Preferencias, Ayuda.
2. No aparece `Suggestions` como modulo de workspace.
3. `/history` redirige a `/watchlist` sin pantalla intermedia visible.
4. `/preferences` redirige a `/preferencias` sin pantalla intermedia visible.
5. `/suggestions` redirige a `/soporte/feedback?type=idea`.
6. Watchlist no muestra copy EN residual de Fase 0 (`Back`, `Flight Watchlist`, `Add flight`, `Quick start`, `Got it`, `Last update`).
7. Dashboard no muestra copy EN residual de FTUE (`Quick start`, `Got it`).
8. Badges de estado en alertas usan tonos canonicos (`success`, `warning`, `error`, `info`) via catalogo compartido.
9. Estado de sistema en backend deriva de `ok|degraded|critical`.
10. Mapa de vocabulario producto↔ruta↔API↔entidad existe y esta actualizado.

## Evidencia automatizada minima

- Frontend:
  - `navigation-v1.test.ts`
  - `legacy-route-redirects.test.ts`
  - `private-visible-copy-es.test.ts`
  - `status-catalog.test.ts`
  - `product-vocabulary-map.test.ts`
- Backend:
  - `test_domain_vocabulary.py`
  - `test_alert_rule_aliases.py`
