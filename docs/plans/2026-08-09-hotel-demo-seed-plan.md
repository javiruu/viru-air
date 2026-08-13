# Hotel Demo Seed/Reset Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Añadir un CLI H44 que prepare y limpie un dataset hotelero Mock reproducible sobre SQLite temporal sin tocar datos fuera del scope demo.

**Architecture:** `backend/scripts/hotel_demo_seed.py` ejecuta Alembic `head`, valida una DB SQLite dentro del workspace temporal y aplica un dataset declarado `hoteles-demo-v1`. El seed es idempotente: reutiliza usuarios, hoteles, aliases, snapshots, tracked offers, reglas, eventos y deliveries identificados por claves sintéticas. El reset requiere entorno seguro, DB temporal, dataset explícito y confirmación; borra únicamente filas de los usuarios demo y hoteles/aliases/runs del provider `mock` que pertenecen al dataset.

**Tech Stack:** Python, SQLAlchemy, Alembic, SQLite temporal, pytest.

---

### Task 1: Manifest y contrato del CLI

**Files:**
- Create: `backend/app/hotels/fixtures/hoteles_demo_manifest.json`
- Create: `backend/scripts/hotel_demo_seed.py`
- Test: `backend/tests/unit/test_hotel_demo_seed.py`

- Definir `dataset_id=hoteles-demo-v1`, `fixture_version=1`, `synthetic_label=DEMO_NO_LIVE_AVAILABILITY`, `provider_mode=mock`, `expected_external_calls=0` y fechas fijas.
- Exigir `--db-url` explícita, SQLite absoluta dentro de `tempfile.gettempdir()`, y no reutilizar la DB por defecto de la aplicación.
- Exponer `seed` y `reset`, output JSON redacted y códigos no-cero para configuración insegura.

### Task 2: Seed idempotente

**Files:**
- Modify: `backend/scripts/hotel_demo_seed.py`
- Test: `backend/tests/unit/test_hotel_demo_seed.py`

- Ejecutar `alembic upgrade head` en la DB aislada.
- Crear/reutilizar `demo-user-a@viru.local` y `demo-user-b@viru.local` con password sintética fija solo para QA.
- Ejecutar ingestión Mock con `HOTEL_PROFILE=local_fixture`, `HOTEL_FEATURE_ENABLED=true`, `HOTEL_SWEEP_ENABLED=false`, `HOTEL_GEOCODER_ENABLED=false`.
- Crear/reutilizar watchlist, tracked offer, snapshot histórico, regla y evento/delivery para User A; crear una regla/evento equivalente para User B sin compartir ownership.
- Reportar counts por tabla, rows created/reused y cero llamadas externas.

### Task 3: Reset acotado y fail-closed

**Files:**
- Modify: `backend/scripts/hotel_demo_seed.py`
- Test: `backend/tests/unit/test_hotel_demo_seed.py`

- Rechazar `reset` sin `--confirm-demo-db`, con `APP_ENV` inseguro, dataset incorrecto, DB no temporal, URL no SQLite o scope ausente.
- Borrar primero deliveries/events/rules/tracked offers/watchlists/snapshots/aliases/provider runs y hoteles/usuarios demo, respetando FKs.
- Verificar que no quedan filas del scope y que la operación no elimina una fila sentinel fuera del dataset.

### Task 4: Validación y documentación

**Files:**
- Modify: `docs/reference/backend/hoteles-seed-demo-fallos-h44.md`
- Modify: `docs/reference/backend/hoteles-release-canary-smoke-rollback-h45.md`

- Actualizar H44 para separar el CLI, fault profiles y browser E2E local ya verificados de los gates externos aún pendientes (canary comercial, cross-browser y QA humano).
- Ejecutar tests unitarios H44, suite hotelera focalizada, Ruff, compileall, CLI seed dos veces, reset confirmado y `git diff --check`.
- Revisar privacidad, aislamiento y claims con un reviewer independiente.
