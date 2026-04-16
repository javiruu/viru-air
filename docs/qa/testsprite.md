Status: reference
Scope: reusable QA reference or checklist
Last reviewed: 2026-04-15
Canonical source: docs/qa/testsprite.md
Related: docs/qa/README.md, docs/archive/qa/README.md

---
# Testsprite - Viru Tracker Test Catalog

Fecha: 2026-02-15

Este documento lista todo lo que se puede hacer en Viru Tracker segun los .md y .log del repo, para que Testsprite lo pruebe.

## Entorno objetivo
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

## Alcance funcional (usuario)
- Registro y login de usuario.
- Sesion autenticada y lectura de perfil (me).
- Dashboard (vista privada principal).
- Watchlist de vuelos (crear y listar).
- Refresh manual de un item de watchlist.
- Historial de precios.
- Quick search de rutas.
- Reglas de alertas (crear y listar).
- Preferencias de usuario (leer y actualizar).
- Sugerencias (generar).

## Alcance funcional (operacion)
- Health check /health.
- Readiness /ready.
- CORS para frontend local.
- Header x-correlation-id en respuestas.

## Rutas UI (frontend)
- Publicas: /login, /register
- Privadas: /dashboard, /watchlist, /history, /quick-search, /alerts, /preferences, /suggestions

## Endpoints API (backend)
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- GET /api/v1/auth/me
- POST /api/v1/watchlist
- GET /api/v1/watchlist
- POST /api/v1/watchlist/{watch_id}/refresh-now
- GET /api/v1/prices/history
- POST /api/v1/prices/history/batch (max 500 watch_ids)
- POST /api/v1/search/quick
- POST /api/v1/alerts/rules
- GET /api/v1/alerts/rules
- GET /api/v1/preferences
- PUT /api/v1/preferences
- POST /api/v1/suggestions
- GET /health
- GET /ready

## Casos de prueba sugeridos (P0/P1)

Autenticacion
1. Registrar usuario con email+password validos. Espera: 201/200 y usuario creado.
2. Login con credenciales validas. Espera: token JWT valido.
3. Login con password incorrecto. Espera: 401.
4. /api/v1/auth/me con token valido. Espera: datos de usuario.
5. /api/v1/auth/me sin token. Espera: 401.

Rutas privadas (UI)
1. Acceso a /dashboard sin login. Espera: redireccion a /login.
2. Acceso a /watchlist con login. Espera: render y datos.
3. Acceso a /preferences con login. Espera: render y datos.

Watchlist
1. Crear watchlist item (POST /watchlist). Espera: item creado.
2. Listar watchlist (GET /watchlist). Espera: contiene item.
3. Refresh-now con id valido. Espera: 200 y snapshot actualizado.
4. Refresh-now con id inexistente. Espera: 404.

Quick search
1. POST /search/quick con origin_iata, destination_iata, travel_date. Espera: resultados.
2. Validacion de parametros faltantes. Espera: 400.

History
1. GET /prices/history con filtros validos. Espera: serie de precios.
2. Sin token. Espera: 401.

Alerts
1. Crear regla (POST /alerts/rules). Espera: 201/200.
2. Listar reglas (GET /alerts/rules). Espera: incluye regla creada.

Preferences
1. GET /preferences. Espera: valores por defecto.
2. PUT /preferences con cambios. Espera: persistencia.
3. Verificar que afecta UI (por ejemplo currency/locale si aplica).

Suggestions
1. POST /suggestions con payload valido. Espera: sugerencias.

Health y readiness
1. GET /health. Espera: 200.
2. GET /ready. Espera: 200.

## Casos de prueba P2 (operacion)
- CORS permite origen http://localhost:3000.
- Header x-correlation-id presente en respuestas API.
- Resiliencia proveedor: si el adapter falla, el sistema expone estado degradado (stale=true) cuando aplique.

## Feature flags (si hay panel/config)
- ff_prediction_enabled (M7)
- ff_self_connect_enabled (M8)
- ff_everywhere_enabled (M9)
- ff_deeplink_hardened (M10)
- ff_country_content (M11)
- ff_full_i18n (M12)
- ff_suggestions_pipeline (M13)

Para cada flag, validar:
- Flag OFF: la funcion no aparece o responde segun la politica definida.
- Flag ON: la funcion aparece y responde correctamente.

## Notas para Testsprite
- El backend usa JWT bearer; los endpoints privados requieren Authorization: Bearer <token>.
- El backend corre por defecto en 8000 y el frontend en 3000.
- El stack base es FastAPI + Next.js; datos locales pueden usar SQLite.





