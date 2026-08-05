# H33 — Auditoría de accesibilidad WCAG 2.2 AA para `/hoteles`

**Estado:** completa como contrato de auditoría; remediación frontend, tests a11y y recorrido manual pendientes  
**Fecha:** 2026-08-05  
**Área:** QA / frontend / accesibilidad / UX / i18n  
**Fuente de verdad:** sí para el alcance, prioridades y gate de accesibilidad hotelera  
**Fase del roadmap:** H33  
**Depende de:** [H13 — formulario](../backend/hoteles-search-form-h13.md), [H16 — result cards](hoteles-result-cards-h16.md), [H18 — detalle y navegación](hoteles-detail-navigation-h18.md), [H27 — inbox y deep links](../backend/hoteles-private-inbox-deeplinks-h27.md), [H32 — responsive y CTAs](hoteles-responsive-accessible-ctas-h32.md)  
**Relacionado con:** [H21 — estados](hoteles-state-matrix-h21.md), [H31 — dirección visual](hoteles-visual-direction-states-h31.md), H34 i18n, H36 rendimiento, H39 tests, H40 browser QA

> H33 no se cierra porque existan labels, `focus-visible` o algunos roles aislados. Se cierra cuando una persona puede buscar, entender, seleccionar, guardar, seguir, revisar una señal y recuperarse de errores usando teclado, lector de pantalla, zoom y temas dark/light, sin perder contexto ni recibir estados engañosos.

## 1. Alcance y límites

H33 define la auditoría WCAG 2.2 AA específica para:

1. landmarks, headings y orden de lectura de `HotelRadarPage`;
2. formulario de búsqueda por nombre/ciudad y por área;
3. autocomplete/listbox y navegación con teclado;
4. resultados, selección, detalle y acciones internas;
5. favoritos, tracking, histórico, snapshots, alertas, paridad y comp sets;
6. loading, empty, partial, stale, auth, not-found, cancelled y error según H21;
7. nombre, descripción, estado, foco y anuncios de cada control;
8. contraste, zoom, touch targets y reduced motion en dark/light;
9. errores inline, validación, live regions y recuperación de foco;
10. pruebas automatizadas, inspección manual y evidencia browser.

H33 **no** implementa todavía la remediación, no cambia el contrato de negocio/API, no declara certificación legal ni conformidad WCAG completa por inspección estática. H32 fija responsive/touch/zoom; H34 cerrará i18n; H40 verificará browser QA de release.

## 2. Evidencia V1 comprobable

### 2.1. Semántica existente útil

La implementación actual ya aporta:

- `main#main-content` en `HotelRadarPage`;
- headings de página, paneles y subsecciones;
- `<form>` y labels envolventes para buena parte de los campos;
- estilos globales `:focus-visible` con outline de 3 px y offset de 2 px;
- `aria-pressed` para favorito y tracking;
- `role="listbox"`, `role="option"` y `aria-selected` en sugerencias de área;
- botones nativos para acciones, controles de modo y selección;
- `font-size: 1rem` en inputs de fecha móvil y una utilidad `.ios-zoom-fix`;
- copy ES/EN para las principales superficies y estados.

Esto es una base aprovechable, no evidencia de conformidad. La auditoría debe comprobar nombres accesibles, relaciones, estados, foco y comportamiento real, no solo la presencia literal de atributos.

### 2.2. Gaps actuales observados

#### P0 — bloqueantes antes de declarar H33 cerrada

- El autocomplete de área expone listbox/option, pero el input no tiene contrato completo de combobox: faltan `role="combobox"`, `aria-expanded`, `aria-controls`, `aria-autocomplete`, ownership claro del listbox, `aria-activedescendant` y navegación Arrow/Escape/Enter verificable. Además, el patrón actual `<li role="option"><button>` mezcla un option enfocable con un botón enfocable; la remediación debe elegir un patrón listbox consistente.
- Los paneles plegables de `HotelRadarPage` tienen `aria-expanded`, pero no `aria-controls` ni IDs estables que relacionen botón y región.
- El notice de error de búsqueda usa actualmente `role="status"`; los errores accionables deben usar `role="alert"` o una asociación equivalente, manteniendo `status` para progreso informativo.
- Errores de campo, validaciones de alertas y cambios de resultados no tienen todavía una estrategia común de `aria-describedby`, `aria-invalid`, `aria-live` y foco inicial.
- `HotelTrackedOfferSnapshots` convierte un fallo de endpoint en lista vacía; esto puede anunciar “sin historial” cuando existe un error, contradiciendo H21 y perjudicando la comprensión con lector de pantalla.
- No existe cobertura hotelera suficiente que pruebe teclado, nombres accesibles, roles, foco, estados ni targets; los tests existentes son principalmente estructurales.
- El botón de tracking actual expone `aria-pressed`, pero queda disabled cuando el tracking está activo y no ofrece una transición inversa: no es todavía un toggle real y debe retirarse esa semántica o convertirse en un control toggle coherente.

