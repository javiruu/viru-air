# H29 — Lifecycle seguro de seguimientos: pausa, edición, expiración y eliminación

**Estado:** completa como contrato de lifecycle; implementación V2, migración, scheduler de expiración, archivado y QA E2E pendientes  
**Fecha:** 2026-08-05  
**Área:** producto / backend / DB / frontend / alertas / delivery / privacidad / QA  
**Fuente de verdad:** sí para la semántica de lifecycle de `HotelTrackedOffer` y sus entidades privadas  
**Fase del roadmap:** H29  
**Depende de:** [H22 — favorito frente a tracking](hoteles-favorite-vs-tracking-h22.md), [H23 — tracking desde oferta real](hoteles-real-offer-tracking-h23.md), [H24 — histórico](hoteles-price-history-curve-h24.md), [H25 — freshness y acciones](hoteles-freshness-confidence-actions-h25.md), [H26 — reglas y dedupe](hoteles-alert-rules-dedupe-h26.md), [H27 — inbox privado](hoteles-private-inbox-deeplinks-h27.md), [H28 — delivery](hoteles-delivery-retries-preferences-h28.md)  
**Relacionado con:** H09 sweeps, H10/H11 modelo y migración, H19 precio, H35 legal/retención, H37 coste, H38 ownership, H39-H43 QA/operación

> Pausar, editar, expirar y eliminar no son sinónimos. H29 protege la intención de la persona, evita que una suscripción siga consumiendo provider o enviando alertas por accidente y conserva el histórico solo mientras la política de retención y privacidad lo permitan.

## 1. Decisión de alcance

H29 gobierna el lifecycle de un seguimiento hotelero privado y de sus dependencias:

1. estados de lifecycle y transiciones válidas;
2. pausa/reactivación y sus efectos sobre sweeps, reglas, eventos y delivery;
3. edición de preferencias frente a cambios de identidad de la oferta;
4. expiración por checkout, fecha de policy o incapacidad persistente;
5. archivado reversible, si se implementa como estado persistido;
6. eliminación dura, retención y ausencia de `undo` implícito;
7. ownership, cascadas, huérfanos y borrado de cuenta;
8. idempotencia y carreras entre API, sweep, alertas y delivery;
9. migración V1→V2 y rollback;
10. copy, accesibilidad, métricas y gates.

H29 no elige provider, no define el valor de un snapshot, no decide si una bajada es alertable y no inventa delivery externo. Esas decisiones pertenecen a H05/H06/H09/H19/H24-H28. H29 solo decide si un tracking sigue siendo elegible para que esos sistemas actúen.

## 2. Estado actual comprobable (V1)

### 2.1. Representación y endpoints actuales

`HotelTrackedOffer` tiene hoy, entre otros, `user_id`, `hotel_id`, contexto de área, `check_in`, `check_out`, `guests`, `room_label`, `meal_plan`, `cancellation_policy`, `provider`, precios, `currency`, `is_active`, `created_at` y `updated_at`.

La API V1 expone:

- listar/crear `GET/POST /hotels/tracked-offers`;
- leer snapshots `GET /hotels/tracked-offers/{id}/snapshots`;
- actualizar `PATCH /hotels/tracked-offers/{id}`;
- eliminar `DELETE /hotels/tracked-offers/{id}`.

Las lecturas y mutaciones actuales comprueban ownership del tracking. H29 conserva esa regla, pero exige que también se aplique a snapshots, reglas, eventos, delivery intents y cualquier estado V2 derivado.

### 2.2. Lo que `is_active` significa hoy

`is_active=true/false` es un flag técnico. En V1:

- `false` funciona como pausa práctica;
- el tracking pausado debe quedar fuera de la elegibilidad normal del sweep;
- no existe un estado persistido separado `paused`, `expired` o `archived`;
- no hay auditoría de quién pausó, cuándo, por qué ni desde qué superficie;
- la UI y el backend no tienen todavía una semántica completa de reactivación;
- `is_active=true` no demuestra que el tracking tenga fechas, snapshot elegible, provider operativo ni policy de revalidación.

