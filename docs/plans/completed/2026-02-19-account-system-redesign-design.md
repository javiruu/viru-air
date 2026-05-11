# Account System Redesign - Design Doc

Date: 2026-02-19
Owner: Codex
Status: Draft (approved by user on architecture, pages, backend)

## Context
The current account menu is structurally misleading: all options point to the same screen. This breaks trust and makes the product feel simulated. The goal is to create a real account system with a clear mental model, distinct routes, and coherent page responsibilities.

## Goals
- Separate identity, preferences, and support into distinct routes and screens.
- Make each menu item map to a real page.
- Preserve the current visual language of Viru while increasing clarity and professionalism.
- Introduce backend endpoints and storage to support the new pages.
- Add a small public Help page for non-auth users.

## Non-Goals
- No complex new features beyond the reorganization.
- No major redesign of the overall app layout or navigation.
- No new auth flows beyond session display and logout.

## Constraints
- Stack: Next.js frontend + FastAPI backend + SQLite.
- Must keep current Viru design language and reuse existing layout components where possible.
- Must stay in Spanish copy by default.

## Lluvia de ideas (bonita, antes de decidir)
- La cuenta debe sentirse como "tu control center", no como un menu apilado.
- Separar "quien eres" de "como usas Viru" es clave para confianza.
- La seguridad no puede mezclarse con preferencias: debe tener su propio espacio serio.
- La apariencia es emocional; debe tener previews, no solo toggles.
- La region/idioma es cultural: mantenerla separada evita confundir con la busqueda.
- Soporte necesita humanidad: no un link muerto, sino una pagina con estructura real.
- Un mini centro de ayuda publico reduce friccion y aumenta percepcion de producto real.

## Approach Options (trade-offs)
1) Separate routes per item (recommended)
   - Pros: clear mental model, scalable, honest navigation.
   - Cons: more files and endpoints.
2) Single page with tabs/anchors
   - Pros: less work, fewer routes.
   - Cons: still feels simulated and contradicts the brief.
3) Hybrid (some routes + anchors)
   - Pros: partial separation.
   - Cons: inconsistent and confusing.

Recommendation: Option 1.

## Information Architecture
Menu groups in the account dropdown:
- Cuenta: Perfil, Seguridad
- Preferencias: Busqueda, Apariencia, Idioma y region
- Soporte: Centro de ayuda, Feedback
- Separador: Cerrar sesion

Private routes:
- /cuenta/perfil
- /cuenta/seguridad
- /preferencias/busqueda
- /preferencias/apariencia
- /preferencias/region
- /soporte/ayuda
- /soporte/feedback

Public route:
- /ayuda (mini centro de ayuda)

## Page Design Specs

### /cuenta/perfil
Purpose: identidad y estado de cuenta.
Cards:
- Identidad: avatar editable, nombre editable, email (editable con confirmacion), fecha registro, estado cuenta.
- Sesiones: sesion actual, otros dispositivos, boton "Cerrar todas las sesiones".
- Zona sensible: eliminar cuenta con modal de confirmacion fuerte.

### /cuenta/seguridad
Purpose: percepcion de producto serio y control.
Cards:
- Cambiar contrasena.
- 2FA (future-ready, deshabilitado con hint).
- Actividad: ultimo acceso + historial reciente.

### /preferencias/busqueda
Purpose: estilo de busqueda por defecto.
Controls:
- Radio por defecto (slider + input).
- Incluir escalas (toggle).
- Evitar salidas antes de (time picker + chips).

### /preferencias/apariencia
Purpose: personalizacion visual real.
Controls:
- Tema: claro / oscuro / sistema con preview.
- Densidad: compacta / comoda.
- Accesibilidad: reducir animaciones, alto contraste.

### /preferencias/region
Purpose: configuracion regional.
Controls:
- Idioma interfaz.
- Region.
- Formato hora (12/24).
- Separador decimal.
- Moneda.

### /soporte/ayuda
Purpose: soporte humano, no vacio.
Sections:
- Como funciona Viru.
- FAQ rapidas.
- Estado del sistema (version usuario).
- Contacto.

### /soporte/feedback
Purpose: canal claro de feedback.
Form:
- Tipo: bug / idea / general.
- Texto largo.
- Adjuntar captura (opcional).
- Mensaje post-envio: "Gracias por mejorar Viru."

### /ayuda (publico)
Purpose: mini centro de ayuda para no autenticados.
Contenido:
- FAQ corta.
- Como funciona Viru (resumen).
- CTA a login / registro para enviar feedback.

## Backend Design

### Endpoints
Cuenta:
- GET /account/profile
- PUT /account/profile
- GET /account/sessions
- POST /account/sessions/close_all
- DELETE /account

Seguridad:
- POST /account/security/password
- GET /account/security/activity

Preferencias:
- GET /preferences/search
- PUT /preferences/search
- GET /preferences/appearance
- PUT /preferences/appearance
- GET /preferences/region
- PUT /preferences/region

Soporte:
- GET /support/help
- POST /support/feedback

Publico:
- GET /public/help

### Data Model (SQLite)
New tables (minimal viable):
- user_profile (user_id, name, avatar_url, status, created_at)
- user_sessions (session_id, user_id, device, ip, last_seen, created_at)
- user_preferences_search
- user_preferences_appearance
- user_preferences_region
- security_activity (user_id, event_type, ip, created_at)
- support_feedback (user_id nullable, type, message, attachment_url nullable, created_at)
- support_help_content (optional if stored in DB, else serve markdown/static)

## Error Handling
- Frontend: inline validation, toast for server errors, safe fallback text.
- Backend: 400 for validation, 401 for unauth, 404 for missing, 500 for unexpected.

## Accessibility
- Headings H1 -> section -> card -> field.
- ARIA labels for interactive controls.
- Keyboard support for menu and form components.

## Telemetry (lightweight)
- Log security events (password change, logout all).
- Log feedback submissions.

## Testing Strategy
- Unit tests for API validation.
- E2E smoke: open each route, check data loads.
- Visual QA: menu grouping, page titles, card layout.

## Rollout Plan
- Phase 1: Backend endpoints + DB migrations.
- Phase 2: Frontend routes and AccountMenu update.
- Phase 3: Public help page and footer link.
- Phase 4: QA, bugfix, polish.

## Risks
- Migration complexity if old preferences were stored in a single table.
- Inconsistent copy across pages if not standardized.
- Confusion if menu items and routes do not match 1:1.

## Open Questions
- Will email be editable? If yes, confirm flow.
- Should help content be static markdown or stored in DB?
- Any legal copy or policy links required in help?

## Implementation Plan (complete)
1. Audit current account menu and preferences usage.
2. Define DB migrations for new tables.
3. Implement backend endpoints with validation and auth guards.
4. Create new frontend routes and page shells.
5. Build each page UI with consistent header, container, and cards.
6. Connect each page to its endpoint.
7. Update AccountMenu grouping and links.
8. Add public /ayuda page and footer link.
9. QA: navigation, accessibility, regression checks.
10. Ship behind a feature flag if needed (optional).
