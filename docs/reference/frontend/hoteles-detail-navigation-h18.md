# H18 — Detalle hotelero navegable y retorno a búsqueda

**Estado:** contrato de navegación y superficie de detalle; implementación frontend, URL state y QA E2E pendientes  
**Fuente de verdad:** sí, para selección, detalle, contexto preservado, back/forward y deeplinks de hoteles  
**Fase del roadmap:** H18  
**Dependencias:** H10, H13, H15, H16, H17  
**Siguiente fase:** H19 — total, noches, fees y transparencia de precio

## 1. Propósito y decisión de fase

H18 convierte el detalle de hotel en una superficie útil para decidir sin romper la búsqueda que lo originó. Una persona debe poder abrir un hotel, revisar identidad, ubicación, rates, histórico, provider, paridad, tracking y acciones; después debe volver exactamente a su contexto de resultados.

Esta fase es **contractual**. No implementa todavía una ruta nueva, adaptadores ni cambios en `HotelRadarPage`. La decisión recomendada es conservar el master-detail en `/hoteles` y hacer la selección URL-driven con un parámetro `hotel_id`, dejando una ruta dedicada para una futura ampliación si el detalle necesita más espacio.

La regla principal es:

> Abrir el detalle nunca debe borrar ni reinterpretar la búsqueda que llevó al hotel.

## 2. Estado actual comprobable

### 2.1. Superficie actual

`HotelRadarPage` ya contiene un panel lateral de “Hotel seleccionado” que muestra:

- nombre, ciudad y país del hotel seleccionado;
- dirección cuando `HotelDetailOut` la aporta;
- última actualización del catálogo;
- estado de carga de rates;
- paneles separados de watchlist, paridad, alertas, comp sets, tracking e histórico.

La selección se produce al pulsar `HotelResultCard` y se guarda en `useHotelSearch` como `selectedHotelId` local. `useHotelDetail` reacciona a ese ID y dispara en paralelo:

```text
getHotelDetail
getHotelRates
getHotelParity
```

Usa `Promise.allSettled`, por lo que puede conservar detalle/rates aunque parity falle, aunque la representación final todavía es básica.

### 2.2. Gaps actuales

- `/hoteles` no serializa búsqueda ni selección en URL.
- `selectedHotelId` se pierde al refrescar o salir y volver.
- Browser back/forward no representa abrir/cerrar el detalle.
- No existe un deeplink canónico de hotel con contexto de búsqueda.
- El panel seleccionado no tiene acción explícita de “cerrar detalle y volver a resultados”.
- El detalle, rates y parity tienen errores y cargas separadas, pero no una taxonomía H15 visible común.
- La card y el panel pueden discrepar si una respuesta antigua termina después de seleccionar otro hotel.
- `deep_link` solo existe en snapshots/rates y no se valida aún como CTA seguro desde detalle.
- `HotelTrackedOfferOut` contiene `user_id`, pero ese campo no debe aparecer en superficies públicas ni en un deeplink compartible.
- watchlist, tracking, alertas, parity y comp sets viven en paneles hermanos; H18 debe definir cuál es el orden de decisión sin convertir el detalle en otro dashboard técnico.

## 3. Decisión de superficie

### 3.1. Master-detail URL-driven

La primera implementación debe mantener:

```text
/hoteles?hotel_id=<id>&<search-state>
```

El parámetro canónico de selección será `hotel_id`. Debe validarse con una allowlist de formato/longitud adecuada al ID real del dominio; no se debe reutilizar `sanitizeIata` ni aceptar strings sin límite.

Ventajas:

- conserva visible la lista y el contexto;
- el back del navegador puede cerrar el detalle antes de abandonar `/hoteles`;
- refresh puede restaurar búsqueda y selección;
- permite compartir una URL reproducible sin introducir inmediatamente una ruta dinámica;
- encaja con el panel lateral actual y con H13 URL state.

El detalle puede renderizarse como panel lateral en desktop y sheet/drawer accesible en mobile, siempre que tenga semántica de diálogo o landmark apropiada y no oculte permanentemente el contexto.

### 3.2. Ruta dedicada futura

Una ruta como `/hoteles/<hotel_id>` puede habilitarse en H18/H19 si el detalle requiere:

