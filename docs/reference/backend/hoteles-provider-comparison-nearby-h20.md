# H20 — Comparación de providers, paridad y hoteles cercanos

**Estado:** contrato de comparación y contexto secundario; implementación V2, comparabilidad completa, frontend y QA pendientes  
**Fecha:** 2026-08-05  
**Área:** backend / frontend / producto / QA  
**Fuente de verdad:** sí para elegibilidad de comparación, estados de paridad, comp sets y acciones de hoteles cercanos  
**Fase del roadmap:** H20  
**Depende de:** H05, H10, H15, H17, H18, H19  
**Relacionado con:** H20 habitaciones/régimen en el modelo H10, H22 favoritos, H23 tracking, H25 confidence, H26 alertas, H31 dirección visual, H35 deeplinks

> H20 ayuda a decidir sin convertir señales incompletas en una recomendación falsa. Paridad de providers y hoteles cercanos son dos herramientas distintas: una compara ofertas del mismo hotel; la otra explora propiedades diferentes alrededor de un hotel ancla.

## 1. Decisión de alcance

H20 cubre dos superficies relacionadas, pero no intercambiables:

| Superficie | Qué compara | Pregunta que responde | No debe afirmar |
|---|---|---|---|
| Paridad de providers | Tarifas del mismo `HotelProperty` para una estancia comparable | “¿Qué provider ofrece la observación más baja bajo las mismas condiciones?” | “Este hotel es mejor” o “el precio final está garantizado” |
| Hoteles cercanos/comp set | Propiedades distintas respecto a un hotel ancla | “¿Qué alternativas de la zona puedo explorar?” | “Estas propiedades tienen la misma oferta o paridad” |

H20 no implementa todavía:

- migración de `HotelRateSnapshot` a oferta V2;
- normalización completa de habitación, régimen, cancelación y fees;
- nuevos providers o servicios externos;
- ranking `recommended` o bonus por afiliación;
- cambios de CSS, layout o URL state;
- alertas de paridad listas para producción.

La fase sí deja definidos los contratos, estados, ordenación, ownership, acciones y gates que las implementaciones posteriores deben respetar.

## 2. Estado actual comprobable

### 2.1. Paridad actual

`HotelParityService` agrupa snapshots por:

```text
(check_in, check_out, guests, currency)
```

Para cada grupo:

- cuenta providers distintos;
- calcula mínimo, máximo, promedio, spread absoluto y porcentaje;
- devuelve `limited` cuando hay menos de dos providers o importes insuficientes;
- clasifica `stable` por debajo del 10 %;
- clasifica `tensioned` desde el 10 %;
- clasifica `breach` desde el 20 %;
- ordena señales por entrada/salida descendente.

`HotelParityOut` expone actualmente fechas, huéspedes, moneda, cantidad de providers, importes, spread, `is_parity_broken`, `status` y `label`.

Esto es una base V1 útil para explorar, pero **no es todavía paridad de ofertas estrictamente comparables ni una comparación contextual activa**. El endpoint actual `GET /{hotel_id}/parity` no recibe fechas, ocupación ni una `StayQuery`: devuelve snapshots históricos del hotel y la UI toma la primera señal ordenada por fechas, que no equivale necesariamente a la observación más fresca.

Además, `ParitySignal.from_rates()` cuenta nombres de provider distintos, pero incorpora todos los rates del grupo. Varias habitaciones/ofertas del mismo provider pueden inflar el spread aunque `provider_count >= 2`. Hasta H10/H11/H19 no debe llamarse a esto “comparación de providers” ni usarse para afirmar un provider más barato.

La respuesta V1 usa `status="info"` y `label="limited"` para varios casos limitados. Los estados detallados de H20 (`one_provider`, `partial`, `stale`, `invalid`, `provider_degraded`, `comparable`) son contrato V2 propuesto, no estados ya serializados por la API.

