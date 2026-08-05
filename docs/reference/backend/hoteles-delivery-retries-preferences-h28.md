# H28 — Delivery hotelero, reintentos, preferencias y quiet hours

**Estado:** completa como contrato de delivery; implementación de adapters externos, consentimiento por canal, endurecimiento hotelero y QA operativo pendientes  
**Fecha:** 2026-08-05  
**Área:** backend / infraestructura / producto / privacidad / frontend / QA / observabilidad  
**Fuente de verdad:** sí para la semántica de delivery hotelero, canales, reintentos, preferencias y quiet hours  
**Fase del roadmap:** H28  
**Depende de:** [H25 — freshness, confidence y acciones](hoteles-freshness-confidence-actions-h25.md), [H26 — reglas, baselines y deduplicación](hoteles-alert-rules-dedupe-h26.md), [H27 — inbox privado y deep links](hoteles-private-inbox-deeplinks-h27.md)  
**Relacionado con:** [contrato general de notificaciones](notifications-contract.md), [runbook del worker](../../runbooks/runbook-notification-worker.md), H09 sweeps, H29 lifecycle, H35 legal/consentimiento, H37 costes y límites, H38 seguridad, H40 QA, H41 observabilidad, H42 recovery, H43 flags

> Un evento hotelero persistido no equivale a una entrega externa. H28 debe poder explicar qué se generó, qué se puso en cola, qué canal se intentó, qué se confirmó, qué se reintentará y qué quedó definitivamente fallido.

## 1. Decisión de alcance

H28 define el tramo entre el evento autorizado de H26/H27 y el canal elegido por la persona:

1. separación entre generación, cola, adapter y estado final;
2. canales soportados y capacidades reales;
3. consentimiento, preferencias y quiet hours;
4. reintentos, backoff, límites e idempotencia;
5. estados `queued`, `sent`, `delivered`, `failed`, `suppressed` y `dead_letter`;
6. errores temporales frente a permanentes;
7. plantillas ES/EN y deep links seguros de H27;
8. ownership y no exposición de contenido entre cuentas;
9. observabilidad redacted, métricas y runbook;
10. migración V1→V2, fixtures, sandbox y gates operativos.

H28 no decide si una señal hotelera debe existir —eso corresponde a H26— ni quién puede verla —eso corresponde a H27—. Tampoco promete proveedor de email/push, frecuencia de sweeps, reserva o disponibilidad del partner. H29 gobierna la pausa, expiración y eliminación del seguimiento; H35 gobierna consentimiento, legal y disclosures.

## 2. Estado actual comprobable (V1)

### 2.1. Cola y dispatcher

El sistema actual usa `NotificationEvent` como ledger/cola persistida. Sus campos relevantes son:

```text
rule_id
channel
 delivery_status
attempts
next_attempt_at
last_error
delivered_at
dedupe_key
group_key
group_reason
is_digest
grouped_count
created_at
```

`dispatch_pending_events()`:

- selecciona eventos ligados a `AlertRule -> FlightWatch -> User`;
- en V1 no selecciona `HotelAlertEvent`: las señales hoteleras aparecen en el inbox mediante la agregación de H27, pero todavía no pasan por este dispatcher ni por un adapter de canal;
- pretende procesar estados `queued` y `failed` cuyo `next_attempt_at` ya venció, pero la consulta actual solo aplica explícitamente el vencimiento a `failed`; un `queued` con `next_attempt_at` futuro puede resultar elegible. H28 debe corregir este gap antes de tratar quiet hours como garantía operativa;
- respeta `NOTIFICATION_DISPATCH_BATCH_SIZE` y `NOTIFICATION_MAX_ATTEMPTS`;
- usa adapters internos para `in_app` y `email`;
- incrementa `attempts` antes de llamar al adapter;
- marca `in_app` como `delivered` cuando el adapter devuelve éxito;
- marca `email` como `sent` cuando el adapter devuelve éxito;
- conserva `delivered_at` y limpia `next_attempt_at/last_error` en éxito;
- reprograma fallos recuperables con backoff acotado;
- deja fallos agotados en `failed` con `next_attempt_at = null`.

