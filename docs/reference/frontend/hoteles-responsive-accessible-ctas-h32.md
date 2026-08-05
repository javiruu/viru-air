# H32 — Responsive hotelero, overflow y CTAs accesibles

**Estado:** completa como contrato responsive; implementación frontend, hardening de CSS, tests de viewport y browser QA pendientes  
**Fecha:** 2026-08-05  
**Área:** frontend / accesibilidad / UX / QA / i18n  
**Fuente de verdad:** sí para el comportamiento responsive y la accesibilidad operativa de CTAs de `/hoteles`  
**Fase del roadmap:** H32  
**Depende de:** [H16 — result cards](hoteles-result-cards-h16.md), [H21 — estados y recuperación](hoteles-state-matrix-h21.md), [H31 — dirección visual](hoteles-visual-direction-states-h31.md)  
**Relacionado con:** H03 arquitectura, H13 formulario, H18 detalle, H22 favoritos, H23 tracking, H27 inbox, H33 WCAG, H34 i18n, H36 rendimiento, H40 browser QA

> H32 no convierte `/hoteles` en una versión desktop encogida. Define cómo debe reordenarse, respirar y seguir siendo accionable cuando cambian el viewport, el zoom, el idioma, el estado de datos o el método de interacción.

## 1. Decisión de alcance

H32 fija el contrato para:

1. layout por viewport y anchuras intermedias;
2. orden móvil de búsqueda, resultados, detalle y secundarios;
3. prevención de overflow horizontal, clipping y saltos de layout;
4. touch targets y CTAs de búsqueda, favorito, tracking, retry y paneles;
5. navegación por teclado, foco y controles plegables;
6. zoom de texto, nombres largos, mensajes traducidos y safe areas;
7. drawers/sheets y gráficos cuando existan;
8. reduced motion y estabilidad durante loading/refresh;
9. matriz de pruebas y evidencia browser.

H32 **no** implementa todavía React/CSS, no cambia endpoints ni estados de negocio, no declara cumplimiento WCAG completo y no introduce una librería UI. H33 será la auditoría WCAG transversal; H34 cerrará la cobertura lingüística; H40 aportará la evidencia browser de release.

## 2. Estado actual comprobable

### 2.1. Composición real

`HotelRadarPage` renderiza cabecera, métricas, `HotelSearchPanel`, notice global, resultados, seguimientos, timeline y una columna lateral con detalle, favoritos, paridad, alertas y comp sets. La página ya tiene paneles plegables para parte de los secundarios, pero la jerarquía móvil y la accesibilidad completa de esos paneles siguen pendientes.

### 2.2. Evidencia CSS actual

La implementación actual contiene:

- `.hotel-search-grid` y `.hotel-search-area-grid` con grids de varias columnas;
- un breakpoint `max-width: 768px` que pasa el buscador a una columna y coloca las tabs en vertical;
- un breakpoint `max-width: 480px` que fija las tabs en `min-height: 44px`;
- inputs de fecha con `font-size: 1rem` en móvil;
- reglas globales `focus-visible` y una utilidad `.ios-zoom-fix`;
- `html { zoom: 75% }` global desde 1024 px, una decisión de densidad que puede falsear la percepción de zoom/viewport y debe validarse explícitamente;
- drawers de filtros en otras superficies del frontend con scroll interno/safe areas, que sirven de patrón pero no prueban que `/hoteles` ya tenga un drawer equivalente.

Esto es una base V1, no evidencia de que todos los CTAs, cards, paneles y estados hoteleros funcionen sin clipping en 360/390/414/768/1024 px o con zoom de texto. El mínimo H32 para **todos los controles hoteleros existentes y nuevos** será **48 px**, aunque el CSS actual aún conserve un caso de 44 px.

### 2.3. Gaps explícitos que H32/H33/H40 deben cerrar

- validar el ancho total real en 360, 390/414, 600, 768, 820, 1024 y desktop;
- retirar o justificar cualquier control táctil menor de 48 px;
- comprobar que nombres de hoteles, precios, warnings, botones y copy ES/EN no fuerzan overflow;
- añadir `aria-controls` e IDs únicos con asociación estable: los paneles plegables actuales tienen `aria-expanded`, pero todavía carecen de `aria-controls` explícito;
- garantizar que el error accionable use `role="alert"`, no solo el `role="status"` actual de `HotelRadarPage`;
- probar teclado, focus visible, lector de pantalla, zoom y reduced motion sobre estados no felices;
- comprobar que el CTA no queda bajo teclado virtual, safe area, sticky header o drawer.

