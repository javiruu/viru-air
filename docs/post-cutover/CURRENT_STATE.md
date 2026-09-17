# ESTADO ACTUAL (POST-HARDENING)

**Fecha de recuento:** 17 Septiembre 2026
**Ubicación:** `docs/post-cutover/CURRENT_STATE.md`

## 1. Estado de Git (Recuento)
- **Archivos modificados/staged:** 468 archivos (`24322 insertions(+), 19105 deletions(-)`)
- **Archivos untracked (nuevos):** Múltiples scripts, pruebas de migraciones, reportes finales (e.g. `FINAL_CUTOVER_REPORT.md`, `backend/scripts/`, `docs/migration/final-decommission-v3/`, `supabase/`).
- **Riesgo:** El volumen de cambios en el working tree es masivo. Es imperativo separar y commitear estos cambios antes de realizar nuevas implementaciones de código.

## 2. Inventario de Código (Recuento de referencias)

Se han analizado las referencias clave para medir la adopción real y la deuda pendiente.

### 2.1. Frontend (`frontend/src`)
- **Auth storage mechanisms** (`localStorage`, `sessionStorage`, `sb_access_token`, etc.): **6 referencias**
- **Consumidores del cliente API legacy** (`apiFetch`, `apiFetchWithStatus`, `fetch(`, `@/modules/shared/api`): **4 referencias**
- **Imports de Orval/TanStack** (`src/api/generated`, `useQuery`, `useMutation`, etc.): **6 referencias**

*Nota:* Aún existe uso residual del sistema antiguo de fetching. El storage local para auth se utiliza en 6 puntos, lo que exige consolidar a una sola autoridad (Cookies/SSR) en la próxima fase.

### 2.2. Global y Deuda Técnica
- **Referencias a SQLite, Alembic y Docker:** **131 referencias** (en código, comentarios o documentación, excluyendo dependencias/builds). 
- **Estado de los slices SHADOW_VERIFIED:** **9 referencias** encontradas (el estado de la base de datos y la auth aún figuran como `SHADOW_VERIFIED` en la documentación/auditorías en lugar de estar 100% probados en un entorno remoto puro).

## 3. Estado de los Gates Rápidos
- **Frontend Typecheck (`tsc --noEmit`):** PASS
- **Frontend Lint (`eslint . --max-warnings 0`):** PASS
- **Backend Tests (`pytest`):** PENDIENTE (entorno virtual no cargado correctamente en la primera pasada, requiere ejecución manual o CI).

## 4. Conclusión y Siguientes Pasos
El estado "verde" en compilación es engañoso frente a la cantidad de deuda remanente (`SHADOW_VERIFIED` y 131 menciones de tecnologías legacy). 
1. **Paso inmediato:** Aislar los 468 archivos en commits semánticos separados.
2. **Setup STAGING:** Desplegar el esquema a un proyecto Supabase real remoto para validar schema y matriz RLS sin Docker, tal y como exige `VIRU_NEXT_STEPS_AFTER_CUTOVER.md`.