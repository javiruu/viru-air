# Briefing de contexto de Viru para IA

> Documento vivo. Lo generado en sesiones IA debe consolidarse aqui, no repetirse en cada conversacion.
>
> Estado: vivo
> Ultima revision: 2026-09-01
> Fuente de verdad: si, junto con DESIGN.md y los contratos en docs/reference/backend/*
> Area: prompts / contexto IA
>
> Generado por la sesion del 2026-09-01 a partir de cinco agentes en paralelo (identidad, producto, voz, frontend/tokens, operativa/QA) sobre el repo canonico. Cuando un punto entra en conflicto entre documentos, sigue la jerarquia: DESIGN.md manda en visual y voz, los contratos en docs/reference/backend/* mandan en API, y docs/overview/current-state.md manda en que hay vivo hoy.

## 0. Como usar este briefing

- Leelo entero antes de un cambio no trivial.
- Si vas a tocar visual, lee DESIGN.md y docs/reference/ui-visible-language-guide.md antes de tocar codigo.
- Si vas a tocar una ruta, lee su docs/product/<x>.md y su contrato en docs/reference/backend/<x>-contract.md antes.
- Si vas a anadir un patron, mira primero frontend/src/styles/components.css y los patrones compartidos: si es reutilizable dos veces, va a tokens/components, no al componente local.
- Si dudas entre simple generico y controlado con personalidad, gana el segundo.
- Si el usuario te pide algo que rompe cualquiera de las reglas innegociables, explicale el tradeoff antes, no lo asumas en silencio.

---

## 1. Quien es Viru y que NO es

- Vuelo + watchlist + historico + alertas, no un SaaS de viajes.
- Cabina viva: informacion precisa, orientacion inmediata, personalidad que acompana.
- Calido, aeronautico, animado, distintivo, humano.
- NO es un dashboard generico, ni un panel corporativo frio, ni una UI de aerolinea clasica.  No generic SaaS significa mas personalidad, no menos.
- Dual por contrato: dark (Aviation Dark-Luxe, profundo y calido, nunca lugubre/gamer/neon) y light (luminosa con alma, nunca blanco plano corporativo) comparten personalidad.

### Principios de identidad calida (resumen de AGENTS.md y DESIGN.md)

1. Calidez antes que frialdad.
2. Personalidad antes que neutralidad.
3. Movimiento intencionado, no inmovilidad.
4. Claridad sin austeridad.
5. Premium pero cercano, nunca distante.
6. Estetica aeronautica, no UI corporativa de aerolinea.
7. Modo claro con alma, no blanco plano generico.
8. Modo oscuro cinematografico, nunca lugubre.
9. Interfaz que se siente disenhada, no ensamblada.
10. Pequenos detalles que hagan sonreir sin estorbar.

---

## 2. Reglas innegociables del repo

Estas viven en AGENTS.md, frontend/AGENTS.md, tests/AGENTS.md y DESIGN.md. Cualquier IA que toque Viru debe respetarlas literalmente:

- Repo canonico = C:\Users\javiru\Desktop\viru-tracker. No uses _publish_repo, ni crees mirrors, ni empujes desde otro lado.
- Default: commits directos a main. No crear ramas ni PRs salvo que el usuario lo pida.
- users_prueba.txt es un archivo intencional del proyecto. No tocar.
- No uses la guia de diseno para justificar cambios de logica, rutas o contratos.
- Cambios visuales sin pedirlo: no introduzcas dependencias, no reescribas pantallas completas, no redishenes areas no relacionadas, no inventes paletas paralelas, no uses shadcn/ui si no lo piden, no sustituyas el caracter calido por UI generica.
- Verificacion: nada de  should be fixed o looks fine. Si es visible, exige captura real. Si es logico, exige test que falle antes y pase despues.
- Tests existentes primero: antes de crear Playwright/TestSprite nuevos, reutiliza frontend/tests/*quick-search*e2e*.ts, frontend/scripts/qa_*.mjs y docs/qa/reports/.
- En QA visual: dark + light, desktop 1440x900, tablet 768x1024, mobile 375x812 y 320x780 si hay ruta privada. Cubre estados normal, loading, empty, error, parcial, exito.

### Publicacion

- Cloudflare Tunnel como via principal de exposicion publica.
- Tailscale Funnel como failover o bypass.
- Panel unificado VIRU_PANEL.bat con estado, inicio y parada de ambos tuneles.
- Sin dependencia de DuckDNS ni Caddy.

---

## 3. Sistema visual (la libreta de dibujo de Viru)

- Tipografia: Playfair Display para identidad (titulares, acentos), IBM Plex Sans para cuerpo y controles, monoespaciada solo cuando la cifra u hora gana precision.
- Paleta accent: #d95d39 (terracota o coral calido) y familia. #2e6e62 (verde petrol) = exito. #cd9a56 (ambar) = warning. #4f7fa6 (azul) = info. Rojo = error. El color nunca es la unica senal.
- Tokens (CSS variables) viven en frontend/src/styles/tokens.css (semanticos, alias) y frontend/src/styles/screens.css (valores de tema). Si necesitas un valor nuevo, primero mira si ya existe uno semantico.
- Patrones compartidos: panel, panel-soft, card, page-header, panel-header, panel-actions, panel-title, panel-subtitle, list-row, action-row, row-actions, section-gap con sm o lg, notice-compact, notice-actions, status-pill, state-success con warning, error, info. Reutilizalos, no dupliques.
- CTAs: una accion primaria por bloque (primary confirma, secondary acompana, ghost o link-subtle revela, vuelve o reintenta, danger solo para destructivas).
- Motion: 4 a 8 px de entrada, 1 a 2 px de compresion, glow contextual tenue. Casi todo con transform y opacity. Prohibido: loops en estados estaticos, scroll sorpresa, apariencia de live update falso para datos historicos. prefers-reduced-motion corta lo no esencial sin ocultar nada.
- Asimetria controlada, jerarquia visible: no hacer que todas las secciones pesen igual. Una pieza protagonista esta bien, paredes de cards iguales no.
- Estructura del frontend: Next.js 15 + React 19 + TypeScript. Alias @/* mapea a src/*. Sin Tailwind, sin shadcn/ui inicializado, sin helper cn, sin lib/utils.ts. CSS esta en frontend/src/styles/ (tokens.css, components.css, screens.css, base.css, globals.css, quick-search-dual.css, community-routes.css, signals.css). Iconos corporativos en frontend/src/icons/ como componentes. App Router en frontend/src/app/ con (private) y (public).

### Estructura del frontend (referencia rapida)

- frontend/src/app/: rutas App Router.
- frontend/src/modules/: modulos de producto (quick-search, watchlist, door-to-door, hotels, dashboard, alerts, shared).
- frontend/src/components/: componentes UI compartidos (components/ y ui/).
- frontend/src/icons/: SVGs corporativos como componentes React (RyanairIcon, WizzAirIcon, GenericProviderIcon, etc.).
- frontend/src/styles/: estilos globales y CSS modules.
- frontend/src/i18n/: archivos de internacionalizacion por dominio.

### Rutas privadas canonicas

- /dashboard, /watchlist, /quick-search, /notifications, /recomendaciones, /preferencias, /soporte/ayuda, /puerta-a-puerta, /hoteles.
- /cuenta/perfil, /cuenta/seguridad.
- /admin/hotels-observability, /admin/product-health, /admin.

### Rutas publicas canonicas

- /, /login, /register, /forgot-password, /ayuda, /policies, /prueba.

### Alias legacy activos

- /history -> /watchlist.
- /alerts -> /notifications?view=rules.
- /preferences -> /preferencias.
- /suggestions -> /soporte/feedback?type=idea.

---

## 4. Voz y lenguaje visible (la voz de Viru)

Fuente: docs/reference/ui-visible-language-guide.md + docs/reference/product-language-map.md.

- Cada texto visible responde a: que pasa, me afecta, que hago ahora.
- Espanol cercano, accionable, humano. Sin tono infantil, sin jerga, sin mezcla gratuita ES/EN.
- Lo tecnico puede vivir en backend, logs, codigo y nombres internos; NO en la UI visible.

### Sustituciones obligatorias

| Evitar en UI visible | Usar en su lugar | Nota |
| --- | --- | --- |
| modo degradado | resultados parciales / ultimo dato confirmado | Reservar degraded para backend y observabilidad |
| frescura | ultima comprobacion / comprobado hace | Hablar de tiempo real comprensible |
| score | valoracion Viru / mejor opcion / por que aparece arriba | Explicar el significado |
| heuristico | orden inteligente / criterio automatico | Evitar jerga tecnica |
| strict | modo estricto | Sin mezcla ES/EN |
| apertura | cobertura | Mejor describe el alcance |
| soporte parcial | datos parciales permitidos | Evita tono de atencion al cliente |
| revalidar | actualizar / comprobar de nuevo | Mas accionable |
| visto hace | comprobado hace | visto parece accion humana |
| workspace | panel / espacio de busqueda / espacio privado | Segun contexto |
| ranking | orden recomendado / como ordenamos | Hablar del beneficio |
| feedback de producto | Enviar opinion | Mas natural |

### Estados semanticos

- success: completado.
- warning: parcial o pendiente.
- error: fallo o validacion.
- info: contexto neutral.
- No usar warn en cambios nuevos.

Cada estado combina senal visual + texto comprensible + siguiente accion. El color nunca es la unica senal.

### Labels de producto congelados

- Watchlist, Quick Search, Oportunidades, Senales, Preferencias, Ayuda.
- Dentro de Senales: Bandeja (avisos recibidos) y Reglas (lo que Viru vigila).
- Alertas puede aparecer en copy contextual, pero NO es modulo de navegacion independiente.

### Vacios y errores

Los vacios, cargas y confirmaciones son oportunidades de personalidad: acompanar sin retrasar la tarea ni prometer capacidades inexistentes.

---

## 5. Producto y rutas vivas (la mapa del mundo)

### Watchlist (/watchlist)

Centro operativo. Absorbe historico.

- La cesta comparable (viajeros, equipaje, seguro, Fast Track, embarque prioritario, asiento, cambios flexibles) viaja desde Quick Search y se traduce a  Hasta +X (no rangos inventados).
- Estado operacional del vuelo (normalizado, numero, ruta, salida o llegada programada, estimada o real, retraso, terminal, puerta) NO desplaza la lectura de precio.
- Prediccion de retraso solo si hay identidad completa en Fare Memory; nunca cruza cuentas.
- Community Pricing (rango anonimo por persona, minimo 3 viajeros distintos en 365 dias, EUR) aparece como hub lateral de solo lectura; Comprado se gestiona dentro del hub, no en la fila.
- Acciones Pausar, Reanudar, Eliminar separadas de lo comunitario.
- N siguiendo (mas de 5) y En tendencia (top 20 por ciento de busquedas en 7 dias) pueden combinarse en una sola capsula.
- En multi-leg solo el primer tramo expandido; los siguientes bajo demanda.

### Quick Search (/quick-search)

Busqueda rapida con cache L1 (memoria) + L2 (DB) + provider y anti-stampede.

- Cesta comparable editable (equipaje, seguro, Fast Track, etc.) y persistida al guardar en Watchlist.
- Calendar hints con precios estimados por mes.
- Proveedores: Ryanair, Vueling, Wizz Air, easyJet, Duffel.
- Indicadores visuales por proveedor en tiempo real.
- Politica de weather documentada en docs/reference/quick-search-weather-policy.md.

### Senales (/notifications)

Una sola pieza con dos vistas: Bandeja y Reglas (con ?view=rules).

- Toast in-app avisan en el momento; la bandeja conserva el rastro consultable.
- Categorias: cambios de precio, tendencias, hoteleras, seguridad, digest, incidencias.
- Estado de lectura privado por usuario (UserNotificationState).
- No introduce un pipeline paralelo; agrega fuentes existentes y les suma estado de lectura.

### Puerta a puerta (/puerta-a-puerta)

Decidir viaje completo con un vuelo guardado (con ?watchId=...).

Taxonomia honesta de fuentes:

| Categoria | source_type | confidence | Precio? | Horario? | Booking? |
| --- | --- | --- | --- | --- | --- |
| Real (API) | api, maps | live, cached | Parcial | Si | No |
| Open data | open_data | cached | No | Si | No |
| Deeplink | deeplink | deeplink | No | Estimado | URL externa |
| Estimacion | estimate, mock | estimated | Estimado | Estimado | No |
| Scraper | scraper | (no aplica) | (no aplica) | (no aplica) | (no aplica) |

Limites explicitos:

- No confirma precios en nombre del usuario.
- No hace scraping activo por defecto.
- No reserva ni compra billetes.
- No tiene cobertura  Europa completa.
- No sustituye a Google Maps, BlaBlaCar, GoOpti, etc.
- GTFS y open data solo con feeds configurados explicitamente.
- Mock desactivado por defecto (DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER=true solo para desarrollo, demos o tests).

Perfiles: local_demo, local_real, staging_safe, prod_gradual.

### Hoteles (/hoteles)

Exploracion con comp-sets. En cierre. Fases A a E de correcciones post-cierre en progreso. No expandir scope aqui salvo que el usuario lo pida.

### Dashboard

Referencia viva: docs/specs/product/dashboard-redesign-v2.md.

Descubrimiento:

- Banda horizontal de 10 celdas (concentracion de busquedas).
- Lista de hasta 10 rutas direccionales (ultimos 7 dias).
- Desktop: izquierda comunidad, derecha oportunidad personal.
- Movil: comunidad primero.
- Empty state honesto mientras se reune cobertura.

---

## 6. APIs v1 y entidades (no inventar nombres)

### Endpoints canonicos

- /api/v1/watchlist, /api/v1/prices.
- /api/v1/search, /api/v1/search/quick, /api/v1/search/quick/calendar-hints, /api/v1/search/deeplink.
- /api/v1/alerts, /api/v1/alerts/events, /api/v1/notifications.
- /api/v1/recommendations, /api/v1/preferences, /api/v1/support/feedback.
- /api/v1/door-to-door.
- /api/v1/airports (seeds, sugerencias, paises).
- /api/v1/watchlist/{watch_id}/live (autenticado por owner).
- /api/v1/admin/product-health, /api/v1/admin/hotels-observability.

### Entidades persistidas (nombres canonicos)

FlightWatch, PriceSnapshot, AlertRule, NotificationEvent, UserNotificationState, UxEvent, RecommendationResponse, UserPreference, UserPreferenceAppearance, UserPreferenceRegion, SupportFeedback.

### Nombres legacy NO persistidos (no usar)

- watchlist_item -> no existe; usar FlightWatch.
- activity_event -> no existe; usar UxEvent o NotificationEvent segun contexto.
- system_status -> no existe como tabla; es estado derivado en /api/v1/admin/product-health.

### Stack

- Backend: FastAPI + SQLAlchemy + Alembic. PostgreSQL como objetivo, SQLite para arranque local.
- Frontend: Next.js 15 + React 19 + TypeScript.
- Package manager: npm (frontend/package-lock.json).
- Datos sensibles y secretos: JWT_SECRET obligatorio, no puede ser change-me. Alembic gestiona esquema; no se ejecuta bootstrap global en runtime.

---

## 7. Operativa, flags y QA (las valvulas de seguridad)

### Feature flags (no hay sistema unico)

Defaults en backend/.env.example. Si hay conflicto: 1) codigo o config real, 2) backend/.env.example, 3) spec o runbook vivo, 4) docs historicas.

Fare Memory y Quick Search shared cache:

- QUICK_SEARCH_SHARED_CACHE_ENABLED=false.
- FARE_MEMORY_ENABLED=true.
- FARE_MEMORY_WATCHLIST_BACKFILL_ENABLED=false.
- FARE_MEMORY_BOOT_WARMUP_ENABLED=false.
- FARE_MEMORY_RETENTION_ENABLED=false.
- FARE_MEMORY_REVALIDATION_WORKER_ENABLED=false.
- Redis opcional con REDIS_URL y QUICK_SEARCH_REDIS_*.

Puerta a puerta:

- DOOR_TO_DOOR_ENABLE_*, DOOR_TO_DOOR_GTFS_*.
- API keys: GOOGLE_MAPS_API_KEY, GTFS_NAP_API_KEY, NAVITIA_API_KEY (segun perfil).

Providers de vuelo:

- FLIGHT_PROVIDER_ORDER=ryanair,vueling.
- FLIGHT_PROVIDER_RYANAIR_ENABLED=true.
- FLIGHT_PROVIDER_VUELING_ENABLED=true.
- FLIGHT_PROVIDER_NON_CORE_ENABLED=false.
- FLIGHT_PROVIDER_WIZZAIR_ENABLED=false.
- FLIGHT_PROVIDER_EASYJET_ENABLED=false.
- FLIGHT_PROVIDER_IBERIA_ENABLED=false.
- FLIGHT_PROVIDER_DUFFEL_ENABLED=false.

Flags legacy archivadas (M7 a M13, NO usar para activaciones nuevas):

- ff_prediction_enabled, ff_self_connect_enabled, ff_everywhere_enabled, ff_deeplink_hardened, ff_country_content, ff_full_i18n, ff_suggestions_pipeline.

### Como se prueba (estado vivo)

- Backend: cd backend y python -m pytest -q (alrededor de 945 passed, 2 skipped).
- Frontend: cd frontend y npm test (alrededor de 421 passed, 17 skipped; los skips son E2E que requieren backend levantado), npm run build, npx tsc --noEmit, npm run test:e2e:quick-search.
- Lint de frontend limpio en estado actual.

### QA visual obligatorio

Capturas en navegador real, dark + light, breakpoints canonicos, estados aplicables. El AI NO declara cierre visual sin captura.

### Para UI

Pedir al usuario revision manual con (ruta, interaccion, resultado esperado, feedback). El AI se encarga de build, tests, lint y typecheck.

### Para diagnosis

Reproducir antes de patchear; capturar request y response real si es HTTP; mirar consola; si frontend y backend discrepan, tratar el contrato como root cause.

### Pruebas no se debilitan

- No debilitar assertions para hacer pasar un test.
- No normalizar tests flaky.
- No usar datos privados reales.
- No actualizar snapshots sin entender el cambio.
- No usar mocks que escondan el bug.

---

## 8. Estructura de la documentacion viva

Punto de reentrada: docs/README.md, docs/INDICE_UNICO.md, docs/DOCS_INVENTORY.md.

- docs/overview/: reentrada, estado actual, arquitectura, mapa del repo.
- docs/adr/: decisiones arquitectonicas (3 ADRs vigentes).
- docs/reference/: contratos API, feature flags, guias tecnicas activas.
- docs/specs/: specs activas de producto, UI y contenido.
- DESIGN.md: sistema visual, contrato creativo y guia estetica (Aviation Warm-Luxe).
- docs/product/: resumenes funcionales por area de producto.
- docs/engineering/: resumenes tecnicos por capa.
- docs/runbooks/: operacion y respuesta ante incidentes.
- docs/qa/: checklists, reportes y referencias QA reutilizables.
- docs/plans/: planes activos y completados.
- docs/prompts/: prompts y contexto IA (aqui vive este briefing).
- HISTORY.md: historial resumido de cambios relevantes.

docs/archive/ conserva historico y trazabilidad; NO es fuente de verdad activa.

### Nunca tratar como documentacion

_publish_repo, node_modules, .venv, venv, .next, caches, logs, test outputs, generated files, snapshots, dependency docs, local artifacts.

users_prueba.txt no es documentacion, pero se conserva intencionalmente.

### Preferencia de documentos

Preferir los marcados como Estado: vivo y Fuente de verdad: si.

---

## 9. Anti-patrones explicitos

- Adivinar causa y patchear antes de reproducir.
- Resolver varios bugs a la vez sin pedirlo.
- Sobredisenar o abstraer especulativamente.
- Refactors amplios disfrazados de fix.
-  Build pasa como prueba de fix visible.
- Aplanar Viru a SaaS generico para hacer mas facil la implementacion.
- Cambios visuales sin captura real.
- Dejar cambios sin publicar cuando el usuario pidio completado.
- Usar _publish_repo o cualquier mirror como repo de respaldo.
- Commits desde un directorio que no sea el repo canonico.
- Pedir aclaraciones evitables en lugar de asumir y proceder.
- Diff grande cuando un fix pequeno y verificado basta.
- Cambiar estado, logica, rutas o contratos para encajar con una regla visual.
- Introducir una dependencia nueva para un retoque visual menor.
- Tocar users_prueba.txt.

---

## 10. Resumen ejecutivo en una pagina

| Bloque | Clave |
| --- | --- |
| Producto | Vuelo + watchlist + historico + alertas. Cabina viva, calida, aeronautica. |
| Identidad | No generic SaaS. Dual-theme (Aviation Dark-Luxe + day-light). |
| Reglas duras | Repo canonico, commits a main, sin _publish_repo, sin tocar users_prueba.txt. |
| Tipografia | Playfair Display (identidad) + IBM Plex Sans (cuerpo) + mono (datos). |
| Acento | #d95d39 (terracota). Estados: #2e6e62 ok, #cd9a56 warn, #4f7fa6 info. |
| Tokens | frontend/src/styles/tokens.css + screens.css. No inventar valores. |
| Patrones | panel, card, page-header, notice-compact, status-pill, state-*. |
| CTAs | Una primaria por bloque. primary confirma, secondary acompana, ghost revela. |
| Motion | 4 a 8 px entrada, transform y opacity. Sin loops en estatico. prefers-reduced-motion. |
| Voz | Espanol cercano, sin jerga, sin ES/EN mixto. Sustituciones obligatorias en tabla. |
| Labels congelados | Watchlist, Quick Search, Oportunidades, Senales, Preferencias, Ayuda. |
| Rutas privadas | /dashboard, /watchlist, /quick-search, /notifications, /recomendaciones, /preferencias, /soporte/ayuda, /puerta-a-puerta, /hoteles. |
| Rutas publicas | /, /login, /register, /forgot-password, /ayuda, /policies, /prueba. |
| Stack | FastAPI + SQLAlchemy + Alembic. Next.js 15 + React 19 + TS. PostgreSQL objetivo. |
| Publicacion | Cloudflare Tunnel (principal) + Tailscale Funnel (failover). VIRU_PANEL.bat. |
| QA visual | Dark + light, 1440x900, 768x1024, 375x812 (+320x780 si ruta privada). |
| Verificacion | Reproducir -> aislar -> patchear -> verificar -> resumir. Captura real, no deberia. |