## 3. Contrato de layout por viewport

### 3.1. Mobile base: 360 px

La página debe funcionar sin scroll horizontal a 360 px CSS y sin depender de hover.

Orden de fuente/lectura obligatorio:

```text
cabecera → buscador → estado de búsqueda → resultados → detalle seleccionado
→ guardar/seguir → histórico/seguimiento → alertas/paridad/cercanos
```

Reglas:

- una sola columna;
- padding lateral suficiente para foco y toque, sin crear una segunda barra de scroll;
- destino, fechas, ocupación y CTA en secuencia natural;
- cards apiladas: identidad → precio/estado → estancia → confianza → acciones;
- secundarios plegables después de la decisión, sin ocultar retry o CTA principal;
- ningún dato esencial se comunica únicamente por icono, color, tooltip o hover;
- los botones de acción pueden ocupar el ancho disponible, pero no deben desbordar por copy traducido;
- si una tabla o gráfico no cabe, se ofrece resumen/lista accesible, no un canvas ilegible.

### 3.2. Mobile ancho: 390/414 px

La interfaz puede ganar aire y distribuir acciones en una fila solo si cada control conserva 48 px de altura y un nombre visible/accessible. No se debe usar el espacio adicional para reintroducir una cuadrícula de desktop.

### 3.3. Tablet/intermedio: 768 px

- buscador en una columna si la combinación de campos no garantiza legibilidad;
- resultados y detalle pueden ser dos regiones solo si cada una conserva `min-width: 0` y no fuerza clipping;
- si el detalle pasa debajo de resultados, el orden DOM y el tab order deben coincidir con la lectura;
- las acciones permanecen visibles sin depender de un `position: sticky` que tape contenido;
- los paneles secundarios no se convierten en cinco columnas estrechas.

### 3.4. 1024 px y desktop

- resultados y detalle pueden usar layout de dos columnas con columnas `minmax(0, ...)`;
- la columna de decisión tiene prioridad de ancho sobre secundarios;
- nombres largos y estados no desplazan el precio fuera de la card;
- no introducir scroll interno en cards para resolver un problema que debe resolver el wrapping;
- la densidad desktop no puede eliminar labels, foco o contexto de estancia.

### 3.5. Anchuras intermedias y zoom

No se permite diseñar solo para los saltos de 480/768/1024. Deben probarse al menos 600, 820 y 1280 px, además de los mínimos de H31. Con 200% de zoom de texto o viewport reducido equivalente:

- no aparece scroll horizontal de página;
- no se recorta copy ni CTA;
- los botones pueden crecer en altura;
- no se usan alturas fijas para contenido variable;
- el foco no queda oculto detrás de un contenedor con overflow;
- la información secundaria puede apilarse, pero no desaparecer silenciosamente.

## 4. CTAs y targets de interacción

### 4.1. Mínimo común

Todo `button`, enlace que actúe como control, input, select, summary, toggle o `[role="button"]` táctil debe ofrecer un área de interacción de **48 × 48 px mínimo**. Si el icono visual es menor, el hit area sigue siendo 48 px.

Esto aplica a:

- buscar y cancelar;
- seleccionar modo nombre/área;
- elegir sugerencia;
- guardar hotel y quitar favorito;
- seguir/detener precio;
- reintentar búsqueda, rates, paridad, alertas o cercanos;
- abrir/cerrar detalle y secundarios;
- activar/pausar/eliminar una alerta;
- navegar una tabla/curva si existe;
- abrir filtros y aplicar/borrar filtros.

No se debe arreglar el target con padding que provoque que el elemento salga de su card o tape otro control.

### 4.2. Jerarquía y estados

- una acción primaria como máximo por panel/card/bloque, según H31;
- el CTA conserva espacio cuando pasa a `loading`, `disabled` o `success`, evitando layout shift;
- `disabled` incluye razón visible o asociación accesible cuando el contexto está incompleto;
- `retry` nombra la superficie concreta: “Reintentar tarifas”, no solo “Reintentar”;
- guardar hotel y seguir precio siguen siendo acciones semánticamente distintas según H22/H23;
- no mostrar “seguir precio” como disponible desde `empty`, `error`, `unavailable` o una oferta sin contexto elegible;
- una confirmación local no sustituye al estado persistente del tracking o de la alerta.

