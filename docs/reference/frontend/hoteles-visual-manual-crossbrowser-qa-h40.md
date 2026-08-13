# H40 — QA visual, manual y cross-browser de `/hoteles`

**Estado:** EN QA; smoke browser Chromium actual repetido con evidencia vigente en `docs/qa/evidence/hotels-h40-rerun-audit-current/`; cross-browser, revisión humana y cierre visual completo siguen pendientes
**Fecha:** 2026-08-05  
**Área:** frontend / QA / accesibilidad / responsive / cross-browser / producto  
**Fuente de verdad:** sí para la matriz visual, browser, manual y criterios de cierre de H40  
**No es:** una certificación visual permanente, una garantía cross-browser ni una sustitución de H33/H39

**Depende de:** H21 estados, H31 dirección visual, H32 responsive/CTAs, H33 WCAG, H34 i18n, H36 performance, H38 seguridad, H39 test pyramid  
**Relacionado con:** H13 formulario, H15 resultados, H16 cards, H18 detalle, H22 favorito/tracking, H26 alertas, H27 inbox/deeplinks, H28 delivery, H30 fechas flexibles, H35 disclosure, H41 observabilidad, H45 release.

> H40 verifica la experiencia renderizada, no solo el DOM ni el build. Un test estructural puede demostrar que `HotelRadarPage` está cableada; solo el navegador puede demostrar que el buscador se puede usar, que el layout no desborda, que el foco vuelve, que los requests reales terminan y que el copy/jerarquía se entienden.

---

## 1. Objetivo y frontera

H40 debe demostrar, con evidencia fechada y reproducible, que `/hoteles`:

1. funciona en desktop, móvil y ancho intermedio;
2. conserva jerarquía y acciones principales en dark y light;
3. permite completar búsqueda, selección, favorito, tracking, alerta y comparativa;
4. representa loading, empty, error, partial, stale y provider limitado sin engañar;
5. no introduce overflow, cards deformadas, CTAs bloqueados o paneles inaccesibles;
6. mantiene foco, teclado, zoom, reduced motion y lectura razonable;
7. no produce errores de consola ni requests inesperados durante el recorrido;
8. localiza copy, fechas, monedas y estados en ES/EN según H34;
9. muestra una experiencia coherente cuando el provider está apagado, lento, rate-limited o sin datos;
10. deja evidencia humana sobre claridad, densidad, tono y decisión principal.

H40 cubre:

- QA browser con Chromium y cross-browser acordado;
- screenshots, traces, consola, red y viewport;
- responsive, dark/light, zoom, teclado y reduced motion;
- estados funcionales y transiciones reales;
- visual review humana y checklist de producto;
- datos/fixtures controlados y repetibilidad;
- regresión de layout y copy ante cambios.

H40 no cierra por sí sola:

- ownership, BOLA, SSRF o secretos (H38);
- cobertura lógica completa (H39);
- Web Vitals field o coste provider (H36/H37);
- conformidad WCAG completa (H33); H40 aporta evidencia browser complementaria;
- una aprobación de lanzamiento sin H45.

---

## 2. Evidencia actual y límites

### 2.1. Evidencia histórica localizada

`docs/qa/hotels-visual-qa.md` y `docs/qa/hotels-pending-closeout.md` describen un cierre de junio de 2026 con:

- escenarios `desktop-dark`, `desktop-light`, `mobile-dark` y `mobile-light`;
- búsqueda por Madrid, selección, tracking, watchlist, alerta y comp set;
- resultado, tracked offer, watchlist y alert rule tras las acciones;
- ausencia documentada de overflow y errores de consola;
- correcciones de CTA de watchlist, override global de `.card` y runner visual;
- runner `frontend/scripts/qa_hotels_phase57.mjs`.

### 2.2. Discrepancia de artefactos

La documentación histórica referencia un report.json de la fase visual 57 y capturas asociadas, pero ese directorio/artefacto no está presente en el árbol actual auditado. Por tanto:

- el relato se conserva como evidencia histórica declarada;
- no se cuenta como artefacto reproducible actual;
- no se afirma que el resultado histórico siga vigente tras cambios posteriores;
- H40 exige recuperar el reporte/capturas o repetir el runner y guardar nueva evidencia;
- cualquier gate cerrado debe incluir commit, entorno, viewport, tema, locale, datos y timestamp.

