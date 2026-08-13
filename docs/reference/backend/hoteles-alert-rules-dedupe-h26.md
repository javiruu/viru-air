# H26 — Reglas de alerta, baselines y deduplicación hotelera

**Estado:** implementación local V1 cerrada con límites explícitos; quedan fuera del cierre los gates avanzados de provider/freshness, scheduler, inbox/delivery y QA visual/manual
**Fecha:** 2026-08-05  
**Área:** backend / producto / DB / frontend / privacidad / QA / observabilidad  
**Fuente de verdad:** sí para la semántica de reglas, baselines, eventos, cooldown y deduplicación de alertas hoteleras  
**Fase del roadmap:** H26  
**Depende de:** [H19 — precio total y fees](hoteles-price-total-fees-h19.md), [H21 — matriz de estados](../frontend/hoteles-state-matrix-h21.md), [H22 — favorito frente a tracking](hoteles-favorite-vs-tracking-h22.md), [H23 — tracking desde oferta real](hoteles-real-offer-tracking-h23.md), [H24 — histórico y curva](hoteles-price-history-curve-h24.md), [H25 — freshness, confidence y acciones](hoteles-freshness-confidence-actions-h25.md)  
**Relacionado con:** H10-H12 modelo/migración/API, H20 comparación, H27 inbox, H28 delivery, H29 lifecycle, H31-H34 UX/i18n/a11y, H36 rendimiento, H40 QA, H41 observabilidad

> H26 evita que una alerta sea una consulta ambigua ejecutada muchas veces. Cada evento debe poder responder qué regla se evaluó, contra qué baseline, sobre qué oferta, con qué snapshot, por qué se disparó y por qué no se volvió a emitir de forma redundante.

## 1. Decisión de alcance

H26 define:

1. tipos de regla hotelera y sus parámetros válidos;
2. relación entre regla, favorito, tracking y oferta concreta;
3. baselines `snapshot_previous`, `initial_price`, `target_price` y comparaciones de estado;
4. elegibilidad de snapshots antes de evaluar;
5. transición de estado y condición de disparo;
6. identidad determinista de un evento;
7. cooldown, dedupe, rearmado y agrupación;
8. ownership de reglas, eventos y futuros mensajes de inbox;
9. metadatos auditables y reason codes;
10. compatibilidad V1 y envelope/event ledger V2.

H26 no implementa por sí misma el inbox de usuario, canales externos, scheduler, provider gateway, deeplinks ni lifecycle completo. H27 consume los eventos ya validados; H28 decide delivery; H29 gobierna pausa, expiración y borrado.

## 2. Estado actual comprobable

### 2.1. Reglas V1

`HotelAlertRule` contiene actualmente:

```text
id
user_id
hotel_id
tracked_offer_id nullable
rule_type
threshold_amount nullable
threshold_percent nullable
compare_against
cooldown_minutes
evaluation_state
last_fired_at nullable
last_event_fingerprint nullable
is_active
```

Los tipos aceptados son:

```text
price_below
price_above
percentage_drop
percentage_increase
provider_changed
availability_returned
parity_break
```

Los schemas validan combinaciones básicas de umbral y `compare_against` (`snapshot_previous` o `initial_price`). El servicio valida que `tracked_offer_id` pertenezca al usuario autenticado y que corresponda al `hotel_id` de la regla; este gate de ownership/coherencia está cerrado y cubierto por integración.

`price_below`/`price_above` aceptan `threshold_amount` o `threshold_percent` en schema/UI. Para reglas trackeadas, el evaluador aplica ambos tipos contra el baseline explícito (`snapshot_previous` o `initial_price`) y cuenta con regresiones unitarias para bajada/subida porcentual.

La UI permite crear reglas desde el hotel seleccionado y gestionar activación/eliminación, pero no presenta todavía identidad de oferta, snapshot baseline, estado de cooldown, razón estructurada ni evidencia comparable.

### 2.2. Evaluación V1