### 4.3. Focus y teclado

- todos los controles son alcanzables por teclado en orden de lectura;
- `:focus-visible` mantiene outline de al menos 2 px, offset visible y contraste suficiente en dark/light;
- no se elimina el outline con `outline: none` salvo que exista un reemplazo equivalente verificable;
- seleccionar una card no intercepta ni impide activar sus botones internos;
- al cerrar un panel/drawer, el foco vuelve al control que lo abrió;
- Escape cierra overlays cuando el patrón lo requiera, sin perder búsqueda ni selección;
- un drawer/sheet debe tener nombre, estado `aria-expanded`, `aria-controls`, región asociada y estrategia de focus/scroll lock documentada;
- no se exige un drawer hotelero hasta que exista una implementación accesible; mientras tanto no se debe presentar un botón que abra un panel inexistente.

## 5. Overflow, wrapping y estabilidad

### 5.1. Reglas CSS de implementación

- grids y flex children de contenido usan `min-width: 0` donde puedan recibir texto largo;
- preferir `minmax(0, 1fr)` a columnas que conserven un `min-content` excesivo;
- preferir `min-height` a `height` para cards, notices, botones y estados;
- permitir `flex-wrap` en acciones y metadata;
- precios, monedas y fechas pueden envolver de forma legible; nunca se cortan con ellipsis si el valor completo es necesario para decidir;
- `overflow-x: hidden` no se acepta como parche global sin identificar el elemento que desborda;
- cualquier scroll horizontal intencional debe estar contenido, anunciado y tener alternativa accesible;
- no anidar scrolls en card + panel + página para resolver una única lista.

### 5.2. Contenido difícil

Verificar con:

- nombre de hotel de al menos 80 caracteres;
- ciudad/país largos;
- precio con moneda y separadores locales;
- warnings partial/stale/error de varias líneas;
- nombres de provider largos;
- ES y EN, incluyendo plural de noches/huéspedes;
- fechas y timezones diferentes;
- usuario con zoom de texto 200%.

El resultado debe preservar identidad, importe, contexto de estancia, estado de confianza y CTA; lo ornamental es lo primero que puede comprimirse.

### 5.3. Loading y refresh

- skeletons reservan una altura aproximada y no producen saltos que muevan el CTA bajo el dedo;
- refresh compatible conserva resultados anteriores con etiqueta de estado según H21;
- una respuesta obsoleta no reordena ni sobrescribe una selección nueva;
- la transición de loading a error/empty conserva formulario y contexto;
- reduced motion elimina shimmer, desplazamientos y pulsos no esenciales, pero mantiene feedback textual.

## 6. Responsive por superficie

| Superficie | Mobile | Tablet/intermedio | Desktop | Criterio de salida |
|---|---|---|---|---|
| Buscador | una columna, CTA visible | wrapping sin campos comprimidos | agrupación por intención | completar y corregir sin perder foco |
| Result cards | apiladas, acciones visibles | dos regiones solo con ancho real | precio/CTA alineados | ninguna acción depende de hover |
| Detalle | debajo o panel accesible | no roba el tab order | columna ancla | volver conserva búsqueda |
| Tracking/histórico | resumen + lista alternativa | timeline legible | curva + resumen | no se depende solo de gráfico |
| Alertas | reglas/eventos apilados | panel plegable | secundarios agrupados | error y retry localizados |
| Paridad/cercanos | secundarios después de decisión | no crean mosaico estrecho | columna de apoyo | no confundir con oferta principal |
| Filtros | sheet/drawer si se implementa | panel que no tape CTA | panel lateral o toolbar | focus, Escape y retorno verificados |

## 7. Estados H21 en mobile

La adaptación visual no puede simplificar la semántica:

- `idle`: CTA visible y formulario intacto;
- `loading`: skeleton estable, contexto conservado y opción de cancelar si existe;
- `success`: resultados y acciones completas;
- `empty`: explicación y acción para ampliar/cambiar, no un panel vacío;
- `partial`: warning junto al dato afectado, no banner técnico que desplace todo;
- `stale`/`stale_while_error`: fecha de observación, limitación y retry accesible;
- `unavailable`: alternativa honesta, no falsa disponibilidad;
- `auth_required`: reautenticación sin borrar campos ni URL state;
- `not_found`: retorno claro a resultados;
- `cancelled`: sin toast de error;
- `error`: `role="alert"`, foco/lectura accionable y retry específico.