La selección actual está construida para alertas de vuelos: se une a `AlertRule` y `FlightWatch`. H28 no debe afirmar que los `HotelAlertEvent` ya tienen delivery externo conectado a este dispatcher. Primero debe existir un evento/notificación hotelera con destinatario y relación contractual compatibles con H27.

### 2.2. Canales actuales

| Canal | V1 observable | Qué significa | Limitación |
|---|---|---|---|
| `in_app` | adapter que devuelve éxito local para `NotificationEvent` de vuelos | el evento de vuelo queda marcado en el ledger y puede aparecer en inbox | los `HotelAlertEvent` aún no pasan por este adapter; no prueba lectura, websocket ni entrega fuera de la API |
| `email` | adapter stub | permite probar estados y errores sin enviar correo | no hay proveedor externo ni correo real |
| `push` | no existe adapter operativo comprobable | no disponible | no debe aparecer como activado |
| `sms`/`webhook` | fuera del contrato actual | no disponible | no anunciar ni modelar como capacidad activa |

El caso de prueba `force_fail` del stub email es una fixture de test, no una simulación de un proveedor real ni una política de producción.

### 2.3. Worker y operación V1

`backend/app/worker/notifications.py` puede ejecutarse:

```bash
cd backend
python -m app.worker.notifications --once
python -m app.worker.notifications --loop --limit 50 --sleep-seconds 60
```

El worker está desactivado por defecto mediante `NOTIFICATION_WORKER_ENABLED=false` y no se arranca automáticamente con la API. Existe un endpoint manual de administración para `dispatch-pending`, pero no es un scheduler distribuido ni una garantía de ejecución hotelera.

Los logs de ciclo incluyen contadores como `processed`, `delivered`, `failed`, `retried` y `skipped`, sin payload de mensaje. Esto es una base útil, pero todavía no distingue de forma específica hotel, regla, canal, error temporal/permanente, supresión por consentimiento ni dead letter.

### 2.4. Reintentos V1

El backoff actual es determinista y pequeño:

- máximo configurable por `NOTIFICATION_MAX_ATTEMPTS`, por defecto 3;
- `2 ** (attempts - 1)` minutos, acotado a 30 minutos;
- respeta `next_attempt_at`;
- cuando se alcanza el máximo, deja el evento `failed` y lo cuenta como agotado.

V1 no tiene jitter, clasificación formal de errores, lease de delivery, outbox separada, DLQ dedicada ni garantía de exclusión concurrente. La columna `dedupe_key` existente no demuestra por sí misma que el dispatcher hotelero sea idempotente.

### 2.5. Preferencias y quiet hours V1

`UserPreference` contiene:

```text
quiet_hours_enabled
quiet_hours_start
quiet_hours_end
quiet_hours_timezone
language
preferred_currency
```

El dispatcher calcula la ventana en la zona horaria configurada y, si quiet hours está activa:

- retrasa `email` manteniéndolo `queued` y establece `next_attempt_at` al final de la ventana;
- deja que `in_app` siga siendo entregable para conservar trazabilidad interna;
- no implementa una matriz granular de consentimiento por canal;
- no permite aún reglas hoteleras de severidad, digest y excepción formalmente separadas.

Quiet hours no debe borrar el evento ni convertirlo en `failed`. Tampoco debe reinterpretar un provider error como una señal entregable.

## 3. Contrato objetivo V2 hotelero

### 3.1. Pipeline separado

La arquitectura objetivo es:

```text
HotelAlertEvent elegible (H26)
  → destinatario/ownership autorizado (H27)
  → DeliveryIntent versionado
  → cola/outbox transaccional
  → adapter por canal
  → intento y resultado
  → inbox/estado de delivery/telemetría
```

