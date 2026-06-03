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
8. Cierre de Fase 4 de este closeout: la UI minima de alertas hoteleras ya existe en `/hoteles`, con reglas `price_below`, `price_above` y `parity_break`, listado de eventos recientes por hotel seleccionado y estados `loading` / `empty` / `error`.
9. Cierre de Fase 5 de este closeout: `HOTEL_FEATURE_ENABLED` queda limitado a ingesta, providers y sweeps, sin apagar la lectura ni la navegacion de `/hoteles`.
10. Cierre de Fase 6 de este closeout: Makcorps valida payloads/rates invalidos, no promete fallback automatico a mock y deja la TTL documentada como reserva futura.

Pendiente:

1. Verificación visual manual en navegador real (dark/light/responsive/focus/copy).

## Actualización 2026-06-03 (cierre Fase 9)

Completado en esta pasada:

1. Añadida función `deleteHotelCompSetMember` en el API frontend.
2. Añadido `handleDeleteMember` en `HotelRadarPage`.
3. Añadida sección de lista de miembros con botón "Quitar" en `HotelCompSetPanel`.
4. Añadidas strings i18n para la sección de miembros (ES + EN).
5. Añadido CSS para la sección de miembros del comp set.
6. Añadido polish visual: hover/focus/transiciones en result cards y comp set items.
7. Corregido `import datetime` faltante en `parity.py`.
8. Creado `docs/qa/hotels-visual-qa.md` con el registro de cambios y checklist de verificación.

Pendiente:

1. Verificación visual manual en navegador real.
2. `deleteHotelCompSet` (backend no expone DELETE de comp set entero).

## Orden recomendado de trabajo

1. Fase 5: aclarar `HOTEL_FEATURE_ENABLED`.
2. Fase 6: endurecer Makcorps.
3. Fase 7A: documentar sweeps manuales.
4. Fase 7B: scheduler opcional solo si se decide automatizar.
5. Fase 8: busqueda robusta por ciudad con acentos.
6. Fase 9: QA visual y polish final.
7. Fase 10: cierre documental final.

## Archivos probables por fase posterior

Fase 7A-7B:
- `docs/runbooks/hotels-sweeps.md`
- `backend/app/worker/hotels_sweep.py`
- tests backend del flujo de sweep

Fase 8:
- `backend/app/infrastructure/db/models.py`
- `backend/alembic/versions/0019_hotels_normalized_city.py`
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
4. Riesgo de sobreprometer automatizacion de sweeps si se documenta como integrado al API cuando en realidad vive en worker separado.
5. Integracion Makcorps con semantica ambigua si se documenta mas de lo que hoy implementa.
6. La UI de alertas ya no depende de los ultimos 50 eventos globales, pero sigue pendiente validacion visual manual del flujo completo en navegador.

## Checks necesarios

Checks ya ejecutados para este cierre:

1. `cd backend && python -m pytest backend/tests/unit/test_hotels_ingestion.py backend/tests/unit/test_hotels_makcorps_provider.py backend/tests/integration/test_hotels_api_flow.py` -> `46 passed`
2. `cd frontend && npm run build` -> OK

Checks no disponibles como comando separado en este momento:

1. `cd frontend && npm run typecheck` no existe como script en `package.json`.

Checks recomendados para el siguiente cierre visual:

1. Abrir `/hoteles`.
2. Cargar fixture mock.
3. Buscar hotel.
4. Seleccionar hotel y confirmar senal de paridad desde backend.
5. Crear alerta `price_below`.
6. Crear alerta `parity_break`.
7. Confirmar que eventos recientes corresponden al hotel seleccionado.
8. Crear o abrir comp set.
9. Cambiar busqueda hasta sacar de `results` el hotel base y confirmar que sigue visible en el panel.
10. Revisar dark y light.
11. Revisar desktop y viewport estrecho.

## Actualizacion 2026-06-03 (closeout Fases 7 y 8)

Completado en esta pasada:

1. Existe runbook canonico en `docs/runbooks/hotels-sweeps.md` con comando manual exacto, variables, tablas afectadas y forma de verificar `HotelProviderRun` y `HotelAlertEvent`.
2. La operativa queda descrita con honestidad: no hay scheduler integrado al startup del API.
3. Existe worker opcional separado en `backend/app/worker/hotels_sweep.py`, gobernado por `HOTEL_SWEEP_ENABLED=false` y `HOTEL_SWEEP_INTERVAL_SECONDS=3600`.
4. El worker puede ejecutarse `--once` o `--loop` sin bloquear startup ni requests del API.
5. `HotelProperty` guarda `normalized_city` y la busqueda por ciudad usa ese campo en vez de `city` crudo.
6. La migracion `0019_hotels_normalized_city` hace backfill para hoteles existentes antes de exigir el campo.
7. Queda cubierta la deuda de acentos y mayusculas/minusculas para filtros de ciudad como `Malaga`/`Málaga` y `Cordoba`/`Córdoba`.

## Nota de alcance

Este documento usa "Fase 1" y "Fase 2" como fases del closeout operativo de `/hoteles`, no como sustitucion de la numeracion historica del spec principal.

## Actualizacion 2026-06-03 (closeout Fases 5 y 6)

Completado en esta pasada:

1. `HOTEL_FEATURE_ENABLED` queda aclarado como flag de ingesta, providers y sweeps; no apaga la navegacion ni la lectura de `/hoteles` si ya hay datos.
2. El copy del frontend deja de presentar el flag como si toda la ruta estuviera desactivada.
3. Makcorps deja de prometer fallback automatico a mock.
4. `HOTEL_PROVIDER_CACHE_TTL_SECONDS` queda documentado como reservado para una fase futura, sin cache runtime activa.
5. El parser Makcorps descarta rates con importe no positivo, moneda invalida o fechas invalidas, pero mantiene hoteles validos aunque se queden sin rates utilizables.
6. La respuesta top-level malformada de Makcorps se trata como error controlado y los logs evitan exponer `MAKCORPS_API_KEY`.