En ningún viewport `[]`, timeout, 401/403, 404 o fallo de provider pueden compartir el mismo copy de “sin hoteles”.

## 8. i18n, zoom y temas

- ES/EN se prueban con el mismo viewport; no basta con que las claves existan;
- fechas, monedas, noches, huéspedes y “comprobado hace” usan locale real;
- no concatenar frases que cambien de orden en inglés;
- los labels no se ocultan para ahorrar ancho si dejan el control ambiguo;
- dark/light conservan la misma estructura, estado, orden y foco;
- no introducir colores hoteleros paralelos para indicar éxito/error/partial;
- los contrastes y outlines usan aliases/tokens canónicos;
- zoom de navegador y texto no rompen la acción de búsqueda ni la de tracking.

## 9. QA y gates de aceptación

### 9.1. Contract tests/estáticos

- existe un layout con `minmax(0, ...)`/`min-width: 0` donde el contenido lo necesita;
- no hay control táctil hotelero existente o nuevo menor de 48 px;
- no hay botones anidados ni CTA oculto exclusivamente por hover;
- los controles plegables tienen `aria-expanded` y `aria-controls` cuando controlan una región;
- error accionable usa `role="alert"` y progreso usa `role="status"`;
- favorito y tracking mantienen copy/estado separados;
- H21 no se contradice: `empty` no es `error` y un `provider_error` no se presenta como `empty`/`sold_out`;
- no aparecen nuevos colores hardcodeados ni tokens paralelos;
- reduced motion (`prefers-reduced-motion`) cubre animaciones hoteleras.

### 9.2. Browser matrix

Ejecutar con fixtures controlados y estados reales disponibles:

- viewports: 360×800, 390×844, 414×896, 600×900, 768×1024, 820×1180, 1024×768 y desktop habitual;
- temas: dark y light;
- zoom/text scaling real: 100%, 150% y 200%, verificando además que el `html { zoom: 75% }` global de desktop no invalida la lectura del resultado;
- interacción: ratón/táctil, teclado completo y lector de pantalla cuando el entorno lo permita;
- datos: idle, loading, success, empty, partial, stale, stale-while-error, unavailable, auth, not-found, cancelled y error;
- contenido: nombres largos, copy ES/EN, monedas y fechas distintas;
- acciones: buscar, seleccionar, guardar, seguir, retry, plegar/desplegar y volver al detalle.

### 9.3. Evidencia mínima

Cada ejecución debe guardar:

- viewport, tema, locale y zoom;
- fixture/request fingerprint no sensible;
- interacción ejecutada;
- screenshot o video solo cuando aporte evidencia visual;
- consola limpia o errores explicados;
- resultado de scroll horizontal (`document.documentElement.scrollWidth` no excede el viewport salvo región intencional documentada);
- foco antes/después de abrir/cerrar un panel;
- cualquier gap residual con owner y fase (H33/H34/H40).

### Gate H32

H32 podrá marcarse implementada cuando:

1. `/hoteles` funciona en todos los viewports de la matriz sin overflow horizontal inesperado;
2. todos los CTAs y controles táctiles existentes y nuevos ofrecen 48 × 48 px mínimo;
3. el buscador y el tracking siguen siendo operables con teclado, touch y zoom 200%;
4. cards, detalle y secundarios respetan el orden H31 y no ocultan acciones por hover;
5. nombres largos, warnings y ES/EN no recortan información esencial;
6. loading/error/empty/stale/partial conservan contexto y muestran recuperación según H21;
7. controles plegables y drawers, si existen, tienen semántica y retorno de foco verificables;
8. dark/light mantienen contraste, estructura y significado equivalentes;
9. reduced motion elimina movimiento no esencial sin eliminar feedback;
10. browser QA aporta evidencia de estados felices y no felices, no solo una captura desktop;
11. no se confunde el cierre responsive con el cierre WCAG completo de H33 ni con la localización completa de H34.

**Resultado contractual:** H32 define el responsive hotelero y el contrato de CTAs accesibles. El CSS actual aporta una base parcial —incluido un control de 44 px que debe corregirse—, pero la implementación completa y su evidencia quedan pendientes de H32/H33/H34/H40.