#### P1 — necesarios para uso robusto

- Definir nombre accesible único para cada botón de acción repetido: hotel, operación y estado deben poder distinguirse sin leer visualmente toda la card.
- Exponer la selección de resultado con `aria-current`, `aria-pressed` o patrón equivalente documentado; no depender solo de clase/color.
- Relacionar `aria-expanded` con las regiones de snapshots, advanced alerts y paneles secundarios; devolver foco al trigger al cerrar.
- Anunciar una sola vez loading, resultados nuevos, empty, partial/stale y error; no convertir cada precio/card en una live region ruidosa.
- Asociar mensajes de validación de alertas a los campos afectados y señalar `aria-invalid` solo mientras el error sea válido.
- Distinguir en el árbol accesible favorito simple, tracking activo/pendiente/pausado y acciones destructivas.
- Asegurar que disabled/busy conserva un nombre útil y explica la razón cuando el contexto falta; loading no debe degradar todos los botones a “Cargando…”.
- Verificar orden de tabulación con la composición H31: búsqueda → resultados/detalle → guardar/seguir → histórico → secundarios.
- Revisar labels implícitos y convertir a `htmlFor`/IDs donde se necesite relación estable, especialmente para campos que reciben mensajes de error.
- Probar dark/light, zoom 200%, copy ES/EN, nombres largos y focus contrastado en todos los estados.

#### P2 — endurecimiento y calidad de experiencia

- Añadir alternativa textual equivalente para timeline, snapshots y cualquier visualización futura.
- Añadir tests de lector de pantalla/árbol accesible en los flujos más sensibles.
- Documentar nombres de landmarks y headings para evitar regiones repetidas ambiguas.
- Auditar `aria-label` en spinners y evitar que un indicador puramente visual sea el único feedback.
- Revisar motion hotelero con `prefers-reduced-motion` y asegurar que la reducción no elimina confirmación textual.
- Verificar idioma del documento, fechas, monedas, pluralización y pronunciación razonable de precios/estados en ES/EN.

## 3. Matriz WCAG aplicada a `/hoteles`

