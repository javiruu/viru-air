# H23 — Crear tracking hotelero desde una oferta real

**Estado:** contrato de dominio/API/UX; implementación frontend/backend, migración V2, idempotencia, i18n y QA E2E pendientes  
**Fecha:** 2026-08-05  
**Área:** backend / frontend / DB / producto / providers / seguridad / QA  
**Fuente de verdad:** sí para la creación de una suscripción hotelera reconstruible desde una oferta observada  
**Fase del roadmap:** H23  
**Depende de:** H10, H11, H12, H13, H14, H15, H18, H19, H20, H21, H22  
**Relacionado con:** H05 freshness/provenance, H06 provider-neutral, H09 sweeps, H24 histórico, H25 confidence, H26 alertas, H27 inbox, H29 lifecycle, H34 i18n, H35 legal/deeplinks, H37 coste, H38 ownership, H39-H40 QA

> H23 evita crear un “seguimiento” que solo recuerda un hotel y una cifra suelta. Una suscripción debe reconstruir qué estancia y qué oferta quiso vigilar la persona, cuál era la observación inicial y qué partes siguen pendientes o no son evaluables.

## 1. Decisión de fase

La creación de tracking parte de una **oferta visible y contextualizada**, no de un hotel abstracto:

```text
búsqueda válida
  → oferta/rate elegible
  → revisión del contexto
  → confirmación explícita
  → suscripción privada
  → snapshot inicial enlazado
  → active | pending_first_observation | partial
```

H23 define el contrato y la migración segura. No selecciona un provider nuevo, no garantiza sweeps diarios por sí misma y no convierte un snapshot mock en dato live.

### Resultado que debe poder reconstruirse

Después de crear el tracking, la aplicación debe poder explicar sin leer el estado efímero de la búsqueda original:

- qué hotel canónico se sigue;
- para qué entrada, salida y número de noches;
- qué ocupación se conoce y cuál es la fuente del bridge V1;
- qué habitación, régimen y cancelación se observaron;
- qué moneda y semántica de precio aplican;
- qué provider o scope se sigue;
- cuál fue el importe inicial y cuándo se observó;
- qué freshness, provenance y warnings tenía;
- si el tracking está activo, pendiente, parcial, stale, pausado, expirado o no disponible;
- qué acciones están permitidas a continuación.

## 2. Estado actual comprobable

### 2.1. Alta V1

`POST /hotels/tracked-offers` acepta actualmente `HotelTrackedOfferCreateIn`, donde son opcionales:

- `check_in` y `check_out`;
- `room_label`, `meal_plan` y `cancellation_policy`;
- `initial_price`, `current_price` y `target_price`;
- varios campos de búsqueda de área.

`guests` tiene default `2` y `provider` default `mock`. El servicio valida el hotel y crea `HotelTrackedOffer`. Solo crea `HotelRateSnapshot` si existen fechas y un precio actual derivable. Por tanto, hoy puede existir una fila sin snapshot inicial.

Los tests actuales cubren deliberadamente ambos caminos:

- snapshot cuando hay fechas y precio;
- ausencia de snapshot cuando falta fecha o precio;
- fallback de `current_price` a `initial_price`;
- creación mínima con defaults;
- duplicado exacto mediante `IntegrityError`/`tracked_offer_already_exists`.

Estos tests describen compatibilidad V1, no el criterio de “tracking real listo”. H23 debe conservarlos durante la transición y añadir el contrato estricto para nuevas altas desde una oferta.

### 2.2. Alta actual desde frontend

`useTrackedOffers.handleTrackPrice` recibe solo `hotelId`. Busca una tarifa del hotel seleccionado, elige la más barata, y crea el tracking con los campos disponibles. Para una card no seleccionada puede no tener rates; en ese caso usa provider `mock`, moneda `EUR` y deja fechas/precio ausentes.

Ese comportamiento no demuestra que la persona haya confirmado una oferta concreta. La nueva UX debe dejar de presentar esa acción como tracking operativo sin contexto: si no hay una oferta compatible, debe llevar al detalle/búsqueda o marcar la intención como `pending_context`, nunca ocultar la falta de datos.

