# H19 — Precio total, noches, fees y transparencia de precio hotelero

**Estado:** contrato de precio y transparencia; implementación backend/frontend, migración V2, i18n, legal y QA pendientes  
**Fecha:** 2026-08-05  
**Área:** backend / producto / frontend / legal / QA  
**Fuente de verdad:** sí para la semántica de importe, noches, fees, moneda, comparabilidad y copy de precio en hoteles  
**Fase del roadmap:** H19  
**Depende de:** H05, H06, H10, H11, H15, H16, H17, H18  
**Relacionado con:** H20 comparación/paridad, H22 favoritos vs tracking, H23 creación de tracking, H24 histórico, H25 confidence, H26 alertas, H27 inbox, H28 delivery, H29 lifecycle, H35 legal/afiliación

> H19 evita que una cifra barata se convierta en una promesa falsa. Define qué importe se puede mostrar, qué unidad representa, qué cargos se conocen, qué comparaciones son válidas y qué debe explicarse antes de abrir un partner.

## 1. Decisión de alcance

H19 cierra el contrato de **precio contextualizado**. No implementa todavía tablas V2, nuevos adapters, componentes, CSS, delivery de alertas ni servicios externos.

El alcance obligatorio es:

1. total de estancia;
2. noches calculadas;
3. precio equivalente por noche, solo cuando sea válido;
4. impuestos, tasas, fees y cargos conocidos;
5. moneda solicitada frente a moneda observada/devuelta;
6. diferencia entre precio observado en Viru y precio final que pueda presentar el partner;
7. comparabilidad entre resultados y snapshots;
8. copy de transparencia, variación, limitaciones y siguiente acción;
9. reglas para que tracking y alertas no usen una observación no elegible.

El alcance **no** convierte H19 en la fase de lifecycle. La separación de producto queda así:

| Capa | Significado | Fase principal |
|---|---|---|
| Hotel guardado | Favorito simple, sin promesa de comprobación periódica | H22 |
| Oferta trackeada | Suscripción privada a hotel + estancia + condiciones | H23 |
| Histórico | Serie de snapshots comparables | H24 |
| Confidence/freshness | Lectura accionable de calidad y recencia | H25 |
| Regla de alerta | Condición evaluable sobre snapshots elegibles | H26 |
| Inbox | Señal persistente con ownership y deep link | H27 |
| Email/push | Delivery externo y preferencias de canal | H28 |
| Pausa/edición/expiración/borrado | Lifecycle de la suscripción | H29 |

H19 define las precondiciones de precio para esas fases; no declara ninguna de ellas implementada por el mero hecho de existir un modelo V1.

## 2. Estado actual comprobable

### 2.1. Campos que existen hoy

`HotelRateSnapshot` dispone actualmente de:

- `provider`;
- `provider_run_id`;
- `check_in` y `check_out`;
- `guests`;
- `room_label`;
- `meal_plan`;
- `cancellation_policy`;
- `currency`;
- `amount`;
- `availability_status`;
- `deep_link` nullable;
- `collected_at`.

`HotelTrackedOffer` dispone de `initial_price`, `current_price`, `target_price`, `currency`, fechas, huéspedes, habitación, régimen, cancelación, provider e `is_active`.

La tabla V1 permite fechas nulas y su unicidad puede no impedir duplicados cuando intervienen valores `NULL`; H11/H23 deben resolverlo de forma aditiva antes de usar una oferta incompleta como identidad fuerte.

Estos campos son una base V1, pero no demuestran por sí solos:

- si `amount` es base, total con impuestos o total parcial;
- si incluye resort fee, limpieza, servicio o impuestos locales;
- si dos habitaciones con el mismo `room_label` son la misma oferta;
- si el precio es reciente o reservable ahora;
- si un deeplink sigue siendo válido;
- si la moneda fue convertida o simplemente devuelta por el provider;
- si una observación es apta para una alerta.

### 2.2. Comportamiento actual que no se debe reinterpretar