### 2.3. Evidencia automatizada actual

| Evidencia | Existe | Qué demuestra | Qué no demuestra |
|---|---:|---|---|
| `frontend/tests/hotels-f56-audit.test.ts` | sí | estructura de ruta/componentes, wiring y algunos estados | render browser, CSS real, red, foco, overflow o consola |
| `frontend/tests/hotels-signal-assessment.test.ts` | sí | clasificación de señales insuficientes/limitadas/comparables | flujo completo, visual, provider real o recuperación |
| `frontend/scripts/qa_hotels_phase57.mjs` | sí | runner actual con `H40_OUTPUT_DIR`, metadata Chromium/locale, redaction de URLs y escenarios Mock/local | no sustituye cross-browser ni revisión humana; no prueba todos los estados F5 |
| `docs/qa/hotels-visual-qa.md` | sí | decisiones/correcciones y relato de cierre histórico | evidencia binaria/capturas actuales |
| `docs/qa/hotels-pending-closeout.md` | sí | checklist y comandos históricos | no sustituye un rerun con el código actual |
| rerun Chromium 2026-08-10 | sí | cuatro perfiles desktop/mobile × dark/light; resultados, tracking, favorito, alerta y comp set visibles; sin overflow ni errores de consola; evidencia en `docs/qa/evidence/hotels-h40-rerun-audit-current/report.json` | solo Chromium automatizado con locale ES; no autoriza declarar QA visual/cross-browser cerrado |

**Estado de lanzamiento:** el smoke funcional Chromium actual pasa y queda trazado contra una instancia Next fresca (cuatro perfiles, locale ES), pero H40 no declara el QA visual/cross-browser completo como pasado hasta revisión humana y navegador adicional.

---

## 3. Superficie visual que debe revisarse

La composición actual de `HotelRadarPage` incluye:

- header y contexto de provider;
- strip de resumen de hoteles/tracking/watchlist;
- `HotelSearchPanel` con modos nombre/área;
- autocomplete, fechas, huéspedes, radio y toggle provider;
- lista de resultados y cards con tracking/watchlist;
- tracked offers y timeline;
- sidebar de detalle, watchlist, parity, alerts y comp set;
- paneles colapsables y sugerencias cercanas.

Cada superficie debe revisarse en estados:

```text
default | hover | focus | active | disabled | loading | empty |
success | error | partial | stale | provider-off | provider-slow |
rate-limited | long-content | many-items | collapsed
```

No basta con revisar el happy path: los estados secundarios pueden cambiar altura, foco, scroll y jerarquía.

---

## 4. Matriz de viewport, tema y navegador

### 4.1. Viewports mínimos

| Perfil | Viewport objetivo | Preguntas |
|---|---:|---|
| móvil estrecho | 360×800 | ¿acciones y autocomplete caben sin overflow? |
| móvil común | 390×844 | ¿cards, fechas y botones conservan jerarquía? |
| tablet estrecha | 768×1024 | ¿la composición intermedia evita columnas rígidas? |
| tablet/ancho intermedio | 1024×900 | ¿sidebar y resultados siguen equilibrados? |
| desktop | 1440×900 | ¿el radar no se dispersa y el CTA primario domina? |
| desktop amplio | 1920×1080 | ¿no aparecen huecos, escalados o cards sobredimensionadas? |

Los valores son perfiles de QA, no una promesa de soportar cualquier resolución sin prueba adicional.

### 4.2. Temas y preferencias

Cada recorrido crítico debe cubrir:

- dark;
- light;
- preferencia `prefers-reduced-motion: reduce`;
- zoom 200% y reflow cuando aplique;
- locale ES y EN;
- timezone/locale representativos para fechas y horas.

Dark y light deben conservar semántica, contraste, estado y prioridad; light no puede degradar a SaaS blanco genérico ni dark a contraste insuficiente.

### 4.3. Navegadores

Gate mínimo:

- Chromium/Chrome estable en el runner de referencia;
- un navegador adicional acordado para release (Firefox o WebKit);
- revisión manual en navegador real para cambios de interacción o layout;
- móvil real periódico para confirmar que viewport emulado no oculta chrome/touch issues.