### 2.3. Snapshot inicial actual

El servicio crea un snapshot enlazado usando los datos recibidos, con `availability_status="available"`, pero el modelo V1 no conserva todavía un `observed_at` independiente de `collected_at`, una semántica completa de fees, un fingerprint de oferta ni un token de observación. Por sí solo, ese snapshot V1 no permite validar de forma fiable freshness, fees o elegibilidad V2.

H23 exige que el snapshot inicial de una oferta real sea inmutable como evidencia de creación; esa inmutabilidad es un requisito V2 de H11, no un comportamiento garantizado por el modelo actual. Los campos desconocidos permanecen desconocidos y la implementación aditiva concreta no se inventa en esta fase contractual.

### 2.4. Duplicados y ownership actuales

La unicidad V1 es `(user_id, hotel_id, check_in, check_out, guests, provider)`. Es insuficiente porque permite ambigüedad con `NULL` y no incluye habitación, régimen, cancelación, moneda, fees ni oferta concreta. El servicio traduce el conflicto de base de datos a `tracked_offer_already_exists`; no existe todavía una respuesta de idempotencia basada en intención de creación.

Las lecturas, PATCH, DELETE y snapshots comprueban ownership del tracked offer. H23 conserva esa regla y añade que una regla o tracking nunca puede aceptar un `tracked_offer_id` ajeno desde el cliente.

## 3. Modelo canónico de creación

### 3.1. Contexto de estancia

El bridge V1 puede representar temporalmente:

```text
canonical_hotel_id
check_in
check_out
guests                  bridge legacy
currency
occupancy_source        legacy_form | legacy_inferred | confirmed
```

El contrato objetivo de H10 es:

```json
{
  "hotel_id": "canonical-id",
  "stay_query": {
    "check_in": "2026-09-10",
    "check_out": "2026-09-13",
    "occupancy": {
      "rooms": [{"adults": 2, "children_ages": []}]
    },
    "currency": "EUR"
  }
}
```

Invariantes:

- el hotel existe y es un ID canónico interno;
- `check_out > check_in`;
- las noches son positivas y calculables;
- la ocupación tiene una fuente identificable;
- no se inventan habitaciones, adultos o edades a partir de una cifra sin marcarla como inferida;
- currency es ISO-4217 y coincide con la semántica observada o conserva solicitada/devuelta por separado;
- fechas y ocupación forman parte de la identidad de estancia.

### 3.2. Identidad de oferta

Una creación H23 debe transportar o resolver una identidad de oferta suficiente:

```text
offer_identity {
  canonical_hotel_id
  stay_query_fingerprint
  provider_id / provider_scope
  provider_offer_id nullable
  room_signature nullable/unknown
  meal_plan_normalized nullable/unknown
  cancellation_signature nullable/unknown
  fee_semantics
  currency
}
```

Un `room_label` libre sirve como evidencia descriptiva, pero no como única clave de dedupe. Si el provider no aporta un `provider_offer_id`, se utiliza una firma normalizada y se marca la completitud.

Dos ofertas del mismo hotel y estancia pueden ser trackings distintos cuando cambian habitación, régimen, cancelación, provider scope o semántica de fees. No se deben fusionar porque tengan el mismo precio.

### 3.3. Observación inicial

El request de creación debe referenciar la observación que la persona vio, mediante una estrategia V2 futura (ninguna de estas capacidades existe todavía en el endpoint V1):

1. `source_rate_id` interno de un `HotelRateSnapshot` elegible;
2. `offer_fingerprint` + contexto completo, resuelto server-side contra una observación reciente;
3. un token opaco de selección emitido por el backend y de vida corta.

Hasta que H11/H15/H19 implementen ese bridge, el backend no puede tratar un `source_rate_id`, fingerprint o token como si fueran campos V1 disponibles ni validar automáticamente el total/freshness que el modelo actual no conserva.

