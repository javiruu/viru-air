# Runbook — Supabase nativo (auth ES256, base de datos y arranque local)

**Estado:** vivo
**Última revisión:** 2026-09-22
**Fuente de verdad:** sí
**Área:** runbook / infraestructura

## Propósito

Documento canónico de cómo `viru-air` se conecta a Supabase de forma **nativa** (sin Docker, sin stack local, sin secretos compartidos heredados). Cualquier agente o persona que necesite arrancar el proyecto, depurar login o tocar la capa de autenticación debe empezar aquí.

Resumen mental en 30 segundos:

- Auth: Supabase Auth hosted emite tokens **ES256** (claves `sb_publishable_`). El backend los verifica contra el **JWKS público** del proyecto; no existe ningún secret HS256.
- Base de datos: el backend conecta como rol dedicado `viru_app` a través del **pooler de sesión** (IPv4). El esquema se aplica con `Base.metadata.create_all` (no hay Alembic en este repo).
- Red local: frontend Next.js (3000) reescribe `/api/*` hacia el backend FastAPI. El backend corre por defecto en el 8000; si ese puerto está ocupado, se usa el 8001 vía variables de entorno (ver sección Arranque).
- Data API (PostgREST) **sin permisos**: `anon` y `authenticated` no pueden leer ni escribir ninguna tabla; toda la lógica de autorización vive en el backend.

## Prerrequisitos

- Proyecto Supabase hosted activo (ref: `ttwvoliuqaqhxkkyhdvf`, región `eu-central-1`).
- `SUPABASE_ACCESS_TOKEN` (formato `sbp_...`) para operaciones de Management API y CLI.
- Python >= 3.12 con `backend/.venv` y Node >= 20 para el frontend.
- Sin dependencia de Docker ni del CLI de Supabase para el desarrollo diario.

### Arranque desde cero (clonado fresco)

La historia del repo fue reescrita el 2026-09-23 con `git-filter-repo` (purga de
binarios accidentales: runtime de Python, builds `.next_broken`, dumps y media de
skills eliminadas). Los SHAs anteriores ya no existen; cualquier clon previo a esa
fecha debe descartarse y re-clonarse. Flujo limpio:

```bash
# 1. Clonar fresco (los SHAs post-rewrite son los únicos válidos)
git clone https://github.com/javiruu/viru-air.git viru-tracker
cd viru-tracker

# 2. Backend: venv + dependencias (uv o pip)
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -e .   # o: uv sync

# 3. Config: crear backend/.env y frontend/.env.local siguiendo las secciones
#    de abajo (DB_URL con el rol viru_app, SUPABASE_URL, NEXT_PUBLIC_*).
#    El valor SUPABASE_ACCESS_TOKEN se añade a backend/.env cuando se necesite
#    el Management API (ver sección SQL puntual).

# 4. Frontend
cd ../frontend
npm ci

# 5. Arrancar (secciones Arranque local y Verificación rápida de este runbook)
```

Notas post-rewrite:

- El tamaño de `.git` quedó en ~223MB (antes 396MB). El backup temporal
  `viru-tracker-backup-rewrite.git` fue eliminado el 2026-09-23 tras verificar
  fsck, tests, tsc y smoke del backend; no hay recuperación de SHAs viejos.
- Si un PR antiguo de GitHub muestra SHAs inexistentes, es cosmético: la rama
  canónica es `main` post-rewrite.
- Referencias a rutas borradas de la historia (p. ej. `docs/archive/qa-visual/`)
  en docs históricos son válidas solo como registro; no intentes recuperarlas.

## Configuración

### Frontend — `frontend/.env.local` (git-ignored)

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://ttwvoliuqaqhxkkyhdvf.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_...
# Solo si el backend no está en el 8000 (p. ej. puerto ocupado):
NEXT_PUBLIC_LOCAL_API_ORIGIN=http://127.0.0.1:8001
INTERNAL_API_URL=http://127.0.0.1:8001/api/v1
```

### Backend — `backend/.env` (git-ignored)

```dotenv
# Rol dedicado con formato <rol>.<project-ref> para el pooler de sesión.
DB_URL=postgresql+psycopg://viru_app.ttwvoliuqaqhxkkyhdvf:<PASSWORD>@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Activa el modo de verificación asimétrica (ES256/JWKS). No pongas SUPABASE_JWT_SECRET:
# este proyecto firma con clave EC P-256 y no tiene secret HS256.
SUPABASE_URL=https://ttwvoliuqaqhxkkyhdvf.supabase.co

