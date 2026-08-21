# DESIGN.md — Viru Air

**Estado:** vivo
**Última revisión:** 2026-08-22
**Fuente de verdad:** sí, para toda decisión estética y creativa de Viru Air
**Área:** diseño UI/UX y guía para agentes

## 1. Mandato

Viru Air es una plataforma de *flight intelligence* cálida, cercana, animada y aeronáutica. No es un SaaS genérico, un panel corporativo frío ni una interfaz de aerolínea convencional.

La impresión buscada es una cabina viva: información precisa, orientación inmediata y una personalidad que acompaña. La claridad no significa austeridad; el refinamiento no significa distancia; la creatividad no significa ruido.

Este documento es la única fuente viva para identidad visual, libertad creativa, composición, motion, microcopy, accesibilidad visual y QA de interfaz. Las decisiones de producto, flujo, datos y contratos siguen perteneciendo a sus especificaciones respectivas.

## 2. Identidad dual

- **Dark:** Aviation Dark-Luxe cinematográfico, profundo y cálido; nunca lúgubre, gamer, neón ni cyberpunk.
- **Light:** contraparte de día luminosa y con alma; nunca una superficie blanca, plana o corporativa.
- Ambos temas conservan geometría, jerarquía, orden de información, foco y significado de estados. Cambia la luminancia y el tratamiento de superficie, no la personalidad.
- Las claves de marca aparecen con intención: IATA, rutas, terminales, radar, pista, señales de vuelo, estancia o trayecto. Son contexto, nunca decoración obligatoria.

## 3. Libertad creativa media

La creatividad es **media y transversal**: cada superficie debe evitar parecer una plantilla repetida y puede usar una variación intencional de composición, ritmo, profundidad, detalle aeronáutico, microcopy o microinteracción.

Una pantalla conserva una lectura primaria inequívoca, pero puede tener un gesto memorable: una pieza protagonista, una transición de secciones con cadencia, un detalle de ruta, una confirmación cálida o una composición menos simétrica. El resultado debe tener jolgorio con criterio, no solemnidad ni artificio.

| Regla | Qué implica |
| --- | --- |
| **Congelado** | Valores y alias de `frontend/src/styles/tokens.css`; semántica `success`, `warning`, `error`, `info`; contraste, foco, teclado, reduced motion; jerarquía de información; identidad dual. |
| **Flexible** | Composición, peso visual, ritmo, profundidad, densidad, detalles de viaje, recursos de marca, tono del microcopy y microinteracciones. |
| **Prohibido** | SaaS genérico, simetría monótona, paredes de cards iguales, gamificación estridente, color sin semántica, ornamento que compita con la decisión, movimiento decorativo o que altere el scroll. |

## 4. Composición y componentes

- Priorizar una lectura: contexto y decisión primero; datos de apoyo, historial y herramientas después.
- No hacer que todas las secciones pesen igual. Alternar descanso y densidad útil, con asimetría controlada cuando mejore la lectura.
- Usar paneles, bordes finos y sombras largas y suaves como estructura, no como una colección de cajas anidadas.
- Mantener como patrones compartidos `panel`, `panel-soft`, `card`, `page-header`, `panel-header`, `panel-actions`, `panel-title`, `panel-subtitle`, `list-row`, `action-row`, `row-actions`, `section-gap|section-gap-sm|section-gap-lg`, `notice-compact`, `notice-actions`, `status-pill` y `state-success|warning|error|info`.
- Una acción primaria por panel, card, modal o bloque de decisión. Las acciones secundarias deben quedar disponibles sin disputar la lectura principal.
- `primary` inicia o confirma la decisión principal; `secondary` acompaña sin competir; `ghost` o `link-subtle` revela, vuelve, reintenta o amplía contexto; `danger` queda reservado para acciones destructivas.
- Si un valor semántico o patrón aparece en dos o más pantallas, pertenece a `tokens.css` o `components.css`; no crear tokens locales en componentes.

## 5. Tipografía, color y datos