No se acepta que el cliente convierta libremente un precio numérico en “oferta real”. Si solo hay precio sin observación, la creación queda `pending_context`/`partial` y no `active`.

La observación debe conservar, cuando exista:

```text
observed_at / collected_at
provider_run_id
provider
amount_base / fees / amount_total
currency
room / meal / cancellation
availability_status
freshness_state
provenance
confidence
source rate/fingerprint
```

H19 decide la semántica de total y fees; H05 decide freshness/provenance. H23 solo permite activar el tracking cuando el resultado de esos contratos es compatible.

## 4. Campos de entrada y estados de validación

### 4.1. Requeridos para una creación activa

| Campo | Obligatorio | Motivo |
|---|---:|---|
| hotel canónico | sí | ownership y destino estable |
| check-in/out | sí | estancia reconstruible |
| ocupación | sí, con fuente | precio y matching |
| currency | sí | comparación válida |
| provider/scope | sí | qué se revalida |
| oferta o rate referenciada | sí | no crear tracking desde cifra suelta |
| precio observado elegible | sí para `active` | baseline y snapshot inicial |
| condiciones | según capability | marcar `partial/unknown`, no inventar |

`target_price` es opcional y pertenece a la preferencia privada, no a la identidad compartida de la oferta.

### 4.2. Clasificación de entrada

| Resultado | Condición | Estado inicial | ¿Alerta? |
|---|---|---|---:|
| `active` | contexto completo, rate elegible y policy/provider aptos | `active` | todavía no hasta que H26 lo habilite |
| `pending_first_observation` | contexto completo, pero falta snapshot confirmable | pendiente | no |
| `pending_context` | faltan fechas, ocupación, currency u oferta | incompleto | no |
| `partial` | oferta válida con condiciones/fees/provider incompletos | parcial | no evaluable |
| `stale` | existe observación, pero excede TTL H05 | stale | no hasta revalidar |
| `unavailable` | provider/capability no puede comprobar la oferta | no disponible | no |
| `duplicate` | misma identidad ya pertenece al usuario | devolver existente/idempotencia | conserva el estado existente |
| `invalid` | fechas, hotel, moneda, oferta o precio inválidos | rechazo 422 | no |

`active` no significa “precio garantizado” ni “sweep diario garantizado”; significa que el contexto permite una suscripción y existe una policy operativa explícita. Con el worker/provider V1 actual no se puede prometer tracking diario estable solo por almacenar `is_active=true`; la copy debe mostrar última observación, capacidad real y cualquier limitación operativa.

## 5. Flujo de confirmación frontend

### 5.1. Desde resultados

La card no debe crear tracking con solo `hotelId`. La acción recomendada es:

```text
Ver oferta / seleccionar hotel
  → cargar rates del mismo contexto
  → elegir una oferta concreta
  → abrir resumen de tracking
  → confirmar
```

Si la card no tiene una oferta elegible:

- “Seguir precio” no crea la suscripción silenciosamente;
- puede abrir el detalle y conservar búsqueda/URL state H13/H18;
- puede ofrecer “Guardar hotel” como favorito H22;
- puede mostrar “Completar fechas” si existe una intención incompleta;
- no muestra “seguimiento activo” después de una fila V1 sin snapshot.

### 5.2. Resumen de confirmación

Antes de enviar, la persona debe ver:

- nombre del hotel y ubicación;
- entrada, salida y noches;
- habitaciones/adultos/niños o bridge `guests` claramente etiquetado;
- habitación, régimen y cancelación;
- provider o “cualquier provider elegible”;
- precio observado, moneda y semántica de fees;
- última observación/freshness y warnings;
- target price opcional;
- qué significa “seguir” y qué no se promete;
- CTA de confirmar y opción de cancelar sin mutación.

La confirmación debe ser accesible, localizada y no esconder condiciones en un tooltip. Si la observación se vuelve stale durante la confirmación, se debe advertir/revalidar según policy, no presentarla como live.

### 5.3. Respuesta posterior