Mientras H10/H11/H19 no se implementen:

- `amount` se conserva como importe legacy y no se renombra conceptualmente a “total final”;
- `guests` no se presenta como ocupación completa si no se conocen habitaciones, adultos y edades;
- `current_price` es una proyección de la última observación elegida por el sweep, no una garantía del partner;
- `initial_price` es el baseline de creación cuando existe, no necesariamente el mínimo histórico;
- `target_price` es un objetivo del usuario, no una predicción ni una oferta disponible;
- `availability_status=available` legacy no supera por sí solo el TTL de H05;
- `deep_link` nullable no autoriza una CTA externa sin allowlist y disclosure;
- un provider con error, timeout o respuesta inválida no equivale a `sold_out`;
- una lista vacía no prueba que no haya habitaciones disponibles.

## 3. Modelo conceptual de precio

### 3.1. Unidad de estancia

La unidad base de H19 es:

```text
StayPriceContext =
  destino/hotel canónico
  + check_in
  + check_out
  + número de noches
  + ocupación conocida
  + habitación
  + régimen
  + cancelación
  + moneda
  + semántica de fees
```

Una cifra solo puede compararse como total de estancia con otra observación si comparte el mismo contexto o existe una normalización explícita y auditable.

El `user_id` no forma parte de la identidad compartida del precio. Thresholds, labels, canales y preferencias privadas tampoco forman parte del fingerprint de una estancia.

### 3.2. Noches

Para fechas locales de hotel:

```text
nights = check_out - check_in
```

Invariantes:

- `check_out` debe ser posterior a `check_in`;
- las fechas se interpretan en la zona horaria del destino o en la zona definida por el contrato de estancia;
- una estancia de entrada el día 10 y salida el día 13 son 3 noches, no 4;
- no se muestra precio por noche si la cantidad de noches no es positiva y verificable;
- el cálculo de noches no sustituye a las reglas de ocupación del provider;
- si el provider devuelve un periodo diferente, la observación queda incompatible o parcial, no se ajusta silenciosamente.

El frontend puede mostrar “por noche” solo cuando:

1. el total representa todo el periodo solicitado;
2. `nights` es entero positivo;
3. la división está definida por el contrato de importe;
4. fees one-off y fees por noche están identificadas o se advierte que la división es orientativa;
5. moneda y contexto están presentes.

### 3.3. Precio total y precio por noche

H19 distingue tres valores:

```text
amount_base       importe base si el provider lo identifica
fees_known        cargos conocidos y su semántica
amount_total      total aplicable a toda la estancia cuando está demostrado
amount_per_night  amount_total / nights, solo como derivado
```

Reglas:

- `amount_total` no se fabrica sumando columnas con semántica incierta; no se inventa un total para completar una card;
- `amount_per_night` nunca es la fuente de verdad: se deriva y conserva el total de origen;
- si solo existe `amount_base`, la UI dice “precio observado” o “desde”, según corresponda, pero no “total final”;
- si existen fees parciales, el total puede ser `partial` y debe mostrar qué queda fuera;
- si el provider devuelve solo precio por noche, no se multiplica a total sin confirmar que la tarifa sea lineal y que los cargos no cambien por noche;
- redondear solo para presentación; las comparaciones usan una precisión y moneda definidas por backend;
- `0` no representa “desconocido”. Los valores ausentes permanecen `null`/`unknown`.

### 3.4. Fees y cargos

Cada cargo debe tener, cuando exista, estas dimensiones:

```text
fee_code              código canónico o unknown
label_raw              texto original sanitizado
amount                 importe
currency               moneda del cargo
scope                  per_stay | per_night | per_room | per_guest | percentage | unknown
status                 included | excluded | estimated | unknown | not_applicable
mandatory              true | false | unknown
source                 provider | derived | policy | unknown
```

Vocabulario mínimo de cargos:

- `tax` / impuestos;
- `resort_fee`;
- `cleaning_fee`;
- `service_fee`;
- `booking_fee`;
- `deposit` / depósito;
- `city_tax` / tasa local;
- `other`;
- `unknown`.

Reglas de honestidad:

- un fee ausente no se interpreta como incluido;
- un fee marcado como `unknown` no se convierte en cero;
- un cargo opcional no se suma al total obligatorio;
- un depósito reembolsable no se comunica como coste permanente sin explicarlo;
- `estimated` se muestra como estimación, nunca como precio confirmado;
- `included` significa que el provider lo declaró incluido en el importe correspondiente, no que Viru lo haya verificado independientemente;
- si el provider solo entrega un texto libre, conservarlo como raw y marcar completitud parcial;
- si el mismo cargo aparece en base y total, no sumarlo dos veces;
- no deducir “sin tasas” porque el payload no contenga un campo de fees.

### 3.5. Moneda

Se distinguen:

```text
requested_currency       moneda solicitada por la búsqueda
observed_currency        moneda del importe recibido
display_currency         moneda usada para mostrar, si hay conversión válida
conversion_rate_source   fuente/versionado de conversión, si aplica
currency_status          same | converted | unavailable | unknown
```

Reglas:

- ISO-4217 en mayúsculas;
- si `requested_currency != observed_currency`, conservar ambas;
- no convertir en frontend con una tasa implícita;
- una conversión no autoriza afirmar que el partner cobrará en `display_currency`;
- si no hay tasa válida o timestamp de conversión, no comparar importes convertidos como si fueran exactos;
- alertas de importe absoluto solo comparan la misma moneda o una conversión versionada aceptada por el contrato;
- porcentajes pueden ser comparables solo si baseline y nueva observación tienen semántica y moneda compatibles.

## 4. Comparabilidad

### 4.1. Clave mínima V1

Mientras H10/H11 no estén migradas, una comparación legacy exige como mínimo:

```text
hotel_id canónico
check_in
check_out
guests
currency
```

Pero esa clave se marca `legacy_comparison` porque no demuestra:

- número de habitaciones;
- adultos frente a niños;
- habitación equivalente;
- régimen equivalente;
- cancelación equivalente;
- fees y semántica de total.

### 4.2. Clave objetivo H10/H19

La comparación total futura debe usar una identidad equivalente a:

```text
comparability_key = hash(
  canonical_hotel_id
  + check_in + check_out + nights
  + canonical_occupancy
  + room_signature
  + meal_plan_normalized
  + cancellation_signature
  + currency_or_conversion_context
  + fee_semantics
)
```

La clave no incluye `user_id`, regla, canal, label ni timestamps.

Dos observaciones pueden agruparse como relacionadas, pero no como “misma oferta”, si alguna dimensión crítica está `unknown`. La UI debe preferir:

- “otras tarifas observadas” para datos relacionados;
- “comparables” solo para datos con condiciones suficientes;
- “no comparable” cuando la diferencia pueda cambiar la decisión.

### 4.3. Elegibilidad para ranking

Antes de ordenar por total o ahorro:

1. estancia y ocupación compatibles;
2. moneda/convertibilidad compatible;
3. semántica de importe compatible;
4. fees obligatorias conocidas o limitación visible;
5. availability no negativa ni error;
6. freshness H05 elegible para el contexto;
7. condiciones de habitación/régimen/cancelación comparables;
8. provider y observación trazables.

Un precio bajo con fees desconocidas puede aparecer como oportunidad parcial, pero no como “total más barato” frente a un total completo sin explicación.

## 5. Precio observado frente a precio final del partner

### 5.1. Precio observado

Es el importe que Viru recibió y persistió asociado a un provider run o snapshot. Debe conservar:

- provider;
- `provider_run_id`;
- `collected_at` y, cuando exista, `observed_at`;
- estancia y ocupación;
- importe y moneda;
- condiciones conocidas;
- estado de disponibilidad;
- freshness/provenance/confidence;
- warnings y completitud.