APP_ENV=local
RUN_SEED_USERS=true
```

Resto de flags operativas (aviation, hotels, door-to-door): ver `backend/.env.example`.

## Cómo funciona la autenticación (ES256/JWKS)

Basado en la documentación oficial de Supabase: [JWT Signing Keys](https://supabase.com/docs/guides/auth/signing-keys) y [Connecting to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres).

1. El frontend hace `signInWithPassword` contra Supabase Auth con la publishable key.
2. Supabase devuelve un access token firmado **ES256** (curva NIST P-256, el algoritmo recomendado por Supabase) con cabecera `kid`.
3. El frontend envía `Authorization: Bearer <token>` en cada llamada (el mutator de Orval lo inyecta desde la sesión de Supabase).
4. `backend/app/api/deps.py` verifica el token:
   - lee la cabecera; si `alg == ES256`, descarga (y cachea 1 h) `https://<PROYECTO>/auth/v1/.well-known/jwks.json`;
   - selecciona la clave pública por `kid`, verifica la firma y valida claims (`exp`, `nbf`, `iat`) con la misma semántica que la vía HS256;
   - si el `kid` no está en el JWKS cacheado, **fuerza un refetch** antes de rechazar: la clave pudo rotar con nuestra caché aún fresca (Supabase recomienda este patrón para backends que auto-verifican JWT; su propia caché edge dura 10 min y la revocación no es instantánea para verificadores locales);
   - si `alg != ES256`, usa el secret HS256 (`SUPABASE_JWT_SECRET`/`JWT_SECRET`): vía legacy para tests y despliegues antiguos. Si no hay secret configurado, los tokens HS256 se rechazan (fail-closed).
5. Tras verificar, aprovisiona al usuario en la tabla `users` si es su primer login (requiere `email` y confirmación en el claim `email_verified` — o dentro de `user_metadata`, según versión de GoTrue).

Notas de la doc oficial que aplican a este proyecto:

- La rotación de claves no requiere despliegue: el JWKS expone las claves nuevas y nuestro refetch-on-unknown-kid + TTL de 1 h las recogen solos.
- Supabase desaconseja HS256/shared secret para producción (revocación difícil, riesgo de fuga); ES256 es la opción por defecto de los proyectos nuevos desde octubre de 2025.
- La caché del JWKS de Supabase edge dura 10 min; si alguna vez necesitas revocación urgente (incidente de seguridad), reduce `_JWKS_TTL_SECONDS` en `deps.py` o fuerza refetch.

Puntos de código relevantes:

- `backend/app/api/deps.py` → `_fetch_supabase_jwks`, `_decode_es256_with_jwks`, `get_current_user`, `_provision_user_from_claims`.
- `frontend/src/lib/supabase/client.ts` y `server.ts` → clientes de navegador y SSR (con aviso claro si falta configuración).
- `frontend/src/api/mutator/custom-client.ts` → inyección del Bearer token y resolución idempotente del prefijo `/api/v1`.

## Base de datos

- Conexión **solo vía pooler de sesión** (`aws-0-<región>.pooler.supabase.com:5432`), con usuario `viru_app.<project-ref>` — formato oficial para roles personalizados, según [Connecting to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres). El puerto 5432 es el de sesión; el 6543 (transaction pooler) no es compatible con `pool_pre_ping`/sesiones largas de SQLAlchemy y no se usa. La conexión directa a `db.<ref>.supabase.co` requiere IPv6 o contraseña de `postgres` (no disponible).
- **Esquema:** `Base.metadata.create_all` idempotente desde `app.infrastructure.db.models`. Complementos puntuales en `app/infrastructure/db/schema_compat.py`.
- **Semillas:** `RUN_SEED_USERS=true` crea `user@viru.local` y `admin@viru.local` al arrancar.
- **RLS:** desactivada en todas las tablas de `public`. La autorización es responsabilidad del backend (`get_current_user`, `require_admin`).
- **Data API apagada:** `anon` y `authenticated` no tienen privilegios sobre `public` (tablas, secuencias ni esquema). Verificado que `rest/v1/...` responde `permission denied`. Si algún día se necesita PostgREST, reactivar RLS por tabla y crear políticas explícitas.

### SQL puntual sin conexión directa (Management API)

Para consultas/administración sin psql se puede usar el endpoint de query que usa el dashboard:

```bash
curl -s -X POST "https://api.supabase.com/v1/projects/<REF>/database/query" \
  -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"select current_user;"}'
```

Útil para: crear/ajustar roles, revocar permisos, inspeccionar tablas. No usar para operaciones de la aplicación en caliente.

