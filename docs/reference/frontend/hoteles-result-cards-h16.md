# H16 — Contrato de result cards hoteleras

**Estado:** contrato visual/funcional; implementación frontend, CSS, i18n y QA visual pendientes  
**Fuente de verdad:** sí, para la anatomía, jerarquía, estados y acciones de las cards de resultados hoteleros  
**Fase del roadmap:** H16  
**Dependencias:** H13, H14, H15, H31  
**Superficies:** resultados por nombre/ciudad, resultados por área, detalle seleccionado y futuras cards V2

## 1. Propósito y decisión de fase

H16 convierte el resultado hotelero en una unidad de decisión comprensible. Una persona debe poder responder rápidamente:

1. qué hotel es;
2. dónde está y qué distancia tiene;
3. para qué estancia se muestra el precio;
4. cuánto se ha observado y en qué condiciones;
5. cuándo se comprobó y de qué fuente procede;
6. qué puede hacer ahora: ver detalle, guardar o seguir una oferta.

Esta fase es **contractual**. No modifica todavía `HotelSearchPanel.tsx`, `HotelRadarPage.tsx`, CSS ni i18n. La implementación deberá respetar H15 para no inferir precio, freshness, disponibilidad o condiciones desde campos ausentes.

La regla principal es:

> La card debe priorizar la decisión de viaje, no la cantidad de datos técnicos que el backend sea capaz de devolver.

## 2. Estado actual comprobable

### 2.1. `HotelResultCard` actual

La card principal actual:

- muestra `canonical_name`, ciudad, país y estrellas;
- permite seleccionar el hotel mediante el cuerpo de la card;
- ofrece `Trackear precio` como acción de tracking;
- ofrece la acción de watchlist/favorito;
- comunica estados `is-active`, `watchlistBusy`, `trackedBusy` y `hasTracking`;
- no muestra precio, fechas, huéspedes, provider, freshness ni condiciones;
- usa un botón interno para seleccionar y botones de acción separados.

La card es útil como selector de catálogo, pero todavía no es una card de oferta comparable.

### 2.2. Card de resultado por área actual

La variante de `area-search` actual:

- muestra nombre, ciudad, país y distancia;
- muestra `lowest_price` y `currency` cuando existe;
- muestra `provider` cuando existe;
- muestra “sin precio” cuando `lowest_price` es `null`;
- muestra un contador de resultados y no una explicación por resultado;
- no permite seleccionar, guardar ni iniciar tracking desde la card;
- no muestra fechas/huéspedes aunque el payload sí contiene `check_in`, `check_out` y `guests`;
- no muestra `stars` aunque el payload lo contiene;
- no muestra `price_basis`, freshness, disponibilidad, habitación, régimen, cancelación o fees.

Hay, por tanto, dos experiencias distintas bajo el mismo módulo. H16 las unifica semánticamente sin obligar a que compartan exactamente el mismo layout.

### 2.3. Datos disponibles frente a datos que no deben inventarse

| Información | Existe hoy en búsqueda | Puede mostrarse ahora | Condición H16/H15 |
|---|---:|---:|---|
| Nombre y ubicación | Sí | Sí | identidad de hotel |
| Estrellas | Sí en ambos tipos, aunque no se muestra siempre | Sí, como dato conocido o “sin categoría” | nunca convertir null en rating |
| Distancia | Sí en área | Sí en área | no fingir distancia en búsqueda por nombre |
| Precio mínimo | Sí en área | Sí con moneda y estado | no llamarlo total/noches sin `basis` |
| Fechas/huéspedes | Sí en área | Sí como contexto resumido | debe ser el contexto real de la consulta |
| Provider | Sí en área, no en `HotelSearchOut` | Sí si existe | no mostrar “live” por el nombre del provider |
| Freshness/captura | No en `HotelAreaSearchResultOut` | No como hecho actual | H15 debe aportar metadata |
| Habitación | Solo en `HotelRateOut`/tracking | No en card de búsqueda actual | H10/H15 deben agregar oferta comparable |
| Régimen | Solo en `HotelRateOut`/tracking | No en card de búsqueda actual | normalización H10 |
| Cancelación | Solo en `HotelRateOut`/tracking | No en card de búsqueda actual | campo comparable y legal H19/H35 |
| Fees/total por noche | No de forma fiable | No | H19 y `price.basis` |
| Deeplink | Solo en rate snapshot | No desde lista actual | allowlist y H35 |
| Explicación de orden | No | No inventar copy | H14/H15/H17 |