La base V1 no incorpora como clave de agrupación:

- habitaciones/rooms;
- adultos y niños diferenciados;
- `room_label` normalizado o `room_id`;
- régimen;
- cancelación;
- semántica base/total;
- fees obligatorias;
- freshness/provenance/confidence;
- disponibilidad elegible;
- comparability key/version.

Por tanto, las etiquetas actuales no deben reinterpretarse como una certificación comercial.

### 2.2. Comp sets y hoteles cercanos actuales

El modelo actual de comp set tiene:

- `user_id`;
- nombre;
- hotel ancla;
- miembros por `hotel_id`.

`HotelGeoService.suggest_for_comp_set` actualmente:

1. valida que el comp set pertenezca al usuario;
2. obtiene coordenadas del hotel ancla;
3. excluye ancla y miembros ya incluidos;
4. calcula distancia Haversine contra propiedades con coordenadas;
5. ordena por distancia, nombre normalizado e ID;
6. devuelve hasta el límite solicitado.

`HotelNearbySuggestionOut` devuelve identidad básica, ciudad, país, estrellas y distancia. No devuelve todavía precio, disponibilidad, estancia, provider, fees ni comparabilidad.

La UI actual permite crear comp sets, añadir/quitar miembros y añadir sugerencias cercanas. Esa acción significa “incorporar a mi comparativa de zona”; no significa seguir precio ni comparar automáticamente tarifas.

## 3. Contrato de paridad de providers

### 3.1. Unidad de comparación

Una fila de paridad pertenece a:

```text
canonical_hotel_id
+ stay_query / fechas
+ ocupación canónica
+ habitación
+ régimen
+ cancelación
+ moneda o contexto de conversión
+ semántica de fees/importe
```

El `user_id`, regla, label, canal, afiliación y timestamp de captura no forman parte de la identidad compartida de la comparación.

Dos rates solo son **comparables** si:

1. apuntan al mismo hotel canónico;
2. cubren entrada y salida idénticas;
3. representan la misma ocupación o una normalización explícita;
4. tienen moneda compatible o conversión versionada;
5. tienen semántica de importe compatible (`total` con `total`, `base` con `base`, nunca mezclar silenciosamente);
6. tienen habitación equivalente o una condición explícita de equivalencia;
7. tienen régimen equivalente;
8. tienen cancelación equivalente o una diferencia visible que impide comparación directa;
9. fees obligatorias conocidas o estado parcial explícito;
10. availability y freshness permiten usar la observación;
11. provider y provider run son trazables.

Si una dimensión crítica es `unknown`, la fila puede permanecer visible como dato relacionado, pero no entra en un spread de paridad fuerte.

### 3.2. Estados canónicos

H20 define estados independientes de los colores actuales de la UI:

| Estado | Condición | Qué puede decir la UI | Acción |
|---|---|---|---|
| `no_data` | no hay rates o no hay grupo válido | “No hay tarifas comparables” | buscar/reintentar |
| `one_provider` | solo un provider elegible | “Solo hay un provider observado” | revisar o volver más tarde |
| `partial` | hay rates relacionados, pero falta una condición crítica | “Hay datos, pero no se pueden comparar del todo” | ver diferencias |
| `stale` | rates fuera del TTL de H05 | “La comparación puede haber cambiado” | revalidar |
| `invalid` | moneda, fechas, amount o condiciones inválidas | “Comparación no disponible” | corregir/reintentar |
| `provider_degraded` | timeout, 429, error o run parcial | “Falta información de un provider” | reintentar más tarde |
| `comparable` | al menos dos rates elegibles y comparables | “Comparación disponible” | revisar provider/condiciones |
| `stable` | comparable y spread por debajo del umbral documentado | “Diferencia pequeña entre providers” | revisar cualquier opción |
| `tensioned` | comparable y spread relevante | “Hay una diferencia apreciable” | abrir la oferta elegible |
| `breach` | comparable y spread alto según política versionada | “Hay una diferencia notable” | revisar la opción más baja y disclosure |