La UI actualiza card, detalle y panel de tracking con el objeto devuelto por backend. No reconstruye el estado a partir de la búsqueda anterior.

Debe poder mostrar:

```text
active                    seguimiento creado
pending_first_observation primera comprobación pendiente
pending_context           faltan datos
partial                   seguimiento limitado/no evaluable
duplicate                 ya existía; abrir el existente
unavailable               provider/capability no disponible
```

Un error de carga posterior se muestra como `error`, no como lista vacía H21.

## 6. Idempotencia, duplicados y concurrencia

### 6.1. Intención de creación

La intención de crear tracking debe tener una clave idempotente por usuario y endpoint. La adopción de `Idempotency-Key`/hash de request es una capacidad V2 propuesta; el endpoint V1 actual no la implementa y solo dispone del conflicto `tracked_offer_already_exists`. Cuando exista el bridge V2, no debe confiar únicamente en un UUID generado de nuevo en cada retry.

La clave debe asociarse a un hash del request normalizado. Si se repite la misma clave con un payload diferente, el backend rechaza la reutilización (`idempotency_key_reused`) y no crea otra suscripción.

### 6.2. Duplicado semántico

La identidad objetivo es:

```text
user_id privado
+ stay_query_fingerprint
+ offer_fingerprint o provider_scope
```

El `user_id` participa en ownership/constraint privado, pero no se incluye en fingerprints compartidos.

Ante una creación concurrente o retry semánticamente idéntico:

- no se crean dos trackings;
- se devuelve el tracking existente con estado `duplicate`/idempotent replay o un `409` estable según el contrato de API;
- el frontend abre o enfoca el tracking existente;
- no se crea un segundo snapshot inicial;
- no se dispara una alerta por la repetición.

La unicidad legacy no es suficiente para ofertas con `NULL`. H11 debe preparar la migración, detectar candidatos duplicados y aplicar constraints nuevas solo tras dry-run y rollback probado.

## 7. Snapshot inicial y proyección de precio

### 7.1. Reglas de persistencia

Estas son reglas objetivo V2; el modelo V1 no impone por sí solo inmutabilidad, freshness, fees ni fingerprint.

Al crear un tracking activo desde una oferta elegible:

1. enlazar el snapshot de origen si ya existe;
2. si no existe, persistir una copia inmutable con `tracked_offer_id` y provenance equivalente;
3. conservar el importe original y su semántica, sin recalcular fees inciertas;
4. guardar fecha/hora de observación y provider run cuando estén disponibles;
5. marcar el snapshot con freshness/outcome/confidence según H05;
6. establecer `initial_price` solo desde el valor observado aceptado;
7. establecer `current_price` como proyección de ese snapshot, nunca como garantía live;
8. no crear snapshot “available” con un timeout, rate limit, provider error o valor inventado;
9. no actualizar `current_price` si la única respuesta posterior es error o disponibilidad no evaluable.

### 7.2. Compatibilidad V1

Mientras no existan columnas V2:

- `collected_at` representa la captura legacy y no se rebautiza como `observed_at` si no se demuestra equivalencia;
- `amount` conserva su semántica desconocida;
- `room_label`, `meal_plan` y `cancellation_policy` pueden ser `NULL`/raw;
- `current_price` y `initial_price` se exponen con copy de precio observado, no precio final garantizado;
- una fila creada sin snapshot se devuelve como legacy/incompleta, no como tracking activo;
- el bridge puede crear `HotelRateSnapshot` solo cuando el origen y el contexto son válidos.

## 8. Inmutabilidad y edición posterior

La identidad de una oferta no debe mutar silenciosamente después de crear la serie histórica.

### Campos que normalmente no se PATCH-ean

- `hotel_id`;
- `check_in`/`check_out` de la serie existente;
- ocupación estructurada;
- provider scope;
- `offer_fingerprint`;
- habitación, régimen o cancelación si cambian comparabilidad;
- `initial_price` y snapshot inicial.

Cambiar esas dimensiones debe crear una nueva versión o una nueva suscripción, conservando relación de origen para UI.

