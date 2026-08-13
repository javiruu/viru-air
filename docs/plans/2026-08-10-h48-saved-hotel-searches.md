# H48 Saved Hotel Searches Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar búsquedas hoteleras guardadas privadas, restaurables y con ownership server-side, reutilizando el estado URL canónico existente.

**Architecture:** Añadir una entidad `SavedHotelSearch` con payload canónico JSON, fingerprint determinista y lifecycle local `active/paused/deleted`. El backend expondrá CRUD autenticado y filtrado por `user_id`; el frontend añadirá API/hook/panel para guardar y restaurar la intención sin ejecutar providers al montar. Los tokens públicos, expiración productiva, share links opacos y llamadas implícitas al provider quedan fuera de este bloque.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, Next.js/React, TypeScript, Node test runner y pytest.

---

### Task 1: Añadir el modelo y migración de SavedHotelSearch

**Files:**
- Modify: `backend/app/infrastructure/db/models.py`
- Create: `backend/alembic/versions/0056_hotel_saved_searches.py`
- Test: `backend/tests/unit/test_alembic_audit.py`

**Steps:**
1. Crear `HotelSavedSearch` con ID UUID opaco, `user_id`, `schema_version`, `fingerprint`, `canonical_query_json`, `label`, `status`, `created_at`, `updated_at`, `last_used_at`.
2. Añadir índice por owner/status y unicidad `(user_id, fingerprint)` para idempotencia local.
3. Crear migración `0056` con FK a `users(id)` `ON DELETE CASCADE`, límites de longitud y defaults seguros.
4. Actualizar la auditoría de Alembic si requiere declarar la nueva revisión.
5. Ejecutar `alembic upgrade head` y `alembic check` sobre SQLite temporal.

### Task 2: Añadir schemas y servicio CRUD con ownership

**Files:**
- Modify: `backend/app/domain/hotels_schemas.py`
- Modify: `backend/app/services/hotels_service.py`
- Test: `backend/tests/unit/test_hotels_saved_searches.py`

**Steps:**
1. Definir `HotelSavedSearchCreateIn`, `HotelSavedSearchUpdateIn` y `HotelSavedSearchOut`.
2. Validar schema version, fingerprint, JSON canónico, label y estados permitidos.
3. Implementar listar, crear idempotentemente por fingerprint, obtener, actualizar label/status y borrar.
4. Resolver siempre por `user_id`; recursos ajenos se comportan como `not_found` o `PermissionError` según el patrón hotelero existente.
5. No guardar snapshots, targets, alert rules, tokens ni payloads crudos de provider.
6. Cubrir aislamiento entre usuarios, duplicado idempotente, pausa, restauración, borrado y payload inválido.

### Task 3: Exponer API autenticada

**Files:**
- Modify: `backend/app/api/v1/hotels.py`
- Test: `backend/tests/integration/test_hotels_saved_search_api.py`

**Steps:**
1. Añadir `GET/POST /hotels/saved-searches`, `GET/PATCH/DELETE /hotels/saved-searches/{id}`.
2. Mapear errores a códigos HTTP consistentes sin filtrar existencia privada.
3. Aceptar únicamente el payload canónico ya sanitizado por el frontend/backend; no ejecutar búsqueda ni provider en estas mutaciones.
4. Verificar tests con dos usuarios y reintentos de creación.

### Task 4: Integrar API y UI mínima de guardado/restauración

**Files:**
- Modify: `frontend/src/modules/hotels/api.ts`
- Create/Modify: `frontend/src/modules/hotels/hooks/useSavedHotelSearches.ts`
- Create/Modify: `frontend/src/modules/hotels/components/HotelSavedSearchesPanel.tsx`
- Modify: `frontend/src/modules/hotels/HotelRadarPage.tsx`
- Modify: `frontend/src/i18n/domains/hotels.ts`
- Test: `frontend/tests/hotels-saved-searches.test.ts`

**Steps:**
1. Añadir tipos y funciones API para listar/crear/actualizar/borrar búsquedas guardadas.
2. Serializar únicamente el subconjunto público soportado por `hotelSearchUrlState`; generar fingerprint desde la query canónica.
3. Añadir acción “Guardar búsqueda” cuando exista una intención válida y panel de búsquedas guardadas.
4. Restaurar un registro en la URL/formulario sin llamar al provider automáticamente; la búsqueda seguirá siendo acción explícita.
5. Mostrar estados loading/empty/error/success y diferenciar búsqueda guardada de hotel guardado/tracking.
6. Cubrir copy ES/EN, sanitización y no ejecución implícita mediante tests existentes de fuente/API.

### Task 5: Validación y documentación de alcance

**Files:**
- Modify: `docs/reference/backend/hoteles-busquedas-guardadas-compartibles-h48.md`
- Modify: `docs/qa/hotels-pending-closeout.md`

**Steps:**
1. Ejecutar suites backend H48/tracking/API y frontend URL/H36/H48.
2. Ejecutar typecheck, ESLint, Alembic, canary offline, recovery drill y `git diff --check`.
3. Actualizar H48 para distinguir el CRUD privado implementado de los pendientes: share tokens públicos, expiración productiva, cache privada avanzada, browser QA y provider live.
4. Revisar el cambio con code-reviewer-luna y corregir cualquier issue accionable.