La generación de una señal no debe llamar directamente a un proveedor externo. El commit del evento y la creación del `DeliveryIntent` deben ser atómicos o recuperables mediante outbox. Un worker puede procesar después del commit sin perder la señal.

Campos mínimos de `DeliveryIntent`/equivalente V2:

```text
id
source_event_id
recipient_user_id
ownership_scope
channel
template_key
template_version
payload_reference
idempotency_key
attempt_count
status
available_at
last_attempt_at
next_attempt_at
provider_message_id nullable
error_code nullable
error_class nullable
created_at
updated_at
```

`payload_reference` debe apuntar a datos autorizados y versionados; no debe duplicar payload raw de provider ni secretos dentro de una cola pública.

### 3.2. Delivery at-least-once

La política de H28 es **at-least-once con consumidores/adapters idempotentes**, no exactly-once. Puede haber reintentos después de un timeout ambiguo; el receiver debe aceptar una `idempotency_key` estable y evitar dos envíos visibles cuando el proveedor lo soporte.

La clave debe derivarse del evento autorizado, destinatario, canal y versión de entrega, por ejemplo:

```text
hash(
  source_event_id
  + recipient_user_id
  + channel
  + template_version
)
```

No incluir email, token, umbral privado ni URL externa completa en una clave compartida o log. Un cambio de plantilla o una nueva transición de H26 crea una intención nueva de forma explícita.

### 3.3. Estados canónicos

| Estado | Significado | ¿Visible como alerta entregada? | Siguiente acción |
|---|---|---:|---|
| `queued` | intención persistida, aún no intentada o reprogramada | no | esperar worker |
| `suppressed` | no se intenta por opt-out, quiet hours/priority policy o dedupe | no por ese canal | mantener inbox si procede; registrar razón |
| `sending` | lease de intento adquirido | no | finalizar o recuperar lease |
| `sent` | adapter/proveedor aceptó el mensaje | depende del canal | esperar confirmación si existe |
| `delivered` | proveedor confirmó entrega o canal local la materializó | sí para ese canal | conservar evidencia |
| `failed_retryable` | fallo temporal o timeout recuperable | no | backoff y nuevo intento |
| `failed_permanent` | fallo no recuperable: dirección inválida, opt-out o payload inválido | no | no reintentar; explicar/configurar |
| `dead_letter` | fallo agotado o ambiguo enviado a cuarentena | no | alerta operativa y replay explícito |
| `cancelled` | seguimiento/evento ya no debe entregarse por lifecycle | no | conservar auditoría según H29 |

V1 puede seguir usando `queued`, `sent`, `delivered` y `failed`; el adapter/bridge debe mapearlos sin afirmar que `sent=email` equivale a `delivered`.

## 4. Canales, consentimiento y preferencias

### 4.1. In-app

In-app es el canal base de H27, pero en V1 hay que separar persistencia de dispatch: un `HotelAlertEvent` autorizado aparece en el inbox por la agregación de H27 aunque no exista email/push; eso no significa que el worker actual lo haya enviado. El dispatcher `in_app` existente procesa `NotificationEvent` de vuelos.

- un evento autorizado aparece en el inbox aunque no exista email/push;
- `read/unread` es estado de lectura, no confirmación de delivery externo;
- `in_app` no debe bloquearse por quiet hours si la política de producto mantiene la trazabilidad;
- toasts son una capa efímera y no sustituyen al inbox persistente;
- una señal stale/provider degraded conserva su copy honesto al abrirse.

### 4.2. Email

Email solo puede activarse cuando exista:

- consentimiento/opt-in registrable y revocable;
- dirección verificada y ownership de cuenta;
- template versionado ES/EN;
- provider/adapter real con sandbox y límites;
- allowlist de enlaces internos y partner conforme H27/H35;
- clasificación de bounce, complaint, rate limit, timeout y error permanente;
- logs redacted y mecanismo de unsubscribe;
- contract/integration tests y canary.

