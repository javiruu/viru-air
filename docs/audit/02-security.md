# 02 — Seguridad, Secretos, Auth y Privacidad

**Fecha:** 2026-09-12  
**Commit auditado:** 91e6717d9bbd43d4ba148c6a114426266fabb823  

## 1. Secret Scanning (Working Tree + Historial Git)
- **Herramientas:** Búsqueda recursiva de patrones de credenciales, tokens, claves privadas y revisión exhaustiva de `.gitignore`.
- **Archivos de entorno encontrados en disco:**
  - `backend/.env` (ignorado por git)
  - `backend/.env.example` (trackeado, valores de plantilla sin secretos reales)
  - `frontend/.env.example` (trackeado, solo valores locales de desarrollo)
  - `infra/.env` (ignorado por git)
  - `infra/.env.prod.example` (trackeado, plantilla)
  - `infra/duckdns.local.env` (ignorado por git)
- **Archivos sensibles ignorados:** `.gitignore` incluye explícitamente `.env`, `.env.*`, `*.pem`, `*.key`, `*.db`, `*.sqlite*`, `token.txt`, `keys.txt`, `viru.db`.
- **Hallazgos:** Cero secretos reales expuestos en el árbol de trabajo trackeado.

## 2. Frontend Env Leakage (Next.js)
- **Inspección de `NEXT_PUBLIC_*`:**
  - `NEXT_PUBLIC_API_URL` (URL base de la API, ej. `/api/v1` o localhost)
  - `NEXT_PUBLIC_LOCAL_API_ORIGIN` (origen local de fallback)
  - `NEXT_PUBLIC_SITE_URL` (URL canónica del sitio)
  - `NEXT_PUBLIC_GA_MEASUREMENT_ID` (ID público de medición de Google Analytics)
- **Resultado:** Cero claves secretas, cero tokens de base de datos ni credenciales privadas expuestas en variables cliente.

## 3. Claves Privilegiadas de Supabase
- **Estado:** No existen claves de servicio ni clientes Supabase instanciados en frontend ni en backend. El archivo SQL `supabase/migrations/20260912000001_create_flight_watch.sql` define la tabla y políticas RLS pero no contiene claves embebidas.

## 4. Auth / Session Storage
- **Mecanismo:** Token JWT en `localStorage` (`viru_token`) con rotación de refresh tokens en backend.
- **Riesgo evaluado:** Tokens en `localStorage` son susceptibles a robo en caso de XSS. El backend mitiga con revocación explícita de refresh tokens en logout y validación estricta de caducidad.
- **Recomendación futura:** Evaluar migración a cookies `HttpOnly` + `Secure` + `SameSite=Lax` cuando se realice una refactorización de sesión dedicada.

## 5. Autorización Negativa (Backend Tests)
- Pruebas negativas ejecutadas y validadas en `tests/integration/test_auth_flow.py` y `test_community_pricing.py`:
  - Request sin token a ruta protegida -> 401 Unauthorized (`VERIFIED_OK`).
  - Credenciales inválidas -> 401 Unauthorized (`VERIFIED_OK`).
  - Token expirado -> 401 Unauthorized (`VERIFIED_OK`).
  - Reuso de token de reset de contraseña -> 400 Bad Request (`VERIFIED_OK`).
  - Acceso cross-user a recursos ajenos -> 403 Forbidden / Deny (`VERIFIED_OK`).

## 6. CORS, CSRF y Headers de Seguridad
- **CORS (`backend/app/main.py`):**
  - `allow_origins` parseado estrictamente desde variables de entorno.
  - `allow_credentials=True` NO convive con comodín `*`.
  - Métodos y cabeceras limitados a los requeridos (`Authorization`, `Content-Type`, `X-Correlation-Id`, `X-Client-Event-Id`).
  - Correlation ID normalizado por middleware en cada petición.

## 7. Dependencias y Vulnerabilidades
- **Frontend (`npm audit`):**
  - `esbuild` (dev, no expuesto en producción).
  - `fast-uri` (transitiva via validador).
  - `maplibre-gl <= 6.4.0` (Crítica: XSS sanitizer bypass en `DOM.sanitize()`). Requiere upgrade mayor a 6.9.0 (`DEFERRED` para no romper rendering de mapas existente).
  - `next` (Crítica: RCE en Image Optimization API con AVIF y entornos Windows específicos). Requiere `next@15.5.25` (`DEFERRED` para validación de compatibilidad con React 19).
  - `sharp` (Alta: dependiente de Next).
- **Backend:** Dependencias principales fijadas en `pyproject.toml` con rangos controlados.

## 8. Privacidad en Telemetría y Analytics
- **PostHog (`frontend/src/lib/posthog.ts`):**
  - `autocapture: false` (desactivada captura no controlada).
  - `maskAllInputs: true` y `maskTextSelector: "*"`.
  - No inicializado en producción local.
- **OpenTelemetry (`backend/app/core/telemetry.py`):**
  - Redacta atributos de clave sensible (`password`, `token`, `secret`, `authorization`).
  - No emite trazas activas ni exporta a la red.

## Veredicto de Seguridad
- Cero secretos activos en código o git.
- Autorización negativa verificada en suites reales.
- Vulnerabilidades de dependencias clasificadas con riesgo y mitigación documentada.

