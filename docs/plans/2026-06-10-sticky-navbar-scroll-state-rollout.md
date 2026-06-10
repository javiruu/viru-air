# Plan de 5 fases para introducir una navbar sticky morph con CSS scroll-state en todo Viru Tracker

**Estado:** activo  
**Fecha:** 2026-06-10  
**Autor:** Codex  
**Area:** plan  
**Fuente de verdad:** no; plan operativo para rollout UI transversal apoyado en el estado real del frontend

## Objetivo

Introducir en todo `viru-tracker` una cabecera sticky que cambie de forma al quedar fijada durante el scroll usando `container-type: scroll-state` y `@container ... (stuck: top)`, manteniendo la identidad calida y aeronautica de Viru, evitando dependencias de JS para la animacion principal y sin degradar dark/light, mobile ni accesibilidad.

## Decision de enfoque

La propuesta no debe entrar como un truco CSS aislado, sino como una mejora de shell compartida:

- la navegacion privada ya esta centralizada en `frontend/src/modules/shared/PrivateNav.tsx`;
- la shell privada ya concentra la cabecera en `frontend/src/app/(private)/layout.tsx`;
- hoy existe un comportamiento parcial con JS en `frontend/src/modules/shared/PrivateTopBar.tsx` mediante `IntersectionObserver`;
- la parte publica aun no tiene una shell de navegacion equivalente en `frontend/src/app/(public)/layout.tsx`.

Por eso el rollout correcto es:

1. convertir la morph navbar en un patron canonico de sistema;
2. activarlo primero en la shell privada;
3. extenderlo luego a la shell publica y a rutas especiales;
4. retirar JS donde ya no aporte valor funcional real.

## Principios de implementacion

- Progressive enhancement: si `scroll-state` no esta disponible, la navbar debe seguir siendo usable y visually coherent.
- Sin JS para detectar el estado sticky final: el morph debe depender de CSS container queries, no de observers ni animation libraries.
- Un solo patron compartido: evitar duplicar una navbar distinta por pantalla.
- Dual-theme obligatorio: dark y light deben conservar la misma personalidad, no solo la misma estructura.
- Scope controlado: no mezclar este rollout con refactors de routing, auth, copy o negocio.

## Superficies reales afectadas

### Shell y navegacion

- `frontend/src/app/(private)/layout.tsx`
- `frontend/src/app/(public)/layout.tsx`
- `frontend/src/modules/shared/PrivateTopBar.tsx`
- `frontend/src/modules/shared/PrivateNav.tsx`
- `frontend/src/modules/shared/navigationV1.ts`

### Capa visual

- `frontend/src/styles/tokens.css`
- `frontend/src/styles/components.css`
- `frontend/src/styles/screens.css`
- `frontend/src/styles/base.css` o `frontend/src/styles/globals.css` solo si hace falta fijar comportamiento base de scroll/safe areas

### QA y documentacion

- `frontend/tests/navigation-v1.test.ts`
- nuevos tests de navbar/shell si se crean
- `docs/ui/UI_CONTRACT_V1.md` solo si el patron queda ya congelado como contrato
- `docs/qa/` para evidencia visual si el rollout se ejecuta

## Riesgo tecnico principal

El mayor riesgo no es visual sino de compatibilidad: `container-type: scroll-state` y `@container scroll-state(...)` deben entrar como mejora progresiva. La regla de producto debe ser:

- con soporte: navbar morph completa, centrada, compacta y con glass/control de ancho al quedar stuck;
- sin soporte: navbar sticky estable, sin morph o con morph minima no dependiente de deteccion JS;
- nunca: ocultacion, saltos de layout, CTA inaccesibles o drift a un header SaaS generico.

---

## Fase 1. Baseline, compatibilidad y contrato visual del patron

### Objetivo

Definir exactamente como debe comportarse la navbar morph en Viru antes de tocar toda la app, aterrizando soporte, limites visuales y alcance real del rollout.

### Trabajo

- Auditar el estado actual de la shell privada:
  - `frontend/src/modules/shared/PrivateTopBar.tsx`
  - `frontend/src/app/(private)/layout.tsx`
  - `frontend/src/styles/screens.css` (`.private-account-anchor`, `.private-nav`, `.private-account-controls`)
- Auditar la shell publica para ver si necesita una barra compartida nueva o un patron mas ligero:
  - `frontend/src/app/(public)/layout.tsx`
  - `frontend/src/app/page.tsx`
  - rutas publicas largas como `/policies` y `/ayuda`
- Definir el comportamiento canonico de los dos estados:
  - `resting`: ancho mas generoso, respiracion editorial, integracion con la hero/shell
  - `stuck`: ancho contenido, radio mayor, fondo mas denso o glass, sombra controlada, prioridad de CTA y toggles