Por tanto, V1 no debe presentar una fila con `is_active=true` como tracking operativo si faltan las condiciones de H22/H23/H25.

### 2.3. PATCH actual y riesgo de identidad

El PATCH V1 permite mutar campos que pueden definir una oferta distinta, incluyendo fechas, provider, precios y condiciones como habitación, régimen o cancelación. Si se cambia uno de esos campos dentro de la misma fila:

- la serie histórica puede mezclar ofertas no comparables;
- el snapshot inicial deja de describir la identidad actual;
- las reglas pueden comparar baselines de estancias distintas;
- un deeplink o evento antiguo puede apuntar a una configuración que ya no existe.

H29 documenta este comportamiento como deuda de compatibilidad, no como semántica deseada. La implementación V2 debe separar edición de preferencias de una nueva versión o suscripción cuando cambie la identidad.

### 2.4. DELETE actual

El DELETE V1 es borrado duro del tracked offer. No debe llamarse archivado, pausa ni “quitar temporalmente”. No existe una garantía de `undo`, recuperación de snapshots o restauración del tracking después de responder correctamente.

La implementación debe verificar ownership antes de borrar. Un ID de otro usuario debe producir la respuesta de autorización/not-found definida por la política sin revelar fechas, precio, provider, snapshots o existencia privada.

### 2.5. Sweeps y expiración actuales

El sweep actual considera ofertas activas con fechas no nulas. No existe una transición hotelera persistida a `expired` al alcanzar `check_out`, ni un job de archivado/limpieza contractual. En consecuencia:

- el estado de la base puede permanecer `is_active=true` después de la estancia;
- un tracking sin fechas queda fuera de la selección, pero no necesariamente se explica como incompleto;
- pausar o borrar durante un sweep puede competir con una lectura previa del worker;
- H29 no puede afirmar que hoy no haya seguimientos huérfanos o activos indefinidamente.

La expiración V2 debe ser explícita, auditable, idempotente y segura frente a zona horaria, carreras y reintentos.

## 3. Modelo canónico V2

### 3.1. Estados

El estado canónico debe ser aditivo y no depender solo de un booleano:

| Estado | Significado | Sweep | Alertas/delivery | ¿Reversible? |
|---|---|---:|---:|---:|
| `pending_context` | faltan fechas, ocupación u otra dimensión necesaria | no | no | sí, completando datos |
| `pending_first_observation` | contexto suficiente, sin observación elegible todavía | según policy | no hasta observar | sí |
| `active` | elegible para revalidación según capability y policy | sí | sí, solo con evento válido | sí |
| `paused` | pausa explícita del usuario o policy | no | cancelar/suprimir trabajo futuro | sí, si aún es reactivable |
| `stale` | histórico existente fuera del TTL; requiere revalidación | según policy | no hasta policy explícita | sí |
| `unavailable` | provider/capability temporalmente no disponible | no o según policy | no generar señal favorable | sí |
| `expired` | checkout pasado o policy de finalización alcanzada | no | cancelar/suprimir trabajo futuro | normalmente no; nueva suscripción |
| `archived` | fuera de vistas activas, histórico conservado | no | no | sí solo mediante restore real |
| `deleted` | eliminado de la superficie y de datos privados conforme a retención | no | no | no por defecto |

`is_active` se mantiene como bridge durante la migración. El mapping mínimo es `true → active` solo después de validar contexto y policy; `false → paused` solo para filas no borradas y con la advertencia de que V1 no conserva metadata de la pausa.

### 3.2. Invariantes

