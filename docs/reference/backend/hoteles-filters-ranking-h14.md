# H14 — Contrato de filtros y ordenación hotelera explicables

**Estado:** contrato de producto y datos; implementación frontend/backend pendiente  
**Fuente de verdad:** sí, para filtros, precedencia, ordenación y explicación de resultados de `/hoteles`  
**Fase del roadmap:** H14  
**Dependencias:** H10, H12, H13  
**Siguiente contrato:** H15 — resultados versionados, metadata, warnings y paginación

## 1. Propósito y decisión de fase

H14 define cómo una persona filtra y ordena hoteles sin perder contexto ni tener que adivinar por qué una opción aparece, desaparece o queda fuera de los primeros resultados.

Esta fase es **contractual**. No declara terminada la implementación del filtro visual ni del ranking final. El objetivo es dejar una especificación verificable para que H15, H17 y la implementación frontend/backend puedan avanzar sin inventar semántica distinta en cada pantalla.

La regla principal es:

> Un filtro solo puede mostrarse como accionable cuando el backend y la fuente de precios pueden demostrar qué campo modifica y bajo qué contexto de estancia.

## 2. Estado actual comprobable

### 2.1 Backend V1 disponible

`HotelAreaSearchQueryIn` acepta actualmente:

- `latitude` y `longitude`;
- `radius_km` entre 1 y 50;
- `check_in` y `check_out`;
- `guests` entre 1 y 20;
- `currency`;
- `min_stars` entre 1 y 5;
- `max_price` mayor o igual que cero;
- `sort` con los valores `price`, `distance` o `stars`.

La ruta V1 de `area-search` también recibe `use_provider`. La respuesta actual contiene hotel, ciudad, país, estrellas, distancia, precio mínimo, moneda, proveedor, fechas, huéspedes y `has_tracking`.

### 2.2 Semántica actual de filtrado

- El radio se aplica mediante distancia geográfica calculada con coordenadas del hotel.
- `min_stars` excluye hoteles sin estrellas conocidas y hoteles por debajo del mínimo.
- `max_price` excluye resultados con precio conocido superior al máximo.
- Un hotel sin precio conocido **no se excluye actualmente** por `max_price`; se conserva con precio nulo.
- El precio usado es el menor snapshot compatible por hotel, fecha, huéspedes y moneda.
- Cuando `use_provider=true`, el precio fresco del proveedor puede sobrescribir el precio de base de datos, pero la implementación actual todavía no valida de forma estricta que cada tarifa devuelta conserve la moneda y todo el contexto solicitado antes de usarla. Esto es un gap de H14/H15, no una garantía actual.
- Si el provider falla, el servicio registra el fallo y puede continuar con datos locales; la respuesta actual no expone una warning estructurada suficiente para distinguir ambos casos.
- La implementación actual tampoco debe considerarse una prueba de comparabilidad completa: H10/H15 deben endurecer fechas, ocupación, moneda, habitación, régimen y condiciones antes de activar ranking o filtros avanzados.

### 2.3 Semántica actual de ordenación

- `price`: menor precio primero; los precios nulos van al final; el empate usa distancia.
- `distance`: menor distancia primero.
- `stars`: mayor número de estrellas primero; estrellas nulas se comportan como cero; el empate usa distancia.
- No existe todavía `recommended`, `rating`, `signal` o `savings` como valor contractual de V1.
- Los desempates no incluyen aún un identificador estable del hotel, por lo que H14 exige añadirlo antes de prometer orden determinista entre respuestas iguales.

### 2.4 Gaps de interfaz actuales

El formulario actual permite destino, fechas, huéspedes, radio y provider, pero no expone de forma completa `min_stars`, `max_price`, `sort` ni `currency` como controles de búsqueda por área. El cliente tampoco envía explícitamente todos esos valores en la llamada actual; algunos dependen de los defaults V1.

La tarjeta actual muestra distancia, precio mínimo y provider cuando existen, pero no muestra:

- si el precio es total o por noche;
- freshness o momento de captura;
- disponibilidad y motivo de ausencia de precio;
- política de cancelación, régimen o tipo de habitación;
- razón concreta por la que un hotel fue ordenado antes que otro;
- warning de fallback local/provider parcial.

Por tanto, no se deben implementar controles visuales que aparenten soportar esos criterios hasta que H10/H15 y el provider aporten campos comparables.

## 3. Vocabulario canónico

### 3.1 Contexto de búsqueda

El contexto que da significado a precio y disponibilidad es:

```text
(destination, latitude, longitude, radius_km,
 check_in, check_out, occupancy, currency, provider_policy)
```

