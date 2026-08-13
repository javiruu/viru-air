# H44 Revalidation Fault Profiles Implementation Plan

**Goal:** Aplicar los fault profiles locales del Mock al flujo de revalidación de tarifas y hacer visibles sus outcomes en `HotelProviderRun`, sin romper el contrato V1 ni presentar H44 como completo.

**Architecture:** `MockHotelProviderAdapter.fetch_hotel_rates()` reutiliza el fixture local y filtra la estancia solicitada. Los profiles ejecutables se aplican dentro del adapter; `sweep_tracked_offers()` conserva la regla de no crear snapshot ni reutilizar historial ante errores del provider. Los outcomes se amplían de forma aditiva con `warnings`, `warning_count`, `needs_review` y `fault_profile`, se persiste latencia por operación y `unavailable/stale` queda fuera de precio/parity/alertas. `hotel_ambiguous`, `stale_history` y `partial_batch` ya están integrados a nivel servicio; la matriz offline completa y el dry-run desechable ya están implementados en el canary.

**Tech Stack:** Python, FastAPI services, SQLAlchemy, pytest, Ruff, SQLite temporal.

---

### Task 1: Extender el contrato Mock de tarifas — COMPLETADA

**Files:**
- Modify: `backend/app/hotels/mock_provider.py`
- Modify only if needed: `backend/app/hotels/contracts.py`
- Test: `backend/tests/unit/test_hotels_fault_profiles.py`

**Steps:**
1. Añadir `fetch_hotel_rates(hotel_id, check_in, check_out, guests, currency)` al Mock.
2. Leer el fixture sin modificarlo y localizar el hotel por `provider_hotel_id`.
3. Filtrar rates por fechas, huéspedes y moneda, devolviendo una lista vacía cuando no haya coincidencia.
4. Reutilizar las transformaciones de profiles soportadas para revalidación: vacío, fallos tipados, sold out y deeplink inválido.
5. Mantener `stale_history`, `hotel_ambiguous` y `partial_batch` explícitamente fuera del comportamiento completo y documentar esa limitación en tests.
6. Añadir tests unitarios de happy path, filtro de estancia, vacío, fallos tipados, sold out y deeplink.

### Task 2: Propagar outcomes de revalidación — COMPLETADA

**Files:**
- Modify: `backend/app/services/hotels_service.py`
- Test: `backend/tests/unit/test_hotels_phase8_sweep_tracked.py`
- Test: `backend/tests/unit/test_hotels_sweep_outcomes.py`

**Steps:**
1. Conservar los contadores existentes y añadir un contador aditivo para códigos de error de profile, sin cambiar el significado de `provider_fetch_failed`.
2. Clasificar `HotelFaultProfileError` sin depender de imports circulares.
3. Asegurar que fallo, rate limit, timeout, invalid response y ausencia de rates no crean snapshot ni hacen fallback histórico cuando proceden del adapter.
4. Mantener el fallback histórico nominal del Mock únicamente para la ruta existente sin fallo/profile.
5. Verificar que `run_hotel_sweep()` persiste outcomes y determina el estado agregado sin convertir un vacío válido en `failed`.

### Task 3: Verificar sanitización y persistencia — COMPLETADA A NIVEL SERVICIO

**Files:**
- Modify: `backend/tests/integration/test_hotels_api_flow.py` or create a narrowly scoped integration test beside it.
- Test: integration coverage for `deeplink_invalid`, `sold_out`, and typed provider failure.

**Steps:**
1. Ejecutar un sweep con profile `deeplink_invalid` y comprobar que el snapshot no conserva `javascript:`.
2. Ejecutar `sold_out` y comprobar `availability_status="unavailable"`, sin convertirlo en precio cero.
3. Ejecutar un profile de error y comprobar `HotelProviderRun.status`, `error_message` sanitizado, outcomes y cero snapshots nuevos.
4. Mantener User A/B ownership fuera de este task; ya está cubierto por el smoke anterior.

### Task 4: Documentar el cierre parcial — COMPLETADA

**Files:**
- Modify: `docs/reference/backend/hoteles-seed-demo-fallos-h44.md`
- Modify: `docs/plans/2026-08-10-hoteles-auditoria-checklist-completa.md`
- Modify: `docs/plans/2026-08-04-hoteles-master-roadmap.md`

**Steps:**
1. Marcar como verificada la integración de todos los profiles soportados en revalidación/worker solo con la evidencia obtenida.
2. Mantener como pendientes solo una matriz histórica persistida entre ejecuciones y browser E2E; la matriz declarativa offline y el dry-run desechable están cerrados y el workflow backend queda configurado para ejecutar ese gate en CI; la ejecución remota queda fuera de esta sesión.
3. No declarar H44 `COMPLETA TOTAL`.

### Task 5: Validación y revisión

**Commands:**
- `cd viru-tracker/backend && python -m pytest tests/unit/test_hotels_fault_profiles.py tests/unit/test_hotels_phase8_sweep_tracked.py tests/unit/test_hotels_sweep_outcomes.py tests/integration/test_hotels_api_flow.py -q`
- `cd viru-tracker/backend && python -m pytest tests/unit/test_hotels*.py tests/integration/test_hotels*.py -q`
- `cd viru-tracker/backend && python -m ruff check app/hotels/mock_provider.py app/hotels/contracts.py app/services/hotels_service.py tests/unit/test_hotels_fault_profiles.py tests/unit/test_hotels_phase8_sweep_tracked.py tests/unit/test_hotels_sweep_outcomes.py tests/integration/test_hotels_api_flow.py`
- `cd viru-tracker && git diff --check`

**Exit criteria alcanzados para esta frontera:** 39 tests focales de profiles/canary y 320 tests de la suite hotelera relacionada pasan; la matriz de 13 profiles y `--dry-run` pasan con cero llamadas externas, cero SQLite temporal residual, comparación de expected status/run status/error/counts y redaction; Ruff/compileall/diff limpios; el workflow backend queda configurado para ejecutar el dry-run como gate CI; la ejecución remota queda fuera de esta sesión. Pendientes: browser E2E, canary comercial y, opcionalmente, una matriz histórica persistida entre ejecuciones.
