Status: archived
Scope: archived tooling-generated report or summary
Last reviewed: 2026-04-15
Original source: testsprite_tests/SKILLSPRITE_USER_CAPABILITIES.md
Related: docs/archive/README.md, docs/INDICE_UNICO.md

---
# SkillSprite - Mapa Completo de Capacidades de Usuario (Viru Tracker)

Fecha de consolidacion: 2026-02-17  
Fuentes revisadas: `docs/`, `logs/`, `logs_ia/`

## Alcance
Este documento enumera todo lo que puede hacer un usuario en Viru Tracker, separando capacidades por tipo de usuario y por modulo, para uso directo en SkillSprite (diseno de pruebas funcionales y E2E).

## Roles de usuario
- `Visitante (no autenticado)`: puede ver landing, politicas, login y registro.
- `Usuario autenticado`: puede usar dashboard, watchlist, historico, quick search, alertas, preferencias, sugerencias y notas personales.
- `Administrador`: ademas de lo anterior, puede operar usuarios/watchlists desde panel admin.

## Rutas UI disponibles
- Publicas: `/`, `/login`, `/register`, `/policies`
- Privadas usuario: `/dashboard`, `/watchlist`, `/history`, `/quick-search`, `/alerts`, `/preferences`, `/suggestions`
- Privada admin: `/admin`
- Fallback: `not-found` personalizado

## Capacidades del visitante
- Registrarse con email y password.
- Iniciar sesion.
- Ver pagina de politicas.
- Navegar landing y acceder a login/registro.

## Capacidades del usuario autenticado

### 1) Sesion y cuenta
- Mantener sesion con JWT bearer.
- Cerrar sesion.
- Al cerrar sesion, redireccion a landing (`/`) y no a `/login`.
- Ver estado de cuenta desde menu de usuario.
- Cambiar tema (claro/oscuro) de forma global.

### 2) Dashboard
- Ver KPIs de usuario activo, vuelos activos y actividad reciente.
- Acceder a modulos principales: Watchlist, Busqueda rapida, Sugerencias.
- Acceder a modulos operativos: Alertas, Historico, Actividad reciente.
- Ver modulo unico de `Sugerencias` (sin duplicidad con Alertas/Quick Search).
- Ver y gestionar notas personales dentro del dashboard.
- Crear nota.
- Editar nota.
- Eliminar nota.

### 3) Watchlist
- Crear vuelo en seguimiento.
- Listar vuelos en seguimiento.
- Refrescar manualmente un vuelo (`refresh-now`).
- Ver estado y precio por vuelo.
- Usar historial integrado y comparativa visual (segun redisenos documentados en logs_ia).

### 4) Historico de precios
- Consultar historico por `watch_id`.
- Ver snapshots de precio (incluyendo hora de salida cuando aplica).
- Aplicar filtros de historico en UI.
- Cambiar vista de historico (lineal/calendario en implementaciones de referencia UI).

### 5) Quick Search (busqueda rapida)
- Buscar rutas por origen, destino y fecha.
- Buscar ida y opcion ida/vuelta.
- Ajustar adultos (stepper).
- Aplicar filtros avanzados:
- radio de busqueda
- origenes/destinos cercanos
- ventanas horarias
- incluir/excluir escalas
- maximo de escalas
- exclusiones por IATA
- modo estricto/relajado
- flexibilidad de fechas (`dias_antes`, `dias_despues`)
- riesgo, precio, duracion y orden (segun evolucion UI en logs_ia)
- Ver resultados enriquecidos con metadatos:
- precio/currency
- duracion
- escalas
- `risk_label`
- `freshness_ts`
- `stale_data` (modo degradado)
- `ranking_score`
- Abrir deeplink de compra en Ryanair.
- Guardar resultado en watchlist.
- Copiar parametros cuando no hay deeplink.
- Ver clima origen/destino durante ventana consultada (weather cards en UI).
- Ver estado de busqueda: idle, loading, success, empty, error, rate limit.
- Usar selector de aeropuertos por pais con buscador y recientes.