| Área WCAG 2.2 AA | Aplicación hotelera | Evidencia V1 | Criterio de aceptación |
|---|---|---|---|
| 1.1.1 Contenido no textual | iconos de estado, spinners, gráficos, estrellas | hay texto en varios estados; no hay auditoría de iconos/curvas | cada información no textual tiene texto/label o es decorativa; ningún estado depende solo del icono |
| 1.3.1 Información y relaciones | labels, headings, panels, card/selection, errores | labels envolventes y headings existen; relaciones dinámicas incompletas | árbol accesible refleja campo→label→error, trigger→región y resultado→estado |
| 1.3.2 Secuencia significativa | formulario, lista, detalle, secundarios | DOM general sigue la página; mobile/tab order no probado | lectura y tabulación siguen H31/H32 en todos los viewports |
| 1.3.3 Características sensoriales | color, posición, forma de estado | status pills y clases existen | cada estado tiene texto/semántica además de color, posición o icono |
| 1.4.1 Uso del color | success/warning/error/partial/stale | tokens semánticos existentes | el significado permanece entendible en escala de grises y dark/light |
| 1.4.3 Contraste mínimo | copy, borders relevantes, focus y status pills | tokens/focus global; ratios no medidos por superficie | texto normal 4.5:1, texto grande 3:1 y componentes/foco no textuales 3:1 donde aplique |
| 1.4.4 Redimensionar texto | 200% zoom, nombres y warnings largos | `html zoom` y `ios-zoom-fix` parciales | 200% sin pérdida de contenido/función ni scroll horizontal inesperado |
| 1.4.10 Reflow | 360–1024, cards, detalle y secundarios | breakpoint 768/480; cobertura incompleta | reflow equivalente a 320 CSS px sin pérdida de acción o información |
| 1.4.11 Contraste no textual | borders, selected, focus, controls disabled/active | focus global, ratios no medidos | estados y límites necesarios alcanzan contraste verificable y no dependen de color único |
| 1.4.12 Espaciado de texto | copy ES/EN y zoom | no auditado | line-height, letter/word spacing ampliados no recortan ni solapan contenido |
| 1.4.13 Hover/focus content | autocomplete, tooltips, overlays | listbox visible; overlays no auditados | contenido adicional es persistente, descartable y alcanzable por teclado; no hay dato crítico solo en hover |
| 2.1.1 Teclado | tabs, autocomplete, cards, buttons, snapshots, alertas | botones nativos; Arrow/Escape autocomplete no probado | todo flujo operativo funciona sin ratón y sin trampa de teclado |
| 2.1.2 Sin trampa de teclado | drawers/sheets/paneles | no existe estrategia hotelera completa | foco entra/sale de overlays de forma determinista; Escape funciona cuando procede |
| 2.4.1 Bloques | skip link, landmarks | `main#main-content` existe; ruta hotelera no auditada | skip link llega a main y regiones tienen nombres únicos |
| 2.4.2 Título de página | `/hoteles` | no verificado en esta fase | título identifica hoteles y idioma correctamente |
| 2.4.3 Orden del foco | búsqueda→decisión→secundarios | no probado | tab order coincide con orden visual/DOM y no salta fuera de contexto |
| 2.4.4 Propósito del enlace | volver, deeplink, history, partner | acciones mayoritariamente buttons; futuro deeplink pendiente | cada enlace describe destino/acción sin contexto visual obligatorio |
| 2.4.6 Encabezados y etiquetas | panels, fields, alerts, results | headings y labels parciales | cada región tiene heading/label único, breve y traducido |
| 2.4.7 Focus visible legacy / 2.4.11 Focus appearance | todos los controles | outline global 3 px | foco visible, no oculto por overflow/sticky, contraste medido en ambos temas |
| 2.4.11 Focus Not Obscured (Minimum), AA | sticky header, keyboard, drawers | no auditado | foco no queda tapado en ningún viewport/zoom |
| 2.4.12 Focus Not Obscured (Enhanced), AAA | no es objetivo de conformidad H33 AA | fuera de alcance | no convertir este criterio AAA en requisito de cierre H33 |
| 2.5.3 Label in name | botones con copy/icono | copy visible existe | nombre accesible contiene el label visible; icon-only controls tienen nombre claro |
| 2.5.7 Dragging movements | timeline/filtros futuros | no hay drag confirmado | toda acción drag tiene alternativa click/teclado |
| 2.5.8 Target size minimum | CTAs hoteleros | H32 fija 48 px; CSS actual tiene 44 px | targets existentes y nuevos ≥48×48 px, sin solapes |
| 3.1.1 Idioma de página | ES/EN | i18n de dominio existe; atributo/documento no verificado | idioma programático correcto y cambia de forma coherente |
| 3.1.2 Idioma de partes | provider, nombres propios, mensajes | no auditado | cambios de idioma/partes especiales no rompen pronunciación ni significado |
| 3.2.1 On focus | inputs/tabs | handlers locales; no cambio de contexto documentado | enfocar no envía ni navega inesperadamente |
| 3.2.2 On input | dates, selects, toggles | updates locales; provider checkbox puede cambiar flujo | cambios no causan pérdida de contexto ni submit inesperado |
| 3.3.1 Identificación de error | búsqueda/alertas/tracking | mensajes existen; roles/relaciones incompletos | error identificado en texto, campo/región y estado accesible |
| 3.3.2 Labels or instructions | fechas, huéspedes, umbrales | labels visibles envolventes | cada input tiene label/instrucción y unidad/ejemplo cuando necesario |
| 3.3.3 Error suggestion | fechas, umbrales, destino | copy parcial | mensaje indica corrección segura sin lenguaje técnico |
| 3.3.4 Error prevention | crear/eliminar tracking/alerta | no hay confirmación transversal auditada | operaciones destructivas se pueden revisar, confirmar o deshacer según riesgo |
| 4.1.2 Name, role, value | combobox, expanded, pressed, busy, selected | listbox/pressed parcial | cada control expone nombre, rol, valor y cambios al árbol accesible |
| 4.1.3 Status messages | loading, count, empty, price change, provider error | `role=status` global; estrategia incompleta | cambios se anuncian sin mover foco salvo error que requiera recuperación |