`one_provider` no es `stable`. `partial` no es `breach`. `provider_degraded` no es `sold_out`. Un estado sin datos no debe desaparecer convirtiéndose en una lista vacía sin explicación.

### 3.3. Cálculo de spread

Solo para un grupo `comparable`:

```text
lowest_price  = mínimo de importes elegibles
highest_price = máximo de importes elegibles
spread_amount  = highest_price - lowest_price
spread_percent = spread_amount / lowest_price * 100
```

Invariantes:

- todos los importes son positivos y están en la misma semántica;
- la moneda o conversión está documentada;
- no se cuentan providers con error como un precio;
- no se mezclan habitaciones o políticas incompatibles;
- snapshots stale/expired no entran en el spread activo;
- un provider con varias ofertas aporta varias filas solo si cada oferta tiene identidad y condiciones claras;
- no se deduplica por importe únicamente;
- el redondeo es de presentación y la decisión usa precisión backend;
- el umbral y la versión de política quedan en metadata.

Los umbrales V1 actuales de 10 % y 20 % pueden conservarse como compatibilidad visual, pero no deben promocionarse como política definitiva hasta que H19/H10 aporten total, fees y comparability key. La futura respuesta V2 debe incluir `comparison_status`, `eligible_provider_count`, `excluded_provider_count`, `exclusion_reasons` y `policy_version`.

### 3.4. Provider más barato

Puede mostrarse “menor precio observado” solo cuando:

- la oferta pertenece al mismo contexto de estancia;
- es comparable con las alternativas;
- su freshness y disponibilidad son elegibles;
- el importe no oculta fees obligatorias desconocidas;
- el provider está identificado;
- el deeplink, si existe, ha pasado allowlist;
- la UI explica que es precio observado y puede cambiar en el partner.

Si el provider A tiene 300 € con fees desconocidas y B tiene 320 € total conocido, A puede mostrarse como “observación base más baja” pero no como “total más barato” sin una advertencia prominente.

### 3.5. Alertas de paridad

La regla `parity_break` debe usar el mismo contrato de elegibilidad que la pantalla:

- no disparar con un solo provider;
- no disparar por cambiar de habitación, régimen, cancelación o moneda;
- no disparar con `provider_error`, fixture, expired o condiciones desconocidas incompatibles;
- conservar snapshots origen, provider run, policy version y contexto;
- aplicar cooldown/dedupe H26;
- tener ownership inequívoco por regla/suscripción H26-H27.

El endpoint V1 puede seguir exponiendo `is_parity_broken`, pero la implementación nueva debe evitar usarlo como único dato para enviar una señal privada.

## 4. Contrato de hoteles cercanos y comp sets

### 4.1. Hotel ancla y miembros

Un comp set es una vista privada del usuario:

```text
anchor_hotel_id
+ member_hotel_ids
+ user_id
+ label/name
```

El ancla define el centro geográfico y la propiedad de referencia. Los miembros son alternativas explorables, no equivalentes automáticos.

Reglas:

- todos los IDs se validan como hoteles canónicos internos;
- el ancla no puede añadirse como miembro;
- un miembro no puede duplicarse en el mismo set;
- un usuario solo puede leer/modificar sus comp sets;
- eliminar un comp set no elimina hoteles, snapshots, favoritos ni trackings;
- comp set y tracking son entidades independientes;
- un hotel cercano puede añadirse al set sin alterar la búsqueda actual hasta que el usuario lo seleccione explícitamente;
- cualquier navegación al miembro debe conservar el retorno al ancla y al contexto H18.

### 4.2. Qué significa “cercano”

La sugerencia cercana se define inicialmente por:

```text
coordenadas válidas del ancla
+ radio_km explícito
+ propiedad con coordenadas válidas
+ distancia Haversine reproducible
```