`evaluate_hotel_alerts()`:

- evalúa reglas activas en cada sweep;
- para reglas con tracking consulta snapshots de la oferta;
- para reglas sin tracking usa rates generales del hotel como fallback legacy;
- compara contra el último snapshot o `initial_price` según la regla;
- aplica `clear → fired`, `fired → fired` suprimido y rearme al limpiar la condición;
- en `price_below`/`price_above` trackeados aplica `threshold_amount` o `threshold_percent` contra el baseline configurado;
- exige comparabilidad de estancia, ocupación, moneda y condiciones para snapshots trackeados;
- persiste cooldown, fingerprint y metadata de snapshots/razón en cada evento nuevo;
- los gates externos de freshness H25/provider y la semántica completa de fees H19 siguen fuera de esta migración local.

Los eventos pueden contener:

```text
id
rule_id nullable
hotel_id
provider_run_id nullable
event_type
message
trigger_value
created_at
```

### 2.3. Eventos V1 del sweep y riesgo de privacidad

`sweep_tracked_offers()` crea eventos de cambio de precio sin `rule_id` cuando detecta diferencia entre snapshots. `list_hotel_alert_events()` autoriza la consulta mediante conjuntos de `hotel_id` derivados de reglas y trackings del usuario, y devuelve eventos por `hotel_id`.

Este comportamiento no es apto para una bandeja privada: dos usuarios que sigan el mismo hotel podrían recibir señales del otro. H26/H27 deben migrar a ownership por `tracked_offer_id`/subscription o `rule_id`, nunca por hotel abstracto.

Además, el sweep V1 puede convertir un error del provider dirigido en `provider_rates=[]`, tomar un snapshot general y actualizar `current_price`; un evento nacido de ese fallback no es elegible. H26 no debe deduplicar un evento inválido: debe impedir su creación.

### 2.4. Dedupe y cooldown implementados en V1

La tabla `HotelAlertEvent` conserva ahora metadata nullable para compatibilidad histórica:

```text
event_fingerprint
snapshot_before_id
snapshot_after_id
baseline_snapshot_id
comparability_key
reason_code
eligibility_status
rule_version
cooldown_until
```

Los eventos nuevos llevan fingerprint único, razón y estado de elegibilidad. Las observaciones históricas del sweep sin regla se conservan para trazabilidad con `not_evaluable` y no se exponen en el listado privado de alertas. La existencia de un `provider_run_id` sigue sin sustituir a la identidad de dedupe; por eso el fingerprint se persiste con índice único.

## 3. Separación de superficies

### 3.1. Favorito simple

Un favorito de H22 no crea una regla ni una alerta automáticamente. Guardar un hotel no autoriza evaluar cambios privados de precio.

### 3.2. Tracking/oferta

Una regla vinculada a `tracked_offer_id` evalúa únicamente la oferta/estancia/condiciones que el usuario posee. Su baseline y sus eventos deben conservar esa identidad.

### 3.3. Regla legacy por hotel

Una regla sin `tracked_offer_id` puede mantenerse durante la migración como regla de catálogo/hotel, pero debe etiquetarse `legacy_hotel_scope`. No puede enviar copy de “tu oferta bajó” ni mezclarse con eventos de una suscripción privada.

Una regla legacy no debe convertirse silenciosamente en tracking. Si H26 no puede probar comparabilidad, solo puede producir un evento de señal general con alcance explícito, o quedar `not_evaluable`.

## 4. Tipos de regla y semántica

### 4.1. Precio absoluto

```text
price_below: dispara cuando current < threshold_amount
price_above: dispara cuando current > threshold_amount
```

Requisitos:

- importe positivo;
- misma moneda y semántica que el baseline/regla;
- snapshot elegible;
- condición de comparación exacta;
- no evaluar un provider error, fixture, sold out sin precio o snapshot incompatible.

El operador (`<`/`>`) debe ser determinista y versionado. El valor igual al umbral no dispara salvo que una versión explícita use `<=`/`>=`.

