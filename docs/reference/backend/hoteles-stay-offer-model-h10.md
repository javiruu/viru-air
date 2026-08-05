# H10 — Modelo canónico de estancia, ocupación, oferta y matching hotelero

**Estado:** completa como contrato de dominio; implementación y migración pendientes  
**Fecha:** 2026-08-04  
**Área:** backend / DB / dominio / API / providers  
**Fuente de verdad:** sí para la semántica de una estancia, una oferta comparable, un snapshot y el matching entre identidad interna y externa.

**Depende de:** [H05 — freshness, procedencia y confidence](hoteles-freshness-provenance-confidence-h05.md), [H06 — contrato provider-neutral](hoteles-provider-neutral-contract-h06.md), [H07 — auditoría Makcorps](hoteles-makcorps-audit-h07.md), [H08 — onboarding de providers](hoteles-provider-onboarding-h08.md), [H09 — gateway y sweeps](hoteles-sweep-gateway-h09.md)  
**Relacionado con:** H11 migración de datos, H12 contratos API, H15 resultados, H19 fees, H20 habitaciones/régimen, H23 tracking, H26 dedupe de alertas, H35 deeplinks, H37 coste/rendimiento, H41 observabilidad y frontend de `/hoteles`.

---

## 1. Propósito y decisión de fase

H10 define qué significa exactamente “seguir un hotel” o “comparar una tarifa” en Viru. El objetivo es impedir que una cifra aislada se trate como una oferta comparable cuando cambian las fechas, la ocupación, la habitación, el régimen, la cancelación, los fees o la freshness.

La fase produce un modelo conceptual y una migración compatible. **No cambia todavía las tablas, no rompe los endpoints actuales y no habilita providers externos.**

### Decisión H10

**Adoptar una consulta canónica de estancia compartible y anónima, separada de las suscripciones privadas del usuario.**

- `StayQuery` representa los parámetros que determinan qué se está buscando.
- `HotelProperty` representa la propiedad canónica de Viru.
- `HotelProviderAlias` relaciona la propiedad interna con un `provider_hotel_id` externo.
- `HotelOffer`/oferta canónica representará una combinación comparable de estancia, habitación, régimen y condiciones.
- `HotelRateSnapshot` representa una observación temporal de una oferta, no la oferta eterna.
- `HotelTrackedOffer` seguirá siendo una suscripción/target privado del usuario durante la migración.
- Los resultados compartidos no deben incluir `user_id`, email, alertas privadas ni datos de ownership.

Esto permite que H09 dedupe llamadas equivalentes sin mezclar la configuración privada de dos usuarios.

---

## 2. Estado actual y límites que H10 corrige

| Área | Estado V1 comprobable | Riesgo |
|---|---|---|
| estancia | `check_in`, `check_out` y `guests` escalar | no representa habitaciones, adultos, niños ni edades |
| tracked offer | `user_id + hotel_id + fechas + guests + provider` | una suscripción privada se usa como identidad de consulta |
| rate snapshot | precio, moneda, labels y políticas como columnas planas | no hay fingerprint de comparabilidad ni completitud de fees |
| identidad externa | `HotelProviderAlias(provider, provider_hotel_id)` | el caller puede confundir `HotelProperty.id` con ID externo, como detectó H07 |
| habitación | `room_label` libre | variaciones textuales crean duplicados o falsos cambios |
| régimen | `meal_plan` libre | no hay vocabulario común para comparar RO/BB/HB/FB/AI |
| cancelación | texto libre | no distingue reembolsable, penalización, fecha límite o desconocido |
| disponibilidad | `availability_status` básico | no separa provider error, sold out, unknown y ausencia de observación |
| fees | `amount` y parseo dependiente del provider | no se sabe si es base, total o doblemente sumado |
| deeplink | string nullable en snapshot | no tiene objeto validado, allowlist ni relación segura con oferta |
| parity | agrupa por fechas, `guests` y moneda | puede comparar habitaciones/régimen/condiciones incompatibles |
| freshness | `collected_at` del snapshot | falta estado de elegibilidad y explicación de fallback/replay |