- Un tracking pertenece a un único usuario y hotel canónico.
- Solo `active` y estados explícitamente habilitados por policy entran en sweeps.
- `paused`, `expired`, `archived` y `deleted` no crean nuevas alertas ni intents de delivery.
- Pausar o expirar no borra snapshots ni histórico automáticamente.
- Editar preferencias no cambia la identidad de la oferta.
- Cambiar identidad crea versión/suscripción nueva o una migración explícita de serie; nunca mezcla snapshots sin marcarlo.
- Un tracking borrado no reaparece por un retry tardío, replay de worker o respuesta cacheada.
- Todas las mutaciones comprueban ownership server-side y no confían en `user_id` enviado por cliente.
- El resumen de cuenta y el inbox no pueden mostrar un estado de otro usuario por resolver solo `hotel_id`.

## 4. Transiciones y acciones

### 4.1. Pausar

Pausar es una acción reversible mientras el tracking no haya expirado o sido eliminado:

1. comprobar ownership y versión esperada;
2. cambiar estado a `paused` de forma transaccional;
3. registrar `paused_at`, actor/surface y reason code;
4. impedir que nuevos sweeps lo seleccionen;
5. cancelar o suprimir intents de delivery futuros, sin borrar el evento histórico;
6. dejar intactos snapshots, histórico, reglas y configuración salvo que una policy específica indique lo contrario;
7. devolver el estado canónico y acciones disponibles.

Un sweep que ya adquirió un lease debe comprobar el estado antes de persistir snapshot, actualizar precio o publicar una alerta. Si no puede comprobarlo, debe fallar cerrado y reintentarse de forma segura, nunca ganar por haber leído `active` unos milisegundos antes.

### 4.2. Reactivar

Reactivar no es un simple `is_active=true`:

- validar que `check_out` siga siendo futuro según la zona horaria de la estancia/policy;
- validar contexto, provider/scope, capability, freshness policy y reglas asociadas;
- no reactivar una identidad incompleta como `active`;
- conservar el histórico anterior y marcar el momento de reanudación;
- evitar duplicar una alerta solo porque el tracking volvió a estar activo;
- devolver `pending_first_observation`, `stale`, `unavailable` o `active` según evidencia.

Un tracking `expired` no se “reactiva” cambiando un flag: la UX debe crear una nueva versión/suscripción o pedir una nueva estancia confirmada.

### 4.3. Edición: preferencias frente a identidad

| Campo/acción | ¿Editar en la misma suscripción? | Regla |
|---|---:|---|
| `target_price` | sí | preferencia privada; versionar/auditar el cambio |
| label/nombre privado | sí | no afecta matching ni snapshots |
| canales, quiet hours, digest | sí | pasa por H28; no cambia la oferta |
| idioma/moneda de presentación | sí, con cuidado | no reinterpretar el importe observado |
| `check_in/check_out` | no como mutación silenciosa | nueva versión o nueva suscripción; conservar serie anterior |
| ocupación/habitaciones/edades | no como mutación silenciosa | cambia la estancia y comparabilidad |
| habitación/régimen/cancelación | no como mutación silenciosa | cambia identidad de oferta |
| provider/provider scope | no como mutación silenciosa | nueva identidad o versión con baseline separado |
| `initial_price/current_price` | no desde cliente | solo observación/sweep autorizado |
| `hotel_id` | no | nuevo tracking; no trasladar histórico entre hoteles |

La UI debe distinguir “Editar preferencias” de “Cambiar estancia/oferta”. Al cambiar identidad, la confirmación debe mostrar qué se conserva, qué empieza de cero y si la acción pausa/expira la serie anterior.

### 4.4. Expirar

La expiración hotelera V2 se produce cuando:

- la fecha local de `check_out` ya ha pasado;
- una fecha de expiración explícita de policy se alcanza;
- el usuario pide finalizar el tracking;
- una migración/reconciliación clasifica la fila como no recuperable.

La comparación debe usar una zona horaria definida y documentada. No usar la zona del servidor de forma implícita ni expirar a medianoche UTC una estancia cuya semántica es local.

Al expirar:

1. adquirir una transición idempotente con control de versión/lock;
2. impedir nuevas selecciones de sweep;
3. cancelar/suprimir delivery futuro según H28;
4. conservar snapshots, alertas e historial con estado contextual;
5. mostrar “Finalizado” o “Estancia terminada”, no “error” ni “eliminado”;
6. permitir consultar histórico si la retención y ownership lo permiten;
7. no reactivar la misma serie si eso mezclaría una nueva estancia con la anterior.

Un proceso de reconciliación debe detectar filas `active` con checkout pasado y producir métricas de reparación. Hasta que exista ese job, la ausencia de filas expiradas no es evidencia de que el sistema esté limpio.

### 4.5. Archivar

`archived` solo puede existir si hay una columna/entidad persistida, endpoint/UI de recuperación, policy de retención y tests de restore. No se debe usar `is_active=false` como sinónimo de archivado.

Archivado recomendado:

- no participa en sweeps, alertas ni delivery;
- conserva snapshots e historial privado hasta su TTL;
- queda fuera de la lista activa por defecto;
- aparece en una vista histórica si el producto la ofrece;
- puede restaurarse solo con ownership y revalidación de fechas/capability;
- no convierte automáticamente una serie vieja en `active`.

### 4.6. Eliminar

Eliminar es destructivo respecto de la superficie de usuario y, según la policy, respecto de datos privados:

- pedir confirmación cuando se eliminen histórico o reglas asociadas;
- ejecutar la operación con ownership, transacción y resultado idempotente;
- bloquear o cancelar intents de delivery futuros;
- impedir que eventos o snapshots queden accesibles por deep link antiguo;
- no borrar tablas globales de provider, caché compartida o datos sin ownership por accidente;
- documentar qué se elimina ahora, qué se retiene por obligación legal/operativa y durante cuánto tiempo;
- no prometer `undo` si no existe tombstone/restore real.

Si V1 mantiene DELETE duro, el copy debe decir “Eliminar seguimiento”. Un futuro undo requiere un estado `deleted_pending_purge`, tombstone privado, ventana temporal, restauración probada y purge irreversible posterior.

## 5. Dependencias: snapshots, alertas y delivery

### 5.1. Snapshots e histórico

Pausar, expirar o archivar no elimina por defecto `HotelRateSnapshot`. El histórico debe conservar:

- ownership del tracking o referencia privada equivalente;
- identidad de estancia/oferta y versión;
- `observed_at`, provider, condiciones, moneda y freshness cuando existan;
- razón de exclusión si la observación no es comparable;
- retención hot/warm/cold definida por H11/H24/H35.

Los snapshots no deben quedar huérfanos: durante el backfill se comprueba la referencia a tracking, y si una migración no puede resolver ownership se clasifica `needs_review`/no entregable, no se publica en otro inbox.

### 5.2. Alert rules y eventos

Al pausar o expirar:

- las reglas asociadas dejan de evaluarse o quedan `paused/cancelled` con razón;
- eventos ya generados se conservan con ownership y estado histórico;
- no se crean nuevas alertas por un sweep que termine después de la transición;
- un evento pendiente de delivery se suprime/cancela conforme H28;
- la bandeja no debe borrar retrospectivamente un evento que la persona ya recibió, salvo policy legal explícita.

Al eliminar, las reglas, eventos privados, deeplinks y resúmenes derivados se borran o anonimizan conforme a la policy; nunca se dejan accesibles solo porque el `hotel_id` siga existiendo.

### 5.3. Delivery

H28 gobierna los intents de canal. H29 aporta el motivo `lifecycle_cancelled` y el orden de precedencia:

```text
deleted/expired/paused
  > ownership
  > consent/preferences
  > dedupe/cooldown
  > delivery
```

Un retry de email/push no puede revivir un tracking expirado ni enviar una alerta creada después de una pausa. Un evento histórico puede permanecer en inbox si H27 lo autoriza, pero su estado de delivery nuevo debe reflejar la cancelación.

## 6. Ownership, cascadas y borrado de cuenta

### 6.1. Ownership obligatorio

Filtrar por usuario autenticado en:

- tracking y sus versiones;
- snapshots e histórico;
- alert rules/events;
- delivery intents y preferencias;
- deep links, summaries, caches privadas y acciones bulk.

Un ID de otro usuario debe producir una respuesta indistinguible o estable según la política, sin confirmar fechas, precios, labels, provider o existencia. Dos usuarios pueden seguir el mismo hotel y la misma oferta sin compartir ninguna configuración, snapshot privado, regla o delivery.

### 6.2. Cascadas

La migración debe decidir y probar explícitamente:

| Entidad | Pausa/expira | Archiva | DELETE tracking |
|---|---|---|---|
| snapshots | conservar | conservar según TTL | borrar/retener según policy; nunca exponer |
| history aggregates | conservar/rotular | conservar según TTL | borrar/anonimizar según policy |
| alert rules | pausar/cancelar | ocultar/no evaluar | borrar o retener auditoría mínima |
| alert events | conservar estado | ocultar de activos | borrar/anonimizar según policy |
| delivery intents | suprimir/cancelar | no enviar | cancelar y purgar según H28 |
| watchlist favorite | no tocar | no tocar | no tocar |

El borrado de un tracking no debe borrar automáticamente el favorito del mismo hotel. El borrado de cuenta sí debe ejecutar el flujo de privacidad que cubra todos los datos privados de la cuenta, con retención legal mínima si aplica. Las filas globales de catálogo/provider/cache no se borran por FK de usuario.

### 6.3. Huérfanos y reconciliación

Debe existir un job o comando de auditoría que detecte:

- snapshots sin tracking/version ownership;
- reglas cuyo tracking no existe o es de otro usuario;
- eventos sin owner determinable;
- delivery intents de tracking `paused/expired/deleted`;
- filas `active` con checkout pasado;
- versiones duplicadas por retry/concurrencia.

La reparación debe ser conservadora: aislar, marcar `needs_review` o cancelar; no reasignar datos privados por coincidencia de hotel.

## 7. Idempotencia, concurrencia y rollback

### 7.1. Idempotencia

Pausa, reactivación, expiración y eliminación deben aceptar retries sin duplicar historial ni efectos:

- misma operación + misma versión devuelve el estado final existente;
- doble click no crea dos versiones ni dos eventos;
- DELETE repetido no confirma la existencia de datos privados eliminados;
- una expiración automática repetida no duplica métricas ni cancela dos veces un intent;
- el resultado incluye `state_version`/ETag o equivalente para detectar conflicto.

### 7.2. Carreras críticas

Probar al menos:

```text
sweep lee active       || usuario pausa
sweep lee active       || usuario elimina
sweep crea snapshot    || checkout expira
alert evaluator corre  || tracking cambia de oferta
email retry corre      || tracking se elimina
restore archived       || cleanup/purge vence
```

La solución puede usar transacción, optimistic locking, lease o lock compatible con H09/H28. Lo obligatorio es que el estado final no permita snapshot, alerta o delivery de una identidad que ya dejó de ser elegible.

### 7.3. Rollback

Toda migración H29 debe ser expand-and-contract:

1. añadir estado/version/auditoría sin retirar `is_active`;
2. backfill dry-run con métricas y `needs_review`;
3. doble lectura y shadow compare;
4. activar transiciones detrás de flag;
5. conservar bridge reversible;
6. purgar solo tras ventana y evidencia aprobadas.

Un rollback desactiva las nuevas transiciones sin reactivar automáticamente trackings que el usuario pausó o eliminó. El historial de lifecycle no debe reescribirse para ocultar el rollback.

## 8. API, frontend y copy

### 8.1. Envelope V2 objetivo

```json
{
  "id": "opaque-tracking-id",
  "state": "paused",
  "state_version": 4,
  "capabilities": {
    "pause": false,
    "resume": true,
    "edit_preferences": true,
    "edit_stay": true,
    "archive": false,
    "delete": true
  },
  "check_out": "2026-09-13",
  "last_observation_at": "2026-08-10T09:00:00Z",
  "history_available": true,
  "warnings": ["tracking_paused"]
}
```