### 4.2. Porcentaje frente a baseline

```text
percentage_drop:
  ((baseline - current) / baseline) * 100 >= threshold_percent

percentage_increase:
  ((current - baseline) / baseline) * 100 >= threshold_percent
```

No calcular si baseline es nulo, cero, negativo, otra moneda, otra semántica de fees, otra estancia o no elegible. El evento conserva importes, monedas, snapshots y precisión de cálculo.

### 4.3. Cambio de provider

`provider_changed` dispara solo cuando dos snapshots consecutivos **elegibles y comparables** cambian de provider dentro de la política de `provider_scope`.

Cambiar provider no implica por sí mismo que suba o baje el precio. El evento debe expresar transición de procedencia y puede incluir diferencia solo si H19/H24 permiten comparar.

### 4.4. Disponibilidad recuperada

`availability_returned` requiere una transición válida. El contrato objetivo admite estados previos confirmados como `sold_out`/`unavailable` hacia `available`, pero la implementación V1 actual solo detecta `unavailable → available`; H26 debe ampliar la taxonomía o documentar el subconjunto soportado antes de prometer más.

```text
previous = sold_out | unavailable | unknown elegible como estado
current  = available
```

No tratar `provider_error` como `sold_out`. No disparar si solo cambió el precio o si el nuevo estado no está confirmado por provider.

### 4.5. Paridad

`parity_break` solo evalúa señales con al menos dos observaciones/provider comparables para la misma estancia y condiciones. `provider_count` bruto no equivale a `provider_count_comparable`.

La regla no debe disparar repetidamente mientras el mismo spread permanezca sin transición material. Un nuevo evento requiere superar el umbral después de haber salido del estado disparado o cambiar la identidad comparable.

## 5. Baselines

### 5.1. `snapshot_previous`

Es el snapshot anterior **elegible** de la misma identidad, no simplemente la fila anterior insertada. Se excluyen errores, fixtures, snapshots incompatibles y observaciones sin semántica necesaria.

Si no existe baseline, el resultado es `not_evaluable` y no se crea un evento de precio.

### 5.2. `initial_price`

Es el snapshot inicial elegible de H23 o el `initial_price` legacy cuando su contexto coincide. Debe conservar:

```text
baseline_snapshot_id o baseline_source
baseline_amount
baseline_currency
baseline_price_semantics
baseline_conditions/comparability_key
```

No usar `initial_price` mutado por PATCH como si fuera el histórico original. H23/H29 deben impedir esa mutación silenciosa.

### 5.3. `target_price`

`target_price` es un objetivo privado del usuario. No es un snapshot ni un precio observado y no entra en métricas históricas. Una alerta `price_below` frente a target puede existir como política V2, pero debe marcar `baseline_kind=target_user_value` y no afirmar una bajada porcentual histórica.

### 5.4. Cambio de identidad

Cambiar fechas, huéspedes, habitación, régimen, cancelación, moneda o provider scope crea una nueva serie o invalida el baseline. H26 no cruza automáticamente eventos entre identidades.

## 6. Elegibilidad antes de evaluar

Un snapshot es `eligible` para una regla solo si:

1. pertenece al tracking/regla autorizado;
2. estancia y ocupación coinciden;
3. moneda y semántica de precio son compatibles;
4. condiciones exigidas están presentes o explícitamente permitidas por política legacy;
5. availability no es un error no evaluable;
6. freshness H25 permite la decisión;
7. provenance no es fixture de producto;
8. provider/run y timestamp son trazables;
9. no fue ya consumido como replay duplicado;
10. no es resultado del fallback general después de error dirigido.

Resultado de evaluación:

```text
evaluable        puede calcularse la regla
triggered        condición cumplida y evento candidato válido
not_triggered    snapshot válido pero condición no cumplida
not_evaluable    falta baseline/contexto o hay incompatibilidad
suppressed       condición cumplida, pero cooldown/dedupe la suprime
invalid          dato no apto; debe generar warning operativo, no alerta al usuario
```