### Regla de honestidad

Mientras H10–H11 no estén implementadas, los campos legacy pueden seguir funcionando para compatibilidad, pero no deben recibir semántica nueva por inferencia. En particular:

- `guests=2` no significa necesariamente “2 adultos en 1 habitación” si el origen no lo demuestra;
- `amount` no significa “precio total” si fees/taxes son desconocidos;
- `room_label` igual no significa misma habitación;
- `availability_status=available` legacy no prueba disponibilidad actual si el snapshot es viejo;
- `tracked_offer_id` no es una identidad global de oferta.

---

## 3. Vocabulario canónico

### 3.1. `HotelProperty`

Identidad canónica de una propiedad dentro de Viru:

```text
canonical_hotel_id       ID interno estable de HotelProperty
canonical_name           nombre normalizado de producto
city/country_code        ubicación canónica
coordinates              opcionales y validadas
matching_confidence      confianza del mapping
```

No contiene precio, fechas, ocupación ni provider. Una propiedad puede tener varios aliases de provider.

### 3.2. `HotelProviderAlias`

Relación entre la propiedad canónica y un origen externo:

```text
provider_id
provider_hotel_id       opaco, no reutilizar como ID interno
canonical_hotel_id
mapping_status           confirmed | ambiguous | rejected | pending
confidence_score
observed_name/address
source_metadata          redacted/interno
first_seen_at
last_seen_at
```

La unicidad mínima es `(provider_id, provider_hotel_id)`. Un ID externo no se puede asignar a otro hotel sin revisión de mapping. Si el mapping es `ambiguous` o `pending`, no se llama a revalidación dirigida.

### 3.3. `StayQuery`

Consulta canónica que determina la estancia y su ocupación:

```text
canonical_hotel_id       nullable para area search; obligatorio para hotel search
provider_hotel_id        nullable hasta resolver alias
area                     destino/radio/coordenadas, si aplica
check_in                 fecha local de entrada
check_out                fecha local de salida
occupancy                estructura canónica
currency                 ISO-4217 solicitada
room_preferences         opcional y explícita
meal_preferences         opcional y explícita
cancellation_preferences opcional y explícita
```

Una `StayQuery` no contiene `user_id`, API keys, emails ni preferencias privadas que no cambien el precio/resultado. El usuario se enlaza mediante una suscripción separada.

### 3.4. Ocupación canónica

La forma objetivo es:

```json
{
  "rooms": [
    {
      "adults": 2,
      "children_ages": []
    }
  ]
}
```

Invariantes:

- al menos una habitación;
- cada habitación tiene al menos un adulto;
- `children_ages` contiene edades enteras dentro del rango de negocio aprobado;
- la cantidad de niños se deriva de la lista, no se duplica como campo independiente;
- no se inventan edades desconocidas;
- el total de adultos/niños se calcula, no se acepta como una cifra independiente sin reconciliar;
- rooms, adultos y edades forman parte del fingerprint;
- si un provider no soporta una dimensión, el resultado se marca `unsupported`/`partial`, no se normaliza silenciosamente a 1 habitación.

Compatibilidad V1:

```text
guest_count legacy -> 1 room con adults=guest_count, children_ages=[]
```

Esta transformación es válida solo como **suposición de migración etiquetada**, no como evidencia histórica de la ocupación real. El sistema debe conservar `occupancy_source=legacy_inferred` hasta que el usuario confirme o una fuente fiable lo sustituya.

### 3.5. Habitación

```text
room_id                  ID externo opaco, si existe
room_label_raw           texto original limitado y sanitizado
room_type_normalized     standard | superior | deluxe | suite | apartment | other | unknown
beds_normalized          vocabulario opcional
room_count               número de habitaciones cubiertas
```

`room_label_raw` es descriptivo; no es una clave de dedupe. Para comparar se usa `room_id` cuando el provider lo garantiza y, en su ausencia, un `room_signature` normalizado con confianza y fuente.

### 3.6. Régimen