El stub actual **no** satisface estos requisitos. La aceptación del adapter por el dispatcher solo prueba el flujo interno del código.

### 4.3. Push

Push permanece `planned` hasta definir:

- dispositivo/token ownership y revocación;
- consentimiento por dispositivo/cuenta;
- expiración de tokens;
- proveedor y capacidades de deep link;
- rate limits, quiet hours y fallback a inbox;
- privacidad del texto en lock screen.

No se debe mostrar un control “push activo” mientras no exista esta evidencia.

### 4.4. Matriz de preferencia

El objetivo V2 es una preferencia explícita por usuario, canal y tipo de señal:

```text
(user_id, signal_kind, channel)
  enabled
  consented_at
  revoked_at
  quiet_hours_policy
  minimum_severity
  digest_mode
  locale
```

Prioridad recomendada:

1. bloqueo legal/opt-out;
2. lifecycle: tracking pausado/expirado/eliminado;
3. ownership de H27;
4. dedupe/cooldown de H26;
5. preferencia de canal;
6. quiet hours y digest;
7. envío.

Una preferencia no cambia el evento histórico ni lo borra del inbox. Solo decide si se crea/entrega esa intención de canal, con razón auditable.

## 5. Quiet hours, severidad y digest

### 5.1. Semántica

Quiet hours es una política de entrega, no una política de generación. H26 puede crear un evento válido durante la ventana; H28 decide si un canal se retrasa.

Para cada canal debe definirse:

- zona horaria de la cuenta;
- ventana normal y overnight;
- qué tipos/severidades pueden atravesarla;
- si se agrupan señales;
- cuándo expira el evento antes de enviarse;
- qué ocurre si el usuario cambia su preferencia durante la espera.

El MVP conserva la decisión V1: email se retrasa; in-app permanece disponible. Una futura excepción crítica debe ser explícita y no inferirse de `tone`.

### 5.2. Digest

Un digest puede agrupar solo eventos del mismo destinatario, canal, ventana y política de privacidad. No debe mezclar:

- cuentas distintas;
- hoteles/ofertas sin relación;
- señales con severidad incompatible;
- eventos stale con frescos sin copy diferenciado;
- provider errors con bajadas confirmadas.

La agrupación debe conservar `grouped_count`, IDs fuente autorizados, rango temporal y razón. H27 sigue siendo la fuente de verdad para la bandeja; un digest externo no concede acceso a un evento que el usuario no posee.

## 6. Retries, backoff y dead letter

### 6.1. Clasificación

| Clase | Ejemplos | Acción |
|---|---|---|
| `retryable` | timeout, 429, conexión, 5xx | reintentar con backoff y jitter |
| `permanent` | opt-out, email inválido, token expirado, template inválido | marcar fallo permanente, no insistir |
| `ambiguous` | timeout después de aceptar, respuesta perdida | reintentar con idempotency key o reconciliar |
| `invalid_domain` | evento sin ownership, snapshot no elegible, provider error | no entregar; cuarentena/métrica |
| `cancelled` | tracking pausado/expirado/eliminado | cancelar intención según H29 |

El mensaje del proveedor nunca se presenta directamente como copy de usuario. Se mapea a `error_code` allowlisted y se conserva detalle redacted para operación.

### 6.2. Backoff objetivo

El valor exacto se configura por entorno/política, pero debe cumplir:

- límite de intentos y ventana máxima;
- backoff exponencial acotado;
- jitter para evitar thundering herd;
- `next_attempt_at` persistido;
- lease/lock para evitar dos workers enviando la misma intención;
- replay manual explícito para dead letters;
- métrica de edad de cola y eventos agotados.

El backoff V1 de 2^n minutos, máximo 30 y tres intentos puede mantenerse como bridge, pero no se debe llamar producción robusta mientras falten clasificación, jitter y concurrencia.

### 6.3. Dead letter

