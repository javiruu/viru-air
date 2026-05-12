# Task: Rediseñar y corregir el footer block de Viru Tracker

Quiero que arregles el footer de la landing de Viru Tracker. No quiero un rediseño total de la web: quiero corregir específicamente el footer para que deje de verse raro, poco profesional o como un bloque de placeholder.

## Contexto del problema

El footer actual de Viru Tracker se percibe raro porque no se comporta visualmente como un footer real de producto. Parece una sección editorial/card más, centrada y estrecha, pegada al final de la landing.

El footer actual contiene textos que parecen internos o de diseño, como:

- `FO OT ER BLO CK`
- `Footer adaptado a Viru con rutas reales del producto y accesos de soporte existentes.`

Estos textos NO deben aparecer en producción. Dan la sensación de componente sin terminar, placeholder, nota interna o copy de diseñador.

También aparece un bloque tipo status:

- `CONTEXTO ACTIVO`
- `Acceso público`
- botones como `Copiar enlace base`
- `Volver arriba ↑`

Esto mezcla footer con dashboard/estado/CTA. El footer debería ser una zona de cierre del sitio, no una mini tarjeta de producto ni una interfaz de control.

## Diagnóstico visual basado en referencias

Comparé Viru Tracker con footers de Nike, adidas, PcComponentes y Leroy Merlin.

Patrón común en esas referencias:

1. El footer ocupa una zona amplia y estable del ancho de pantalla.
2. La navegación se organiza en columnas.
3. La marca/legal/cookies/contacto viven en una zona secundaria.
4. No hay textos internos de componente.
5. La jerarquía tipográfica es más discreta que en una hero section.
6. El footer tiene una delimitación visual clara: fondo propio, banda, borde superior, bloque full-width o estructura ancha.

Medidas aproximadas en capturas de 1835 px de ancho:

- Viru footer: ancho útil aprox. 965 px, es decir ~52.6% del viewport.
- Nike footer: ~1733 px, ~94.4%.
- PcComponentes footer: ~1456 px, ~78.6%.
- Leroy Merlin footer: ~1501 px, ~81.8%.
- adidas footer: ~1362 px, ~74.2%.

Conclusión: Viru está demasiado estrecho para un footer. Aunque el contenido principal de la landing sea editorial y contenido, el footer debe sentirse como cierre del sistema, no como otra card centrada.

## Objetivo de diseño

Transformar el footer actual en un footer profesional, estable y sobrio, con:

- contenedor exterior full-width;
- fondo propio o borde superior claro;
- contenido interno mucho más ancho que el actual;
- columnas limpias;
- tipografía secundaria;
- menos iconos;
- sin textos internos;
- sin CTAs raros;
- sin enlaces fantasma;
- sin sensación de dashboard;
- responsive correcto.

El resultado debe parecer un cierre real de producto SaaS/editorial, no una sección de marketing más.

## Qué debes inspeccionar primero

Antes de editar, inspecciona el repo:

1. Localiza el componente del footer:
   - busca `FO OT ER BLO CK`
   - busca `Footer adaptado`
   - busca `CONTEXTO ACTIVO`
   - busca `Viru Tracker`
   - busca `soporte@viru.app`
   - busca componentes llamados `Footer`, `FooterBlock`, `SiteFooter`, `LandingFooter`, `MarketingFooter` o similares.

2. Identifica el stack:
   - Next.js / React / Vite / Astro / otro.
   - Tailwind / CSS modules / styled-components / CSS global.
   - sistema de rutas existente.
   - componentes de botón/link existentes.
   - tokens de diseño existentes: colores, bordes, radios, sombras, spacing.

3. No asumas rutas nuevas. Usa solo rutas existentes. Si una ruta no existe, no la inventes.

4. Mantén el estilo general de Viru:
   - editorial;
   - cálido;
   - beige/cream;
   - acentos coral/verde;
   - bordes suaves;
   - estética limpia;
   - no convertirlo en un footer corporativo genérico negro si no encaja con el resto.

## Cambios obligatorios

### 1. Eliminar textos internos/placeholder

Eliminar completamente del render:

- `FO OT ER BLO CK`
- `FOOTER BLOCK`
- `Footer adaptado a Viru...`
- cualquier variante de texto que explique que el footer está adaptado, diseñado o basado en rutas reales.

