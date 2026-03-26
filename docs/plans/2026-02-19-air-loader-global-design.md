# Plan + Diseño - Air Loader global y menú bilingüe de cuenta

Fecha: 2026-02-19  
Responsable: Codex  
Alcance: loader reusable entre páginas, rutas reales del menú de cuenta y copy automático ES/EN sin feature flag.

## Objetivo
Unificar la experiencia de carga en todos los puntos críticos mientras se lanza un menú de cuenta honesto y bilingüe. El loader `AirLoader` (nubes + avión) será la única animación usada en transiciones, verificaciones de sesión y estados de fetch. Cada ruta de cuenta/preferencia/soporte expone su propio endpoint y copy (ES/EN) para que la interfaz cambie de idioma con la selección actual.

## Lluvia de ideas (bonita)
- **Cielo compartido:** todas las cargas usan `AirLoader` envuelto en `air-loader-wrap` o `air-loader-screen` para no romper layout.  
- **Copy vivo:** `shared.loader.flightLabel` rota entre `cargando vuelo` y `loading flight` según el idioma activo; los demás textos (botones, títulos, avisos) usan dominios `account`, `preferences`, `support`.  
- **Menú con realidad:** cada item del dropdown apunta a `/cuenta`, `/preferencias` o `/soporte` y tiene un endpoint dedicado.  
- **Public landing + ayuda:** la experiencia pública (`/ayuda`) utiliza el mismo loader y copy, asegurando que incluso no autenticados vean la consistencia.  
- **Soporte humano:** la sección `Feedback` mantiene formulario con tipos (bug/idea/general) y entrada extendida, y `Help` público reafirma la seriedad del producto.  
- **Accesibilidad:** `role="status"`, `aria-live="polite"`, `prefers-reduced-motion` ya contemplado en CSS, `aria-label` contextual (default + prop).

## Plan de implementación

### Fase 1: Fundamentos del AirLoader
1. Crear `frontend/src/modules/shared/AirLoader.tsx` (props: `label`, `ariaLabel`, `theme`, `size`, `className`). Usa `useI18n`, `shared.loader.flightLabel`, y replica la estructura de nubes + avión facilitada por UX.  
2. Añadir wrappers y utilidades en `frontend/src/styles/globals.css` (`.air-loader-wrap`, `.air-loader-screen`, `.air-loader-section`) para centrar y espaciar el componente en distintos contextos.  
3. Reemplazar el loading global (`app/loading.tsx`) con `AirLoader` y envolverlo en `air-loader-screen`.  
4. Actualizar `RequireAuth`, fallbacks de Suspense en login/register y los fetch esperados (admin, quick search, preferences) para renderizar `AirLoader`.  
Habilidades movilizadas: `frontend-design` (componentes y layout), `ui-design` (jerarquía y texto), `web-design-guidelines` (accesibilidad/rol/labels).

### Fase 2: Rutas nuevas + copy bilingüe
1. Rediseñar `AccountMenu` para apuntar a rutas 1:1: `/cuenta/perfil`, `/cuenta/seguridad`, `/preferencias/busqueda`, `/preferencias/apariencia`, `/preferencias/region`, `/soporte/ayuda`, `/soporte/feedback`, y la ruta pública `/ayuda`.  
2. Crear los skeletons de página (headers, cards, sections) para cada ruta y documentar el copy en `i18n/domains/account|preferences|support`. Asegurar que la selección de idioma en `/preferencias/region` actualiza `document.documentElement.lang` y persiste en `localStorage`.  
3. Cada página envuelve sus fetches con el loader (por ejemplo, perfil y sesiones muestran `AirLoader` mientras fetch). Incluir `notice` accesible en errores (props `aria-live`, copy `shared.errors.generic`).  
4. Public `/ayuda` y soporte usan la misma base visual (header + cards) y los endpoints `GET /public/help`, `GET /support/help`, `POST /support/feedback`.  
Habilidades: `frontend-design`, `ui-design`; validar contraste y micro-copy con `web-design-guidelines`.

### Fase 3: Endpoints + backend (FastAPI + SQLite)
1. Documentar (y si procede, implementar) los endpoints: `GET/PUT /account/profile`, `GET /account/sessions`, `POST /account/sessions/close_all`, `DELETE /account`, `POST /account/security/password`, `GET /account/security/activity`, `GET/PUT` para cada preferencia, `GET /support/help`, `POST /support/feedback`, `GET /public/help`.  
2. Asegurar que cada endpoint responde con información para alimentar los paneles (perfil, sesiones, preferencias, soporte) y que el UI muestra `AirLoader` hasta recibir los datos.  
3. Registrar en `docs/estetica.md` o nueva sección cómo se deben usar los cards, spacing y microinteracciones para estas páginas.

### Fase 4: QA, documentación y rollout
1. QA visual: checklist `docs/qa/frontend-pr-checklist.md` + `docs/qa/account-system-redesign-...` (añadir si no existe).  
2. Pruebas: smoke en rutas `/cuenta/*`, `/preferencias/*`, `/soporte/*`, `/ayuda`, verificando que el loader aparece durante fetch y que el texto cambia cuando se selecciona English vs Español.  
3. Logs/documentación: generar entradas en `logs_ia/` para cada fase y actualizar `docs/INDICE_UNICO.md` si surge un nuevo plan.  
4. Hand off y seguimiento: recopilar evidencias (screenshots, logs, tests) en un solo documento, listo para QA/otro equipo.

## Rutas y Endpoints clave
- Rutas privadas: `/cuenta/perfil`, `/cuenta/seguridad`, `/preferencias/busqueda`, `/preferencias/apariencia`, `/preferencias/region`, `/soporte/ayuda`, `/soporte/feedback`.  
- Ruta pública: `/ayuda`.  
- Endpoints backend:
  - `GET /account/profile`, `PUT /account/profile`
  - `GET /account/sessions`, `POST /account/sessions/close_all`, `DELETE /account`
  - `POST /account/security/password`, `GET /account/security/activity`
  - `GET/PUT /preferences/search`, `GET/PUT /preferences/appearance`, `GET/PUT /preferences/region`
  - `GET /support/help`, `POST /support/feedback`
  - `GET /public/help`

## Estrategia i18n
- Los textos (títulos, botones, labels, notices) salen de `i18n/domains/account`, `preferences`, `support` y `shared`.  
- El loader reutiliza `shared.loader.flightLabel` + `shared.loader.aria`.  
- Cambios de idioma via `/preferencias/region` actualizan `document.documentElement.lang` y recargan los namespaces (lazy load).  
- English copy es un switch; no hay dual-lingual view.

## QA y aceptación
- Loader visible en cada transición y cada fetch crítico (landing, login, RequireAuth, account routes).  
- `AccountMenu` muestra categorías con headers (“Cuenta”, “Preferencias”, “Soporte”) y cada item enlaza a su ruta real.  
- Preferencias de idioma cambian UI y loader.  
- Cada endpoint respondido o muestra `notice` con copy traducido.  
- Documentación actualizada (logs + INDICE_UNICO).

## Dependencias y notas
- Invocar a backend para garantizar que los endpoints estén soportados (FastAPI).  
- `prompts/account_system_redesignment.md` es la base del restructuring (ya revisado).  
- Mantener `frontend-design`, `ui-design`, `web-design-guidelines` activos durante la implementación para asegurar calidad.  
- Logging: cada subpaso registra en `logs_ia/2026-02-19-air-loader-implementacion.log` (o nombre similar).