## 7. Máquina de estados y rearmado

Una regla no debe emitir una alerta por cada sweep que conserve el mismo estado. La evaluación distingue:

```text
clear       no se cumple la condición
candidate   se cumple, pendiente de validación/dedupe
fired       se emitió evento de transición
suppressed  se habría disparado, pero cooldown activo
rearmed     volvió a clear y puede disparar una nueva transición
invalid     no evaluable por datos/ownership/provider
```

Política inicial:

1. `clear → fired` crea evento;
2. `fired → fired` no crea otro evento idéntico;
3. `fired → clear` rearma la regla;
4. `clear → fired` posterior crea nuevo evento con snapshot nuevo;
5. `fired → suppressed` registra métrica interna, no otro mensaje visible;
6. cambio de baseline, identidad o versión de regla reinicia el fingerprint de forma explícita.

Para disponibilidad, la transición `unavailable → available → available` solo avisa una vez hasta perder disponibilidad y recuperarla de nuevo.

## 8. Identidad determinista y deduplicación

### 8.1. Fingerprint de evento

La clave objetivo es equivalente a:

```text
event_fingerprint = hash(
  owner_user_id
  + rule_id
  + tracked_offer_id o legacy_scope
  + rule_type
  + rule_version
  + baseline_snapshot_id o baseline_kind
  + current_snapshot_id
  + comparability_key/version
  + normalized_trigger_bucket
  + event_semantics
)
```

`owner_user_id` puede formar parte del ledger privado, pero no debe mezclarse en la identidad de observación compartida. La clave nunca se basa solo en `hotel_id`.

### 8.2. Ventana y bucket

Para evitar cambios mínimos que produzcan ruido:

- importes se normalizan con precisión de moneda;
- porcentajes se redondean solo después de comparar con precisión completa;
- parity usa el spread y versión de política;
- el bucket temporal y cooldown son configurables por tipo de regla;
- un nuevo snapshot material puede crear un nuevo evento aunque el texto sea igual.

No usar `message` como clave de dedupe: cambia por locale, copy o formato.

### 8.3. Unicidad y concurrencia

La persistencia V2 debe tener una restricción/índice equivalente a:

```text
(owner, event_fingerprint, delivery_scope)
```

La evaluación concurrente debe tolerar conflicto de unicidad, recuperar el evento existente y no duplicar delivery. Un lock de scheduler no reemplaza a la restricción de base de datos.

## 9. Cooldown

### 9.1. Cooldown de usuario

Cooldown evita repetir la misma señal visible durante una ventana definida. Debe distinguirse de rate limit del provider y de cooldown de refresh.

```text
cooldown_scope: rule | tracked_offer | user | event_type
cooldown_started_at
cooldown_until
cooldown_policy_version
last_emitted_event_id
```

Default recomendado inicial: por regla + tipo de evento + identidad de oferta. H41/H28 pueden calibrarlo con evidencia; no codificar una cifra en frontend.

### 9.2. Qué hace cooldown

- no borra el snapshot ni la evaluación;
- registra `suppressed` y motivo en métricas/telemetría;
- no prolonga indefinidamente la ventana por re-evaluaciones idénticas;
- permite rearmar al salir de la condición o al superar una transición material;
- no impide que el usuario consulte el histórico.

### 9.3. Provider error y retry

Un error del provider puede tener backoff operativo, pero nunca debe convertirse en cooldown de una alerta de bajada. Provider error no es `not_triggered`; es `not_evaluable`/`invalid` con reason code.

## 10. Evento y ledger objetivo

Un evento de alerta debe conservar al menos:

```text
id
owner_user_id o relación inequívoca
rule_id
tracked_offer_id nullable solo para legacy
hotel_id como dimensión secundaria
provider_run_id
snapshot_before_id
snapshot_after_id
baseline_snapshot_id
rule_type
rule_version
comparability_key
event_fingerprint
reason_code
eligibility_status
trigger_value
currency/price_semantics
created_at
suppressed_at/cooldown_until si aplica
```