### Campos editables

- `target_price`;
- preferencias de alerta cuando H26 lo permita;
- lifecycle `paused/active` según H29;
- label privado si se añade explícitamente;
- configuración no identitaria y auditada.

El PATCH V1 actual acepta más campos y actualmente permite mutar fechas, provider, habitación, régimen, cancelación y precios después de crear la fila; esto es un gap bloqueante de consistencia histórica. H23 lo documenta como compatibilidad legacy y exige que la futura API rechace o versiona esas mutaciones, o cree una nueva versión/suscripción sin reescribir la serie anterior.

## 9. Ownership, seguridad y privacidad

- Toda lectura/mutación filtra por `current_user.id` o comprueba ownership antes de serializar.
- El cliente nunca puede elegir `user_id`.
- `source_rate_id`, `tracking_id` y snapshots privados no se exponen en URL pública sin contrato seguro; `source_rate_id`, fingerprints y tokens son capacidades V2 propuestas, no campos V1 actualmente disponibles.
- No incluir targets, thresholds, emails, notas, tokens ni raw provider en fingerprints compartidos o telemetry.
- Un rate público/cacheado puede servir para discovery, pero al crear tracking el backend debe comprobar que pertenece al hotel/contexto y que es elegible.
- Una regla de alerta solo puede referenciar un tracking del mismo usuario y hotel coherente.
- Dos usuarios pueden trackear la misma oferta compartida sin ver snapshots privados, targets ni eventos del otro.
- Los errores 403/404 no deben filtrar fechas, importes ni existencia de IDs ajenos.
- La eliminación de cuenta y retención se coordina con H11/H27/H29.

## 10. Contrato API V1→V2

### V1 que se conserva temporalmente

- `POST /hotels/tracked-offers` y respuesta `201`;
- `GET/PATCH/DELETE /hotels/tracked-offers/{id}`;
- `GET /hotels/tracked-offers/{id}/snapshots`;
- campos legacy de área y `guests` scalar para lectura/backfill;
- `is_active` como bridge técnico;
- errores `hotel_not_found`, `tracked_offer_already_exists`, `tracked_offer_not_found` y ownership actual.

### V2 objetivo aditivo

```json
{
  "tracking": {
    "id": "tracking-id",
    "state": "active",
    "hotel_id": "canonical-hotel-id",
    "stay_query": {
      "check_in": "2026-09-10",
      "check_out": "2026-09-13",
      "nights": 3,
      "occupancy": {
        "rooms": [{"adults": 2, "children_ages": []}],
        "source": "confirmed"
      },
      "currency": "EUR"
    },
    "offer": {
      "fingerprint": "opaque",
      "provider": "provider-id",
      "room": {"normalized": "standard", "raw": "Standard Double"},
      "meal_plan": "BB",
      "cancellation": {"type": "refundable"},
      "completeness": "complete"
    },
    "initial_observation": {
      "snapshot_id": "opaque",
      "observed_at": "2026-08-05T10:00:00Z",
      "amount_total": 420.0,
      "currency": "EUR",
      "semantics": "total",
      "freshness": "recent"
    },
    "target_price": null,
    "capabilities": {
      "pause": true,
      "edit_target": true,
      "create_alert": false,
      "delete": true
    },
    "warnings": []
  },
  "creation": {
    "outcome": "created",
    "idempotent_replay": false,
    "request_id": "short-lived-redacted"
  }
}
```

No se debe fabricar `amount_total` ni `freshness` en el ejemplo real si el provider no los demuestra; el ejemplo representa únicamente un payload elegible V2.

## 11. Migración y rollout

### H23-A — Inventario de legacy

Clasificar sin borrar:

```text
complete_with_snapshot
complete_without_snapshot
missing_dates
missing_price
missing_conditions
duplicate_candidate
expired
owner_unverifiable
mock_or_fixture
```

Medir cantidades y riesgos con IDs redacted en logs. No convertir automáticamente todos los `mock` en tracking real.

### H23-B — Nueva alta estricta

