# H17 — Contrato de ranking determinista y explicación hotelera

**Estado:** contrato de producto y backend; implementación del ranking V2 y metadata pendiente  
**Fuente de verdad:** sí, para ordenación, desempates, señales, elegibilidad y explicaciones de resultados hoteleros  
**Fase del roadmap:** H17  
**Dependencias:** H14, H15, H16  
**Handoff principal:** H18 detalle navegable; H19 precio comparable; H20 providers/paridad; H41 observabilidad

## 1. Propósito y decisión de fase

H17 define cómo se ordenan los resultados hoteleros y cómo se explica ese orden sin convertir una heurística en una promesa.

La fase separa cuatro conceptos que no deben mezclarse:

1. **Filtro:** excluye resultados por una condición explícita.
2. **Orden:** cambia la posición de resultados elegibles.
3. **Ranking:** calcula una prioridad dentro de un orden recomendado.
4. **Señal:** aporta evidencia sobre precio, distancia, freshness, provider o comparabilidad, pero no necesariamente cambia la posición.

Esta fase es **contractual**. No implementa todavía `recommended`, no modifica el `sort` V1 y no añade scores calculados en frontend. La implementación futura deberá conservar los órdenes objetivos, versionar cualquier ranking compuesto y devolver explicación estructurada mediante H15.

La regla principal es:

> Ningún resultado puede aparecer arriba por una señal invisible, una comisión de partner, un dato incompleto tratado como ventaja o una puntuación imposible de auditar.

## 2. Estado actual comprobable

### 2.1. Orden V1 disponible

`HotelAreaSearchQueryIn` acepta actualmente:

```text
sort=price|distance|stars
```

`hotels_service.area_search` aplica hoy:

```text
price:
  (lowest_price asc, distance_km asc)
  lowest_price=null se transforma en infinito y queda al final

distance:
  (distance_km asc)

stars:
  (-stars asc, distance_km asc)
  stars=null se comporta como cero
```

No existe un desempate final por `hotel_id` o nombre estable. Cuando dos hoteles tienen el mismo precio/distancia/estrellas, el orden puede depender del orden de la colección original y producir jitter en paginación o refresh.

### 2.2. Campos actualmente disponibles

El resultado por área V1 ofrece:

- `hotel_id`;
- `canonical_name`, ciudad y país;
- `stars` opcional;
- `distance_km`;
- `lowest_price` opcional;
- `currency`;
- `provider` opcional;
- fechas y `guests` del contexto;
- `has_tracking` como proyección del usuario autenticado.

No ofrece aún de forma suficiente:

- `price_basis` total/noche;
- fees y precio final;
- cancellation, régimen o habitación comparables;
- freshness por resultado;
- disponibilidad normalizada;
- rating externo con fuente;
- ahorro o baseline válido;
- explicación de orden;
- confianza por observación;
- capabilities y warnings V2.

Por ese motivo no se puede activar un recomendado que combine precio, confianza, condiciones y provider sin completar H10/H15/H19/H20.

### 2.3. Señales existentes que no son ranking hotelero

El frontend tiene `signalAssessment` para mostrar la calidad de una señal de paridad, pero esa evaluación:

- distingue `none`, `limited` y `scored`;
- exige varios providers, precios y spread para puntuar;
- no debe reutilizarse directamente como score de orden;
- no convierte una diferencia de providers en “mejor hotel”.

Los scores de quick search, recommendations, matching o door-to-door pertenecen a otros dominios. No se copian ni se mezclan con el ranking hotelero.

## 3. Vocabulario canónico

### 3.1. Orden estricto

Un orden estricto es objetivo y reproducible para una misma query:

```text
price
 distance
stars
```

No depende de preferencias personales, `has_tracking`, comisión ni selección previa.

### 3.2. Orden recomendado

`recommended` es un producto futuro, no un alias de `price`. Solo puede activarse cuando:

- las features y sus fuentes están definidas;
- las magnitudes están normalizadas;
- el contexto de estancia es comparable;
- existe versión de fórmula y pesos;
- hay explicación para cada resultado elegible;
- missing data no recibe bonus accidental;
- afiliación/comisión está separada o declarada según H35/H50.

### 3.3. Score

Un score es un número técnico de una versión concreta. No debe mostrarse como “confianza” ni “calidad” sin copy y definición separados.