## 4. Patrones obligatorios de implementación

### 4.1. Formulario y combobox de área

El destino de área debe implementar un patrón combobox/listbox coherente:

- sustituir el patrón híbrido actual `<li role="option"><button>` por un único modelo de foco listbox; después, el input debe tener `role="combobox"`, `aria-expanded`, `aria-controls`, `aria-autocomplete="list"` y valor accesible;
- listbox con ID estable y options con IDs únicos;
- `aria-activedescendant` actualizado al mover ArrowUp/ArrowDown;
- Enter selecciona la opción activa; Escape cierra sugerencias sin borrar query; Tab conserva una selección válida;
- al seleccionar, el input y el badge de área resuelta quedan sincronizados;
- si resolver falla, se anuncia el error sin afirmar que la zona no existe;
- no se mezclan dos owners de foco ni se deja el botón de option como única vía de teclado.

### 4.2. Errores, validación y estados

- errores accionables: `role="alert"` o `aria-live="assertive"` solo cuando la severidad lo justifica;
- progreso y resultados informativos: `role="status"`/`aria-live="polite"` una sola región estable;
- campo inválido: `aria-invalid="true"` + `aria-describedby` a mensaje visible;
- el foco va al primer error del submit cuando sea seguro y vuelve al flujo normal al corregir;
- `empty` no es `error`; `provider_error` no es `sold_out`; `stale` no es `live`;
- snapshots/rates distinguen error de lista vacía antes de anunciar el resultado.

### 4.3. Resultados y card seleccionada

- la card puede seguir siendo `<article>`, pero la selección debe exponerse con una propiedad accesible documentada;
- el botón principal de selección tiene nombre que incluye hotel/destino cuando el contexto lo necesite;
- botones de tracking/favorito no se anidan dentro de otro button interactivo;
- `aria-pressed` solo representa toggles reales; el tracking actual no cumple mientras el botón activo quede disabled sin transición inversa;
- estados disabled/busy y feedback de éxito se anuncian localmente sin saturar el lector;
- el precio, moneda, estancia, condiciones y freshness se leen en un orden comprensible.

### 4.4. Paneles, snapshots y overlays

- cada trigger de expansión tiene `aria-expanded` + `aria-controls` y una región con ID único;
- abrir/cerrar conserva el foco y no desplaza el usuario a un punto inesperado;
- si se introduce dialog/sheet, debe tener nombre, focus trap solo dentro del modal, Escape, retorno de foco y scroll lock reversible;
- timeline/histórico debe tener resumen o tabla equivalente, no depender de una gráfica visual;
- los paneles secundarios no deben ser la única ubicación de una acción primaria.

### 4.5. Tracking, favoritos, alertas e inbox

- “Guardar hotel” y “Seguir precio” tienen nombres, estados y resultados distintos;
- tracking activo, pendiente, pausado, expirado y eliminado se exponen como estados legibles;
- alertas activas/inactivas y acciones activar/desactivar/eliminar tienen nombre contextual por regla/hotel;
- eliminar o detener debe tener confirmación o mecanismo de undo apropiado al contrato H29;
- eventos privados e inbox conservan ownership sin anunciar datos de otra cuenta;
- error de carga no se presenta como lista vacía a un lector de pantalla.

## 5. Priorización de remediación

### P0 — antes de cualquier declaración de accesibilidad

1. Completar combobox/listbox de área.
2. Corregir role/status de errores y añadir estrategia común de alert/status.
3. Añadir relaciones `aria-controls`/IDs a paneles y `aria-describedby`/`aria-invalid` a errores.
4. Separar error de snapshots/rates de empty.
5. Crear pruebas de teclado/árbol accesible para búsqueda, resultados, tracking y alertas.
6. Confirmar que no hay targets <48 px y que el foco no queda oculto.