## Arranque local

```bash
# Backend (puerto 8000 por defecto)
cd backend
set -a && source .env && set +a
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend (puerto 3000)
cd frontend
npm run dev
```

El rewrite de `frontend/next.config.js` apunta al **8000 por defecto** y lee
`NEXT_PUBLIC_LOCAL_API_ORIGIN`/`INTERNAL_API_URL` **solo al arrancar** el dev server:
si cambias esas variables, hay que reiniciar `npm run dev`. El 8001 es un fallback
temporal (p. ej. 8000 ocupado por un proceso zombi); en cuanto el 8000 quede libre,
quita los overrides de `frontend/.env.local` y vuelve al 8000 para no mantener dos
backends en paralelo.

### Verificación rápida (smoke)

```bash
curl http://127.0.0.1:8000/health                      # {"status":"ok"}
# Login real desde http://localhost:3000/login y comprobar el dashboard.
# Token ES256 de prueba contra un endpoint autenticado:
curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
  http://127.0.0.1:8000/api/v1/account/profile
```

## Solución de problemas

| Síntoma | Causa probable | Acción |
| --- | --- | --- |
| `401 invalid_auth` con token ES256 | JWKS no accesible o `SUPABASE_URL` mal puesto en backend | Verificar `SUPABASE_URL` en `backend/.env`; comprobar `GET /auth/v1/.well-known/jwks.json` desde la máquina |
| 401 y en el log aparece "HS256 token received while only ES256/JWKS verification is configured" | Frontend y backend apuntan a proyectos Supabase distintos | Igualar `NEXT_PUBLIC_SUPABASE_URL` (frontend) y `SUPABASE_URL` (backend) |
| `permission denied for table ...` en inserts del backend | RLS reactivada o permisos de `viru_app` perdidos | Reaplicar `GRANT ALL ON SCHEMA public TO viru_app` (+ tablas/seq) y `ALTER TABLE ... DISABLE ROW LEVEL SECURITY` si aplica |
| `ERR_NAME_NOT_RESOLVED` hacia `mock.supabase.co` | Falta `NEXT_PUBLIC_SUPABASE_URL`/`ANON_KEY` en el frontend | Rellenar `frontend/.env.local` (el cliente avisa por consola con instrucciones) |
| 404 en `/api/v1/api/v1/...` | Doble prefijo por mutator | Ya corregido (`resolveFullUrl` idempotente); si reaparece, revisar `custom-client.ts` |
| Backend no arranca: `error while attempting to bind on port 8000` | Puerto ocupado por proceso de otra sesión | Arrancar en 8001 y usar `NEXT_PUBLIC_LOCAL_API_ORIGIN` + `INTERNAL_API_URL` |
| Login correcto pero dashboard vacío / 404 en notificaciones | Backend caído o rewrite apuntando a otro puerto | Confirmar `curl /health` del backend y las variables de rewrite del frontend |
| `Failed to proxy .../api/v1/... [ECONNRESET]` + 500 en `/api/v1/*` | El rewrite del frontend apunta a un puerto donde no hay backend vivo (p. ej. 8001 apagado) | Alinear `NEXT_PUBLIC_LOCAL_API_ORIGIN`/`INTERNAL_API_URL` con el puerto real del backend y reiniciar el dev server de Next |

## Mantenimiento y rotación

- Rotación de claves JWT (JWKS): el refetch-on-unknown-kid y el TTL de 1 h recogen las claves nuevas sin despliegue ni intervención. Para revocación urgente (incidente), reduce `_JWKS_TTL_SECONDS` o reinicia el backend tras rotar y revocar en el dashboard.
- Rotación de la contraseña de `viru_app`: `ALTER ROLE viru_app WITH PASSWORD '...'` vía SQL API + actualizar `DB_URL` y reiniciar backend.
- Altas de tablas nuevas: crear modelo en `models.py`; `create_all` las incorporará al arrancar. Si cambias un modelo existente, añade la columna con una función en `schema_compat.py` (no hay migraciones formales).

## No hacer

- No usar el stack local de Supabase (`supabase start`) ni Docker: este runbook es la referencia nativa.
- No reactivar RLS sin crear primero las políticas que el backend necesita (rompería todos los inserts).
- No conceder permisos a `anon`/`authenticated` sobre `public` (expondría la base de datos por la Data API).
- No commitear `.env.local` ni `backend/.env` (están git-ignored; verificación: `git check-ignore -v backend/.env frontend/.env.local`).