- más espacio para rates comparables, fees e histórico;
- SEO o enlaces externos de hotel;
- compartir un hotel sin una búsqueda concreta;
- navegación móvil de página completa.

Si se adopta, debe aceptar un `return`/context token seguro o query state explícito, sin guardar una URL arbitraria que permita open redirects. La ruta dedicada no sustituye la semántica del panel hasta que exista evidencia de UX y QA.

## 4. URL state canónico

H18 amplía H13 con la selección:

```text
/hoteles?
mode=area
&area=Madrid
&lat=40.4168
&lng=-3.7038
&check_in=2026-09-10
&check_out=2026-09-14
&guests=2
&radius_km=10
&currency=EUR
&min_stars=4
&max_price=600
&sort=price
&cursor=<opaque>
&hotel_id=hotel_123
```

### 4.1. Parámetros que se preservan

Al abrir/cerrar detalle deben conservarse, cuando existan y sean válidos:

- modo de búsqueda;
- destino seleccionado y su tipo/confidence;
- query de nombre/ciudad o área;
- coordenadas solo si H13 las necesita para reproducibilidad;
- entrada, salida, noches y ocupación bridge/estructurada;
- moneda, radio, filtros y orden;
- cursor/snapshot token solo si pertenece al mismo contexto H15;
- provider policy/capabilities cuando sea seguro y público;
- `hotel_id` como selección actual.

No se preservan en URL:

- `user_id`, email, tokens, alert thresholds, notas privadas;
- payload bruto de provider;
- IDs privados de tracking salvo que H23 defina una URL autenticada y segura;
- coordenadas de precisión innecesaria si destino normalizado basta.

### 4.2. Selección y edición

- abrir un hotel válido: `router.push` con el mismo search state + `hotel_id`;
- cambiar selección dentro de la lista: `router.replace` o `push` según H13, pero debe quedar una política única y testeada;
- cerrar el detalle: eliminar únicamente `hotel_id`, conservando el resto;
- editar filtros con detalle abierto: conservar `hotel_id` solo si el hotel sigue siendo elegible; si no, limpiarlo con warning accesible;
- invalidar destino/fecha/ocupación: limpiar selección y cursor incompatibles;
- una URL con `hotel_id` sin contexto de búsqueda puede abrir el detalle en modo standalone limitado, sin fabricar resultados ni filtros.

La recomendación inicial es `push` al abrir y `replace` al cambiar controles internos del detalle o normalizar parámetros, para que el botón Back cierre el detalle de forma natural.

## 5. Back, forward, refresh y scroll

### 5.1. Back/forward

Estados esperados:

```text
/hoteles?<query>
  → /hoteles?<query>&hotel_id=A
  → /hoteles?<query>&hotel_id=B
  ← vuelve a A
  ← vuelve a lista sin selección
```

- Back/forward debe restaurar el `hotel_id` y los datos del contexto;
- no debe crear loops `push → effect → push`;
- seleccionar un hotel no debe abandonar `/hoteles`;
- cerrar mediante botón debe producir el mismo estado que eliminar `hotel_id`;
- si el usuario llegó desde una ruta externa sin historial compatible, “Volver a resultados” reconstruye el search state seguro o vuelve a `/hoteles` sin conservar parámetros inválidos.

### 5.2. Refresh y entrada directa

Al cargar una URL válida:

1. parsear y sanitizar H13/H14/H15;
2. restaurar el formulario y filtros;
3. ejecutar búsqueda solo si el contexto está completo;
4. validar que `hotel_id` pertenece al resultado o consultar detalle directamente con estado `standalone`;
5. abrir el panel cuando la identidad sea válida;
6. si el hotel no existe, mostrar `hotel_not_found` y permitir volver sin perder query;
7. no ejecutar una búsqueda automática para una URL ambigua o incompleta.

### 5.3. Scroll y foco

- al abrir detalle desde una card, mantener referencia de posición de resultados;
- al cerrar, devolver foco a la card que abrió el detalle si sigue montada;
- en mobile, devolver foco al botón de selección/trigger;
- al entrar por deeplink, enfocar título del detalle y anunciar estado de carga;
- no saltar al inicio de página salvo una navegación de página completa explícita;
- H32/H33 verifican focus trap, escape y scroll lock si se usa dialog/sheet.