Mientras H10 no esté desplegada, `occupancy` se representa como el bridge V1 `guests`. No se deben comparar ofertas con fechas, huéspedes o moneda distintos.

### 3.2 Filtro

Un filtro es una restricción que puede excluir resultados del conjunto elegible:

```text
Filter = {
  key,
  value,
  applied,
  supported,
  result_count,
  explanation_code
}
```

`result_count` y `explanation_code` son objetivos H14/H15; no se deben inferir a partir de la longitud de una lista cuando el backend no los envía.

### 3.3 Orden

Un orden es una preferencia de presentación sobre el conjunto elegible, no una nueva exclusión:

```text
Sort = "recommended" | "price" | "distance" | "stars" | "signal" | "savings"
```

- `price`, `distance` y `stars` son bridges compatibles con V1.
- `recommended` requiere un ranking explicable y no puede ser un alias silencioso de precio.
- `signal` requiere evidencia comparable de provider/freshness/paridad.
- `savings` requiere baseline válido y comparable; nunca debe calcularse a partir de precios de monedas, fechas o ocupaciones diferentes.

### 3.4 Precio

Hasta que H10/H15 lo separen, `lowest_price` significa únicamente:

> la menor cantidad observada para el contexto solicitado y la moneda solicitada, sin afirmar si es total de estancia o precio por noche cuando el contrato de provider no lo garantiza.

La UI debe mostrar la unidad únicamente cuando exista `price_basis` explícito (`total_stay` o `per_night`).

### 3.5 Precio ausente

`lowest_price: null` significa “no existe una oferta comparable disponible en la fuente consultada”, no “precio cero”, “gratis” ni automáticamente “agotado”. La causa debe llegar en H15 mediante un código como:

- `no_observation`;
- `provider_unavailable`;
- `not_comparable`;
- `currency_unavailable`;
- `temporarily_unavailable`;
- `unknown`.

## 4. Catálogo de filtros y soporte

### 4.1 Filtros V1 que pueden exponerse

| Filtro | Campo fuente | Aplicación | Estado |
|---|---|---|---|
| Radio | coordenadas + `radius_km` | antes de precio y orden | soportado V1 |
| Estrellas mínimas | `HotelProperty.stars` | antes de consultar/ordenar precios | soportado V1 |
| Precio máximo | precio comparable por hotel | después de elegir la mejor oferta compatible | soportado con caveat de precio nulo |
| Fechas | `check_in`, `check_out` | contexto obligatorio para precio | soportado V1 |
| Huéspedes | `guests` | contexto obligatorio para precio | bridge V1 |
| Moneda | `currency` | contexto y selección de snapshot | parcialmente expuesto; completar en cliente |
| Provider | `use_provider` | política de consulta/freshness | soportado, pero falta estado de resultado |

### 4.2 Filtros que requieren contrato posterior

No deben presentarse como filtros efectivos hasta que exista un campo fuente, normalización y tests:

- categoría/rating externo;
- cancelación gratuita o penalización;
- régimen (`room_only`, desayuno, media pensión, etc.);
- número de habitaciones;
- adultos, niños y edades;
- disponibilidad explícita;
- tipo de habitación;
- amenities;
- precio por noche frente a total;
- ahorro frente a baseline;
- provider específico;
- freshness máxima;
- paridad o señal de confianza.

H10 define la forma de la oferta y H15 define cómo esas capacidades se anuncian en `capabilities`/metadata. Un control visible sin esas garantías sería una promesa falsa.

## 5. Precedencia y pipeline de resultados

El pipeline canónico debe ejecutarse en este orden:

1. Validar el contexto de estancia y normalizar moneda/ocupación.
2. Resolver destino y coordenadas según H12/H13.
3. Aplicar radio geográfico.
4. Aplicar filtros de inventario conocidos, empezando por estrellas.
5. Consultar snapshots locales y, si se solicitó, provider externo.
6. Seleccionar la oferta comparable más barata por hotel dentro del contexto.
7. Aplicar `max_price` únicamente a precios conocidos.
8. Mantener visibles los hoteles sin precio en una sección o estado distinguible, salvo que el usuario active explícitamente “solo con precio”.
9. Ordenar el conjunto según `sort`.
10. Añadir desempates estables, metadata, warnings y explicación por resultado.

El orden no debe invertirse de forma que un filtro de precio cambie el contexto de fechas, ocupe una oferta no comparable o haga desaparecer silenciosamente la falta de datos.

### 5.1 Interacción de `max_price` con precio nulo

La política de producto recomendada es:

