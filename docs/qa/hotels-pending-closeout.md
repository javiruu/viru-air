# Cierre pendiente de `/hoteles`

**Estado:** vivo  
**Ultima revision:** 2026-06-03  
**Fuente de verdad:** si  
**Area:** QA

## Resumen

Checklist viva de cierre para el modulo `/hoteles`.

Este documento corrige la auditoria previa: el backend hotelero y la ruta `/hoteles` existian, pero quedaban dos deudas funcionales en frontend antes de poder considerar cerradas las fases de closeout aqui definidas:

1. La senal de paridad se recalculaba en cliente en vez de usar backend como fuente de verdad.
2. El hotel base del comp set dependia de seguir visible dentro de los resultados de busqueda.

## Estado actual

Completado:

1. Catalogo, matching, snapshots, watchlist backend, comp sets, alert rules y alert events.
2. API interna de hoteles en `backend/app/api/v1/hotels.py`, incluida la ruta `GET /api/v1/hotels/{hotel_id}/parity`.
3. Ruta privada `frontend/src/app/(private)/hoteles/page.tsx`.
4. Panel de sugerencias cercanas apoyado en `GET /api/v1/hotels/comp-sets/{comp_set_id}/nearby-suggestions`.
5. Cierre de Fase 1 de este closeout: la UI consume la paridad desde backend y deja de recalcularla localmente.
6. Cierre de Fase 2 de este closeout: el hotel base del comp set se resuelve por `hotel_id` y ya no depende de `results`.
7. Cierre de Fase 3 de este closeout: la watchlist hotelera ya es visible dentro de `/hoteles`, con alta, baja e hidratacion de detalle por `hotel_id`.

Pendiente:

1. UI minima de alertas hoteleras.
2. Clarificar `HOTEL_FEATURE_ENABLED` en docs, copy y tests.
3. Endurecimiento de Makcorps y su documentacion operativa.
4. Runbook de sweeps hoteleros y decision explicita sobre scheduler.
5. QA visual final dark/light/responsive/focus/copy.

## Orden recomendado de trabajo

1. Fase 4: panel de alertas hoteleras.
2. Fase 5: aclarar `HOTEL_FEATURE_ENABLED`.
3. Fase 6: endurecer Makcorps.
4. Fase 7A: documentar sweeps manuales.
5. Fase 7B: scheduler opcional solo si se decide automatizar.
6. Fase 8: busqueda robusta por ciudad con acentos.
7. Fase 9: QA visual y polish final.
8. Fase 10: cierre documental final.

## Archivos probables por fase posterior

Fase 3:
- `frontend/src/modules/hotels/api.ts`
- `frontend/src/modules/hotels/types.ts`
- `frontend/src/modules/hotels/HotelRadarPage.tsx`
- `frontend/src/modules/hotels/components/HotelSearchPanel.tsx`
- `frontend/src/modules/hotels/components/HotelWatchlistPanel.tsx`
- `frontend/src/i18n/domains/hotels.ts`

Fase 4:
- `frontend/src/modules/hotels/api.ts`
- `frontend/src/modules/hotels/types.ts`
- `frontend/src/modules/hotels/HotelRadarPage.tsx`
- `frontend/src/modules/hotels/components/HotelAlertsPanel.tsx`
- `frontend/src/i18n/domains/hotels.ts`

Fase 5:
- `docs/specs/hotels-intelligence-mvp.md`
- `backend/.env.example`
- `backend/tests/integration/test_hotels_api_flow.py`
- `backend/tests/unit/test_hotels_ingestion.py`
- `frontend/src/i18n/domains/hotels.ts`

Fase 6:
- `backend/app/hotels/makcorps_provider.py`
- `backend/app/hotels/ingestion.py`
- `backend/tests/unit/test_makcorps_provider.py`
- `backend/.env.example`
- `docs/specs/hotels-intelligence-mvp.md`

Fase 7A-7B:
- `docs/runbooks/hotels-sweeps.md`
- worker o scheduler existente si se automatiza
- tests backend del flujo de sweep

Fase 8:
- `backend/app/infrastructure/db/models.py`
- `backend/alembic/versions/*hotels_normalized_city*.py`
- `backend/app/hotels/mapping.py`
- `backend/app/services/hotels_service.py`
- tests backend de normalizacion y busqueda

Fase 9-10:
- `frontend/src/modules/hotels/**`
- `frontend/src/i18n/domains/hotels.ts`
- `frontend/src/styles/screens.css`
- `docs/qa/hotels-visual-qa.md`
- `docs/specs/hotels-intelligence-mvp.md`

## Riesgos detectados

1. Divergencia frontend/backend si vuelven a existir calculos de paridad duplicados.
2. Degradacion de UX si el hotel base vuelve a depender de la busqueda visible.
3. Confusion de alcance si `HOTEL_FEATURE_ENABLED` sigue significando cosas distintas en UI, provider y docs.
4. Riesgo de sobreprometer automatizacion de sweeps si no existe scheduler real.
5. Integracion Makcorps con semantica ambigua si se documenta mas de lo que hoy implementa.

## Checks necesarios

Checks ya ejecutados para este cierre:

1. `npm run typecheck`
2. `npm run build`

Checks recomendados para el siguiente cierre visual:

1. Abrir `/hoteles`.
2. Cargar fixture mock.
3. Buscar hotel.
4. Seleccionar hotel y confirmar senal de paridad desde backend.
5. Crear o abrir comp set.
6. Cambiar busqueda hasta sacar de `results` el hotel base y confirmar que sigue visible en el panel.
7. Revisar dark y light.
8. Revisar desktop y viewport estrecho.

## Nota de alcance

Este documento usa "Fase 1" y "Fase 2" como fases del closeout operativo de `/hoteles`, no como sustitucion de la numeracion historica del spec principal.