- Mantener endpoint V1 para compatibilidad controlada.
- Añadir un camino de creación desde `source_rate_id`/offer token o request V2.
- Bloquear `active` si no hay contexto y observación elegible.
- Devolver estado explícito y warnings.
- Añadir idempotencia de request y dedupe semántico.
- Emitir métricas de creación, duplicado, incomplete y provider unavailable.

### H23-C — Backfill y doble lectura

- Inferir `guests` legacy solo con `occupancy_source=legacy_inferred`.
- No inventar habitación, régimen, cancelación, fees ni snapshot inicial.
- Asociar snapshots existentes solo cuando hotel, fechas, guests, provider y moneda sean compatibles.
- Marcar `needs_review` cuando haya ambigüedad.
- Leer estado V2 si existe; fallback V1 con warning `legacy_tracking_contract`.
- Mantener rollback y comparar divergencias antes de retirar campos legacy.

### H23-D — Rollout frontend

- El CTA desde card requiere oferta/contexto, no solo hotel ID.
- El detalle muestra resumen de confirmación y warnings.
- El panel distingue `active`, `pending_context`, `partial`, `stale`, `paused` y `unavailable`.
- Retry ante 409/idempotent replay abre el tracking existente.
- La ausencia de rates ofrece guardar hotel, no crear un tracking invisible.

## 12. Eventos y observabilidad

Eventos versionados sin PII:

```text
hotel_tracking_offer_selected
hotel_tracking_confirmation_viewed
hotel_tracking_confirmation_cancelled
hotel_tracking_create_started
hotel_tracking_created
hotel_tracking_creation_pending
hotel_tracking_creation_partial
hotel_tracking_creation_duplicate
hotel_tracking_creation_blocked
hotel_tracking_creation_failed
hotel_tracking_initial_snapshot_linked
hotel_tracking_initial_snapshot_missing
hotel_tracking_legacy_detected
hotel_tracking_identity_conflict
hotel_tracking_idempotency_replay
hotel_tracking_ownership_denied
```

Propiedades allowlisted:

- `surface`, `state`, `outcome`, `reason_code`, `provider_scope`;
- `has_context`, `has_initial_observation`, `conditions_completeness`, `freshness_state`;
- fingerprint opaco, duración y código HTTP;
- nunca query completa, email, user ID crudo, target, raw payload o URL externa.

Métricas mínimas:

- porcentaje de tracking creado desde oferta con contexto completo;
- snapshot inicial enlazado frente a ausente;
- creación `active/partial/pending/unavailable`;
- duplicados semánticos y replays idempotentes;
- tiempo confirmación → creación;
- tracking legacy por categoría;
- conflictos de identidad y ownership;
- provider error que no actualiza precio;
- reintentos y errores de API.

## 13. Accesibilidad, copy y legal

- La confirmación tiene heading, resumen legible, CTA de confirmar/cancelar y foco gestionado.
- Cada campo faltante tiene explicación y acción concreta.
- “Precio observado” y “precio total” solo se usan con la semántica H19 correspondiente.
- La UI informa de última observación y no promete disponibilidad o precio final del partner.
- Los estados de creación se anuncian con texto, no solo color/spinner.
- Retry no duplica la entidad ni mueve el foco a un elemento eliminado.
- ES/EN, monedas, noches, fechas y timezone usan formatting locale-aware.
- Deeplink y afiliación se reservan a H35; crear tracking no abre automáticamente un partner.
- El tracking es una acción privada y requiere sesión/consentimiento según producto.

## 14. Tests y gate H23

### Backend/unitarios