Vocabulario canónico mínimo:

```text
RO       room only
BB       breakfast included
HB       half board
FB       full board
AI       all inclusive
UNKNOWN  no demostrado
```

El texto original se conserva en `meal_plan_raw`. Nunca transformar un texto ambiguo a `BB` o `RO` por defecto optimista.

### 3.7. Cancelación

La política canónica debe separar:

```text
cancellation_type       refundable | non_refundable | partially_refundable | unknown
free_until              timestamp local del destino, nullable
penalty_amount          importe nullable
penalty_currency        ISO-4217 nullable
policy_text_raw         texto sanitizado, interno/limitado
conditions_completeness complete | partial | unknown
```

Dos ofertas no son comparables como “misma condición” si una es reembolsable y otra no, aunque tengan el mismo importe.

---

## 4. Oferta canónica y snapshot

### 4.1. `HotelOffer`

La oferta canónica es la combinación estable de una estancia concreta y sus condiciones conocidas:

```text
offer_id                 ID interno o fingerprint estable
provider_id
provider_offer_id        opaco, nullable
canonical_hotel_id
stay_query_fingerprint
room_signature
meal_plan_normalized
cancellation_signature
fee_semantics
currency
conditions_completeness
availability_capability
```

Una oferta no debe guardar `user_id`. Usuarios y alertas apuntan a la oferta/query mediante suscripciones.

### 4.2. `HotelRateSnapshot`

El snapshot es una observación en un momento determinado:

```text
snapshot_id
offer_id / offer_fingerprint
provider_run_id
observed_at
freshness_state
amount_base
fees_amount
fees_currency
amount_total
currency
price_semantics          base | total | unknown
availability_status      available | sold_out | limited | unknown | provider_error
room/meal/cancellation
provider_request_id      sanitizado
outcome                  success | empty | partial | ...
deep_link                objeto validado o null
provenance/confidence
```

Reglas de importe:

- `amount_total` solo existe cuando el contrato demuestra qué incluye;
- no sumar `tax` a `Totalprice` sin una prueba de semántica del provider;
- un importe desconocido no se convierte en cero;
- un snapshot con precio pero fees desconocidos puede mostrarse como parcial, pero no gana un ranking de “total más barato” sin disclosure;
- moneda solicitada y moneda devuelta deben conservarse por separado si difieren.

### 4.3. Estado de disponibilidad

Vocabulario mínimo:

```text
available
sold_out
limited
unknown
provider_error
not_checked
```

`provider_error`, `timeout`, `rate_limited` y `unavailable` son resultados de ejecución; no equivalen a `sold_out`. Un snapshot de error no debe actualizar `current_price` ni disparar `availability_returned`.

### 4.4. Deeplink

El objeto sigue H06/H35:

```text
url
provider_id
partner_id
allowlist_status
expires_at
tracking_context_id
```

Hasta H35, el campo público permanece `null` si no existe validación. Un deeplink no convierte un snapshot en reserva ni confirma precio/disponibilidad.

---

## 5. Fingerprints e identidad de comparabilidad

### 5.1. `stay_query_fingerprint`

Incluye únicamente dimensiones que cambian la consulta:

```text
hash(
  operation + canonical_hotel_id/area +
  check_in + check_out + canonical_occupancy + currency +
  normalized_room_preferences + normalized_meal_preferences +
  normalized_cancellation_preferences
)
```

No incluye `user_id`, alert rule ID, email ni timestamp.

### 5.2. `offer_fingerprint`

Incluye además las dimensiones de la oferta devuelta:

```text
hash(
  provider_id + provider_hotel_id +
  stay_query_fingerprint + provider_offer_id/room_signature +
  meal_plan_normalized + cancellation_signature + fee_semantics + currency
)
```

Si una dimensión relevante es `unknown`, el fingerprint puede existir para dedupe técnico, pero la oferta queda `conditions_completeness=unknown` y no se compara como equivalente a una completa.

### 5.3. `snapshot_dedupe_key`

El dedupe de persistencia debe distinguir una nueva observación de un duplicado de ingestión:

```text
offer_fingerprint + provider_run_id + observed_at_bucket + normalized_amount + outcome
```

La granularidad exacta de `observed_at_bucket` la fijará H11 según la frecuencia y la necesidad de conservar cambios. No usar el importe como única identidad.

---

## 6. Matching y separación de identidades

### Flujo obligatorio

```text
provider_hotel_id externo
        ↓ alias resolver
canonical_hotel_id interno
        ↓ StayQuery
offer/rate snapshot
        ↓ user subscription
HotelTrackedOffer / alert rule
```

Reglas:

1. El adapter recibe `provider_hotel_id` cuando lo requiere el provider.
2. El dominio usa `canonical_hotel_id` para ownership, API y UI.
3. Los snapshots conservan ambos cuando estén disponibles.
4. Un `hotel_id` interno nunca se envía directamente a un endpoint externo sin resolver alias.
5. Un alias ambiguo no se usa para tracking automático.
6. El matching de hotel no implica matching de habitación ni de oferta.
7. Cambiar de provider cambia la identidad de origen; no se mezclan rates solo porque apunten al mismo hotel.
8. Un provider puede tener múltiples ofertas para una misma estancia; la UI no debe colapsarlas si cambian condiciones.

### Matching de propiedades

La decisión de mapear una propiedad debe usar nombre, dirección, ciudad, país, coordenadas y evidencia del provider. `confidence_score` es señal de matching, no de precio ni freshness. Si la confianza baja o hay candidatos cercanos, el estado es `ambiguous`.

### Matching de ofertas

Dos snapshots son comparables solo si coinciden o están explícitamente normalizados en:

```text
canonical_hotel_id
check_in/check_out
rooms + adults + children_ages
currency y semántica de conversión
room_signature
meal_plan_normalized
cancellation_signature
fee_semantics
availability semantics
```

Si faltan condiciones, pueden agruparse como “relacionadas” pero no como “misma oferta”.

---

## 7. `HotelTrackedOffer` como suscripción privada

Durante la transición, la tabla actual continúa existiendo:

```text
user_id
hotel_id
check_in/check_out
legacy guests
provider
legacy room/meal/cancellation
initial/current/target price
is_active
```

H10 propone que conceptualmente represente:

```text
subscription_id
user_id
stay_query_fingerprint
canonical_hotel_id
provider_scope o provider_id
alert preferences
created/updated/active
```

### Reglas de ownership

- `user_id` nunca entra en el fingerprint compartido.
- El usuario solo puede leer/modificar sus suscripciones y alertas.
- El cache compartido no devuelve datos privados.
- Dos usuarios pueden suscribirse a una misma `StayQuery` sin compartir thresholds, labels o canales de notificación.
- `current_price` en la suscripción es una proyección conveniente; la fuente de verdad histórica son snapshots elegibles.
- Cambiar fechas, ocupación o condiciones debe crear una nueva identidad de consulta o invalidar/recalcular la anterior; no mutar silenciosamente el historial.

### Providers en tracking

- `provider="mock"` puede quedar como legacy/fixture.
- Un provider concreto debe aparecer en la query solo si el usuario lo eligió o la política de producto lo declara.
- `provider_scope=any_eligible` es distinto de `provider_scope=makcorps`.
- Cambiar provider no debe producir un falso “price change” de la misma oferta; se registra `provider_changed` separado.

---

## 8. Parity, ranking y alertas

### 8.1. Parity actual

El servicio actual agrupa por `(check_in, check_out, guests, currency)`. Esto es insuficiente para afirmar paridad cuando las habitaciones, régimen, cancelación o fees difieren.

Durante la transición:

- mantener el endpoint actual para compatibilidad;
- etiquetar la señal como `legacy_comparison` cuando falten dimensiones;
- no mostrar “misma tarifa” si room/meal/cancelación son desconocidos;
- H11/H19 deben migrar el agrupamiento a `offer_comparability_key`.

### 8.2. Ranking

Orden mínimo de elegibilidad:

1. estancia exacta;
2. ocupación exacta;
3. moneda y semántica de importe compatibles;
4. freshness H05 dentro del TTL;
5. condiciones completas;
6. habitación/régimen/cancelación equivalentes;
7. precio total comparable;
8. confidence de matching;
9. calidad del deeplink si está aprobado.

Precio menor con fees desconocidos no puede ganar a precio total conocido sin una etiqueta visible.

### 8.3. Alertas

Una alerta de bajada solo se evalúa si:

- snapshot nuevo y baseline son comparables;
- ambos tienen moneda/semántica compatibles;
- el provider outcome es válido;
- freshness cumple H05;
- el importe no es una proyección de error, cache no elegible o replay excluido;
- el dedupe H26 no emitió el mismo evento en la ventana de cooldown.

Si el snapshot es parcial, la alerta puede quedar `not_evaluable` con razón explícita. No se silencia como “no cambió”.

---

## 9. Contratos API y compatibilidad

### V1 actual que se conserva temporalmente

- `guests: int` en `HotelRateOut`, `HotelAreaSearchQueryIn` y `HotelTrackedOffer*`;
- `room_label`, `meal_plan`, `cancellation_policy` como strings;
- `amount` como importe único;
- `deep_link` nullable;
- `HotelProviderRunOut.status` abierto como string;
- IDs actuales y endpoints existentes.

### V2 objetivo

Añadir campos compatibles, sin cambiar el significado de los existentes hasta que todos los callers migren:

```json
{
  "stay_query": {
    "check_in": "2026-09-10",
    "check_out": "2026-09-13",
    "occupancy": {
      "rooms": [{"adults": 2, "children_ages": []}]
    },
    "currency": "EUR"
  },
  "identity": {
    "canonical_hotel_id": "internal-id",
    "provider_id": "provider",
    "provider_hotel_id": "opaque-id"
  },
  "price": {
    "amount_base": null,
    "fees_amount": null,
    "amount_total": 420.0,
    "currency": "EUR",
    "semantics": "total"
  },
  "conditions": {
    "room": {"normalized": "standard", "raw": "Standard Double"},
    "meal_plan": "BB",
    "cancellation": {"type": "refundable", "free_until": null},
    "completeness": "partial"
  },
  "outcome": "success",
  "freshness": {"observed_at": "2026-08-04T12:00:00Z", "state": "fresh"}
}
```

Los campos V2 no deben fabricar valores para columnas legacy. Si el legacy `guests` se deriva de ocupación, incluir `occupancy_source` y conservar la distinción.

---

## 10. Migración compatible

### H10-A — Tipos de dominio y normalizadores

- Crear `StayQuery`, `Occupancy`, `RoomSignature`, `CancellationPolicy`, `FeeBreakdown`, `OfferIdentity` y `SnapshotOutcome` internos.
- Añadir validadores sin cambiar todavía tablas.
- Implementar fingerprints deterministas con serialización canónica.
- Añadir tests de invariantes y equivalencia legacy.

### H10-B — Bridge de entrada

- Convertir request V1 a `StayQuery` con `occupancy_source=legacy_inferred`.
- Rechazar fechas invertidas, moneda inválida, adultos/rooms imposibles y precios negativos.
- No aceptar `children` sin edades cuando el provider las necesita; marcar `unknown` o devolver unsupported según producto.
- Resolver aliases antes de cualquier provider call.

### H10-C — Persistencia aditiva

H11 decidirá si se añaden columnas JSON/versionadas o tablas normalizadas. En ambos casos:

- no borrar columnas legacy;
- conservar datos originales;
- backfill `adults=guests`, `children_ages=[]` solo como inferencia marcada;
- no backfill automático de room/meal/cancelación/fees si no hay evidencia;
- crear índices para fingerprint, provider/ID externo, estancia y freshness;
- usar migraciones idempotentes y rollback documentado;
- comprobar duplicados antes de añadir unicidad nueva.

### H10-D — Doble lectura/doble escritura controlada