V2 debe separar `dead_letter` lógico/operativo de un simple `failed` permanente. La cuarentena debe permitir:

- razón y clasificación;
- primera/última tentativa;
- proveedor/canal/template version;
- replay idempotente después de corregir la causa;
- no reinyectar eventos no autorizados;
- redacción y retención limitada.

Si se mantiene inicialmente en `NotificationEvent`, debe existir un estado/código inequívoco y un runbook equivalente. No prometer una cola física separada si la infraestructura no la tiene.

## 7. Hotel-native delivery

### 7.1. Fuentes válidas

Solo se puede entregar una señal hotelera cuando H26 haya producido un evento `triggered` elegible y H27 haya confirmado destinatario/ownership. Quedan fuera:

- favoritos simples sin regla/tracking;
- provider error o fallback inválido;
- snapshots no comparables o stale fuera de la política;
- eventos legacy huérfanos;
- eventos suprimidos por cooldown/dedupe;
- señales `not_evaluable`/`invalid`;
- fixtures, salvo canal de demo claramente rotulado.

### 7.2. Contenido mínimo

La plantilla debe tener:

- tipo de señal y hotel;
- alcance: tracking privado frente a regla hotelera general;
- estancia/condiciones mínimas cuando sean necesarias;
- valor observado y moneda si son comparables;
- `observed_at`/freshness comprensible;
- razón prudente de la alerta;
- acción interna H27 con deep link reautorizado;
- disclosure de que precio/disponibilidad pueden cambiar;
- no “reserva ahora” automático, garantía ni promesa de precio final.

El contenido externo no debe incluir IDs internos, email, thresholds privados innecesarios, payload raw, tokens ni URL arbitraria.

### 7.3. Provider degraded y stale

Si el evento describe un cambio histórico válido pero la última revalidación falló:

- el inbox puede conservar el histórico conforme H27;
- email/push deben usar copy de señal histórica o suprimirse según freshness policy;
- nunca decir “hemos encontrado disponibilidad” si solo existe un snapshot antiguo;
- un provider error actual no crea una alerta favorable.

## 8. Observabilidad, privacidad y seguridad

Eventos de telemetría allowlisted:

```text
hotel_delivery_intent_created
hotel_delivery_suppressed
hotel_delivery_queued
hotel_delivery_attempted
hotel_delivery_sent
hotel_delivery_confirmed
hotel_delivery_retry_scheduled
hotel_delivery_failed
hotel_delivery_dead_lettered
hotel_delivery_cancelled
hotel_delivery_preference_blocked
hotel_delivery_quiet_hours_delayed
hotel_delivery_provider_degraded
```

Metadata permitida:

- `source_type`, `event_kind`, `channel`, `ownership_scope` no sensible;
- `template_version`, `provider_code`, `error_class`, `attempt_number`;
- duración, cola, estado, razón allowlisted y flags de freshness;
- IDs opacos con retención definida.

No registrar:

- email completo, tokens, secretos o device tokens;
- payload raw del provider;
- URL externa completa;
- thresholds, notas o labels privados salvo necesidad operacional redacted;
- mensaje íntegro cuando pueda contener datos de estancia sensibles.

La cola, logs y caches deben particionarse por ownership/recipient cuando el contenido sea privado. El delivery no puede convertirse en un canal lateral que salte las garantías de H27.

## 9. Compatibilidad y migración V1→V2

1. Mantener `NotificationEvent` y estados V1 durante el bridge.
2. Añadir `source_type/source_id`, scope de ownership y versión de template sin romper eventos de vuelos.
3. Crear adaptador hotelero que solo acepte eventos H26/H27 elegibles.
4. Mapear `queued/sent/delivered/failed` V1 a estados V2 sin llamar delivered a un `sent` de email.
5. Habilitar in-app hotelero primero con fixtures y tests de dos usuarios.
6. Mantener email en stub/sandbox hasta provider, consentimiento, unsubscribe y canary.
7. No activar push por tener un tipo de canal en frontend.
8. Introducir idempotency key, clasificación de error, lease y replay antes de aumentar frecuencia.
9. Medir colas, retries, supresión, errores y eventos sin owner.
10. Rollback por flag a inbox-only sin borrar eventos históricos.

