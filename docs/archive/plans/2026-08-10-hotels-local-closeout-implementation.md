# Hoteles — Cierres locales H04/H43/H55

**Objetivo:** cerrar los pendientes locales verificables de allowlist H04, auditoría de flags H43 y recovery drill H55 sin activar providers comerciales ni infraestructura productiva.

**Arquitectura:** reutilizar `resolve_hotel_activation()` como única fuente de decisión. Añadir una auditoría pura que evalúe los entrypoints API/worker/job directo bajo el mismo entorno y produzca evidencia redacted. Centralizar la allowlist de eventos hoteleros en el contrato UX existente. Implementar un drill offline que cree una SQLite temporal, ejecute migraciones/seed, haga snapshot físico, restaure a otra SQLite temporal y valide conteos, ownership, schema y limpieza.

**Tecnologías:** Python, SQLAlchemy, Alembic, FastAPI/Pydantic, pytest, SQLite temporal.

---

### Tarea 1: Auditoría unificada de flags

**Archivos:**
- Modificar: `backend/app/hotels/activation.py`
- Crear: `backend/scripts/hotel_activation_audit.py`
- Crear: `backend/tests/unit/test_hotel_activation_audit.py`
- Actualizar: `docs/reference/backend/hoteles-flags-canary-killswitch-h43.md`

**Pasos:**
1. Añadir una evaluación pura de los entrypoints `api_read`, `worker_sweep` y `direct_job` bajo un perfil/configuración dada.
2. Verificar que los entrypoints de sweep comparten `enabled`, `reason` y provider; las lecturas siguen disponibles con la feature apagada.
3. Emitir JSON redacted con profile, flags booleanas, decisiones allowlisted, consistencia y limitaciones.
4. Cubrir combinaciones `local_fixture` activo, feature apagada, sweep apagado, provider comercial sin enable y `prod_off`.
5. Ejecutar tests unitarios y documentar el alcance local, no productivo.

### Tarea 2: Allowlist de eventos hoteleros H04

**Archivos:**
- Modificar: `backend/app/api/v1/ux.py`
- Modificar: `backend/tests/integration/test_ux_api_flow.py`
- Crear o actualizar: `frontend/src/modules/hotels/hotelRum.ts` si el contrato frontend necesita versión explícita
- Actualizar: `docs/product/hoteles-metrics-events-h04.md`

**Pasos:**
1. Definir eventos hoteleros permitidos y sus metadatos tipados/versionados.
2. Reutilizar el validador existente para rechazar claves privadas, versiones inválidas y valores fuera de bucket.
3. Añadir cobertura para un evento de producto hotelero permitido, claves desconocidas y PII/IDs rechazados.
4. Mantener compatibilidad con `hotel_rum_vitals` y no ampliar el endpoint a eventos arbitrarios.
5. Ejecutar la suite UX y tests frontend RUM.

### Tarea 3: Recovery drill H55 aislado

**Archivos:**
- Crear: `backend/scripts/hotel_recovery_drill.py`
- Crear: `backend/tests/unit/test_hotel_recovery_drill.py`
- Actualizar: `docs/reference/backend/hoteles-continuidad-disaster-recovery-h55.md`
- Actualizar: `docs/qa/hoteles-h56-annual-review-2026-08-05.md`

**Pasos:**
1. Exigir `APP_ENV` seguro y una SQLite temporal nueva; nunca aceptar DB de producción/staging.
2. Ejecutar `alembic upgrade head`, seed H44, checkpoint físico y restore a una segunda SQLite temporal.
3. Validar schema head, conteos por tablas, usuarios/hoteles demo, separación User A/B y sentinel fuera del scope.
4. Reportar RPO/RTO del ejercicio local, rows restauradas, cleanup y limitaciones.
5. Añadir tests de aislamiento, restore correcto y rechazo de rutas inseguras.

### Tarea 4: Evidencia y gates

**Archivos:**
- Crear: `docs/qa/evidence/hotels-local-closeout-current/` con reportes redacted
- Actualizar: `docs/plans/2026-08-10-hoteles-auditoria-checklist-completa.md`
- Actualizar: `docs/plans/2026-08-04-hoteles-master-roadmap.md`

**Pasos:**
1. Ejecutar auditoría de flags, allowlist y recovery drill en local.
2. Ejecutar suites backend/frontend, Alembic y diff check.
3. Revisar cambios con code review independiente.
4. Marcar H04/H43/H55 como cerrados solo en alcance local; mantener provider live, cross-browser humano, legal, delivery externo y release real como bloqueos externos.