No debe quedar ningún texto que parezca comentario interno.

### 2. Eliminar o simplificar el bloque `CONTEXTO ACTIVO`

El footer no debe tener un bloque protagonista llamado `CONTEXTO ACTIVO`.

Opciones válidas:

A. Eliminarlo por completo.

B. Si hace falta conservar la idea de “Acceso público”, convertirla en un micro-pill discreto dentro del bloque de marca, por ejemplo:

`Acceso público`

Pero debe ser pequeño, secundario y no competir con la navegación.

No debe haber un mini panel con varios botones arriba del footer.

### 3. Quitar CTAs que no son propios de footer

Eliminar o mover fuera del footer:

- `Copiar enlace base`

`Volver arriba ↑` puede mantenerse, pero solo como enlace textual discreto en la parte inferior o superior derecha del footer. No debe parecer un botón principal.

### 4. Rediseñar estructura del footer

Crear esta estructura conceptual:

Footer exterior full-width:

- borde superior sutil o fondo propio;
- padding vertical generoso;
- inner container ancho;
- grid responsive.

Estructura recomendada en desktop:

- columna izquierda: marca + descripción breve;
- columnas derechas: navegación agrupada.

Ejemplo conceptual:

Viru Tracker
Seguimiento de precios Ryanair con alertas, histórico y contexto para decidir cuándo comprar.

Producto
- Inicio
- Ayuda
- Políticas

Cuenta
- Entrar
- Crear cuenta

Contacto
- soporte@viru.app
- privacidad@viru.app
- press@viru.app

Legal / parte inferior
© 2026 Viru Tracker. Todos los derechos reservados.
Políticas
Privacidad
Cookies, solo si existe esa ruta real
Volver arriba ↑, opcional

IMPORTANTE:
No añadir enlaces si no existen en el router/app. Si no existe `/cookies`, no crear “Cookies”. Si no existe `/privacidad`, no crear “Privacidad” salvo que ya haya ruta real o documento real.

### 5. Anchura y layout

El footer actual es demasiado estrecho.

Implementar:

- wrapper exterior: `width: 100%`;
- inner container:
  - ideal: `max-width: 1360px`;
  - aceptable: `max-width: 1280px` si el sistema usa `max-w-7xl`;
  - padding horizontal responsive: 24px mobile, 32px tablet, 48px desktop;
  - centrado con `margin-inline: auto`.

En Tailwind, preferencia:

```tsx
<footer className="w-full border-t border-black/10 bg-[...]">
  <div className="mx-auto max-w-[1360px] px-6 py-14 sm:px-8 lg:px-12 lg:py-16">
    ...
  </div>
</footer>

Si el proyecto usa tokens propios, usa esos tokens en vez de valores hardcodeados.

6. Separación visual

El footer necesita sentirse como el cierre de la página.

Añadir uno de estos enfoques, respetando el diseño actual:

Opción preferida:

fondo ligeramente distinto al body;
borde superior sutil;
sin card grande;
sin sombra fuerte.

Ejemplo:

body: beige cálido;
footer: cream un poco más opaco o rgba(...);
border-top: 1px solid con baja opacidad.

Evitar:

una card centrada estrecha;
sombra excesiva;
fondo completamente distinto que rompa la estética;
hacerlo demasiado negro/corporativo si no existe ese lenguaje en la landing.
7. Tipografía

El título Viru Tracker del footer no debe competir con el hero.

Reglas:

marca footer: aprox. 28-32 px en desktop;
headings de columnas: 11-13 px, uppercase, tracking amplio;
links: 14-15 px;
descripción: 14-16 px;
legal: 12-13 px.

La marca puede usar la tipografía editorial actual, pero reducida.

8. Iconos

El footer actual usa iconos en navegación/contacto. Reducir ruido.

Reglas:

No usar iconos en cada link de navegación salvo que el sistema ya lo haga de forma muy elegante.
En contacto, se puede usar icono solo si queda alineado y discreto.
Priorizar legibilidad textual.
Si los iconos vienen de Font Awesome/lucide, mantener consistencia, pero no llenar el footer de iconitos.
9. Copy final recomendado

Usar este copy o adaptarlo muy poco:

Marca:
Viru Tracker

Descripción:
Seguimiento de precios Ryanair con alertas, histórico y contexto para decidir cuándo comprar.

Producto:

Inicio
Ayuda
Políticas

Cuenta:

Entrar
Crear cuenta

Contacto:

soporte@viru.app
privacidad@viru.app
press@viru.app

Legal:
© 2026 Viru Tracker. Todos los derechos reservados.

No usar:

“Accesos editoriales”
“enlaces fantasma”
“Footer adaptado”
“rutas reales del producto”
“FOOTER BLOCK”
10. Responsive

Mobile:

footer full-width;
columnas apiladas;
marca arriba;
navegación en 1 o 2 columnas según espacio;
legal abajo;
separación vertical clara.

Tablet:

marca arriba o izquierda;
navegación 2-3 columnas.

Desktop:

grid recomendado:
marca: span 4 o 5 columnas;
nav: span 7 u 8 columnas;
columnas internas: 3 o 4.

Ejemplo Tailwind orientativo:

<div className="grid gap-10 lg:grid-cols-12">
  <div className="lg:col-span-5">
    ...
  </div>

  <nav className="grid gap-8 sm:grid-cols-3 lg:col-span-7">
    ...
  </nav>
</div>
11. Accesibilidad
Usar <footer>.
Usar <nav aria-label="Footer"> o varios navs con labels claros.
Los emails deben ser mailto:.
Los links deben tener estado hover/focus visible.
No usar botones para navegación si son enlaces.
Volver arriba puede ser <a href="#top">Volver arriba ↑</a> solo si existe o se puede añadir un id="top" seguro en la página.
No romper navegación por teclado.
12. No crear enlaces fantasma

Antes de añadir cada link, comprueba si existe.

Para Next.js:

revisa app/
revisa pages/
revisa rutas exportadas
revisa configuración de navegación existente.

Si solo existen:

/
/login
/register
/policies

entonces usa solo esos.

Si el proyecto usa nombres distintos:

/signin
/signup
/privacy
etc.

adapta a rutas reales.

Si no existe “Ayuda”, no la añadas o conviértela en mailto:soporte@viru.app con texto Ayuda.

13. Mantener coherencia visual con la landing

No rediseñar hero, cards, secciones ni navbar.

Solo tocar:

componente de footer;
estilos asociados al footer;
constantes de navegación del footer si existen;
tests/snapshots si existen.

No tocar:

lógica de precios;
autenticación;
tracking;
dashboard;
componentes de gráficas;
theme global salvo que sea imprescindible y mínimo.
14. Implementación esperada

Hazlo en este orden:

Inspecciona el repo y localiza el footer.
Resume brevemente qué archivos vas a tocar.
Implementa el nuevo footer.
Elimina textos internos.
Ajusta responsive.
Comprueba rutas reales.
Ejecuta formatter/linter/typecheck/build disponible.
Revisa visualmente el diff.
Entrega resumen de cambios y comandos ejecutados.
Posible implementación si el proyecto usa React + Tailwind

Adapta esto al estilo del repo, no lo pegues ciegamente si hay componentes internos de Link, Button, cn, etc.

const footerGroups = [
  {
    title: "Producto",
    links: [
      { label: "Inicio", href: "/" },
      { label: "Ayuda", href: "mailto:soporte@viru.app" },
      { label: "Políticas", href: "/policies" },
    ],
  },
  {
    title: "Cuenta",
    links: [
      { label: "Entrar", href: "/login" },
      { label: "Crear cuenta", href: "/register" },
    ],
  },
  {
    title: "Contacto",
    links: [
      { label: "soporte@viru.app", href: "mailto:soporte@viru.app" },
      { label: "privacidad@viru.app", href: "mailto:privacidad@viru.app" },
      { label: "press@viru.app", href: "mailto:press@viru.app" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="w-full border-t border-black/10 bg-white/35">
      <div className="mx-auto max-w-[1360px] px-6 py-14 sm:px-8 lg:px-12 lg:py-16">
        <div className="grid gap-10 lg:grid-cols-12">
          <div className="max-w-md lg:col-span-5">
            <p className="text-2xl font-semibold tracking-tight text-neutral-950 sm:text-3xl">
              Viru Tracker
            </p>
            <p className="mt-3 text-sm leading-6 text-neutral-700 sm:text-base">
              Seguimiento de precios Ryanair con alertas, histórico y contexto
              para decidir cuándo comprar.
            </p>
          </div>

          <nav
            aria-label="Footer"
            className="grid gap-8 sm:grid-cols-3 lg:col-span-7"
          >
            {footerGroups.map((group) => (
              <div key={group.title}>
                <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-neutral-500">
                  {group.title}
                </h2>
                <ul className="mt-4 space-y-3">
                  {group.links.map((link) => (
                    <li key={`${group.title}-${link.label}`}>
                      <a
                        href={link.href}
                        className="text-sm text-neutral-700 transition hover:text-neutral-950 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-900/30"
                      >
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </div>

        <div className="mt-12 flex flex-col gap-4 border-t border-black/10 pt-6 text-xs text-neutral-500 sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Viru Tracker. Todos los derechos reservados.</p>
          <a
            href="#top"
            className="w-fit transition hover:text-neutral-900 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-900/30"
          >
            Volver arriba ↑
          </a>
        </div>
      </div>
    </footer>
  );
}

Pero antes de usar este código:

sustituye /login, /register, /policies por rutas reales;
usa el componente Link del framework si corresponde;
usa tokens internos si existen;
no añadas href="#top" si no existe un ancla segura;
no dupliques navegación si ya hay constantes globales.
Criterios de aceptación visual

El cambio se considera correcto si:

El footer ocupa todo el ancho como zona visual.
El contenido interno ya no parece una card estrecha de 965 px.
En desktop el contenido se acerca a 1280-1360 px de ancho máximo.
Desaparece FO OT ER BLO CK.
Desaparece Footer adaptado a Viru....
Desaparece el bloque protagonista CONTEXTO ACTIVO.
La marca Viru Tracker se ve como identidad de footer, no como hero.
Las columnas tienen jerarquía clara.
El legal queda abajo y secundario.
No hay enlaces que no funcionen.
Mobile se ve limpio, apilado y sin overflow horizontal.
No se rompe ningún layout anterior de la landing.
Criterios de aceptación técnica

Al terminar:

Ejecuta el comando de lint si existe.
Ejecuta typecheck si existe.
Ejecuta build si existe.
Si hay tests, ejecuta los relacionados o la suite más razonable.
No introduzcas dependencias nuevas.
No cambies comportamiento de auth/rutas/precios.
No cambies componentes no relacionados salvo imports necesarios.
Reporta comandos ejecutados y resultado.
Si algún comando falla por algo preexistente, indícalo claramente y separa “fallo preexistente” de “fallo causado por este cambio”.
Mensaje final esperado

Cuando termines, responde con:

Archivos modificados.
Qué cambió visualmente.
Qué textos/rutas eliminaste.
Qué rutas reales usaste.
Comandos ejecutados.
Cualquier limitación o cosa que conviene revisar manualmente.

Y este sería un `AGENTS.md` útil para dejarle normas duraderas a Codex en este repo. No sustituye al prompt anterior; sirve para que futuras tareas de Viru no vuelvan a caer en textos placeholder o enlaces inventados.

```md
# AGENTS.md — Viru Tracker

## Product/design rules

Viru Tracker is an editorial SaaS-style web app for tracking Ryanair route prices. Keep the interface calm, clear, warm, and product-like. Avoid generic corporate UI.

## Footer rules

- Never render internal component labels such as `FOOTER BLOCK`, `FooterBlock`, `adapted footer`, or design notes.
- Do not expose implementation commentary in user-facing copy.
- Do not create phantom links. Only link to routes that actually exist in the app.
- If a support/help route does not exist, use `mailto:soporte@viru.app`.
- Footer should be a full-width page closure, not a narrow card.
- Prefer a full-width footer wrapper with an inner max-width around 1280-1360px on desktop.
- Use clear footer columns: Product, Account, Contact, Legal when applicable.
- Keep footer typography secondary. The footer brand must not compete with the landing hero.
- Avoid icon noise in footer navigation.
- Footer legal copy should be short and production-ready.

## Engineering rules

- Inspect existing components and route structure before editing.
- Reuse existing Link, Button, cn/className utilities and design tokens.
- Do not add dependencies unless explicitly requested.
- Keep changes scoped to the requested component.
- Run available lint/typecheck/build commands after changes.
- Report files changed and commands run.