No significa:

- misma categoría;
- mismo barrio percibido;
- misma calidad;
- misma disponibilidad;
- mismo precio;
- mejor alternativa para el usuario.

La UI debe mostrar distancia y ubicación, y si se muestran estrellas, indicar que la categoría puede no estar informada. No debe mostrar precio inventado ni prometer equivalencia.

### 4.3. Orden determinista de cercanos

El orden V1 contractual es:

```text
(distance_km asc,
 canonical_name casefold asc,
 hotel_id asc)
```

En una futura versión con señales de decisión, cualquier precio, estrellas o disponibilidad debe ser un segundo modo explícito (`sort=nearby_value`), no alterar silenciosamente la cercanía.

El backend devuelve el orden; el frontend no reordena con defaults locales.

### 4.4. Estados de cercanos

| Estado | Condición | UI/action |
|---|---|---|
| `available` | ancla y candidatos tienen coordenadas | lista ordenada por distancia |
| `no_coordinates` | ancla o candidato carece de coordenadas | explicar y permitir otra búsqueda |
| `empty_radius` | no hay propiedades en el radio | ampliar radio o volver al resultado |
| `partial_catalog` | catálogo incompleto o coordenadas parciales | mostrar limitación, no afirmar exhaustividad |
| `not_owned` | comp set no pertenece al usuario | respuesta segura de permiso/not-found |
| `error` | fallo inesperado del servicio | reintentar sin perder ancla |

“0 cercanos” no significa que no existan hoteles en la zona: significa que no hay candidatos disponibles en el catálogo y radio consultados.

### 4.5. Acciones permitidas

Desde un cercano, la primera acción puede ser:

1. añadir al comp set;
2. abrir detalle del hotel con H18;
3. seleccionar para una búsqueda comparable si el usuario confirma estancia;
4. guardar como favorito H22;
5. seguir precio solo después de obtener una oferta completa H23.

No se crea automáticamente un tracking, una alerta ni un deeplink externo al añadir un miembro.

## 5. API V2 objetivo y compatibilidad

### 5.1. Comparison group

La respuesta futura puede envolver la salida actual así:

```json
{
  "comparison": {
    "hotel_id": "canonical-id",
    "stay_context": {
      "check_in": "2026-09-10",
      "check_out": "2026-09-13",
      "nights": 3,
      "occupancy_source": "legacy_inferred"
    },
    "status": "partial",
    "policy_version": "hotel-comparison-v1",
    "eligible_provider_count": 1,
    "observed_provider_count": 2,
    "excluded_provider_count": 1,
    "exclusion_reasons": ["fees_unknown"],
    "signals": []
  }
}
```

Cada signal debe contener, cuando exista:

```text
provider
rate/snapshot reference
amount observed/total
currency
conditions summary
freshness/provenance/confidence
comparability status
availability status
deep_link validation status
```

No exponer raw payload, credenciales, `user_id`, thresholds ni labels privados.

### 5.2. Nearby response

La evolución aditiva puede incluir:

```json
{
  "anchor_hotel_id": "canonical-anchor",
  "radius_km": 5,
  "sort_applied": "distance",
  "catalog_completeness": "partial",
  "items": [
    {
      "hotel_id": "canonical-member",
      "canonical_name": "Hotel Example",
      "city": "Madrid",
      "country_code": "ES",
      "stars": null,
      "distance_km": 0.8,
      "price_signal": null,
      "has_tracking": false
    }
  ],
  "warnings": ["price_not_requested"]
}
```

La ausencia de `price_signal` significa que no se solicitó o no es elegible; no significa cero ni agotado. `has_tracking` solo puede aparecer en una respuesta autenticada y específica del usuario; no debe persistirse en cache compartida ni incluirse en un payload público/compartible.

V1 mantiene sus endpoints y schemas actuales durante el bridge. Los campos nuevos son opcionales y los clientes antiguos deben continuar mostrando identidad/distancia/paridad limitada sin inventar precio.