Reason codes allowlisted iniciales:

```text
price_below_threshold
price_above_threshold
percentage_drop_threshold
percentage_increase_threshold
provider_changed
availability_returned
parity_break
missing_baseline
incompatible_conditions
provider_error
stale_observation
duplicate_suppressed
cooldown_active
ownership_mismatch
```

El mensaje humano se deriva de `reason_code` y datos permitidos; no es la fuente de verdad.

## 11. Ownership y frontera con inbox

- Crear una regla con `tracked_offer_id` exige que el tracking pertenezca al usuario y que `tracked_offer.hotel_id == rule.hotel_id`.
- Evaluar una regla nunca debe cargar un tracking ajeno.
- Listar eventos privados debe filtrar por owner a través de `rule_id`/`tracked_offer_id`, no por `hotel_id` solamente.
- Un evento sin owner inequívoco no se muestra en inbox; queda en cuarentena operativa para migración.
- Un mismo hotel seguido por dos usuarios produce eventos privados separados, aunque compartan snapshot base.
- H27 decide cómo un evento pasa a `UserNotificationState`; H26 entrega identidad y ownership suficientes.
- No incluir thresholds, labels, destinos privados o deeplinks de otro usuario en una señal compartida.

## 12. API y compatibilidad

### 12.1. V1 que se conserva temporalmente

Se mantienen endpoints y campos actuales:

- `HotelAlertRuleCreateIn/Out`;
- `HotelAlertEventOut`;
- `rule_id` nullable en eventos legacy;
- tipos de regla actuales;
- `compare_against` V1;
- lectura de eventos con filtros existentes durante migración.

Pero clientes V1 no deben inferir que un evento es privado o deduplicado solo porque tenga `hotel_id`.

### 12.2. Envelope V2 objetivo

```json
{
  "event": {
    "id": "opaque-event-id",
    "owner_scope": "tracked_offer",
    "rule_id": "opaque-rule-id",
    "tracked_offer_id": "opaque-offer-id",
    "hotel_id": "opaque-hotel-id",
    "event_type": "percentage_drop",
    "reason_code": "percentage_drop_threshold",
    "eligibility_status": "triggered",
    "event_fingerprint": "opaque-fingerprint",
    "rule_version": "hotel-alert-v1",
    "provider_run_id": "opaque-run-id",
    "snapshot_before_id": "opaque-snapshot",
    "snapshot_after_id": "opaque-snapshot",
    "baseline": {
      "kind": "snapshot_previous",
      "amount": 150.0,
      "currency": "EUR"
    },
    "current": {
      "amount": 132.0,
      "currency": "EUR",
      "freshness_status": "recent",
      "comparability_status": "comparable"
    },
    "cooldown": {
      "status": "not_active",
      "until": null
    }
  },
  "presentation": {
    "message_key": "hotels.alerts.events.percentageDrop",
    "params": {"percent": 12.0}
  }
}
```

El envelope es objetivo V2. En transición, campos ausentes significan `unknown`, no `eligible`, `private` ni `deduped`.

## 13. Frontend, UX e i18n

La UI de reglas debe mostrar, cuando exista:

- alcance: hotel legacy u oferta trackeada;
- tipo y umbral;
- baseline elegido;
- estado activa/pausada;
- último evento y fecha;
- cooldown o “se avisará de nuevo cuando cambie la condición”;
- razón de no evaluación si faltan datos;
- acción para pausar, editar o eliminar.

La lista de eventos debe distinguir:

```text
nuevo
duplicado suprimido (opcional, normalmente solo telemetría)
not_evaluable
provider_error
stale
provider_changed
availability_returned
```

No mostrar “bajada” si el baseline no es comparable. No usar color como única señal. Los mensajes y parámetros pasan por i18n ES/EN; nunca persistir copy traducido como clave de dedupe.