## 3. Principios de jerarquía

### 3.1. Orden visual obligatorio

En desktop y mobile, la card debe seguir esta prioridad:

1. **Identidad:** nombre del hotel y ubicación;
2. **decisión económica:** precio comparable o estado de precio ausente;
3. **contexto:** fechas, noches, huéspedes y distancia cuando existan;
4. **confianza:** provider, freshness, cobertura y warnings relevantes;
5. **condiciones:** habitación, régimen, cancelación y fees cuando estén respaldados;
6. **acciones:** una acción primaria y acciones secundarias claras.

No se debe dar más peso visual a provider, parity, comp set, IDs o estado técnico que al nombre, precio y CTA.

### 3.2. Una card, una decisión principal

La acción primaria recomendada para una card con oferta es **Ver oferta/detalle**. Si el flujo actual aún usa selección lateral como sustituto, debe conservarse visualmente como “Ver detalle” y no competir con tracking.

Acciones secundarias:

- guardar hotel/favorito;
- seguir precio/oferta;
- abrir partner, solo cuando exista deeplink válido y disclosure H35.

No se deben presentar `Guardar`, `Seguir`, `Trackear`, `Ver`, `Abrir` y `Comparar` con el mismo peso visual.

## 4. Anatomía canónica

### 4.1. Card de oferta completa V2

```text
┌─────────────────────────────────────────────────────────────┐
│ [categoría]  Hotel Example                 [♡ guardar]      │
│ Madrid · 1,2 km                                             │
│                                                             │
│ 10–14 sep · 2 huéspedes · 4 noches                         │
│                                                             │
│ Desde / total observado                                     │
│ 420 €                         105 €/noche (si respaldado)   │
│ Precio observado · no confirmación de disponibilidad        │
│                                                             │
│ Habitación · régimen · cancelación                         │
│ Comprobado hace 2 h · vía provider                         │
│                                                             │
│ [Ver oferta]                  [Seguir precio]               │
└─────────────────────────────────────────────────────────────┘
```

La representación exacta puede ser asimétrica en desktop, pero debe preservar el orden de lectura en mobile y lector de pantalla.

### 4.2. Card de catálogo sin oferta

Cuando solo existe `HotelSearchOut`:

- nombre, ubicación y estrellas dominan;
- el precio no se sustituye por un placeholder engañoso;
- se muestra un estado “Precio aún no observado” si ayuda a la decisión;
- la acción primaria es `Ver detalle`/seleccionar;
- tracking se mantiene desactivado o se explica como pendiente si no hay estancia definida;
- guardar hotel sigue disponible si la sesión y el producto lo permiten.

No se debe renderizar una card “completa” con huecos que parezcan errores de carga.

### 4.3. Card compacta de área

La card de área puede ser más densa, pero debe incluir como mínimo:

- nombre;
- ciudad/país;
- distancia;
- estrellas conocidas;
- precio y moneda o estado `sin precio comparable`;
- contexto de fechas/huéspedes;
- provider/freshness cuando H15 lo aporte;
- selección/detalle y acciones de guardado/tracking cuando exista contexto suficiente.

No se debe mantener una variante de área completamente aislada y no accionable si el resultado representa la misma decisión que la lista principal.

## 5. Precio y condiciones

### 5.1. Semántica de precio

La card debe respetar H14/H15:

- `amount` y `currency` siempre se muestran juntos;
- `basis=total_stay` permite copy de total de estancia;
- `basis=per_night` permite copy por noche;
- `basis=unknown` exige copy neutral: “Precio observado” o equivalente;
- `null` no se muestra como cero, guion ambiguo ni “gratis”;
- `price.status=unavailable` no se traduce automáticamente como “agotado”;
- `stale` y `cached` se muestran como procedencia/freshness, nunca como live;
- `max_price` o sort no se justifican desde la card: la explicación viene de H15/H17.