## 6. Frontend, jerarquía y navegación

### 6.1. Paridad como ayuda secundaria

El panel de paridad debe:

- aparecer después de identidad, resultado/oferta y acciones principales;
- explicar cuántos providers son comparables, no solo observados;
- diferenciar estable, limitada, parcial, stale, degradada y breach;
- enseñar importe, moneda, condiciones y freshness en el mismo contexto;
- ofrecer “ver tarifas”/“abrir detalle” solo para una fila elegible;
- no competir con “Guardar hotel”, “Seguir precio” ni CTA de partner;
- mantener una alternativa textual accesible al porcentaje y al color.

La UI actual `signalAssessment` puede servir como bridge de `none/limited/scored`, pero no debe presentar `scored` como comparabilidad completa hasta que backend lo respalde.

### 6.2. Comp set como exploración

El panel de cercanos debe:

- nombrarse “Hoteles cercanos” o “Comparativa de zona”, no “paridad”;
- mantener visible el hotel ancla;
- mostrar distancia y datos de identidad antes de acciones;
- explicar que añadir un hotel no inicia tracking;
- permitir abrir detalle y volver al ancla/contexto;
- no mostrar una lista de paneles técnicos por cada miembro;
- preservar teclado, focus, touch targets y reduced motion.

### 6.3. URL y retorno

H18 gobierna la navegación:

- abrir el ancla o miembro usa `hotel_id` canónico y conserva búsqueda válida;
- cambiar de miembro sustituye solo la selección cuando la política URL lo permita;
- cerrar detalle mantiene filtros, orden, cursor y comp set si forman parte del contexto seguro;
- no se guardan IDs privados de comp set en URLs públicas sin contrato autenticado;
- no se acepta un `return` arbitrario ni se permite open redirect;
- una entrada directa sin resultados puede mostrar detalle limitado, pero no fabrica una lista comparable.

## 7. Ownership y seguridad

- Paridad pública de catálogo puede ser compartible solo si no contiene datos privados.
- La paridad V1 debe tratarse como señal exploratoria y limitada mientras no tenga contexto de estancia, freshness y dedupe por oferta/provider.
- Un evento/alerta de paridad asociado a usuario debe apuntar a `rule_id`/`tracked_offer_id` y comprobar ownership por esa relación.
- Resolver eventos únicamente por `hotel_id` es insuficiente para nuevas señales privadas cuando varios usuarios siguen el mismo hotel.
- Comp sets, miembros, labels y acciones son privados por `user_id`.
- Un usuario no puede leer el comp set, detalle privado o historial de otro usuario por IDs opacos.
- El endpoint de cercanos debe limitar radio, límite y coste de consulta.
- Coordenadas no disponibles deben degradar de forma explícita; no rellenarse con el centro de ciudad sin etiquetarlo.
- Provider names, raw labels y URLs deben sanitizarse.
- Deeplinks externos requieren allowlist, contexto seguro y disclosure H35.

## 8. Tests y evidencias

### Backend/unitarios

- agrupación no mezcla hoteles, fechas, ocupaciones, monedas ni condiciones;
- `room_label`, régimen, cancelación y fees incompatibles producen `partial`/`invalid`, no `stable`;
- provider error/timeout/429 no entra como precio;
- rates stale/expired quedan fuera de paridad activa;
- un provider devuelve `one_provider`, no `stable`;
- cálculo de spread, cero, negativos, redondeo y moneda;
- umbrales y `policy_version` deterministas;
- cercanos ordenan por distancia, nombre e ID;
- ancla y miembros se excluyen correctamente;
- radio/límite validado y coordenadas ausentes producen estado correcto;
- ownership de comp sets y acciones 403/404 seguras;
- evento de usuario nunca se resuelve solo por hotel;
- V1 y envelope V2 conviven sin romper schemas.