```text
ranking_score = f(features, version, context)
```

El score debe ser:

- reproducible para la misma entrada y versión;
- acotado y serializable;
- independiente del orden accidental de SQL;
- auditable por feature;
- invalidado si falta una feature obligatoria;
- no personalizado salvo flag explícito y contrato aprobado.

### 3.4. Explicación

La explicación es el motivo que puede entender una persona, respaldado por datos:

```json
{
  "primary_reason": "lowest_observed_price",
  "codes": ["price_context_match", "near_destination"],
  "evidence": {
    "amount": 420,
    "currency": "EUR",
    "distance_km": 1.2,
    "stars": 4,
    "provider": "mock"
  },
  "ranking_version": "hotel_ranking.v1"
}
```

No se genera una explicación textual distinta en cada cliente. Backend/H15 entrega códigos y evidencia allowlisted; frontend/i18n decide el copy.

## 4. Orden V1 contractual

### 4.1. Precio ascendente

El orden contractual corregido es:

```text
(price_known desc,
 amount asc,
 distance_km asc,
 hotel_id asc)
```

- `price_known=true` precede a `false`;
- entre precios conocidos, menor importe primero;
- `currency`, fechas, huéspedes y contexto deben ser iguales;
- `distance_km` rompe empates;
- `hotel_id` rompe empates finales.

La implementación actual aproxima esta semántica usando infinito para `null`, pero no tiene todavía el desempate final estable. Además, el gap de H14 sobre validación estricta de moneda/contexto del provider bloquea la elegibilidad de `recommended`. H17 exige cerrar ambos puntos antes de declarar la ordenación lista para H15 cursor/paginación.

### 4.2. Distancia ascendente

```text
(distance_km asc,
 price_known desc,
 amount asc,
 hotel_id asc)
```

La proximidad es el criterio primario. Si dos hoteles están a la misma distancia:

- se prioriza precio conocido;
- después menor precio comparable;
- finalmente `hotel_id`.

No se usa el precio como primario ni se excluyen hoteles sin precio por ordenar por distancia.

### 4.3. Estrellas descendente

```text
(stars_known desc,
 stars desc,
 distance_km asc,
 hotel_id asc)
```

- estrellas conocidas preceden a desconocidas;
- más estrellas primero dentro de datos conocidos;
- distancia y `hotel_id` resuelven empates;
- `stars=null` no significa cero estrellas ni peor hotel verificado;
- la UI debe usar “categoría no informada” o copy equivalente.

### 4.4. Compatibilidad V1

- `price`, `distance` y `stars` mantienen sus nombres y propósito.
- V1 puede conservar la salida desnuda y la semántica aproximada durante la transición.
- V2 debe declarar `sort_applied`, `tie_breakers` y `ranking_version` en metadata.
- Si el backend no puede garantizar el desempate estable, debe marcar la capability como limitada y no prometer paginación estable.

## 5. `recommended`: contrato futuro

`recommended` no está disponible en la implementación actual. Cualquier ejemplo V2 de esta sección describe el estado futuro después de cerrar H19/H20, no una capability que pueda activarse hoy.

### 5.1. Elegibilidad mínima

Un hotel es elegible para `recommended` solo si cumple el contexto y no presenta una carencia que invalide la comparación:

- identidad de hotel resuelta;
- destino y distancia válidos si la proximidad participa;
- precio con moneda/contexto comparable o regla explícita de no precio;
- freshness/provenance conocida o estado `unknown` penalizado de forma documentada;
- disponibilidad/condiciones con semántica conocida si forman parte del score;
- provider status no incompatible con la promesa de la señal;
- explicación generable con evidencia real.

Un hotel no elegible puede permanecer visible como alternativa, pero no debe recibir un score comparable ni una etiqueta “recomendado”. Cuando se solicite `sort=recommended` y exista al menos una limitación de elegibilidad global, la política inicial será fallback completo a `sort=price` (o al orden estricto configurado), con `sort_applied`/warning explícitos; no se mezclará silenciosamente una lista parcialmente recomendada. Los resultados individualmente no elegibles dentro de un conjunto válido permanecen al final, ordenados por los tie-breakers estrictos y con `not_ranked_missing_context`.

### 5.2. Features permitidas inicialmente

