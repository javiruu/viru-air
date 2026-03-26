# Plan - Interfaz bilingüe y nuevo menú de cuenta

Fecha: 2026-02-19
Owner: Codex

## Contexto
El rediseño del sistema de cuenta debe aterrizar con una navegación honesta (un item = una ruta real) y un UI que hable español e inglés sin mezclas. El `AccountMenu` ya muestra grupos claros, así que ahora necesitamos definir los contenidos, rutas, endpoints y la estrategia de copy para ambos idiomas antes de tocar componentes.

## Lluvia de ideas (brainstorming)
- La interfaz debe sentirse como un panel de control real, no como un menú simulado.
- Separar identidad (`/cuenta`), preferencias (`/preferencias`) y soporte (`/soporte`) reforzará confianza.
- Cada ruta carga su propio copy localized y el loader global se mantiene traducido gracias a `shared.loader`.
- El menú de cuenta publica debe ser claro: Perfil, Seguridad, Búsqueda, Apariencia, Idioma y región, Centro de ayuda, Feedback, Cerrar sesión.
- Agregar una ruta pública `/ayuda` que sirva como punto de entrada para usuarios no autenticados.
- El idioma debe reusarse en `AccountMenu`, `Preferencias/Región` y en toasts/labels (uso de `shared` dictionaries).
- Los endpoints ya planificados (`/account/*`, `/preferences/*`, `/support/*`, `/public/help`) se documentan para evitar duplicidades con la lógica actual.
- La base visual permanece: header consistente, cards con elevación, spacing 8-16-24 y toasts suaves.

## Rutas y páginas
1. `/cuenta/perfil` – identidad y sesiones.
2. `/cuenta/seguridad` – password, 2FA (futuro) e historial.
3. `/preferencias/busqueda` – estilo de búsqueda por defecto (radio, escalas, ventanas).
4. `/preferencias/apariencia` – temas, densidad, accesibilidad.
5. `/preferencias/region` – idioma, región, formato hora, separador decimal y moneda.
6. `/soporte/ayuda` – mini centro humano con FAQ y estado del sistema.
7. `/soporte/feedback` – formulario con tipo (bug, idea, general) y opción de adjuntar captura.
8. `/ayuda` (pública) – acceso a ayuda y CTA a login/registro.

## Endpoints nuevos o adaptados
- `GET/PUT /account/profile`
- `GET /account/sessions`, `POST /account/sessions/close_all`, `DELETE /account`
- `POST /account/security/password`, `GET /account/security/activity`
- `GET/PUT /preferences/search`, `GET/PUT /preferences/appearance`, `GET/PUT /preferences/region`
- `GET /support/help`, `POST /support/feedback`
- `GET /public/help` (contenido público de soporte)

## Estrategia i18n
- `shared.loader`, `shared.actions`, `domains/account|preferences|support` ya contienen traducciones para ES/EN.
- `AccountMenu` usa `t("account.menu.*")` para cada item.
- `Preferencias/Región` persiste la selección en `localStorage` y actualiza `document.documentElement.lang`.
- Cualquier copy nuevo (headers, cards, botones) debe definirse en los archivos de `i18n/domains` antes de ser renderizado.
- Se mantiene la sincronía: si el usuario cambia idioma en Preferencias/Región, todo el UI y el loader reflejan la nueva selección.

## Plan de implementación (skills)
Usaré los siguientes skills durante la implementación:
- `frontend-design` para construir componentes polidos, cards y layout del menú / preferencia.
- `ui-design` para asegurar jerarquía, microcopy y la estructura de cards/sections.
- `web-design-guidelines` para auditar accesibilidad, contrastes, patrones de modales y navegación del menú.

## Pasos siguientes inmediatos
1. Revisar el loader global e introducir los wrappers necesarios para mantenerlo en todas las rutas públicas y privadas.
2. Matricular cada nueva ruta con su copy y control de seguridad, utilizando los diccionarios de i18n.
3. Registrar los endpoints en la documentación y diseñar las llamadas desde los componentes de cuenta/soporte.
4. Documentar los estados de carga y errores (modal, toast) para español e inglés.
5. Validar visualmente con QA checklist (frontend-pr-checklist y account-system QA) y complementar con el log en `logs_ia`.