Si el entorno solo ejecuta Chromium, el reporte debe decir `cross_browser_incompleto`, no `cross_browser_pass`.

---

## 5. Flujos browser obligatorios

### Flujo F1 — búsqueda por nombre/ciudad

1. abrir `/hoteles` con sesión válida;
2. verificar header, resumen y buscador;
3. escribir nombre/ciudad;
4. enviar formulario;
5. comprobar request/respuesta esperados;
6. verificar resultados o empty state;
7. seleccionar una card;
8. comprobar detalle, rates, parity y timeline;
9. volver a cambiar la búsqueda y comprobar preservación de contexto.

### Flujo F2 — búsqueda por área/autocomplete

1. cambiar a modo área;
2. escribir una consulta parcial;
3. comprobar debounce/feedback;
4. verificar suggestions, role/listbox y selección por ratón/teclado;
5. elegir fechas, huéspedes y radio;
6. activar provider solo cuando el entorno lo permita;
7. ejecutar búsqueda;
8. comprobar resultados, precio, moneda y estado provider;
9. simular empty/error/timeout/429 si el fixture lo permite.

### Flujo F3 — guardado y tracking

1. seleccionar resultado;
2. añadir favorito simple;
3. confirmar que no crea tracked offer;
4. pulsar `Trackear precio`;
5. verificar snapshot inicial, estado busy y prevención de doble click;
6. comprobar panel de tracked offers e histórico;
7. pausar/eliminar cuando el flujo esté habilitado;
8. verificar que la card distingue favorito de tracking.

### Flujo F4 — alertas y comparativa

1. crear alerta válida;
2. comprobar estado de creación y regla visible;
3. ejecutar fixture/sweep controlado;
4. comprobar evento, estado y copy sin prometer live;
5. crear comp set;
6. añadir/quitar miembro y sugerencia cercana;
7. colapsar/expandir paneles;
8. comprobar que el foco, scroll y CTA principal no se pierden.

### Flujo F5 — degradación

Repetir con:

- provider apagado;
- respuesta lenta;
- `empty` válido;
- `partial`;
- `429`/rate limited;
- timeout/5xx;
- error de autenticación;
- datos stale;
- lista larga y nombres largos;
- request obsoleta o doble submit.

El resultado debe mostrar estado accionable y no `sold_out`, precio cero o “live” por inferencia.

---

## 6. Checklist de interacción y accesibilidad visual

### Teclado y foco

- orden de tabulación sigue la jerarquía visual;
- todos los botones/inputs/selects son alcanzables;
- focus ring visible en dark y light;
- autocomplete permite teclado y no roba foco;
- collapse toggle actualiza `aria-expanded` y mantiene foco;
- loading no deja foco en control muerto sin explicación;
- error/alerta devuelve o mueve foco según H33, sin salto inesperado;
- modal/sheet futuro atrapa y devuelve foco.

### Touch y responsive

- targets primarios ≥48 px según H32;
- botones de card no se pisan;
- CTA tracking y watchlist permanecen ambos disponibles;
- no hay scroll horizontal accidental;
- listas largas no rompen paneles;
- select/date inputs funcionan con teclado/touch del navegador.

### Lectura y estados

- headings siguen una jerarquía lógica;
- labels y mensajes de error son entendibles;
- status/loading/error se anuncian cuando corresponde;
- no se comunica estado solo por color;
- copy ES/EN no queda truncado ni mezcla idioma;
- precio, moneda, fecha y freshness mantienen contexto.

La automatización no sustituye revisión humana de lectura, tono, densidad, contraste perceptual y claridad de la decisión principal.

---

## 7. Visual regression y evidencia

Cada rerun relevante debe guardar:

```text
report.json
commit/config/environment
viewport/theme/locale/browser
screenshots/full
screenshots/results
screenshots/sidebar
screenshots/states (loading/empty/error/success cuando aplique)
trace on retry/failure
console errors/warnings
network summary/statuses
manual reviewer + date + decision
```

Reglas:

- capturas de página completa y de sección afectada, no solo crops ambiguos;
- nombres estables por escenario;
- baseline solo tras aprobación humana;
- diferencias de fuente/OS documentadas y runner consistente;
- no actualizar snapshots para ocultar una regresión;
- toda diferencia debe clasificarse `intentional`, `bug`, `environment` o `needs_review`;
- conservar evidencia histórica separada de la vigente.

---

## 8. Prioridades

### P0 — flujo inutilizable o engañoso

- overflow/click target bloqueado en móvil o desktop;
- no se puede buscar, seleccionar, guardar o trackear;
- loading/error/partial se muestra como éxito/live/sold out;
- CTA tracking/watchlist se oculta o solapa;
- foco perdido en autocomplete, alertas o paneles;
- consola con error runtime que rompe el flujo;
- request/API mismatch que deja UI falsa;
- deeplink o estado privado expuesto en navegador.

### P1 — calidad de release

- dark/light desalineados;
- viewport intermedio roto;
- fechas/moneda/copy incorrectos ES/EN;
- loading produce shifts grandes;
- sidebar o paneles secundarios dominan al resultado;
- reduced motion, zoom o teclado degradados;
- browser adicional falla en flujo crítico;
- evidencia no reproducible o snapshots sin contexto.

### P2 — polish y escala visual

- tipografía, spacing, hover, motion y densidad mejorables;
- listas de 30/100 cards y paneles largos;
- screenshot diff tolerances y visual baselines más finas;
- cobertura adicional de navegador/móvil real;
- QA perceptual de copy y personalidad Viru.

---

## 9. Gates de cierre

### Gate V — visual

- escenarios desktop/mobile/intermedio en dark/light;
- full/results/sidebar y estados críticos capturados;
- sin overflow ni deformación de cards;
- jerarquía, densidad y CTA principal aprobados por revisión humana.

### Gate F — funcional browser

- F1–F5 ejecutados con datos controlados;
- requests/respuestas esperados;
- loading/empty/error/partial/stale verificados;
- consola sin errores no justificados;
- foco, teclado y touch revisados.

### Gate X — cross-browser

- Chromium pasa;
- navegador adicional ejecutado o limitación declarada;
- diferencias clasificadas y no ocultas en snapshots;
- móvil real periódico si el cambio afecta touch/viewport.

### Gate A — accesibilidad complementaria

- H33 automatizado y manual complementario;
- zoom/reflow/reduced motion;
- labels, roles, focus y announcements;
- lectura humana de orden y copy.

### Gate E — evidencia y aprobación

- report JSON/capturas/trace guardados en ruta viva;
- commit, entorno, viewport, tema, locale y browser registrados;
- reviewer humano identificado y feedback explícito;
- ninguna deuda P0/P1 queda disfrazada de “no reproducible”.

**Criterio final:** F1–F5 pasan en la matriz acordada, no hay P0, el navegador adicional pasa o la limitación está aprobada, evidencia vigente está guardada y una persona valida la UI real en dark/light/mobile. El cierre histórico de junio no se reutiliza como pase actual sin rerun o artefacto recuperado.

---

## 10. Claims que H40 no autoriza

Hasta cerrar los gates, no puede afirmarse que `/hoteles`:

- esté visualmente pasado porque exista `hotels-f56-audit.test.ts`;
- sea responsive porque haya CSS o un snapshot histórico;
- funcione en cross-browser por pasar Chromium;
- tenga consola/red limpias sin rerun browser actual;
- tenga dark/light equivalentes sin capturas de ambos temas;
- sea accesible por tener labels o tests estructurales;
- conserve foco, touch y zoom sin interacción real;
- esté listo para release porque el build/typecheck pase;
- mantenga el cierre de junio si el reporte/capturas no están disponibles;
- tenga provider/error states correctos sin fixtures browser ejecutados.

H40 sí autoriza una afirmación limitada: existe una matriz reproducible para volver a verificar la ruta y separar evidencia histórica, automatizada, browser y humana.

**Resultado H40:** smoke browser Chromium actual aprobado automáticamente el 2026-08-10 en cuatro perfiles y evidencia vigente guardada en `docs/qa/evidence/hotels-h40-rerun-audit-current/`; el cierre H40 completo sigue pendiente de revisión humana, navegador adicional, estados F5 y aprobación de release.