## 10. Tests y gates

### Backend unit/integration

- evento hotelero sin ownership no crea intención de delivery;
- favorito simple no dispara email/push;
- usuario A no recibe intención de usuario B aunque compartan hotel;
- un evento hotelero autorizado queda disponible en inbox aunque no dependa de proveedor externo, y una futura intención `in_app` hotelera no se duplica por reintentos;
- email stub nunca realiza una llamada de red;
- email/push sin consentimiento quedan `suppressed` con razón auditable;
- quiet hours retrasa email, conserva `next_attempt_at` y no lo marca como failed;
- in-app respeta la política definida y no se duplica por reintentos;
- 429/timeout/5xx son retryable; opt-out/email inválido son permanentes;
- `next_attempt_at`, backoff, límite de intentos y lease se respetan;
- dos workers concurrentes no generan dos envíos visibles para la misma idempotency key;
- timeout ambiguo puede reintentarse sin duplicar en un receiver idempotente;
- dead letter permite replay explícito y no reinyecta eventos huérfanos;
- provider error/stale no se copia como “disponibilidad confirmada”;
- logs no contienen PII, tokens, URLs externas completas ni payload raw.

### Frontend/contract

- estado `queued/suppressed/retrying/failed` no se presenta como `delivered`;
- inbox sigue mostrando señal persistida aunque email esté pendiente/fallido;
- copy ES/EN distingue evento, entrega y lectura;
- enlaces de email/push abren deep links H27 internos y reautorizados;
- preferencias y quiet hours no borran historial;
- categoría/canal no rompe el normalizador ni el summary;
- error de delivery no se presenta como ausencia de alerta.

### Operación/browser

- worker `--once` y `--loop` tienen runbook y health/logs observables;
- worker desactivado no se interpreta como delivery activo;
- canary sandbox verifica template, idioma, enlaces y unsubscribe;
- retry con reloj controlado y fallo permanente reproducible;
- dos cuentas aisladas en inbox, resumen, delivery y deep link;
- dark/light, móvil, teclado, foco y reduced motion para estados de alerta;
- consola limpia y ningún request externo desde el stub.

## 11. Gates de aceptación H28

H28 podrá considerarse implementada cuando:

1. el evento hotelero, la intención de delivery y el estado final estén separados y trazables;
2. los eventos hoteleros autorizados estén disponibles como inbox privado H27 y, si se les aplica un dispatcher `in_app`, ese dispatch esté verificado por separado sin confundir persistencia con entrega;
3. email/push solo se anuncien donde exista adapter, consentimiento, provider, sandbox, límites y canary verificables;
4. la selección de cola excluya `queued` con `next_attempt_at` futuro y respete leases/concurrencia;
5. la semántica sea at-least-once con idempotencia, no exactly-once implícito;
6. retries, backoff, `next_attempt_at`, lease, clasificación de errores y dead letter/replay sean operables;
7. quiet hours y preferencias sean por canal, explícitas y no destructivas;
8. un evento stale/provider degraded no se entregue con copy de disponibilidad actual;
9. ownership de H27 se conserve en cola, template, logs y deep link;
10. ES/EN, unsubscribe, privacidad, accesibilidad y disclosures pasen QA;
11. worker manual, scheduler y flags indiquen con honestidad si delivery está activo;
12. métricas permitan localizar generación, cola, adapter, provider, retries, supresión y fallo;
13. rollback a inbox-only sea posible sin perder eventos ni reabrir fugas entre usuarios.

**Resultado contractual:** H28 queda definida. La existencia del worker, del stub email, de `delivery_status` o de quiet hours para un canal no basta para declarar delivery hotelero externo listo.