### P1 — antes de release hotelero

1. Nombres contextuales de acciones repetidas.
2. Selección accesible de card y live region estable de resultados.
3. Retorno de foco y Escape en paneles/overlays.
4. Estados completos de H21 en todas las superficies.
5. Contraste medido dark/light y revisión de zoom/spacing.
6. Confirmación/undo de acciones destructivas según H29.

### P2 — endurecimiento posterior

1. Tabla/resumen textual completo para histórico y gráficos.
2. Recorrido con lector de pantalla en navegadores soportados.
3. Tests de idiomas parciales, nombres propios y formato de números.
4. Automatización de contraste y snapshots de árbol accesible.

## 6. Estrategia de pruebas y evidencia

### Automatizadas

- test estructural que compruebe landmarks/headings, labels, IDs únicos y ausencia de botones anidados;
- test de combobox: foco, escribir, ArrowDown, Enter, Escape, selección y error de resolución;
- test de estados: loading/empty/partial/stale/error/auth sin confusión de copy o roles;
- test de `aria-expanded`/`aria-controls`, `aria-pressed`, `aria-invalid` y `aria-describedby`;
- test de resultados: seleccionar hotel, activar tracking/favorito y conservar botones internos operables;
- test de alertas: validación, creación, activar/desactivar y eliminación con nombres contextuales;
- test de snapshots: error no se convierte en empty;
- axe/Lighthouse o equivalente en fixtures representativos, sin tratar una puntuación como sustituto del recorrido manual;
- test de contraste/token donde el tooling lo permita;
- test de 48 px, 200% zoom y scroll width junto con H32.

### Manuales/browser

Para 360×800, 390×844, 414×896, 768×1024, 1024×768 y desktop; dark/light; ES/EN:

1. usar solo teclado desde skip link hasta alertas;
2. recorrer autocomplete con flechas, Enter, Escape y Tab;
3. comprobar foco visible y no oculto al abrir/cerrar paneles;
4. activar/desactivar favorito, tracking y alertas sin ambigüedad;
5. provocar loading, empty, partial, stale, provider error, auth y not-found;
6. comprobar anuncio de estado sin interrupciones excesivas;
7. aumentar zoom/text spacing a 200% y revisar reflow;
8. inspeccionar árbol accesible con lector de pantalla cuando esté disponible;
9. revisar contraste de texto, controles, selección y focus en ambos temas;
10. verificar consola, requests duplicadas y que no se pierda formulario/selección.

### Evidencia mínima

Cada recorrido debe registrar viewport, tema, locale, zoom, fixture/estado, secuencia de teclas o interacción, resultado esperado/observado, consola y screenshot/video solo cuando pruebe el problema. Los fingerprints/request IDs deben ser opacos y no contener PII.

## 7. Gate H33

H33 podrá marcarse implementada cuando:

1. búsqueda por nombre y área sea operable completamente por teclado;
2. autocomplete exponga combobox/listbox correcto y navegación anunciada;
3. todos los campos y errores tengan nombre, relación y estado accesible;
4. landmarks, headings, orden de foco y retorno de foco sean coherentes;
5. resultados, card seleccionada, favorito, tracking, histórico y alertas sean distinguibles sin color ni contexto visual obligatorio;
6. loading, empty, partial, stale, provider error, auth y not-found se anuncien con severidad adecuada y no se confundan;
7. paneles/overlays tengan expansión, cierre, Escape y foco verificables;
8. targets, zoom, reflow, contraste y reduced motion pasen la matriz H32/H33;
9. no queden bloqueantes P0 (P0 = cero) y los P1 de release estén cerrados o aceptados explícitamente con owner;
10. exista evidencia automatizada y recorrido manual de búsqueda, resultados, tracking y alertas en dark/light y ES/EN;
11. la puntuación de una herramienta automática no sea la única evidencia de accesibilidad.

**Resultado contractual:** H33 deja definida la auditoría WCAG 2.2 AA, sus P0/P1/P2 y el gate de evidencia. La implementación actual tiene fundamentos útiles, pero no se declara conforme hasta cerrar los gaps observados y demostrar los recorridos reales.