## 6. Anatomía del detalle

Orden recomendado:

1. identidad: nombre, ciudad, país, estrellas/categoría conocida;
2. acción de cierre/volver y estado seleccionado;
3. ubicación/dirección/mapa si H35/H31 lo permiten;
4. resumen de estancia: fechas, noches, huéspedes/habitaciones, moneda;
5. mejor oferta comparable y condiciones;
6. rates por provider con freshness/provenance;
7. histórico/timeline cuando exista;
8. paridad y cercanos como contexto secundario;
9. acciones de guardar, seguir, alerta y partner;
10. disclaimers de precio observado y variación del partner.

El detalle no debe repetir toda la pantalla de búsqueda ni competir con la acción principal. Parity, comp sets y paneles técnicos quedan debajo de precio, condiciones y tracking.

## 7. Estados de datos

### 7.1. Cargas independientes

Detalle, rates, parity, histórico y acciones pueden cargar por separado:

- estado de carga Boneyard de identidad mientras llega `HotelDetailOut`;
- estado de carga Boneyard de rates mientras llega `HotelRateOut[]`;
- parity puede mostrar `loading`, `limited`, `error` o `empty` sin bloquear identidad;
- no mostrar un spinner global que oculte un detalle ya válido;
- conservar datos anteriores mientras se actualiza la misma selección si H15 lo permite.

### 7.2. Estados de resultado

H18 consume H15:

- `success`: detalle y datos principales válidos;
- `partial`: identidad/rates válidos, parity/provider/enrichment incompleto;
- `empty`: no hay rates comparables, pero el hotel existe;
- `stale/cached`: mostrar freshness y no llamar live al snapshot;
- `provider_unavailable`: mantener histórico/cache solo con advertencia;
- `error`: error de la sección concreta o error total si identidad no se puede cargar;
- `hotel_not_found`: estado de recurso inexistente, con retorno seguro;
- `not_allowed`: no revelar datos privados ni existencia de tracking ajeno.

La UI no debe deducir estos estados solo porque un array esté vacío.

## 8. Acciones y ownership

### 8.1. Acciones del hotel

- guardar hotel/favorito: propiedad simple, ownership del usuario autenticado;
- seguir precio: requiere contexto completo y oferta/snapshot conforme H22/H23;
- crear alerta: requiere tracking/regla válida y no debe aceptar `user_id` desde cliente;
- abrir partner: solo con deeplink allowlisted, contexto y disclosure H35;
- compartir: compartir URL pública de hotel/búsqueda sin datos privados;
- comparar/cercanos: acción secundaria que conserva contexto.

### 8.2. Mutaciones desde detalle

Las mutaciones deben:

- reflejar estado optimista solo cuando sea reversible y no oculte errores;
- actualizar card, panel y watchlist/tracking sin refetch global innecesario;
- invalidar cache de detalle cuando cambia tracking/alerta relevante;
- no modificar ranking objetivo por tener el hotel guardado o seguido;
- respetar ownership en cada endpoint;
- mostrar confirmación y error localizados sin cerrar el detalle accidentalmente.

### 8.3. Deeplinks

Un deeplink de partner requiere:

- URL externa validada por allowlist;
- no aceptar URL arbitraria del query string;
- no pasar tokens, emails ni notas privadas;
- indicar “precio observado” frente a “precio final en partner”;
- preservar la URL de retorno interna mediante estado seguro, no `returnUrl` sin validación;
- registrar click sin PII innecesaria.

## 9. Panel vs página y mobile

### Desktop

- panel lateral o drawer ancho junto a resultados;
- lista permanece visible y conserva selección;
- cierre claro, `Esc` y botón volver;
- panel con scroll propio sin bloquear accidentalmente la página.

### Mobile

- sheet accesible o navegación a página completa según altura del contenido;
- el header del detalle conserva nombre y cierre;
- CTA de tracking/partner accesible sin quedar bajo el teclado;
- tabs o secciones plegables para rates, histórico, paridad y cercanos;
- no depender de hover;
- touch targets 44–48 px según guía mobile.

### Futura ruta dedicada

Si se implementa `/hoteles/[hotel_id]`, debe compartir el mismo contrato de datos y la misma URL de búsqueda de retorno; no crear una segunda semántica de detalle.