## 14. Handoffs

| Fase | Entrega H26 |
|---|---|
| H11-H12 | migración de fingerprints, ownership, índices y envelope V2 |
| H19 | elegibilidad de importe, fees, moneda y semántica total |
| H23-H25 | oferta, snapshots, baselines, freshness, confidence y reason codes |
| H27 | inbox privado, read-state, deep links y cuarentena de eventos legacy |
| H28 | in-app, plantillas, preferencias y delivery deduplicado |
| H29 | pausa, expiración, edición, borrado y retención de reglas/eventos |
| H31-H34 | UX de reglas/eventos, copy, responsive, i18n y accesibilidad |
| H36 | locks, índices, coste y concurrencia |
| H40 | tests unitarios, integración, contract, privacidad y visuales |
| H41 | métricas de fired/suppressed/not_evaluable, dedupe, cooldown y latencia |

## 15. Tests y evidencias requeridos

### Backend/unitarios

- validación de ownership y coherencia `tracked_offer_id`/`hotel_id`;
- regla sin tracking identificada como legacy, nunca como oferta privada;
- baselines previous/initial/target con contexto y snapshots correctos;
- no alerta sin baseline elegible;
- provider error/stale/fixture/incompatible no dispara;
- operadores y redondeo deterministas;
- transición fired → fired no duplica;
- clear → fired rearma y vuelve a emitir una vez;
- disponibilidad solo avisa en transición real;
- provider change no se convierte en price change automático;
- fingerprints estables pese a locale/copy distinto;
- cooldown y suppression por regla/oferta;
- concurrencia e índice único evitan duplicados;
- replay del mismo provider run no duplica;
- eventos sin owner no aparecen en consulta privada.

### Integración/API

- usuario B no puede crear regla sobre tracking de usuario A;
- usuario B no puede ver eventos de usuario A que sigue el mismo hotel;
- evento de sweep tiene owner/rule o queda fuera del inbox;
- dos sweeps idénticos producen un único evento visible;
- cambiar threshold/version crea identidad de evaluación explícita;
- V1 serializa sin romperse durante la doble lectura;
- payload V2 no filtra raw provider payload, labels, targets ni tokens.

### Frontend/QA

- formulario exige umbral correcto por tipo;
- regla legacy se etiqueta como alcance de hotel;
- baseline y estado de evaluación son legibles;
- cooldown no bloquea consulta histórica;
- eventos duplicados no aparecen como tormenta;
- provider error no aparece como bajada ni agotado;
- ES/EN, teclado, lector de pantalla, contraste y reduced motion;
- acciones de pausa/eliminación explican alcance y efecto en futuras alertas.

## 16. Gate H26

H26 puede considerarse implementada cuando:

- cada regla tiene alcance, owner, versión y parámetros válidos;
- solo se evalúan snapshots elegibles y baselines comparables;
- eventos tienen identidad determinista y metadata suficiente;
- cooldown y dedupe sobreviven a reintentos y concurrencia;
- una condición mantenida no produce repetición infinita;
- provider error, stale, fixture e incompatibilidad no disparan falsos positivos;
- reglas legacy por hotel están separadas de tracking privado;
- ningún evento privado se resuelve por `hotel_id` solamente;
- V1 y V2 coexisten con migración y rollback;
- H27 puede consumir eventos con ownership inequívoco;
- observabilidad mide fired, suppressed, not_evaluable, invalid, dedupe y latencia.

**Resultado H26:** el motor local de evaluación determinista, cooldown, rearmado, fingerprint, comparabilidad básica, metadata auditable de `initial_price`, tolerancia a carreras de unicidad y separación de observaciones legacy está implementado y cubierto por regresiones. Permanecen explícitamente fuera de este cierre: freshness avanzada H25, total/fees H19, scheduler/provider real, inbox/delivery H27-H28, lifecycle H29, concurrencia de scheduler H36 y QA visual/manual H40-H41.