### Frontend

- paridad limitada, parcial, stale, degradada y comparable tienen copy distinto;
- no se muestra “mejor provider” con condiciones incompatibles;
- “Hoteles cercanos” no se confunde con paridad;
- añadir cercano no crea tracking ni alerta;
- abrir miembro y volver conserva ancla y búsqueda;
- frontend no reordena respecto a backend;
- ES/EN, dark/light, mobile, teclado y lector de pantalla cubren la superficie;
- no hay CTA de partner para deeplink ausente o bloqueado.

### Producto/QA

- mismo hotel, misma estancia, providers A/B con total comparable;
- mismo hotel con desayuno/cancelación/habitación diferentes;
- una sola fuente, provider caído y catálogo parcial;
- monedas distintas y fees desconocidas;
- hotel ancla sin coordenadas;
- radio sin candidatos;
- comp set con miembros y retorno al detalle;
- precio observado distinto de precio final del partner;
- alertas privadas con dos usuarios siguiendo el mismo hotel.

## 9. Observabilidad y métricas

Registrar, sin PII innecesaria:

```text
hotel_comparison_requests_total
hotel_comparison_comparable_groups_total
hotel_comparison_partial_groups_total
hotel_comparison_one_provider_total
hotel_comparison_provider_degraded_total
hotel_comparison_rates_excluded_total
hotel_comparison_exclusion_reason_total
hotel_nearby_requests_total
hotel_nearby_empty_radius_total
hotel_nearby_missing_coordinates_total
hotel_nearby_member_added_total
hotel_comp_set_ownership_denied_total
hotel_parity_alert_suppressed_total
```

Cada comparación debe poder explicar cuántos rates recibió, cuántos fueron elegibles, por qué se excluyeron los demás y qué versión de política se aplicó. No basta con registrar `provider_count` bruto.

## 10. Gate H20

H20 podrá marcarse completa cuando:

- paridad de providers y hoteles cercanos estén modelados como superficies distintas;
- la comparación fuerte use estancia, ocupación, habitación, régimen, cancelación, moneda, fees, freshness y disponibilidad compatibles;
- one-provider, partial, stale, invalid y provider-degraded tengan estados explícitos;
- no se llame “mejor provider” a una cifra con condiciones incompatibles;
- comp sets conserven ancla, ownership y retorno navegable;
- cercanos tengan orden determinista y no fabriquen precio/disponibilidad;
- añadir un cercano no cree tracking ni alerta automáticamente;
- frontend, backend, inbox y deeplinks respeten ownership;
- V1 conserve compatibilidad y V2 tenga metadata de elegibilidad/exclusiones;
- tests, observabilidad, i18n, accesibilidad y QA visual cubran los estados limitados;
- H19/H35 validen total, fees, disclosure y salida a partner.

**Resultado contractual:** H20 queda definido como contrato. La implementación de comparación estricta y la mejora visual permanecen pendientes; el código actual no debe declararse como paridad completa por devolver `provider_count >= 2`.

## 11. Handoff

| Fase | Handoff H20 |
|---|---|
| H21 | estados de empty/partial/error/stale para paridad y cercanos |
| H22 | guardar un cercano como favorito sin crear tracking |
| H23 | iniciar tracking solo desde una oferta con estancia y condiciones |
| H25 | confidence/freshness por rate, grupo y catálogo |
| H26 | `parity_break` elegible, con cooldown y dedupe por regla |
| H27 | inbox con ownership por evento, no solo hotel |
| H31-H34 | jerarquía, responsive, accesibilidad e i18n de ambas superficies |
| H35 | deeplink, afiliación, disclosure y privacidad |
| H38 | SSRF, ownership, límites y abuso de endpoints |
| H41 | métricas de elegibilidad, exclusión y catálogo parcial |

**No se declara H20 implementada hasta que la evidencia confirme comparabilidad real en backend y UI.**