La primera versión no debe usar más features de las que H10/H15/H19 puedan respaldar:

| Feature | Fuente | Uso posible | Requisito |
|---|---|---|---|
| Precio comparable | StayOffer/rate V2 | señal primaria o tie-break | mismo contexto y moneda |
| Distancia | coordenadas/destination | proximidad | coordenadas válidas |
| Categoría | HotelProperty | preferencia secundaria | null no es cero |
| Freshness | H05/H15 | confianza de dato | TTL y timestamp |
| Completitud | H10/H15 | elegibilidad/penalty | campos definidos |
| Provider quality | H06/H08/H20 | señal de fuente | contrato y evidencia |
| Ahorro | H14/H19/H24 | solo si baseline válido | no mezclar fechas |
| Tracking del usuario | ownership | acción/UI | nunca bonus de ranking global |

No se incluyen inicialmente:

- comisión o margen del partner como bonus oculto;
- popularidad sin contrato de producto;
- rating externo sin fuente y escala normalizada;
- click-through histórico sin consentimiento y revisión H50;
- preferencias sensibles o inferidas;
- `has_tracking` como ventaja para el hotel.

### 5.3. Fórmula y versión

H17 no congela pesos numéricos antes de tener fixtures y evidencia. La implementación debe definir una fórmula versionada, por ejemplo:

```text
hotel_ranking.v1 =
  price_component * w_price
  + distance_component * w_distance
  + category_component * w_category
  + freshness_component * w_freshness
  + completeness_component * w_completeness
```

Requisitos de la fórmula:

- pesos publicados en el contrato técnico, no escondidos en frontend;
- suma y normalización documentadas;
- valores faltantes tienen política explícita (`unknown`, penalty o no elegible);
- score no se calcula si el contexto es incomparable;
- cambiar pesos incrementa `ranking_version`;
- fixtures cubren resultados dominados, empates y missing data;
- se puede desactivar `recommended` y volver a orden estricto sin migración de datos.

## 6. Política de datos faltantes

### 6.1. Regla general

`null` significa desconocido. No es automáticamente:

- cero;
- peor valor;
- mejor oportunidad;
- agotado;
- provider fallido;
- precio gratuito.

Cada feature debe tener una política antes de entrar en un score.

### 6.2. Tabla de missing data

| Campo ausente | Orden estricto | Recommended | UI |
|---|---|---|---|
| Precio | al final en price; no excluye en distance/stars | no elegible para componente de precio o penalty explícita | sin precio comparable |
| Estrellas | al final en stars | no bonus; penalty solo si se decide y documenta | categoría no informada |
| Distancia | no elegible para distance | no score de proximidad | ubicación no calculable |
| Freshness | no afirmar live | estado unknown/penalty | fecha no disponible |
| Provider | conservar si hay observación local | no evaluar provider quality | fuente no informada |
| Cancelación/régimen/habitación | no alterar orden existente | no usar en score | condición no informada |
| Baseline | no ahorro | no savings signal | ahorro no disponible |

### 6.3. No reordenar en frontend

El frontend no puede completar missing data con defaults y reordenar. Debe consumir:

- `sort_applied`;
- `ranking_version`;
- `explanation`;
- `capabilities`;
- warnings y result state de H15.

Si V1 no entrega esos campos, el cliente mantiene el orden recibido y muestra solo copy compatible.

## 7. Explicaciones y copy

### 7.1. Códigos iniciales

```text
lowest_observed_price
nearest_to_destination
highest_known_category
best_comparable_signal
fresh_observation
complete_offer_context
partial_provider_signal
price_unavailable
unknown_category
stale_observation
not_ranked_missing_context
```

Los códigos deben ser allowlisted y tener traducción ES/EN. No se muestran nombres internos como `price_known desc`.

### 7.2. Explicación por tipo de orden

| Orden | Copy orientativo | Evidencia mínima |
|---|---|---|
| price | “Menor precio observado” | amount, currency, context |
| distance | “Más cerca de tu zona” | distance_km |
| stars | “Mayor categoría conocida” | stars |
| recommended | “Equilibrio entre precio, ubicación y señal” | ranking version + breakdown |
| savings | “Ahorro frente a [baseline]” | baseline válido y comparable |

El copy final pertenece a H34/i18n y debe evitar afirmar “mejor hotel” cuando solo se ha ordenado por una dimensión.