## 10. Accesibilidad

- título del hotel como heading principal del detalle;
- `aria-label` y nombre para botón de cierre/volver;
- si es dialog, `role=dialog`, `aria-modal`, `aria-labelledby` y focus trap probado;
- si es landmark persistente, no usar modal semantics;
- focus inicial en título o close, retorno a trigger al cerrar;
- `aria-live` para carga, partial, provider unavailable y errores de sección;
- headings y landmarks para identidad, precio, histórico, acciones;
- no anidar botones/links;
- error de rates asociado al bloque afectado;
- tabla/resumen accesible para histórico y paridad;
- `prefers-reduced-motion`, dark/light, teclado y zoom.

## 11. Tests y gates de aceptación

### 11.1. URL y navegación

- abrir card añade `hotel_id` sin perder query;
- cerrar elimina solo `hotel_id`;
- cambiar A → B → Back restaura A → lista;
- forward restaura B;
- refresh rehidrata búsqueda y detalle válidos;
- URL inválida limpia parámetros sin loop;
- cursor/snapshot incompatible se invalida de forma explicable;
- entrada directa standalone no inventa resultados;
- scroll/foco vuelve al trigger correcto.

### 11.2. Datos y estados

- detalle válido con rates vacíos;
- detalle válido con parity fallida;
- provider parcial/stale/cached;
- hotel inexistente;
- error auth/ownership;
- respuesta antigua no pisa la selección nueva;
- tracking/watchlist/alerta actualizan master y detalle coherentemente;
- deeplink inválido no crea navegación externa.

### 11.3. Browser QA

- desktop panel, mobile sheet/página e intermedio;
- teclado, Escape, focus trap y lector de pantalla;
- dark/light y reduced motion;
- navegación por card, URL directa, refresh, back/forward;
- búsqueda con filtros/sort/cursor;
- consola limpia y sin overflow;
- no se exponen datos privados en URL ni logs de cliente.

## 12. Observabilidad

Registrar sin PII innecesaria:

- `hotel_detail_opened`;
- `hotel_detail_closed`;
- `hotel_detail_return_to_search`;
- `hotel_detail_section_loaded`;
- `hotel_detail_partial_state`;
- `hotel_detail_not_found`;
- `hotel_detail_deeplink_clicked`;
- `hotel_detail_action_blocked`;
- tiempo hasta identidad, precio y CTA;
- abandono con detalle abierto;
- divergencia de contexto al volver.

No registrar tokens, emails, payloads provider, thresholds privados ni URLs externas completas.

## 13. Handoffs

- **H10:** StayOffer, condiciones y contexto de estancia reconstruible.
- **H13:** URL state, validación, focus y retorno.
- **H15:** envelopes, estados, warnings, freshness, ownership y cancelación.
- **H16:** card → detalle, jerarquía y acciones coherentes.
- **H17:** sort/ranking/explanation se conserva al volver; detalle no reordena.
- **H19:** total, noches, fees, currency y disclosure.
- **H20:** parity/cercanos secundarios y comparables.
- **H21:** matriz de estados compartida.
- **H22/H23:** favorito vs tracking y snapshot inicial.
- **H31-H35:** dirección visual, responsive, accesibilidad, i18n y legal/deeplinks.
- **H38/H39/H40:** ownership, seguridad, tests y browser QA.
- **H41/H43:** métricas, flags, canary y rollback.

## 14. Gate H18

H18 podrá considerarse implementada cuando:

1. el detalle sea accesible por selección y URL válida;
2. abrir/cerrar no destruya destino, fechas, ocupación, filtros, sort ni contexto H15;
3. back/forward y refresh restauren selección y búsqueda de forma determinista;
4. detalle, rates, parity, histórico y provider puedan degradarse por separado;
5. ownership y acciones no filtren datos privados ni permitan tracking ajeno;
6. deeplinks estén allowlisted, contextualizados y legalmente rotulados;
7. desktop/mobile/teclado/lector de pantalla pasen QA;
8. H16, H17 y H19 conserven una semántica única de precio, ranking y condiciones;
9. las pruebas cubran URL directa, estados parciales, respuestas obsoletas y retorno.