- `max_price` excluye ofertas conocidas por encima del límite;
- `lowest_price=null` no prueba que el límite se cumpla ni que se incumpla;
- el hotel sin precio permanece en `unknown_price` si la búsqueda no es “solo precios conocidos”;
- H15 debe enviar `exclusion_reason`/`price_status` para que la UI explique el estado;
- si el usuario activa “solo con precio”, el backend aplica una exclusión explícita y medible, no una interpretación del frontend.

## 6. Ordenación explicable y estable

### 6.1 Orden V1

Hasta que el ranking nuevo exista, la semántica es:

```text
price:
  (price_known asc, amount asc, distance asc, hotel_id asc)

distance:
  (distance asc, price_known desc, amount asc, hotel_id asc)

stars:
  (stars_known desc, stars desc, distance asc, hotel_id asc)
```

Los campos no disponibles no deben convertirse silenciosamente en una puntuación positiva. `null` es desconocido, no el mejor valor.

### 6.2 Orden recomendado futuro

`recommended` solo puede activarse cuando cada resultado pueda mostrar señales mínimas:

- disponibilidad/observación válida;
- comparabilidad de fechas, ocupación y moneda;
- freshness o edad de captura;
- calidad de provider;
- distancia y estrellas como señales secundarias;
- explicación legible, por ejemplo: “mejor precio observado y a 0,8 km”.

El score no debe mezclar magnitudes incomparables sin normalización documentada. La fórmula y sus pesos deben versionarse junto al contrato H15, con fixture de ranking y posibilidad de auditoría.

### 6.3 Ahorro y baseline

No se muestra “ahorro” si no existe un baseline explícito y válido. Son baselines permitidos, previa definición H10/H15:

- precio inicial de la misma watch;
- precio anterior de la misma oferta;
- referencia comparable del mismo contexto.

No son baselines permitidos:

- precio de otra fecha;
- otra ocupación;
- otra moneda sin conversión fechada;
- precio de un hotel distinto;
- “precio medio” sin ventana y población documentadas.

## 7. URL state y controles de interfaz

H13 define la serialización general de la búsqueda. H14 añade solamente parámetros de filtro y orden:

```text
sort=price|distance|stars|recommended|signal|savings
min_stars=1..5
max_price>=0
radius_km=1..50
currency=EUR
price_status=all|known_only
```

Reglas:

- omitir defaults para URLs cortas cuando su ausencia sea semánticamente inequívoca;
- serializar filtros activos de manera reproducible;
- `router.replace` durante edición controlada/debounce;
- `router.push` al aplicar filtros o cambiar orden de forma confirmada;
- restaurar filtros desde URL sin ejecutar una búsqueda si el contexto es incompleto o inválido;
- no guardar datos privados, IDs de usuario, emails, thresholds de alertas ni tokens;
- conservar parámetros desconocidos para compatibilidad solo si H13/H15 lo autorizan; de lo contrario, limpiar y registrar `url_param_ignored`.

### 7.1 Aplicar y borrar

Desktop y mobile deben ofrecer:

- contador de filtros activos;
- chips o resumen de filtros aplicados;
- acción “Borrar todo” que restaure defaults sin borrar destino/fechas salvo acción explícita;
- estado pendiente mientras se recalcula;
- prevención de doble aplicación;
- feedback de cuántos resultados cambiaron;
- controles deshabilitados cuando el provider no respalda el campo.

El panel no debe obligar a abrir un modal para descubrir qué filtros están activos en mobile.

## 8. Explicaciones, warnings y estados

Cada resultado debería poder exponer una explicación estructurada, no solo texto generado en frontend:

```text
explanation = {
  primary_reason: "lowest_observed_price" | "nearest" | "highest_stars" | "recommended_signal" | "no_price",
  codes: string[],
  evidence: {
    distance_km?: number,
    stars?: number,
    amount?: number,
    currency?: string,
    collected_at?: datetime,
    provider?: string
  }
}
```

Estados mínimos del conjunto:

- `success`: resultados comparables completos para el contexto;
- `partial`: resultados válidos, pero una o más fuentes/filter capabilities no pudieron aplicarse;
- `empty`: ningún hotel cumple el contexto y filtros;
- `empty_known_price`: hay hoteles, pero ninguno tiene precio conocido;
- `provider_unavailable`: se usó fallback local o no hubo observaciones externas;
- `invalid_filter`: filtro fuera de rango o no soportado;
- `stale`: resultado válido pero más antiguo que el umbral contractual;
- `error`: fallo total sin lista confiable.

No se debe confundir `[]` con todos esos estados. La forma versionada y los warnings pertenecen a H15.

