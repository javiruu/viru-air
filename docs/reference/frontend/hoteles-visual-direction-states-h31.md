# H31 — Dirección visual y estados aprobados de `/hoteles`

**Estado:** contrato de flujo y estados; la dirección visual transversal vive en `DESIGN.md`. Implementación específica, responsive final, i18n completa y browser QA pendientes
**Fecha:** 2026-08-05  
**Área:** UX / frontend / accesibilidad / i18n / producto / QA  
**Fuente de verdad:** sí para el flujo, estados y jerarquía del módulo hotelero; `DESIGN.md` gobierna la dirección visual transversal
**Fase del roadmap:** H31  
**Depende de:** [H02 — benchmark](../../benchmarks/2026-08-04-travelpricedrops-hotels-h02.md), [H03 — arquitectura de información](../../product/hoteles-information-architecture-h03.md), [H16 — result cards](hoteles-result-cards-h16.md), [H21 — estados y recuperación](hoteles-state-matrix-h21.md)  
**Relacionado con:** H13 URL/formulario, H15 resultados, H17 ranking, H18 detalle, H19 precio, H20 comparación, H22 favoritos, H23 tracking, H25 freshness, H27 inbox, H30 fechas flexibles, H32 responsive, H33 WCAG, H34 i18n, H39-H40 QA

> H31 no crea otra identidad visual para hoteles. `DESIGN.md` fija cómo se expresa Viru; H31 conserva cómo la búsqueda, comparación y seguimiento hotelero se ordenan para decidir.

## 1. Decisión de alcance

H31 fija el contrato antes de implementar CSS/React específico:

1. jerarquía de la página y orden de lectura;
2. relación entre buscador, resultados, detalle y paneles secundarios;
3. anatomía visual de estados y cards;
4. encaje de la experiencia hotelera con los tokens y la accesibilidad ya definidos en `DESIGN.md`;
5. responsive, densidad y touch targets;
6. copy visible ES/EN y nomenclatura producto;
7. criterios de accesibilidad, telemetría y visual QA;
8. handoff a H32-H34/H40.

H31 no implementa todavía la dirección, no cambia la paleta global, no añade dependencias y no convierte el módulo en un dashboard de métricas. H16 conserva la anatomía de cards; H21 conserva la máquina semántica de estados; H31 decide cómo se leen y se sienten juntos.

## 2. Estado actual comprobable

### 2.1. Composición actual

`HotelRadarPage` presenta actualmente:

1. cabecera de página;
2. tres métricas de resumen;
3. `HotelSearchPanel`;
4. notice de error/provider;
5. columna principal con resultados, seguimientos y timeline;
6. columna lateral con detalle, watchlist, paridad, alertas y comp set.

La estructura permite reutilizar capacidades existentes, pero tiene riesgo de repartir demasiado pronto la atención entre muchos paneles. H31 no elimina esas capacidades; establece prioridad visual y reglas de colapso.

### 2.2. Evidencia visual existente

Existe evidencia de correcciones visuales previas: aislamiento de estilos globales, ajustes dark/light, responsive, acciones de watchlist/tracking y runner visual sobre datos consultables. Esa evidencia demuestra que ciertos flujos han sido inspeccionados en entornos concretos, pero no equivale a la aprobación del contrato H31 ni al cierre de todos los estados H16/H21, viewports, copy e i18n.

Gap explícito para H33/H40: `HotelRadarPage` usa actualmente `role="status"` también en el notice de error. Los errores accionables deben migrar a `role="alert"` o a una semántica equivalente, mientras el progreso informativo permanece en `role="status"`.

Por tanto:

- no declarar H31 implementada por tener CSS hotelero;
- no usar la existencia de `panel`, `card` o `status-pill` como prueba de jerarquía correcta;
- verificar la dirección sobre datos reales, parciales, stale, vacíos y errores;
- conservar la discrepancia entre “QA de corrección puntual” y “QA visual de release completa”.

## 3. Alcance de la jerarquía hotelera

La expresión estética, la creatividad, los tokens, el motion y el QA transversal se rigen únicamente por `DESIGN.md`. H31 conserva la lectura hotelera: una persona introduce una estancia, entiende la señal de precio y decide qué guardar o seguir.

## 4. Jerarquía de página

### 4.1. Orden obligatorio

El orden de lectura recomendado es:

```text
Cabecera de propósito
  → búsqueda de estancia
  → contexto de resultados
  → lista de opciones
  → detalle de la opción elegida
  → guardar/seguir
  → histórico y señales
  → herramientas secundarias
```

En el layout actual esto se traduce en:

1. **Cabecera:** título humano, propuesta breve y estado global del provider solo como contexto.
2. **Buscador:** bloque protagonista; destino/fechas/ocupación y CTA dominan.
3. **Resumen:** métricas útiles y compactas, nunca tres contadores compitiendo con el formulario.
4. **Resultados:** columna principal; nombre, precio/contexto y siguiente acción primero.
5. **Detalle:** espejo contextual de la selección, no una segunda pantalla que robe el foco.
6. **Tracking e histórico:** visibles después de decidir o agrupados como retorno útil.
7. **Paridad, alertas y comp set:** herramientas secundarias, colapsables y con copy explicativo.

### 4.2. Prioridad de acciones

La jerarquía de botones sigue `DESIGN.md`:

- `primary`: buscar, confirmar una selección o abrir la siguiente decisión principal;
- `secondary`: guardar/seguir cuando acompaña al CTA principal sin competir;
- `ghost`/`link-subtle`: volver, ampliar, comparar, reintentar o revelar contexto;
- `danger`: eliminar una regla/seguimiento o acción destructiva.

No más de una acción primaria por panel, card, modal o bloque. “Guardar hotel” y “Seguir precio” deben seguir siendo dos acciones distintas, pero no dos botones primarios simultáneos en una card.

### 4.3. Métricas de resumen

Las métricas superiores se mantienen solo si ayudan a orientarse:

- hoteles encontrados;
- seguimientos activos/elegibles, no simplemente filas existentes;
- hoteles guardados;
- señal limitada o última comprobación cuando sea relevante.

Reglas:

- no mostrar métricas con cero como si fueran una llamada a la acción principal;
- no dar apariencia de analítica de negocio;
- no presentar `is_active=true` como “seguimiento operativo” si H22/H23/H29 no lo respaldan;
- en mobile se pueden convertir en una franja horizontal o resumen plegable.

## 5. Integración con el sistema de diseño

La identidad, tokens, tipografía, dark/light, motion, foco y QA transversal se rigen únicamente por `DESIGN.md`. Hoteles no crea una paleta, un tema ni una excepción visual propia.

- `frontend/src/styles/tokens.css` contiene valores semánticos; `components.css`, patrones compartidos; y `screens.css`, composición local.
- No hardcodear un color, sombra, radio o spacing si existe un token semántico equivalente.
- La necesidad hotelera no justifica alterar la jerarquía de información, el significado de estados ni las capacidades reales de provider/tracking.

## 6. Anatomía visual por superficie

### 6.1. Buscador protagonista

El buscador debe responder en una mirada:

- dónde;
- cuándo;
- para quién;
- qué ocurrirá al buscar.

Dirección:

- un bloque principal con cabecera breve y una pista de contexto;
- inputs agrupados por intención, no por orden de implementación;
- el CTA de búsqueda visible en desktop y mobile;
- errores junto al campo y resumen accesible del problema;
- provider/demo como estado secundario, no como primer mensaje;
- el toggle name/area no debe robar protagonismo al destino.

No añadir calendarios, filtros avanzados o comp sets dentro del primer bloque hasta que el contrato correspondiente lo respalde.

### 6.2. Resultados

La lista se lee como un itinerario de decisiones:

```text
identidad → precio/estado → estancia → confianza → acciones
```

Cada card debe aplicar H16:

- catálogo sin oferta y oferta comparable tienen tratamiento distinguible;
- precio nunca aparece sin moneda y contexto;
- `no_price`, `partial`, `stale`, `unavailable` y `error` tienen copy y siguiente acción;
- provider no domina la card;
- una card seleccionada tiene borde/fondo/foco inequívoco sin depender solo del color;
- no hay card dentro de card ni botón anidado;
- las acciones secundarias no parecen otra fila de navegación.

### 6.3. Detalle seleccionado

El detalle lateral o URL-driven debe ser un **ancla de contexto**:

- repite nombre y estancia para confirmar que la selección no se perdió;
- concentra precio, condiciones, rates e histórico según disponibilidad;
- conserva una acción principal clara;
- muestra loading/partial/error del detalle sin convertir toda la página en error;
- permite volver a resultados sin perder búsqueda;
- no repite todas las métricas de la página ni compite con la lista.