- Titulares con Playfair Display para momentos de identidad; IBM Plex Sans para controles, cuerpo y copy operativo; monoespaciada sólo cuando los códigos, horarios o cifras ganen precisión.
- La implementación vigente de spacing, foco y estados vive en `frontend/src/styles/tokens.css`; los valores de tema viven en las variables CSS de `frontend/src/styles/screens.css`. No duplicar ni inventar una paleta documental paralela.
- Evitar negro puro masivo, blanco plano sin jerarquía, color decorativo y nuevos valores hardcodeados si existe un token semántico.
- El acento principal guía una acción o un momento de atención; verde, azul y rojo mantienen significado de estado, no adornan tarjetas.
- Usar cifras escaneables, fechas y precios bien agrupados; reservar la expresividad tipográfica para la jerarquía, no para disfrazar datos.

## 6. Estados, microcopy y tono

- `success`: completado; `warning`: parcial o pendiente; `error`: fallo o validación; `info`: contexto neutral. No usar `warn` en cambios nuevos.
- Cada estado combina señal visual, texto comprensible y la siguiente acción cuando exista. El color nunca es la única señal.
- Escribir en español cercano, accionable y humano, sin tono infantil, mezcla gratuita ES/EN ni jerga interna visible.
- Los labels consolidados de producto se respetan; el resto del copy puede tener chispa, calidez y precisión. Explicar siempre qué ocurre y qué puede hacer la persona si un dato es parcial, antiguo o falla.
- Los vacíos, cargas y confirmaciones son oportunidades de personalidad: deben acompañar sin retrasar la tarea ni prometer capacidades inexistentes.

## 7. Motion y respuesta

- El motion explica continuidad, selección, progreso o confirmación: claridad + delight + continuidad + personalidad.
- Preferir entradas de 4–8 px, elevación mínima, glow contextual tenue y compresión de 1–2 px; usar `transform` y `opacity` siempre que sea posible.
- Permitido: transiciones cortas de superficie, énfasis breve de valor, apertura contextual, shimmer discreto y una confirmación local con carácter.
- Prohibido: loops o pulsos para estados estáticos, rebotes repetidos, cambios de layout que muevan la lectura, scroll inesperado o apariencia de actualización en vivo para datos históricos.
- `prefers-reduced-motion` elimina desplazamientos, escalados y loops no esenciales sin ocultar información ni acciones.

## 8. Accesibilidad y responsive

- Cumplir contraste AA, foco visible, orden de tabulación lógico, controles operables sin hover y zoom de texto sin pérdida de acciones.
- La selección, el error, el progreso y la prioridad nunca dependen sólo del color.
- Mantener la misma intención en desktop, tablet y mobile: sin solapes, scroll horizontal inesperado ni acciones relevantes escondidas.
- Los paneles secundarios pueden plegarse en pantallas estrechas, pero no deben ocultar la acción principal ni convertir cada card en un mosaico de badges.
- Usar mensajes accesibles para cambios globales de resultado o error; no anunciar cada elemento repetido de una lista.

## 9. QA visual obligatorio

Antes de cerrar una modificación visual:

- Verificar la superficie afectada en dark y light; desktop 1440×900, tablet 768×1024 y mobile 375×812, además de 320×780 cuando la ruta privada lo requiera.
- Confirmar jerarquía, CTA principal, foco, contraste, overflow, solapes y ausencia de tono frío/corporativo dominante.
- Cubrir los estados aplicables: normal, loading, empty, error, parcial o éxito.
- Para rutas core, reutilizar esta cobertura: `/dashboard`, `/watchlist`, `/quick-search`, `/notifications`, `/login` y `/register`; `/ayuda` y `/policies` cuando cambien.
- Aportar evidencia real del navegador: vista de contexto y del componente afectado; añadir estado de interacción cuando el cambio sea stateful.
- Los tests y builds complementan la evidencia, pero no sustituyen la comprobación visual renderizada.

## 10. Límites de implementación para agentes

- No cambiar lógica de negocio, rutas, contratos API ni semántica de datos como parte de un ajuste visual.
- No introducir dependencias para retoques menores.
- No usar una regla de esta guía para justificar una paleta paralela de módulo, una capacidad no soportada o un cambio de contrato.
- Las especificaciones de Dashboard, Watchlist, Hoteles y otros módulos definen su comportamiento propio; esta guía decide cómo se siente y se expresa esa experiencia.