### 6) Alertas
- Crear regla de alerta por vuelo.
- Tipos soportados:
- `threshold_low`
- `threshold_high`
- `every_change`
- Configurar `cooldown_minutes`.
- Configurar `notify_on_every_change`.
- Listar reglas por vuelo.
- Pausar/activar regla.
- Eliminar regla.
- Ejecutar simulacion/evaluacion inmediata (`/alerts/evaluate`).
- Consultar historial de eventos de alerta (`/alerts/events`).

### 7) Preferencias
- Leer preferencias de usuario.
- Actualizar preferencias.
- Persistir defaults usados por Quick Search (radio, escalas, horario, idioma, moneda, segun fuentes).

### 8) Sugerencias
- Enviar sugerencias/feedback al sistema.
- Enviar en ES o EN.
- Validacion de longitud y estado de envio.

### 9) Aeropuertos y compatibilidad
- Buscar compatibilidad de aeropuertos por origen/destino+fecha.
- Consultar aeropuertos cercanos (endpoint presente en API).

## Capacidades de administrador
- Listar usuarios.
- Cambiar password de usuario.
- Eliminar usuario.
- Listar watchlist de un usuario concreto.
- Crear item de watchlist para un usuario.
- Eliminar item de watchlist.
- Acceso admin protegido (usuario no admin redirigido a dashboard).

## API de capacidades (resumen operativo)
- Auth: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- Watchlist: `POST /api/v1/watchlist`, `GET /api/v1/watchlist`, `POST /api/v1/watchlist/{watch_id}/refresh-now`
- Prices: `GET /api/v1/prices/history`, `POST /api/v1/prices/history/batch` (hasta 500 watch_ids, `max_rows` 1..20000, `captured_since_utc` opcional)
- Search: `POST /api/v1/search/quick`, `GET /api/v1/search/deeplink`
- Alerts: `POST /api/v1/alerts/rules`, `GET /api/v1/alerts/rules`, `PUT /api/v1/alerts/rules/{rule_id}`, `DELETE /api/v1/alerts/rules/{rule_id}`, `POST /api/v1/alerts/evaluate`, `GET /api/v1/alerts/events`
- Preferences: `GET /api/v1/preferences`, `PUT /api/v1/preferences`
- Suggestions: `POST /api/v1/suggestions`
- Notes: `GET /api/v1/notes`, `POST /api/v1/notes`, `PUT /api/v1/notes/{note_id}`, `DELETE /api/v1/notes/{note_id}`
- Airports: `GET /api/v1/airports/compatible`, `GET /api/v1/airports/nearby`
- Admin: `GET /api/v1/admin/users`, `PUT /api/v1/admin/users/{user_id}/password`, `DELETE /api/v1/admin/users/{user_id}`, `GET /api/v1/admin/users/{user_id}/watchlist`, `POST /api/v1/admin/users/{user_id}/watchlist`, `DELETE /api/v1/admin/watchlist/{watch_id}`
- Ops: `GET /health`, `GET /ready`

## Eventos de analitica detectados
- `quicksearch_open_ryanair`
- `dashboard_click_watchlist`
- `dashboard_click_quick_search`
- `dashboard_click_suggestions`
- `dashboard_suggestion_apply`
- `dashboard_alerts_open`

## Evidencia operativa en logs (para priorizar pruebas)
- Respuestas `200` predominan en ejecuciones recientes.
- Existen `401` esperables por accesos sin token en rutas privadas.
- Existen `422` historicos por validacion de payload/auth.
- Se detectaron incidencias de entorno Windows (`WinError 5`, `EPERM`) en ejecuciones concretas.

## Checklist SkillSprite recomendado (alto valor)
- Login/registro y proteccion de rutas privadas.
- Flujo completo Quick Search -> abrir Ryanair -> guardar watchlist.
- Flujo Watchlist -> refresh-now -> Historico.
- Flujo Alertas completo: crear -> pausar/activar -> simular -> revisar eventos.
- Flujo Dashboard con notas CRUD y modulo unificado Sugerencias.
- Flujo Preferencias y persistencia en Quick Search.
- Flujo admin: listar usuarios y operar watchlists de terceros.
- Smoke de `/health` y `/ready`.