### 6.4. Seguimiento e histórico

El tracking es la promesa de volver, por lo que debe tener una lectura tranquila:

- estado de lifecycle visible;
- estancia/oferta concreta, no hotel abstracto;
- última comprobación y confianza contextual;
- precio inicial/actual solo con semántica respaldada;
- pausa, edición y eliminación con copy real de H29;
- histórico disponible como evidencia, no como decoración.

### 6.5. Paneles secundarios

Paridad, alertas y comp set se presentan como instrumentos secundarios:

- encabezado con propósito humano;
- estado resumido antes del detalle técnico;
- panel plegable si no es necesario para la decisión actual;
- una acción principal como máximo;
- warnings próximos al dato afectado;
- no repetir `provider`, `hotel_id`, `status-pill` o copy de “signal” en cascada.

## 7. Estados visuales aprobados

H31 adopta la taxonomía H21. Cada estado debe combinar señal visual, texto y acción; el color nunca basta.

| Estado | Tratamiento visual | Copy/acción |
|---|---|---|
| `idle` | superficie tranquila, CTA visible, sin estado de carga | empezar búsqueda |
| `validating` | campo en foco, error inline, CTA ocupado | corregir el campo |
| `loading` | estado Boneyard con proporción de resultado; preservar contexto | esperar/cancelar |
| `success` | jerarquía completa, selección y acciones disponibles | revisar/guardar/seguir |
| `empty` | espacio respirable, ilustración/señal sutil, explicación concreta | ampliar zona/fechas/filtros |
| `partial` | warning localizado junto al dato incompleto | revisar limitación/reintentar |
| `stale` | etiqueta temporal discreta y accionable | revisar última comprobación |
| `stale_while_error` | conservar datos anteriores con warning visible | reintentar sin perder contexto |
| `unavailable` | estado neutral, no apariencia de error catastrófico | usar alternativa/configurar |
| `auth_required` | notice claro sin borrar formulario | iniciar sesión/continuar |
| `not_found` | identidad perdida explicada | volver a resultados |
| `cancelled` | sin toast de error; transición limpia | nueva intención |
| `error` | notice semántico, foco y retry | reintentar/recuperar |
| `selected` | borde/fondo/foco y aria state coherentes | abrir detalle |
| `disabled` | control atenuado, explicación asociada | completar contexto |

### 7.1. Estados que no se deben fusionar visualmente

- `empty` no es `error`;
- `provider_error` no es `sold_out`;
- `stale` no es `live`;
- `partial` no es `success` sin warning;
- `auth_required` no es ausencia de datos;
- `tracking paused/expired` no es tracking activo;
- favorito guardado no es seguimiento.

### 7.2. Loading y estabilidad

- reservar altura aproximada para evitar saltos;
- conservar resultados anteriores durante refresh cuando el fingerprint sea compatible;
- no animar precios como si fueran una actualización live si solo cambió la presentación;
- ignorar respuestas obsoletas sin parpadeo ni toast falso;
- `prefers-reduced-motion` elimina desplazamientos y pulsos no esenciales.

## 8. Responsive y densidad

### Desktop

- layout principal de resultados + detalle con proporciones estables;
- secundarios en columna de apoyo o debajo de la decisión, no una cuadrícula de cinco paneles equivalentes;
- precio y CTA permanecen alineados aunque el nombre sea largo;
- máximo de densidad útil antes de introducir scroll interno.

### Tablet/intermedio

- probar 768 y 1024 px;
- permitir que detalle pase debajo de resultados sin duplicar contenido;
- mantener acciones visibles y orden de tabulación lógico;
- evitar que una columna estrecha convierta cada card en un mosaico de badges.

### Mobile

- secuencia: cabecera → buscador → resultados → detalle/acciones → seguimiento → secundarios;
- cards apiladas con identidad, precio, contexto y acciones en ese orden;
- touch targets de **48 px mínimo** en acciones táctiles;
- no depender de hover, tooltip o scroll horizontal;
- paneles secundarios plegables, pero no esconder la acción principal;
- selección de card no debe interceptar botones internos;
- respetar safe areas y zoom de texto del navegador.

Viewports mínimos: 360, 390/414, 768, 1024 y desktop habitual. La dirección no se considera válida si solo funciona a 1440 px.

## 9. Feedback de interacción