- leer V2 cuando exista y sea válida;
- fallback a legacy con warning interno `legacy_hotel_contract`;
- escribir ambos formatos durante una ventana;
- comparar resultados y métricas de divergencia;
- desactivar doble escritura solo después de H11 y tests de regresión.

### H10-E — Retirada de ambigüedades

Solo después de migrar todos los callers:

- dejar de usar `guests` como identidad principal;
- mover parity/ranking/alerts a `offer_comparability_key`;
- hacer explícito `unknown` para fees/conditions/availability;
- retirar campos legacy únicamente mediante ADR y migración aprobada.

---

## 11. Invariantes y tests

### `StayQuery`

- `check_out > check_in`;
- fechas válidas para el provider y timezone de destino;
- al menos una habitación y un adulto por habitación;
- edades válidas y ordenadas de forma canónica;
- moneda ISO-4217;
- fingerprint igual para payloads semánticamente iguales aunque cambie el orden de JSON;
- fingerprint distinto si cambia una dimensión que puede cambiar precio.

### Identidad

- nunca confundir `canonical_hotel_id` con `provider_hotel_id`;
- alias `(provider, provider_hotel_id)` único;
- mapping ambiguo bloquea llamadas dirigidas;
- `user_id` no aparece en fingerprints compartidos;
- provider distinto no se considera misma oferta.

### Oferta/snapshot

- importe base/fees/total no se duplican;
- `amount_total` requiere semántica conocida;
- currency válida;
- habitación/régimen/cancelación conservan raw y normalized;
- error/timeout/rate limit no crea snapshot `available`;
- snapshot de replay no entra en alertas por defecto;
- deeplink rechazado queda `null` con warning.

### Comparabilidad

- parity no agrupa ocupaciones distintas;
- no se comparan ofertas con cancelación incompatible;
- fee completeness forma parte de la clave o impide ranking total;
- freshness y provenance son parte de elegibilidad;
- cambios de provider generan outcome separado.

### API/regresión

- endpoints V1 continúan serializando;
- payloads V2 no filtran user/secret;
- legacy `guests` sigue aceptándose durante la migración;
- PATCH no puede mutar silenciosamente la identidad histórica de una query sin nuevo fingerprint;
- tests de area search, tracked offers, parity, ingestion y sweep siguen pasando.

---

## 12. Handoff a fases siguientes

| Fase | Entrega H10 |
|---|---|
| H11 | decidir tablas/columnas, backfill, índices, doble lectura/escritura y rollback |
| H12 | versionar schemas API y compatibilidad frontend/backend |
| H15 | exponer resultado, outcome, freshness y comparabilidad sin listas ambiguas |
| H19 | implementar `FeeBreakdown`, semántica de total y tax/fee inclusions |
| H20 | normalizar room type, room ID, meal plan y condiciones de habitación |
| H23 | conectar subscriptions/tracked offers con `StayQuery` compartida |
| H26 | dedupe de alertas por oferta comparable, baseline y outcome |
| H35 | deeplink object, allowlist, disclosure y privacidad |
| H37 | medir fingerprints, cache sharing, coste y cardinalidad |
| H41 | métricas de matching, occupancy completeness, comparison eligibility y divergencia V1/V2 |
| H43 | flags para doble lectura, provider scope y rollback |

### Gate H10

H10 podrá considerarse implementada cuando:

- exista `StayQuery` estructurada y validada;
- rooms/adults/children ages sustituyan progresivamente al `guests` escalar;
- fingerprints separen consulta, oferta y snapshot;
- aliases bloqueen el uso de IDs internos contra providers;
- rate semantics distingan base, fees, total y unknown;
- room/meal/cancelación/disponibilidad formen parte de comparabilidad;
- suscripciones privadas estén separadas del cache compartido;
- parity, ranking y alertas no mezclen ofertas incompatibles;
- migración y doble lectura/escritura tengan rollback;
- API V1, frontend y providers tengan contract tests.

**Resultado H10:** contrato canónico aprobado. El dominio actual sigue siendo V1 compatible y no se declara migrado hasta cerrar H11/H12/H19/H20.