### 7.3. Explanations sin sobrepromesa

- “Más barato” significa menor precio observado dentro del contexto, no mejor precio final del partner.
- “Más cerca” significa menor distancia calculada, no mejor ubicación para todos los planes.
- “Recomendado” debe explicar al menos dos señales y permitir cambiar a orden estricto.
- “Ahorro” requiere baseline y ventana definidos.
- “Señal comparable” no significa disponibilidad garantizada.

## 8. Provider, freshness y paridad

### 8.1. Provider parcial

Un provider timeout, 429, vacío o fallback local no debe elevar un resultado por defecto. El ranking debe:

- marcar `partial`/warning según H15;
- distinguir observación local de provider fresco;
- evitar comparar cantidades de fuentes con condiciones distintas;
- aplicar la misma política a todos los hoteles;
- explicar si un resultado quedó fuera por falta de evidencia.

### 8.2. Freshness

Freshness puede ser señal de confianza, pero no debe convertirse silenciosamente en “mejor precio”. Requisitos:

- timestamp y TTL definidos por H05;
- edad comparable o normalizada;
- `stale` nunca recibe bonus de frescura;
- cached reciente no se llama live;
- si freshness es mixta, la explicación identifica la observación relevante.

### 8.3. Paridad

La paridad puede ayudar a mostrar una señal secundaria, pero no puede ser score de hotel sin:

- al menos dos providers comparables;
- mismo contexto de estancia;
- moneda y condiciones compatibles;
- spread y muestra válidos;
- explicación que no confunda “provider barato” con “hotel recomendado”.

`signalAssessment` del frontend no debe ser fuente de ranking; debe consumir la señal del backend cuando H15/H20 la publique.

## 9. Personalización y afiliación

### 9.1. Ordenes objetivos

`price`, `distance` y `stars` no pueden personalizarse. Una persona que cambia de usuario debe obtener el mismo orden si la query, datos y versión son iguales, salvo proyecciones de ownership que no alteren el sort.

### 9.2. Recommended personalizable

Una futura personalización debe:

- ser opt-in o estar documentada como preferencia;
- tener flag/versión independiente;
- no modificar los órdenes estrictos;
- explicar qué preferencia influyó;
- no inferir atributos sensibles;
- permitir reset y volver a criterio objetivo;
- pasar H35/H49/H50.

### 9.3. Afiliación

El partner o comisión no puede alterar el ranking sin una política visible y aprobación H35/H50. Opciones permitidas:

1. excluir comisión del ranking y ordenar por utilidad;
2. mostrar promoción separada, claramente etiquetada;
3. aplicar una política editorial declarada, con guardrails y explicación.

Nunca esconder un `affiliate_bonus` dentro de `recommended.v1`.

## 10. Paginación, caché y estabilidad

H15 depende de que el orden sea estable:

- cursor y snapshot token incluyen `sort`, filtros, query fingerprint y `ranking_version`;
- cambiar sort, filtros, provider policy o ranking invalida el cursor;
- `hotel_id` es el desempate final obligatorio;
- mismo snapshot + misma versión produce mismo orden;
- cambios de precios entre páginas requieren snapshot/consistencia declarada;
- cache keys incluyen contexto y versión de ranking;
- un resultado de otra moneda/estancia no puede contaminar el orden.

La ordenación debe ejecutarse antes de paginar. Nunca se pagina una lista en un orden y se reordena después en frontend.

## 11. Contrato V2 de metadata

H15 debe transportar como mínimo. Este payload es un ejemplo de **estado futuro**, solo válido cuando H17/H19/H20 hayan habilitado `recommended`:

```json
{
  "sort_applied": "recommended",
  "ranking": {
    "version": "hotel_ranking.v1",
    "personalized": false,
    "tie_breakers": ["price_known", "amount", "distance_km", "hotel_id"],
    "features": ["price", "distance", "stars", "freshness"],
    "explanation_available": true
  },
  "warnings": [],
  "capabilities": {
    "recommended": "supported",
    "explanations": "supported"
  }
}
```

Mientras `recommended` no esté habilitado, el estado debe ser equivalente a:

```json
{
  "sort_applied": "price",
  "capabilities": {
    "recommended": "unavailable",
    "explanations": "partial"
  },
  "warnings": [{"code": "recommended_not_available"}]
}
```