### 5.2. Contexto de estancia

Toda card con precio debe hacer visible, de forma compacta:

- entrada y salida;
- número de noches cuando sea calculable;
- huéspedes y habitaciones cuando exista H10;
- moneda.

Si el resultado se ha generado con el bridge V1 `guests`, no se debe fingir que representa habitaciones, adultos, niños o edades.

### 5.3. Condiciones

Las condiciones son datos de decisión, no adornos:

- habitación: solo si está normalizada y asociada al precio;
- régimen: solo si está asociado a la misma oferta;
- cancelación: distinguir gratuita, parcial, no reembolsable y desconocida;
- fees: distinguir incluidos, excluidos y no informados;
- disponibilidad: usar solo estados respaldados por provider y H05/H15.

Si una condición falta, la card puede agruparla bajo “Condiciones no informadas”, pero no debe rellenarla con defaults del frontend.

## 6. Freshness, provider y confianza

### 6.1. Lenguaje humano

La card debe preferir copy comprensible:

- “Comprobado hace 2 h”;
- “Precio guardado”;
- “Señal parcial”;
- “Sin observación comparable”;
- “El provider no respondió; mostramos contexto anterior”.

Evitar mostrar como copy principal:

- IDs de provider;
- `provider_run_id`;
- `HotelRateSnapshot`;
- `cached=true` sin traducción;
- “live” si H05 no lo autoriza.

### 6.2. Badge y warning

- Un badge de provider no sustituye freshness.
- Un warning de colección no debe repetirse en todas las cards salvo que afecte materialmente a ese resultado.
- Warnings result-level se muestran próximos al precio/condición afectados.
- Estados de severidad alta deben tener contraste y texto, no solo color.
- La card no debe hacer creer que todos los resultados tienen el mismo nivel de confianza cuando `meta.freshness.mixed=true`.

## 7. Acciones y semántica de producto

### 7.1. Guardar hotel vs seguir oferta

H22/H23 siguen siendo la fuente de verdad:

- **Guardar hotel/favorito:** interés en una propiedad; no promete refresh ni alerta sobre una estancia concreta.
- **Seguir precio:** seguimiento de una estancia/oferta concreta con fechas, huéspedes, condiciones y snapshot inicial.

La implementación actual usa textos que pueden confundir ambos conceptos (`Añadir a seguimiento` para watchlist). H16 exige corregir copy ES/EN antes de declarar la card terminada:

- favorito: “Guardar hotel” / “Save hotel”;
- guardado: “Guardado” / “Saved”;
- tracking: “Seguir precio” / “Track price”;
- tracking activo: “Siguiendo precio” / “Tracking price”.

Si la estancia no está completamente definida, el CTA de tracking debe:

- estar deshabilitado con explicación; o
- abrir un paso de confirmación que complete el contexto;
- nunca crear silenciosamente un tracking incompleto.

### 7.2. Partner/deeplink

El CTA de partner solo aparece cuando:

- existe deeplink válido y allowlisted;
- el precio/condiciones que se muestran corresponden al contexto del enlace;
- H35 ha aprobado disclosure y copy de variación de precio;
- la acción se distingue de guardar y tracking.

No se muestra un botón de reserva si la card solo tiene catálogo o snapshot sin enlace verificable.

## 8. Estados visuales

### 8.1. Estados de card

Cada variante debe cubrir:

- `default`: resultado disponible para interacción;
- `hover`: elevación/contraste sutil, sin desplazar layout;
- `focus-visible`: foco claro en card y acciones;
- `selected`: hotel activo en el panel de detalle;
- `loading`: estado Boneyard que conserva proporciones y no usa solo spinner;
- `disabled`: acción concreta deshabilitada con motivo accesible;
- `no_price`: hotel conocido, sin precio comparable;
- `partial`: precio o condiciones con warning de fuente incompleta;
- `stale`: dato utilizable pero antiguo, con próxima acción;
- `unavailable`: provider/inventario no disponible, sin afirmar sold out;
- `error`: fallo del enriquecimiento, preservando identidad si es segura;
- `long_content`: nombres, ciudades y condiciones largas sin overflow;
- `many_actions`: acciones secundarias agrupadas sin competir con el CTA.