## 9. Compatibilidad V1

- No se cambia la semántica de V1 silenciosamente.
- `sort=price|distance|stars` sigue aceptado durante la transición.
- V1 puede seguir devolviendo listas desnudas hasta H15; el frontend debe usar un adaptador y no mezclar payload V1 con V2 sin detección explícita.
- Los nuevos filtros se introducen de forma aditiva y detrás de capability flags.
- Si V1 recibe un filtro que no conoce, debe devolver validación clara o ignorarlo de forma documentada; nunca debe fingir que se aplicó.
- Los cambios de respuesta que añadan explicación, `price_status` o freshness deben pasar primero por H15.

## 10. Tests y gates de aceptación

### 10.1 Backend unitario

- radio incluye el límite y excluye el siguiente punto;
- `min_stars` excluye `stars=null` de forma explícita;
- `max_price` excluye precios conocidos superiores;
- `max_price` conserva `lowest_price=null` bajo la política `all`;
- `price_status=known_only` excluye nulos cuando esté implementado;
- moneda, fechas y huéspedes no mezclan snapshots;
- provider fresco solo sobrescribe fallback cuando moneda, fechas, ocupación, condiciones y hotel/contexto han sido validados; el test debe fallar con una respuesta de moneda o contexto incorrectos;
- fallo de provider produce estado/warning, no un precio inventado;
- orden price/distance/stars respeta desempates estables por `hotel_id`;
- hoteles sin precio no aparecen como precio cero;
- ranking recomendado no se activa sin evidencia mínima.

### 10.2 Contrato/API

- valores inválidos de filtro producen códigos estables;
- la metadata anuncia filtros y orden realmente aplicados;
- el resultado distingue `success`, `partial`, `empty`, `provider_unavailable` y `error`;
- el payload no filtra ni expone `user_id` en resultados públicos;
- H15 conserva compatibilidad con consumidores V1 y payloads grandes.

### 10.3 Frontend y E2E

- aplicar un filtro actualiza URL y resultados;
- refresh y back/forward restauran destino, filtros y orden;
- borrar filtros no borra contexto por accidente;
- un control no soportado no se muestra o explica por qué está desactivado;
- el contador, chips y estado vacío son accesibles;
- `aria-live` anuncia cambios de resultados y warnings;
- teclado y mobile permiten aplicar, borrar y cerrar filtros;
- respuestas antiguas no pisan una búsqueda posterior;
- la tarjeta distingue precio conocido, sin observación y provider fallback.

## 11. Observabilidad y métricas

Registrar sin datos personales:

- `hotel_search_filters_viewed`;
- `hotel_search_filter_applied` con `filter_key` y resultado agregado;
- `hotel_search_filter_cleared`;
- `hotel_search_sort_changed`;
- `hotel_search_no_price`;
- `hotel_search_partial_provider`;
- `hotel_search_explanation_shown`;
- duración de búsqueda y edad de snapshot;
- ratio de resultados con precio, provider y warning;
- discrepancias entre orden solicitado y capabilities aplicadas.

No registrar querys completos ni coordenadas de precisión innecesaria en eventos de producto si no son necesarias para el diagnóstico.

## 12. Handoffs

- **H10:** definir `StayOffer`, `price_basis`, disponibilidad, cancelación, régimen, habitaciones y comparabilidad.
- **H12:** conservar destination confidence/source y no mezclar un destino ambiguo con filtros de resultados.
- **H13:** integrar filtros/orden en URL state, validación, submit, back/forward y focus management.
- **H15:** convertir lista V1 en envelope versionado con metadata, capabilities, warnings, price status, freshness, explanation y paginación.
- **H17:** concretar componentes visuales, responsive behavior, accesibilidad y copy ES/EN.
- **H20/H23:** definir provider capabilities, límites, fallback y frescura real.
- **H35:** revisar privacidad, tracking, atribución, términos de provider y afirmaciones de precio.
- **H37:** pruebas de carga, concurrencia y coste de consultas externas.
- **H41:** instrumentación de producto y experimentos de filtros/ranking.

## 13. Gate H14

H14 podrá considerarse implementada cuando:

1. cada filtro visible tenga una fuente de datos, una semántica y una prueba;
2. cada orden tenga precedencia y desempate estables;
3. los resultados sin precio y los fallos de provider sean distinguibles;
4. la UI muestre filtros activos, contadores y explicaciones sin adivinar estados;
5. URL, refresh, back/forward y cancelación respeten H13;
6. H15 reciba un payload versionado que permita representar todos esos estados;
7. los filtros no respaldados no se prometan al usuario.