El motion y las microinteracciones se rigen por `DESIGN.md`. En hoteles, además, ningún efecto puede sugerir una actualización live si sólo cambió la presentación, ni desplazar inesperadamente la lista de resultados.

## 10. Accesibilidad e i18n

- headings y landmarks describen buscador, resultados, detalle y secundarios;
- `aria-live` anuncia cambio de resultados y estado global, no cada card;
- `role=status` para progreso y `role=alert` para errores accionables;
- foco visible en ambos temas y retorno de foco al cerrar panel/modal;
- orden de tabulación: búsqueda → resultados/detalle → guardar/seguir → secundarios;
- `aria-pressed` solo para toggles de favorito/tracking;
- selección de card no se expresa solo por color;
- nombres largos, warnings y estados traducidos no rompen layout;
- ES/EN evita concatenaciones frágiles y conserva pluralización de noches/huéspedes;
- fechas, moneda, timezone y “comprobado hace” usan locale real;
- copy visible no expone enums como `provider_error`, `stale_while_error` o `HotelRateSnapshot`;
- reduced motion y zoom de texto pasan sin pérdida de acciones.

## 11. Reglas de implementación para H32-H34

1. No crear tokens locales en TSX si existe alias semántico.
2. No cambiar API, estado de negocio o nombres de endpoints como parte de un polish visual.
3. Extraer a `components.css` solo patrones que aparezcan en dos o más pantallas; lo exclusivo queda en `screens.css`.
4. No añadir iconos, imágenes o mapas externos sin procedencia/licencia y sin evidencia de valor.
5. Mantener fallback funcional sin imágenes y sin provider.
6. No convertir un panel técnico en una nueva fuente de verdad: el copy refleja H10-H30.
7. Cada excepción visual debe indicar qué regla de `DESIGN.md` preserva y por qué es específica de hoteles.
8. La implementación debe poder desactivarse por flag sin dejar la página ilegible.

## 12. Tests y gates

### Contract/estructura

- `HotelRadarPage` conserva la jerarquía buscador → resultados → detalle → secundarios;
- una acción primaria por panel/card;
- favorito y tracking tienen copy y estados distintos;
- estados H21 aparecen con señales y acciones, no solo booleans;
- H16 no se contradice: no se inventan precio, freshness, condiciones o deeplinks;
- no hay colores nuevos hardcodeados fuera de tokens aprobados; la dirección no crea una paleta hotelera paralela;
- dark/light mantienen semántica y orden equivalentes;
- `prefers-reduced-motion` tiene cobertura para animaciones hoteleras;
- no hay botones anidados ni overflow intencional.

### Browser/visual

- búsqueda por nombre y área;
- resultados con precio, sin precio, partial, stale y error;
- selección/detalle y vuelta a resultados;
- favorito, tracking activo, pendiente, pausado y eliminado según capacidad real;
- alertas/paridad/comp set plegados y desplegados;
- 360/390/414/768/1024 px y desktop;
- dark y light;
- teclado, lector de pantalla, focus visible y reduced motion;
- consola limpia, sin solapes, sin scroll horizontal inesperado y sin controles bloqueados.

### Gate de aceptación H31

H31 podrá considerarse implementada cuando:

1. el buscador sea visualmente protagonista y explique la intención de estancia;
2. resultados y detalle tengan una jerarquía de decisión reconocible;
3. favoritos, tracking, histórico, alertas y comp set estén subordinados a la decisión sin desaparecer;
4. la implementación use tokens/patrones canónicos y no cree una paleta hotelera paralela;
5. dark/light compartan estructura, significado y foco visible;
6. loading, empty, partial, stale, unavailable, auth, not-found, cancelled y error tengan tratamiento y acción;
7. cards de catálogo y oferta no se confundan;
8. desktop, intermedio y mobile no presenten overflow ni acciones ocultas por hover;
9. motion sea breve, útil y compatible con reduced motion;
10. ES/EN, fechas, moneda, nombres largos y accesibilidad pasen QA;
11. la evidencia de browser incluya estados no felices y no solo una captura de resultados;
12. ninguna decisión visual sugiera capacidades de provider/tracking que H10-H30 no respalden.

**Resultado contractual:** H31 queda definido como contrato hotelero de jerarquía, estados y comportamiento. La expresión visual transversal vive en `DESIGN.md`; la implementación completa de esta jerarquía, cobertura de estados, responsive, i18n y browser QA queda pendiente de H32-H34/H40.