### 8.2. Loading y estabilidad

- El estado Boneyard debe reservar altura aproximada de la card final.
- Un refresh no debe borrar todas las cards mientras llega la respuesta si H15 permite conservar la búsqueda anterior.
- El estado `selected` debe sobrevivir a la actualización si el hotel sigue en resultados.
- Una respuesta obsoleta no puede modificar precio, selección ni estado de tracking.
- La animación respeta `prefers-reduced-motion` y preferencias de Viru.

### 8.3. Empty y partial

La card no reemplaza el estado de colección:

- colección vacía: mensaje y siguiente acción en el panel de resultados;
- card sin precio: explicación local y CTA de detalle/guardar si procede;
- provider parcial: warning de colección y señal local si aplica;
- stale: acción de revisar/refresh solo si el endpoint lo soporta;
- error total: no renderizar cards inventadas.

## 9. Responsive y layout

### 9.1. Desktop

- Lista legible con una columna principal de cards y panel de detalle separado.
- Precio alineado visualmente en un bloque estable, sin saltos por nombres largos.
- Acciones agrupadas al final de la card, con un CTA primario dominante.
- Los badges no deben crear una fila interminable.
- La distancia y el contexto pueden vivir en una línea secundaria.

### 9.2. Mobile

- Card apilada: identidad → precio → contexto/condiciones → acciones.
- Acciones táctiles de al menos 44–48 px según la guía mobile del repositorio.
- No depender de hover para descubrir condiciones o acciones.
- El CTA primario queda visible sin hacer scroll horizontal.
- Acciones secundarias pueden agruparse en una fila o menú, pero guardar/tracking no deben quedar ocultos sin motivo.
- La selección de card no debe capturar el toque de los botones internos.
- El panel de detalle debe conservar el contexto de búsqueda al volver.

### 9.3. Viewports intermedios

Se debe probar al menos:

- 360 px;
- 390/414 px;
- 768 px;
- 1024 px;
- desktop habitual del producto.

No basta con probar únicamente móvil estrecho y desktop ancho.

## 10. Accesibilidad

- Usar un heading o nombre accesible por card.
- Si el cuerpo es seleccionable, su control debe tener un nombre como “Ver detalles de Hotel Example, Madrid”.
- No anidar botones dentro de botones ni links dentro de botones.
- `aria-pressed` solo en toggles de guardado/tracking, no en la selección de detalle.
- Asociar warning y explicación de precio con `aria-describedby` cuando afecten a la acción.
- Anunciar cambios de resultados, count y estado parcial mediante `aria-live` en el contenedor de resultados, no uno por card.
- El color no es la única señal de stale, no-price, partial o selected.
- El foco debe ser visible en light y dark.
- El orden de tabulación sigue identidad → detalle → guardar → tracking → partner.
- Los iconos de corazón, external link y señales deben tener label o ser decorativos.
- El estado Boneyard debe comunicar carga con `role=status` o texto accesible, sin ruido para cada elemento.

## 11. Copy e i18n

H16 exige claves separadas para:

- favorito frente a tracking;
- precio observado, total, por noche y unidad desconocida;
- no observado, no comparable, stale, cached y provider parcial;
- condiciones desconocidas;
- acciones de detalle, partner, guardar, seguir, pausar y error;
- pluralización de noches, habitaciones y huéspedes;
- warnings de colección y result-level;
- disclosure de variación de precio.

No concatenar strings como `hotel + " · " + price` cuando el orden pueda variar en ES/EN. Las claves deben aceptar variables y pluralización.

## 12. Telemetría

Registrar eventos definidos en H04, sin datos privados innecesarios:

- `hotel_result_card_impression` con posición y estado contractual;
- `hotel_result_card_selected`;
- `hotel_result_detail_opened`;
- `hotel_result_save_clicked`;
- `hotel_result_track_clicked`;
- `hotel_result_partner_clicked`;
- `hotel_result_explanation_shown`;
- `hotel_result_warning_seen`;
- `hotel_result_action_blocked` con razón estable;
- latencia hasta primera card y hasta precio visible.

No registrar nombres completos de querys, emails, tokens, thresholds privados ni payloads de provider. La posición se interpreta junto al sort y contract version.

## 13. Tests y gates de aceptación

### 13.1. Componentes

- card de catálogo con estrellas y sin precio;
- card de área con precio, moneda, distancia y provider;
- `lowest_price=null` no muestra cero ni confirma agotamiento;
- fechas/huéspedes aparecen cuando el precio procede de ese contexto;
- tracking y favorito tienen copy, `aria-pressed` y estados distintos;
- tracking bloqueado no crea una oferta incompleta;
- botones internos no disparan selección accidental de la card;
- loading conserva altura y selected no se pierde;
- long names, warnings y condiciones largas no rompen layout;
- dark/light, focus-visible y reduced motion.

### 13.2. Contrato H15/H10

- la card no accede a campos V2 inexistentes sin fallback explícito;
- `basis`, freshness, price status y explanation se consumen por código, no por heurística;
- capabilities deshabilitan acciones/filtros no respaldados;
- provider parcial/stale/cached tiene copy correcto;
- H10 occupancy y condiciones no se mezclan entre ofertas;
- no se muestra deeplink sin validación de H35.

### 13.3. Browser QA

- búsqueda por nombre y por área;
- resultados con y sin precio;
- provider apagado, provider parcial y datos demo correctamente rotulados;
- seleccionar card y abrir detalle;
- guardar y quitar favorito;
- iniciar y bloquear tracking según contexto;
- refresh/búsqueda repetida sin respuesta obsoleta visible;
- teclado completo y lector de pantalla en el flujo principal;
- 360/390/414/768/1024 px y desktop;
- consola limpia, sin overflow horizontal ni click targets bloqueados.

## 14. Handoffs

- **H10:** aportar StayOffer, ocupación, habitación, régimen, cancelación y comparabilidad.
- **H13:** conservar contexto de URL, retorno y selección al navegar.
- **H14:** consumir filtros, sort y explicaciones sin reordenar/inferir en cliente.
- **H15:** aportar envelope, `price.status`, `basis`, freshness, warnings, capabilities y estados.
- **H17:** transportar la razón de ordenación y tie-breaker de forma explicable.
- **H18:** conectar la card con detalle navegable y retorno a búsqueda.
- **H19:** definir total, noches, fees y copy legal.
- **H21:** compartir matriz de empty/loading/error/partial/stale.
- **H22/H23:** mantener favorito y tracking semánticamente separados.
- **H31:** validar dirección visual, tokens, motion y excepciones de hoteles.
- **H32/H33/H34:** responsive, WCAG e i18n ES/EN.
- **H35:** deeplinks, disclosure, precio variable y privacidad.
- **H39/H40:** tests, browser QA y evidencia visual.
- **H41:** métricas de impressions, actions, warnings y latencia.

## 15. Gate H16

H16 podrá considerarse implementada cuando:

1. cada card responda qué es, qué precio representa y qué acción ofrece;
2. catálogo sin oferta y oferta comparable no se mezclen visualmente sin explicación;
3. precio, unidad, moneda, contexto y freshness sean semánticamente honestos;
4. favorito, tracking y partner tengan acciones y copy distintos;
5. no se inventen habitación, régimen, cancelación, fees, disponibilidad ni deeplinks;
6. loading, selected, no-price, partial, stale y error estén cubiertos;
7. desktop, mobile, dark/light, teclado y reduced motion pasen QA;
8. las cards no rompan H15, H22/H23 ni el retorno de H13;
9. la card principal tenga una jerarquía clara y no parezca un panel técnico genérico.