- Validar que la version stuck siga cumpliendo con:
  - foco visible
  - scroll horizontal controlado en mobile
  - orden claro entre nav, idioma, tema y cuenta

### Archivos de referencia

- `frontend/src/modules/shared/PrivateTopBar.tsx`
- `frontend/src/modules/shared/PrivateNav.tsx`
- `frontend/src/modules/shared/navigationV1.ts`
- `frontend/src/styles/screens.css`
- `DESIGN.md`
- `docs/ui/UI_CONTRACT_V1.md`
- `docs/ui/UI_SYSTEM_V1.md`
- `docs/ui/UI_VISUAL_QA_CHECKLIST.md`

### Criterio de salida

- Existe una definicion cerrada de comportamiento visual y tecnico.
- Se decide explicitamente si la version publica comparte exactamente el mismo patron o una variante hermana.
- Queda fijado que el rollout sera progressive enhancement y no dependera de `IntersectionObserver`.

### Verificacion

- Revision de rutas core afectadas en escritorio y mobile:
  - `/dashboard`
  - `/watchlist`
  - `/quick-search`
  - `/alerts`
  - `/login`
  - `/register`
- Checklist de contrato visual contra `docs/ui/UI_VISUAL_QA_CHECKLIST.md`.

---

## Fase 2. Extraer el patron compartido y los tokens de morph

### Objetivo

Crear la base reutilizable para que la navbar morph exista como patron de sistema y no como CSS pegado a una sola ruta.

### Trabajo

- Crear el set minimo de tokens semanticos para el header morph:
  - ancho maximo en estado stuck
  - radios
  - padding inline/block
  - blur/opacidad/sombra
  - offsets top y safe area
- Mover a `components.css` el patron compartido de shell header si se confirma que aparece en 2+ superficies.
- Encapsular la logica estructural en una pieza compartida, por ejemplo:
  - mantener `PrivateTopBar` pero volverlo presentacional y sin observer, o
  - reemplazarlo por una shell mas canonica compartida entre privado/publico
- Definir el bloque CSS con `@supports` y `@container scroll-state(stuck: top)` para el morph real.

### Archivos candidatos

- `frontend/src/styles/tokens.css`
- `frontend/src/styles/components.css`
- `frontend/src/styles/screens.css`
- `frontend/src/modules/shared/PrivateTopBar.tsx`
- posible nuevo componente compartido en `frontend/src/modules/shared/`

### Decisiones clave

- El estado sticky base debe funcionar incluso sin `scroll-state`.
- El morph no debe depender de clases temporales como `.is-leaving`.
- El patron debe tolerar:
  - nav extensa (`NAV_V1_PRIVATE`)
  - toggles
  - menu de cuenta
  - traduccion ES/EN sin colisiones de ancho

### Criterio de salida

- Existe un patron compartido con tokens y naming canonicos.
- El componente base ya no necesita JS para “saber” que esta stuck.
- El layout no salta al entrar o salir del estado sticky.

### Verificacion

- Test unitario de navegacion existente sin regresiones:
  - `frontend/tests/navigation-v1.test.ts`
- Nuevo test de render si se introduce un wrapper compartido.
- `npm run build` en `frontend/`.

---

## Fase 3. Migrar la shell privada completa al patron CSS-only

### Objetivo

Aplicar la navbar morph a toda la zona autenticada, que hoy es la superficie mas clara y transversal del producto.

### Trabajo

- Reemplazar en la shell privada el comportamiento actual con observer por el patron CSS-only.
- Mantener `PrivateNav` como fuente unica de enlaces, sin tocar contratos de routing.
- Reordenar visualmente la barra privada para que el estado stuck preserve:
  - navegacion prioritaria
  - acciones de idioma/tema
  - acceso a cuenta
- Ajustar responsive para que:
  - en desktop la barra pueda comprimirse a una pieza centrada y premium
  - en tablet/mobile no se vuelva una “capsula bonita” pero impracticable

### Archivos principales

- `frontend/src/app/(private)/layout.tsx`
- `frontend/src/modules/shared/PrivateTopBar.tsx`
- `frontend/src/modules/shared/PrivateNav.tsx`
- `frontend/src/styles/screens.css`
- `frontend/src/styles/components.css`

### Riesgos a controlar

- overflow horizontal en `.private-nav`
- perdida de legibilidad del estado activo
- controles de cuenta demasiado comprimidos en mobile
- conflicto entre stickiness del header y componentes sticky locales como `DoorToDoorStickyBar.tsx`

### Criterio de salida

- Todas las rutas privadas comparten el nuevo patron de navbar morph.
- Se elimina la necesidad del observer actual o queda solo como fallback deliberado y documentado mientras dura la transicion.
- No aparecen regresiones de estructura en `/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/puerta-a-puerta`, `/hoteles`, `/preferencias`.