No serializar `user_id`, target privado innecesario, tokens, payload raw ni provider secrets. `capabilities` debe derivarse server-side del estado, ownership y policy.

### 8.2. Acciones de UI

- Activo: “Pausar seguimiento”, “Editar preferencias”, “Cambiar estancia/oferta”, “Eliminar seguimiento”.
- Pausado: “Reanudar seguimiento”, “Ver histórico”, “Eliminar seguimiento”.
- Expirado: “Ver histórico”, “Crear nuevo seguimiento”; no “Reanudar” sobre la misma serie.
- Archivado: “Ver archivado”, “Restaurar” solo si existe restore real.
- Incompleto/unavailable: explicar qué falta o qué provider impide comprobar.
- DELETE duro: confirmación clara; no toast “deshecho” sin undo real.

El estado de lectura del inbox no confirma que el tracking esté activo. Un toast confirma la mutación inmediata, pero la lista persistente debe reflejar el estado devuelto por backend.

### 8.3. Accesibilidad e i18n

- botones con nombres distintos para pausar, reanudar, editar y eliminar;
- confirmaciones con foco gestionado y retorno de foco;
- estado anunciado sin depender solo del color;
- fechas y checkout en locale/timezone correcto;
- copy ES/EN consistente: “En pausa”, “Finalizado”, “Archivado”, “Eliminado” no son intercambiables;
- reduced motion, teclado, móvil y lector de pantalla cubiertos;
- errores 401/403/404/409/422 no se convierten en empty ni en éxito.

## 9. Migración V1→V2

### H29-A — Inventario y clasificación

Clasificar sin borrar:

```text
active_valid
active_incomplete
paused_legacy
checkout_past
duplicate_candidate
owner_unverifiable
identity_mutable_history
orphan_snapshot_or_rule
```

Generar métricas redacted y una cola de revisión. No inferir que `is_active=true` es `active_valid`.

### H29-B — Bridge de estado

- añadir `lifecycle_state`, `state_version`, timestamps de transición y reason codes de forma aditiva;
- mapear V1 con reglas conservadoras;
- mantener `is_active` sincronizado durante el bridge;
- no backfillear `paused_at`, `expired_at` o `archived_at` con una fecha inventada;
- marcar los valores desconocidos como legacy/unknown.

### H29-C — Identidad y versiones

- bloquear PATCH de campos de identidad para nuevas altas;
- convertir cambios de estancia/oferta en nueva versión/suscripción;
- preservar la serie anterior como `expired`, `archived` o `superseded` según decisión de producto;
- resolver duplicados antes de constraints nuevas;
- mantener idempotency key y optimistic locking.

### H29-D — Expiración y reconciliación

- job explícito con timezone, batch, lease, retry y métricas;
- dry-run que solo reporte checkout pasado;
- canary de transición a `expired`;
- verificación de que no se crean snapshots, alertas o delivery después;
- replay/rollback sin reactivar accidentalmente.

### H29-E — DELETE y retención

- definir ventana de purge, tombstones y datos retenidos;
- probar borrado de cuenta y tracking individual;
- impedir deeplinks antiguos y caches privadas después del borrado;
- no borrar catálogo ni provider cache global;
- documentar respuesta de retries y ausencia de undo V1.

## 10. Métricas y observabilidad

Eventos sin PII:

```text
hotel_tracking_paused
hotel_tracking_resumed
hotel_tracking_preference_updated
hotel_tracking_identity_change_started
hotel_tracking_version_created
hotel_tracking_expired
hotel_tracking_archived
hotel_tracking_restored
hotel_tracking_deleted
hotel_tracking_lifecycle_conflict
hotel_tracking_sweep_cancelled
hotel_tracking_delivery_cancelled
hotel_tracking_orphan_detected
hotel_tracking_reconciliation_completed
```