Copy válido, adaptado por i18n:

- “Precio observado”;
- “Última comprobación …”;
- “Comprobado con [provider]”;
- “Impuestos/tasas no informados”;
- “Puede cambiar al abrir el partner”.

### 5.2. Precio final del partner

Solo se puede llamar así cuando el producto tenga evidencia contractual de que el partner devolvió el total final para el mismo contexto. Incluso entonces, debe aclararse que:

- disponibilidad puede cambiar;
- la reserva se completa fuera de Viru;
- las condiciones del partner prevalecen en el momento de reservar;
- el usuario puede ver diferencias por impuestos locales, moneda, login, disponibilidad o cambios de sesión.

Si no existe esa evidencia, usar “precio observado en Viru” o “desde”, nunca “precio final garantizado”.

### 5.3. Deeplink y disclosure

Antes de abrir un partner, el usuario debe poder entender:

1. qué estancia se está enviando;
2. qué precio observó Viru;
3. qué cargos se conocen y cuáles no;
4. cuándo se comprobó;
5. que el partner puede cambiar disponibilidad/precio;
6. si existe afiliación;
7. qué ocurrirá al salir de Viru.

Un `deep_link` nulo, expirado, no allowlisted o incompatible no genera CTA externa. No se deben copiar URLs arbitrarias del provider a hrefs sin validación, sanitización y política H35.

## 6. Reglas para tracking y alertas

Estas reglas son **precondiciones de H19** y no sustituyen las fases operativas H22-H29.

### 6.1. Qué puede actualizar `current_price`

Una observación solo puede proyectarse a `HotelTrackedOffer.current_price` si:

- pertenece a la misma estancia/ocupación y al mismo contexto de oferta;
- la moneda es compatible;
- el outcome es válido;
- no es `provider_error`, `timeout`, `rate_limited`, replay no elegible o fixture de producto;
- la freshness y conditions completeness alcanzan el mínimo de tracking;
- el provider no ha cambiado silenciosamente respecto a la identidad seguida;
- existe trazabilidad al snapshot y provider run.

Si no se cumplen las condiciones:

- conservar el último precio elegible;
- actualizar el estado de salud/frescura del tracking cuando exista ese campo;
- registrar razón `not_evaluable`, `provider_error`, `incompatible_conditions` o equivalente;
- no presentar una falsa subida, bajada o disponibilidad recuperada.

### 6.2. Baselines

- `initial_price` es baseline de creación y conserva su contexto;
- `snapshot_previous` compara contra la última observación elegible, no contra cualquier fila insertada;
- mínimo histórico solo se calcula con snapshots comparables y retenidos;
- cambio de provider genera una transición de procedencia, no necesariamente una bajada/subida de la misma oferta;
- cambio de fechas, ocupación, habitación, régimen o cancelación crea nueva identidad o invalida el baseline; no muta el historial silenciosamente;
- porcentajes se calculan desde importes no nulos, positivos, comparables y con redondeo definido.

### 6.3. Eventos y ownership

El evento de precio debe conservar una referencia inequívoca a:

```text
user/subscription owner
tracked_offer_id o rule_id
snapshot_before
snapshot_after
comparability_key/version
provider_run_id
reason
old/new amount y currency
fee/completeness status
created_at
```

El actual `HotelAlertEvent` puede existir sin `rule_id` en algunos caminos del sweep. Eso es un gap de seguridad/producto: antes de ampliar alertas, H26/H27 deben impedir que una señal de un seguimiento privado se resuelva únicamente por `hotel_id` y termine visible a otra persona que sigue el mismo hotel.

La bandeja actual ya comprueba ownership por regla o por oferta del mismo hotel; H19 deja claro que esa heurística no sustituye una referencia de suscripción/evento inequívoca para nuevas señales.

## 7. Contrato de API objetivo

La evolución debe ser aditiva. Un envelope V2 de precio puede adoptar esta forma:

```json
{
  "price": {
    "amount_observed": 420.0,
    "currency_observed": "EUR",
    "amount_total": null,
    "amount_per_night": null,
    "semantics": "unknown",
    "nights": 3,
    "currency_status": "same"
  },
  "fees": {
    "status": "partial",
    "items": [
      {
        "code": "city_tax",
        "amount": null,
        "currency": "EUR",
        "scope": "per_guest",
        "status": "unknown",
        "mandatory": "unknown",
        "source": "provider"
      }
    ],
    "unknown_items": ["city_tax"]
  },
  "stay_context": {
    "check_in": "2026-09-10",
    "check_out": "2026-09-13",
    "nights": 3,
    "occupancy_source": "legacy_inferred"
  },
  "comparability": {
    "key": "opaque-key",
    "status": "partial",
    "reasons": ["room_unknown", "fees_unknown"]
  },
  "observation": {
    "provider": "makcorps",
    "provider_run_id": "opaque-run",
    "observed_at": "2026-08-05T10:00:00Z",
    "freshness_status": "recent",
    "provenance_kind": "provider_observed",
    "confidence_level": "medium"
  },
  "partner": {
    "price_is_final": false,
    "deeplink_status": "pending_validation",
    "disclosure_required": true
  }
}
```

Reglas de compatibilidad:

- mantener `amount`, `currency`, `collected_at`, `provider`, `provider_run_id` y `availability_status` mientras existan clientes V1;
- no rellenar `amount_total` con `amount` sin una `price_semantics` explícita;
- no serializar `0` como fee desconocida;
- si el bloque V2 falta, el cliente cae a `unknown/partial`, nunca a “total” o “fresh”;
- `HotelTrackedOfferOut.user_id` sigue siendo privado y no debe exponerse en tarjetas, links públicos ni payloads de partner;
- los nombres de provider y textos raw deben sanearse antes de UI;
- los IDs opacos no conceden acceso: cada endpoint sigue validando ownership.

## 8. Migración y backfill

### H19-A — Normalizadores puros

Crear, sin cambiar todavía persistencia:

- cálculo de noches;
- normalización ISO de moneda;
- clasificación de semántica `base/total/unknown`;
- clasificación de fees y scope;
- comparability key/version;
- cálculo de precio por noche;
- elegibilidad para ranking/tracking/alerta;
- copy model independiente del idioma.

Todos deben ser deterministas y tener tests de límites.

### H19-B — Bridge V1 → V2

- `amount` legacy entra como `amount_observed`;
- `price_semantics=unknown` salvo evidencia del provider;
- `check_in/check_out` producen `nights` si son válidos;
- `guests` se marca `occupancy_source=legacy_inferred`;
- fees ausentes quedan `unknown`, no `included`;
- `deep_link` entra como pendiente de validación, no como CTA aprobada;
- provider `mock` conserva `fixture_demo` en superficies de producto.

### H19-C — Backfill seguro

- añadir campos nuevos como nullable/versionados;
- backfill por lotes, reanudable e idempotente;
- no reescribir históricos para hacerlos parecer totales;
- conservar `legacy_amount`, `legacy_currency` y la versión de política aplicada;
- marcar `needs_review` cuando la semántica del provider no sea demostrable;
- no emitir alertas retroactivas por el mero hecho de recalcular fees/comparabilidad;
- preparar rollback y reconciliación de conteos.

### H19-D — Doble lectura

Durante la transición:

1. leer V2 si es válida;
2. caer a V1 con warning interno y copy parcial;
3. comparar V1/V2 en sombra;
4. medir divergencia de total, noches, fees y elegibilidad;
5. bloquear promoción si V2 convierte desconocido en incluido o cambia el orden de forma no explicada.

## 9. Frontend y copy

### 9.1. Card y detalle

La jerarquía recomendada es:

1. total de estancia, si existe;
2. precio por noche como derivado secundario;
3. fechas/noches/ocupación resumidas;
4. fees incluidas/excluidas/desconocidas;
5. provider y última comprobación;
6. estado de comparabilidad/freshness;
7. acción “Revisar en partner” solo si el deeplink está aprobado;
8. acción “Guardar hotel” o “Seguir precio” según la entidad y H22/H23.

No usar “desde” si el importe no identifica qué estancia/condición lo produce. Si el catálogo no tiene una oferta comparable, mostrar identidad del hotel y CTA de completar contexto, no una cifra inventada.

### 9.2. Estados mínimos

| Estado técnico | Copy de producto orientativo | Acción |
|---|---|---|
| `complete` | “Total de la estancia” | revisar/seguir si elegible |
| `partial` | “Precio observado; faltan algunas tasas o condiciones” | revisar detalles |
| `unknown` | “No podemos confirmar el total con este dato” | buscar/reintentar |
| `stale` | “Este precio puede haber cambiado” | revalidar |
| `provider_error` | “El proveedor no respondió; no significa agotado” | reintentar más tarde |
| `fixture_demo` | “Datos de demostración” | ninguna CTA de reserva real |
| `converted` | “Mostrado aproximadamente en {moneda}; el partner puede cobrar en otra moneda” | revisar disclosure |
| `not_comparable` | “No comparable: cambian las condiciones” | ver condiciones |

Los textos deben existir en ES y EN, usar locale para números/fechas y no depender solo del color.

### 9.3. Accesibilidad

- el lector de pantalla debe recibir total, noches, moneda y limitaciones en el mismo contexto;
- fees desconocidas no pueden aparecer solo como icono;
- el detalle debe anunciar cuándo una tarifa es parcial o stale;
- `aria-describedby` enlaza la nota de precio con la CTA externa;
- cambios de precio en tracking se anuncian de forma no intrusiva y respetan reduced motion;
- las tablas de fees tienen encabezados y relación clara entre importe, alcance e inclusión.

## 10. Legal, afiliación y privacidad

Antes del gate H19/H35:

- no llamar “garantizado”, “final” o “reservable” a un precio no respaldado;
- explicar que impuestos/tasas pueden depender del partner y destino;
- mostrar variación posible al salir de Viru;
- mostrar afiliación donde corresponda, sin alterar silenciosamente el ranking;
- no enviar thresholds, labels, historial privado ni `user_id` al partner;
- no incluir raw payloads en logs, analytics o errores de cliente;
- conservar solo los datos necesarios para tracking y soporte según retención aprobada;
- no construir un redirect con URL arbitraria del provider;
- si el usuario no acepta un canal externo, mantener la señal in-app cuando esté disponible.

## 11. Tests y evidencias

### Unitarios

- fechas límite y noches correctas;
- salida igual/anterior a entrada rechazada;
- total, base y por noche sin doble suma;
- fee por estancia/noche/habitación/huésped y scope desconocido;
- `null` no convertido en cero;
- monedas iguales, convertidas, inválidas y desconocidas;
- comparability key estable y sensible a cambios relevantes;
- habitación/régimen/cancelación distintos no marcados como equivalentes;
- provider error no marcado `sold_out` ni elegible;
- fixture nunca presentado como live/total final;
- baseline inicial/anterior y cambio de provider;
- `current_price` no actualizado con snapshot incompatible;
- porcentajes, redondeos y valores cero/negativos.

### Integración backend

- `HotelRateSnapshot` conserva provider run y timestamp;
- endpoint V1 sigue serializando sin romper clientes;
- envelope V2 no filtra ownership ni raw payload;
- tracked offer rechaza o marca explícitamente fechas/precio insuficientes;
- sweep no crea una bajada por error del provider;
- eventos nuevos tienen owner inequívoco y snapshot de origen;
- inbox no muestra una señal privada a otro usuario que sigue el mismo hotel;
- account deletion limpia tracking, alertas, eventos y read state sin huérfanos;
- migración/backfill es reanudable, idempotente y reversible.