### Verificacion

- `npm test -- tests/navigation-v1.test.ts`
- tests cercanos de navegacion/visibilidad si aplican:
  - `frontend/tests/private-visible-copy-es.test.ts`
  - `frontend/tests/session-routing.test.ts`
- revision real en browser de dark y light en:
  - `1440x900`
  - `768x1024`
  - `375x812`
  - `320x780`

---

## Fase 4. Extender el patron a la shell publica y a rutas largas especiales

### Objetivo

Hacer que la experiencia de navbar morph sea consistente en toda la app, no solo dentro del area autenticada.

### Trabajo

- Decidir si la shell publica necesita:
  - una navbar equivalente con `NAV_V1_PUBLIC`, o
  - una variante mas ligera para no sobrecargar login/register
- Introducir la cabecera compartida en `frontend/src/app/(public)/layout.tsx` si se valida que suma coherencia.
- Ajustar rutas publicas con scroll largo, donde el beneficio es mas claro:
  - `/`
  - `/ayuda`
  - `/policies`
- Evitar que formularios de acceso pierdan protagonismo por un header demasiado dominante.

### Archivos principales

- `frontend/src/app/(public)/layout.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/modules/shared/navigationV1.ts`
- posible `PublicNav` o variante compartida en `frontend/src/modules/shared/`
- `frontend/src/styles/screens.css`
- `frontend/src/styles/components.css`

### Decisiones clave

- En login/register la navbar debe acompañar, no competir.
- En pages editoriales largas (`/policies`, `/ayuda`) el morph puede ayudar mucho si mejora orientacion y no roba lectura.
- La version publica debe sentirse hermana de la privada, no copia degradada.

### Criterio de salida

- La app ya tiene un patron de navbar coherente entre publico y privado.
- Las rutas largas ganan orientacion durante scroll sin introducir ruido.
- Login/register siguen claros, ligeros y bien jerarquizados.

### Verificacion

- Revisar manualmente:
  - `/`
  - `/ayuda`
  - `/policies`
  - `/login`
  - `/register`
- Confirmar accesibilidad de teclado y foco visible sobre enlaces/toggles.
- Confirmar que no hay drift a “header marketing genérico”.

---

## Fase 5. QA transversal, retirada de deuda JS y cierre de contrato

### Objetivo

Cerrar el rollout con evidencia, limpieza de deuda y documentacion suficiente para que el patron quede mantenible en todo Viru.

### Trabajo

- Retirar codigo JS residual si ya no aporta comportamiento necesario:
  - especialmente `IntersectionObserver` en `PrivateTopBar.tsx`
- Añadir tests de regresion para la shell si merece cobertura estable:
  - render
  - clases/atributos de estructura
  - estados de navegacion activa
- Ejecutar QA visual transversal sobre rutas core y rutas publicas largas.
- Documentar el patron si queda consolidado como componente/base del sistema:
  - `docs/ui/UI_CONTRACT_V1.md`
  - `docs/ui/UI_SYSTEM_V1.md`
  - evidencia ligera en `docs/qa/` si el cambio se implementa

### Verificacion minima de cierre

- `npm run build`
- `npm test -- tests/navigation-v1.test.ts`
- tests nuevos de shell/navbar si se crean
- verificacion real en browser de ambos temas
- validacion especifica de:
  - stickiness
  - morph al quedar stuck
  - focus
  - scroll horizontal
  - comportamiento sin soporte de `scroll-state` si se simula fallback

### Criterio de salida

- El producto tiene una navbar sticky morph consistente en publico y privado.
- El comportamiento principal depende de CSS, no de JS.
- La experiencia queda verificada en dark/light, desktop/tablet/mobile.
- La deuda anterior queda retirada o explicitamente documentada.

---

## Orden recomendado de ejecucion

1. Fase 1 para cerrar soporte y patron visual.
2. Fase 2 para extraer base comun y progressive enhancement.
3. Fase 3 para conquistar toda la shell privada.
4. Fase 4 para llevar coherencia al area publica.
5. Fase 5 para QA transversal, limpieza y contrato final.

## Lo que no entra en este plan

- Reescribir el sistema de navegacion.
- Cambiar labels o taxonomia de rutas salvo necesidad puntual de layout.
- Redisenar pantallas completas aprovechando el rollout del header.
- Introducir librerias nuevas de animacion o scroll.
- Resolver otras deudas visuales no relacionadas con la shell.

## Resultado esperado si se ejecuta bien

Viru ganaria una pieza de navegacion mas viva y mas propia: una cabecera que acompana el scroll con intencion, se compacta como instrumento de cabina cuando hace falta y sigue sintiendose calida, premium y cercana en dark y light, sin convertirse en un truco visual ni en una barra generica de SaaS.