Para V1, el adaptador puede completar:

```text
sort_applied = query.sort
ranking.version = "hotel_sort.v1"
personalized = false
explanation_available = false
```

No debe inventar breakdown ni explanation para una lista que no los trae.

## 12. Tests y gates de aceptación

### 12.1. Orden estricto

- precio conocido antes que nulo;
- precio ascendente con misma moneda/contexto;
- distancia ascendente;
- estrellas conocidas antes que nulas;
- empates exactos terminan por `hotel_id`;
- nombres iguales y IDs distintos siguen orden estable;
- resultados sin precio no desaparecen al ordenar por distancia/estrellas;
- sort inválido devuelve error estable;
- el orden no cambia por `has_tracking` ni usuario.

### 12.2. Recommended

- no se activa sin capabilities y fields mínimos;
- fórmula/version/pesos quedan registrados;
- missing data no obtiene bonus accidental;
- provider parcial no gana por default;
- stale no recibe bonus de freshness;
- no usa comisión ni atributos sensibles;
- explanation coincide con features realmente usadas;
- empate por score usa tie-breakers contractuales;
- cambio de versión invalida cache/cursor;
- flag off vuelve a orden estricto.

### 12.3. API y frontend

- H15 serializa `sort_applied`, ranking metadata y explanation;
- V1 permanece compatible y el adaptador no inventa campos;
- card H16 muestra explicación solo cuando está respaldada;
- cambio de sort conserva filtros/contexto y reinicia paginación;
- back/forward restaura sort y cursor solo si el contexto coincide;
- warnings de ranking se anuncian sin duplicarlos por card;
- analytics registra sort y ranking version sin PII.

### 12.4. Seguridad y producto

- dos usuarios obtienen el mismo orden objetivo con los mismos datos;
- tracking/favorito no altera ranking;
- provider/affiliate no puede inyectar score o copy sin allowlist;
- no se exponen pesos secretos, tokens ni payloads externos;
- se puede auditar por qué un resultado quedó primero.

## 13. Observabilidad

Registrar:

- `hotel_sort_requested`;
- `hotel_sort_applied`;
- `hotel_ranking_version`;
- `hotel_ranking_missing_feature`;
- `hotel_ranking_explanation_shown`;
- `hotel_ranking_fallback_to_strict`;
- `hotel_ranking_tie_breaker_used`;
- `hotel_ranking_provider_partial`;
- `hotel_ranking_stale_data`;
- divergencia shadow V1/V2;
- latencia de ranking y porcentaje de resultados no elegibles.

No registrar querys completas, emails, tokens, coordenadas exactas ni datos de afiliación innecesarios.

## 14. Handoffs

- **H14:** conservar filtros y órdenes V1, semántica de precio nulo y política de no reordenar en frontend.
- **H15:** transportar ranking metadata, sort aplicado, explanations, capabilities, cursor y snapshot token.
- **H16:** mostrar explicación, missing data y badges sin inventar señales.
- **H18:** conservar sort, filtros, selección y retorno al detalle.
- **H19:** definir price basis, total/noches, fees y baseline.
- **H20:** convertir provider/parity en señales comparables antes de usarlas en recommended.
- **H21:** estados de ranking parcial, stale y fallback con acciones siguientes.
- **H31-H34:** jerarquía, copy ES/EN, accesibilidad y motion.
- **H35/H49/H50:** privacidad, personalización, afiliación y disclosure.
- **H37/H39:** coste, rendimiento, fixtures, contract tests y carga.
- **H41/H43:** métricas, flags, canary y rollback.

## 15. Gate H17

H17 podrá considerarse implementada cuando:

1. `price`, `distance` y `stars` tengan orden y desempates deterministas;
2. `hotel_id` forme parte del desempate final y H15 pueda paginar sin jitter;
3. `recommended` no sea un alias opaco de precio ni se active sin evidencia;
4. missing data, provider parcial, stale y paridad tengan política explícita;
5. cada ranking V2 incluya versión, features, capabilities y explicación respaldada;
6. el frontend no reordene ni invente scores;
7. personalización y afiliación estén separadas de los órdenes objetivos;
8. fixtures, contract tests, ownership, carga y rollback estén verificados;
9. producto pueda explicar por qué el primer resultado ocupa esa posición.