### Frontend

- total y por noche se distinguen visualmente y semánticamente;
- fees incluidas, excluidas, estimadas y desconocidas tienen copy diferente;
- moneda observada y moneda mostrada no se confunden;
- card, detalle, tracking e inbox comparten la misma semántica;
- deeplink ausente/inválido no produce CTA rota;
- ES/EN, dark/light, mobile, teclado y lector de pantalla cubren los estados;
- no aparece “precio final”, “live” o “disponible ahora” sin evidencia.

### QA de producto y legal

- casos con hotel urbano, resort fee, limpieza, city tax y depósito;
- total completo, total parcial, solo precio base y sin precio;
- provider único, varios providers comparables y providers incompatibles;
- cambio de moneda y partner con precio diferente;
- captura de screenshot y revisión manual de disclosure antes del deeplink;
- aprobación explícita de copy legal y límites de afiliación.

## 12. Observabilidad y operación

Métricas mínimas:

```text
hotel_price_semantics_unknown_total
hotel_fee_completeness_ratio
hotel_total_price_comparability_ratio
hotel_currency_conversion_unknown_total
hotel_snapshot_ineligible_for_tracking_total
hotel_provider_error_not_evaluable_total
hotel_price_delta_suppressed_total
hotel_deeplink_blocked_by_validation_total
hotel_price_v1_v2_divergence_total
```

Logs estructurados deben incluir provider, provider run, policy version, outcome y reason code, sin email, thresholds, user IDs innecesarios, URLs completas ni raw payload.

El dashboard debe separar:

- “no hay precio”;
- “hay precio pero fees desconocidas”;
- “provider falló”;
- “precio stale”;
- “no comparable”;
- “deeplink bloqueado”.

Un run completado no significa que todos sus precios sean totales comparables.

## 13. Gate H19

H19 puede marcarse completa cuando:

- backend y frontend comparten semántica de total, noches y fees;
- ninguna capa llama total/final/live a un dato desconocido, parcial o viejo;
- el precio por noche se deriva solo de una estancia válida;
- moneda observada, solicitada y convertida están diferenciadas;
- comparabilidad incorpora condiciones y semántica de fees;
- V1 sigue funcionando mediante bridge sin reinterpretación optimista;
- snapshots incompatibles no actualizan tracking ni disparan alertas falsas;
- eventos nuevos tienen ownership inequívoco;
- card, detalle, tracking, inbox y partner disclosure cuentan la misma historia;
- ES/EN, accesibilidad y estados degradados están cubiertos;
- migración, observabilidad, rollback y tests están aprobados por backend/DB/QA/producto/legal.

**Resultado contractual:** H19 queda definido. La implementación de precio V2, la consolidación de tracking/alertas y el delivery externo siguen bloqueados en sus fases propias H22–H29 y no deben declararse terminados por cerrar este documento.

## 14. Handoff

| Próxima fase | Handoff de H19 |
|---|---|
| H20 | comparar providers solo con `comparability.status=complete` o disclosure parcial explícito |
| H22 | mantener “Guardar hotel” separado de “Seguir precio” |
| H23 | crear tracking desde una oferta con contexto, baseline y semántica de importe |
| H24 | construir histórico solo con snapshots comparables y clasificar gaps |
| H25 | mostrar freshness/confidence sin convertirlo en promesa |
| H26 | aplicar baseline, elegibilidad, cooldown y dedupe por suscripción/regla |
| H27 | deep link a hotel/tracking/snapshot con ownership inequívoco |
| H28 | delivery de canales con consentimiento, retry e idempotencia |
| H29 | pausa, edición, expiración y borrado sin destruir histórico válido |
| H35 | validar disclosure, afiliación, retención, consentimiento y redirects |
| H41 | instrumentar divergencia de semántica, provider y delivery |

**No se declara H19 implementada hasta que la evidencia confirme el contrato en código y en UI real.**