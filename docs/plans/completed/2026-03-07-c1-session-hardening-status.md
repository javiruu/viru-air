# Estado real C1 - Session Hardening y Route Bridges

Fecha: 2026-03-07

## Objetivo C1
Fortalecer manejo base de sesion, limpiar rutas puente y homogeneizar errores de auth/sesion sin romper endpoints ni contratos funcionales actuales.

## Before
- Frontend:
  - `returnUrl` se validaba de forma duplicada (login/register) y `RequireAuth` no preservaba querystring al redirigir a login.
  - Manejo 401 en `api.ts` dependia de substring `invalid_token`.
- Backend:
  - 401 de auth/sesion mezclaban `invalid_token`, `invalid_credentials` y `"Not authenticated"` (cuando faltaba bearer).
- Rutas puente:
  - Redirecciones existentes en paginas, pero sin un punto unico de decision documentado/testeado.

## After
- Frontend:
  - Se centraliza sanitizacion y uso de `returnUrl` en `modules/shared/navigation.ts`.
  - `RequireAuth` redirige a login preservando `pathname + search`.
  - `api.ts` unifica tratamiento de 401 por codigos (`invalid_auth`, `invalid_token`, `session_expired`) y limpia token solo en sesion expirada/invalida.
- Backend:
  - Se estandariza detalle de 401 de auth/sesion a `invalid_auth` en deps, login y cambio de password.
  - `OAuth2PasswordBearer` pasa a `auto_error=False` para devolver 401 homogeneo tambien cuando falta token.
- Rutas puente:
  - Se define mapping central en `modules/shared/routeBridges.ts`:
    - `/history -> /watchlist`
    - `/preferences -> /preferencias/busqueda`
  - Paginas puente consumen ese mapping.

## Decisiones
- Se mantiene compatibilidad funcional total de `/api/v1/*` existentes.
- No se añaden dependencias.
- Se conserva UX actual (mismas pantallas de redireccion y feedback de login).

## Checks ejecutados
- `npm run build` (frontend): ver resultado en reporte de entrega.
- Tests backend auth/watchlist/alerts: ver resultado en reporte de entrega.
- Smoke manual C1: pasos definidos en `docs/checks/c1-smoke.md`.

## Riesgos abiertos
1. Clientes externos que dependan del detalle legacy (`invalid_token`/`invalid_credentials`) pueden necesitar ajuste a `invalid_auth`.
2. `api.ts` sigue consumiendo errores de algunos endpoints como texto libre fuera de 401.
3. Smoke C1 es manual; no hay e2e automatizado para redirecciones Next.