- rechazar o clasificar creación sin fechas, ocupación u oferta como `pending_context`, no `active`;
- snapshot inicial solo con observación y contexto válidos;
- snapshot conserva provider, condiciones, moneda, amount y timestamp disponibles;
- provider error/timeout/rate limit no crea snapshot elegible ni actualiza `current_price`;
- fee/total desconocido no se inventa;
- `check_out <= check_in` rechaza;
- fingerprint igual para payloads semánticamente iguales;
- cambio de habitación/régimen/cancelación/provider cambia identidad o crea nueva versión;
- retry con misma idempotency key no duplica tracking ni snapshot;
- misma identidad con otra key devuelve existente/409 estable;
- key reutilizada con payload distinto se rechaza;
- PATCH no muta silenciosamente identidad histórica;
- ownership de tracking, snapshot y source rate se cumple;
- dos usuarios pueden trackear la misma oferta sin cruzar datos;
- V1 minimal legacy sigue leyendo y clasificándose.

### Frontend

- card sin oferta lleva a detalle/guardar, no crea tracking activo;
- selección de oferta abre confirmación con resumen completo;
- confirmar crea una sola entidad;
- cancelación no muta nada;
- duplicate/replay enfoca tracking existente;
- estados pending/partial/stale/unavailable/error no se muestran como active;
- refresh de página reconstruye tracking desde su respuesta;
- error no se presenta como empty;
- teclado, lector de pantalla, reduced motion, dark/light y ES/EN pasan.

### Integración/E2E

```text
buscar estancia
  → seleccionar hotel
  → cargar rates
  → seleccionar oferta concreta
  → confirmar contexto
  → crear tracking
  → leer tracking sin búsqueda original
  → consultar snapshot inicial
  → repetir submit/retry
  → comprobar no duplicado
```

Casos obligatorios:

- tarifa completa con fechas, provider y precio;
- precio base con fees desconocidas;
- una card sin rates;
- tracking legacy sin fechas;
- provider mock rotulado como fixture/demo;
- provider timeout después de una oferta válida;
- 409 concurrente y replay idempotente;
- usuario B intentando leer source rate/tracking de A;
- cambio de estancia/condiciones tras la creación;
- back/forward y refresh H13/H18;
- eliminación de cuenta y snapshots privados.

### Gate D parcial

H23 puede marcarse completa como contrato cuando:

1. solo se etiqueta activo un tracking con contexto y oferta observada elegibles;
2. la creación devuelve snapshot inicial o estado pendiente explícito;
3. el tracking se reconstruye sin leer la búsqueda original;
4. identidad, dedupe e idempotencia están definidos y son reversibles;
5. core identity no se muta silenciosamente;
6. provider error no se convierte en precio actual válido;
7. ownership cubre tracking, snapshot, source rate e inbox posterior;
8. V1 legacy se clasifica sin inventar datos;
9. confirmación, copy, a11y, i18n y legal están especificados;
10. tests prueban creación, retry, duplicado, estados, dos usuarios y refresh.

**Resultado contractual:** H23 queda definido como contrato de creación reconstruible. La implementación estricta de alta, snapshot/fingerprint V2, idempotencia, migración, UI de confirmación y QA E2E permanecen pendientes.

## 15. Handoff

| Fase | Entrega H23 |
|---|---|
| H05 | freshness/provenance/confidence para aceptar o excluir observación inicial |
| H09 | policy real de revalidación, scheduler, budget y provider capability |
| H10-H11 | StayQuery, fingerprints, ocupación estructurada, migración y constraints |
| H13/H18 | URL state, retorno, selección y contexto reproducible |
| H19 | fees, amount_total, amount_per_night y disclosure |
| H20 | room/meal/cancelación y comparabilidad entre providers |
| H21/H22 | estados, favorito separado y no confusión de CTA |
| H24-H25 | histórico, agregados, freshness y confianza de la suscripción |
| H26 | reglas solo sobre snapshots comparables y tracking evaluable |
| H27 | inbox con fuente privada y deep link al tracking correcto |
| H29 | editar, pausar, expirar, archivar, eliminar y rollback de lifecycle |
| H34-H35 | i18n, legal, afiliación y deeplinks |
| H37-H40 | coste, seguridad, tests y browser QA |

**No se declara H23 implementada hasta que una suscripción creada pueda reconstruirse completamente desde su propia respuesta y evidencia de snapshot, sin depender del estado de la búsqueda que la originó.**