Propiedades allowlisted: `state_from`, `state_to`, `reason_code`, `surface`, `state_version`, `has_history`, `has_context`, `days_to_checkout`, `outcome`, duración y error estable. No incluir email, user ID crudo, target price, notas, URLs externas, tokens ni payload raw.

Métricas mínimas:

- activos con checkout pasado;
- pausas/reactivaciones y ratio de reactivación válida;
- cambios de identidad frente a cambios de preferencias;
- expiraciones automáticas y fallos de timezone;
- huérfanos por entidad y tiempo de reparación;
- snapshots/alertas/delivery cancelados tras lifecycle;
- conflictos de versión y retries idempotentes;
- borrados individuales y de cuenta según policy;
- intentos de acceso cruzado/IDOR.

## 11. Tests y gates

### Backend/DB

- pause/resume con ownership correcto y `state_version`;
- `is_active=false` excluido de sweep V1;
- checkout pasado no se presenta como activo en V2;
- expiración repetida es idempotente y usa timezone definida;
- edición de target/canales no rompe identidad;
- edición de fechas/ocupación/provider crea versión nueva o se rechaza, nunca mezcla snapshots silenciosamente;
- snapshots e histórico sobreviven a pausa/expiración según retention policy;
- reglas/eventos/delivery se pausan o cancelan sin nuevas emisiones;
- DELETE duro V1 no promete undo y no deja deeplink/cache privado accesible;
- dos usuarios con el mismo hotel permanecen aislados;
- IDOR en tracking, snapshots, reglas, eventos y acciones bulk devuelve respuesta segura;
- sweep concurrente con pausa, expiración y delete no publica resultados posteriores;
- retries no duplican estados, versiones, alertas ni delivery;
- borrado de cuenta cubre datos privados y no elimina catálogo/cache global;
- reconciliación detecta huérfanos y no reasigna por `hotel_id`.

### Frontend/contract/E2E

```text
crear tracking válido
  → pausar
  → comprobar que no hay sweep/alerta/delivery nuevo
  → ver histórico conservado
  → reanudar
  → cambiar target sin cambiar identidad
  → cambiar fechas y crear nueva versión
  → dejar pasar checkout
  → ver estado final y crear nuevo tracking
  → eliminar y comprobar que no hay undo ficticio
```

Cubrir loading, error, 401/403/404/409, doble click, refresh/back-forward, dos usuarios, dark/light, móvil, teclado, lector de pantalla, ES/EN y reduced motion.

### Gate de aceptación H29

H29 podrá considerarse implementada cuando:

1. V2 tenga estados persistidos y transiciones auditables, sin usar `is_active` como lifecycle completo;
2. pausar detenga sweeps, reglas y delivery futuro, conservando histórico según policy;
3. reanudar valide fechas, contexto, provider y capability;
4. editar preferencias no mezcle la identidad de una oferta;
5. cambiar estancia/oferta cree una versión/suscripción nueva o rechace la mutación;
6. checkout y policy expiren con timezone, lease/lock, idempotencia y métricas;
7. archived solo aparezca si existe restore real;
8. DELETE y retención estén definidos, con cascadas probadas y sin undo ficticio;
9. ownership e aislamiento se verifiquen en dos cuentas y en todas las entidades derivadas;
10. carreras sweep/lifecycle no creen snapshot, alerta o delivery fuera de lifecycle;
11. reconciliación detecte huérfanos, activos vencidos y delivery pendiente inválido;
12. migración V1→V2 sea aditiva, reversible y no invente timestamps;
13. frontend, i18n, a11y y estados de error reflejen la semántica real;
14. métricas y runbook permitan explicar cada transición.

**Resultado contractual:** H29 queda definida. V1 sigue teniendo pausa técnica por `is_active`, PATCH con riesgo de mutar identidad y DELETE duro; no existe todavía expiración hotelera automática ni archivado persistido. La implementación V2 y su evidencia quedan pendientes de las fases de ejecución y QA.
