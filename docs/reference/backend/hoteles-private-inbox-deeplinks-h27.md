# H27 — Inbox privado hotelero, ownership y deep links correctos

**Estado:** completa como contrato de privacidad y navegación; implementación de ownership estricto, migración de eventos legacy, deep links contextuales y QA pendientes  
**Fecha:** 2026-08-05  
**Área:** backend / frontend / producto / privacidad / seguridad / QA / observabilidad  
**Fuente de verdad:** sí para la semántica de inbox hotelero, ownership, lectura y deep links  
**Fase del roadmap:** H27  
**Depende de:** [H18 — navegación y detalle hotelero](../frontend/hoteles-detail-navigation-h18.md), [H21 — matriz de estados](../frontend/hoteles-state-matrix-h21.md), [H22 — favorito frente a tracking](hoteles-favorite-vs-tracking-h22.md), [H23 — tracking desde oferta real](hoteles-real-offer-tracking-h23.md), [H26 — reglas, baselines y deduplicación](hoteles-alert-rules-dedupe-h26.md)  
**Relacionado con:** [contrato general de notificaciones](notifications-contract.md), H28 delivery, H29 lifecycle, H31-H35 UX/i18n/a11y/legal, H38 seguridad, H40 QA, H41 observabilidad

> Una señal hotelera solo puede aparecer en el inbox de quien posee la regla, el tracking o la suscripción que la originó. Un `hotel_id` compartido no es ownership.

## 1. Decisión de alcance

H27 define el último tramo entre un evento hotelero elegible de H26 y la persona que debe verlo:

1. fuentes admisibles del inbox privado;
2. ownership verificable por usuario y por origen;
3. estado `read/unread` sin mutar el evento fuente;
4. selección y expiración de eventos legacy;
5. contrato de deep link para detalle, tracking, snapshot y regla;
6. validación de rutas internas y bloqueo de open redirects;
7. estados parciales, fallidos, stale y no disponibles;
8. compatibilidad con `/api/v1/notifications` y el centro actual;
9. migración, auditoría, retención y privacidad;
10. gates backend, frontend, accesibilidad y browser QA.

H27 **no** implementa el motor de reglas/cooldown de H26, el delivery externo de H28 ni el lifecycle de H29. Un evento visible en el inbox demuestra persistencia y ownership de la señal, no entrega por canales externos ni disponibilidad actual del partner.

## 2. Estado actual comprobable (V1)

### 2.1. Inbox común y lectura

La API autenticada `/api/v1/notifications` agrega:

- `notification_event` de alertas de vuelos;
- `hotel_alert_event` de hoteles;
- `security_activity`;
- `community_trending` para rutas vigiladas.

El estado se guarda en `user_notification_state` con la clave única `(user_id, source_type, source_id)`. La ausencia de fila significa `unread`; una fila con `read_at` significa `read`. El evento fuente no se modifica.

`POST /notifications/{source_type}/{source_id}/read` valida pertenencia antes de escribir el estado y devuelve `404 notification_not_found` tanto para una fuente inexistente como para una fuente ajena. Esto evita confirmar a un usuario que otro usuario sí tiene un evento.

El endpoint de `read-all` opera sobre los elementos que el backend puede listar dentro de sus límites; no debe interpretarse como una operación histórica ilimitada si la bandeja está paginada o acotada.

### 2.2. Ownership hotelero actual

La lectura actual de hoteles usa dos caminos:

1. si el evento enlaza una regla, intenta resolver `HotelAlertRule.user_id`;
2. como fallback, considera propietario a cualquier usuario con `HotelTrackedOffer` del mismo `hotel_id`.

El segundo camino es inseguro para señales privadas: dos usuarios pueden seguir el mismo hotel y un evento sin `rule_id` puede aparecer a ambos aunque solo uno haya originado la observación. H27 lo trata como deuda de privacidad bloqueante.

La consulta del listado también filtra eventos por conjuntos de `hotel_id` derivados de reglas o trackings del usuario. Ese filtro es útil como compatibilidad V1, pero no es una autorización suficiente para H27. El mismo riesgo se replica en `count_notification_summary()`, que calcula `total`, `unread` y `price` hotelero mediante esos conjuntos; por tanto, un contador puede incluir una señal de otra cuenta aunque la UI no muestre exactamente el mismo conjunto. `mark_read()` puede aceptar una fuente ajena por el fallback del mismo hotel, y `read-all` reutiliza `list_notification_inbox()`, de modo que también puede escribir estados de lectura sobre eventos no autorizados. Los tres caminos deben migrar juntos.

### 2.3. Eventos legacy

H26 documenta que el sweep puede crear `HotelAlertEvent` sin `rule_id`. Los campos actuales no garantizan por sí solos una relación con:

- `tracked_offer_id`;
- una regla concreta;
- una suscripción del usuario;
- un snapshot antes/después comparable;
- un fingerprint de deduplicación.

Durante la migración, un evento legacy sin ownership determinista debe quedar fuera del inbox privado o mostrarse únicamente en una superficie administrativa/operativa autorizada. No se debe “repartir” por `hotel_id` para evitar perderlo.

### 2.4. Deep link actual

`hotel_alert_item()` genera actualmente:

```text
/hoteles?hotel_id=<hotel_id>
```

Esto abre el detalle básico, pero no conserva de forma explícita:

- `tracked_offer_id`;
- `rule_id`;
- `snapshot_id` o evento de origen;
- fechas, ocupación y condiciones de la oferta;
- una intención de retorno desde el inbox.

La normalización frontend acepta solo rutas internas que empiezan por `/` y no por `//`, y descarta URLs con barra invertida. Esa defensa debe conservarse, pero no sustituye la autorización backend ni la comprobación de contexto al abrir el destino.

### 2.5. Compatibilidad frontend

El backend ya puede devolver `community` como categoría y `community_trending` como fuente. El modelo frontend de señales V1 todavía enumera categorías y fuentes más estrechas en algunos módulos. H27 debe cerrar esta divergencia mediante tipos/normalización compatibles, sin descartar una señal válida ni relajar la validación de identidad.

## 3. Modelo de ownership objetivo (V2)

### 3.1. Principio

Cada item debe poder responder:

```text
¿Quién es el destinatario?
¿Qué relación posee con la señal?
¿Qué entidad privada autoriza el acceso?
¿Qué contexto mínimo puede abrirse?
```

La autorización se resuelve con una cadena de ownership explícita, no por coincidencia de hotel:

```text
user
 └─ owns HotelAlertRule
      └─ targets HotelTrackedOffer (opcional)
           └─ observes HotelRateSnapshot / provider run
                └─ emits HotelAlertEvent
```

Para una regla legacy sin tracking:

```text
user ─ owns HotelAlertRule ─ targets HotelProperty
```

La regla sigue siendo de alcance hotel/catálogo y el copy debe decirlo. No puede atribuir al usuario una oferta privada que no está vinculada.

### 3.2. Requisitos de integridad

Antes de persistir o exponer una señal privada, el backend debe comprobar:

1. `rule.user_id == current_user.id` cuando exista regla;
2. `tracked_offer.user_id == current_user.id` cuando exista tracking;
3. `tracked_offer.hotel_id == event.hotel_id`;
4. `rule.tracked_offer_id == tracked_offer.id` cuando ambos existan;
5. snapshot, provider run y evento pertenecen a la misma identidad de estancia definida por H23/H26;
6. el evento no fue marcado `invalid`, `provider_error`, `fixture` o `orphaned`;
7. el evento conserva una razón y un fingerprint auditables;
8. la autorización se revalida al listar, leer y abrir el deep link.

Si no puede probarse la cadena completa, el resultado público es `not_found` o `not_allowed` sin revelar cuál de las comprobaciones falló.

### 3.3. Favorito frente a tracking

Un `HotelWatchlistItem` solo prueba que el usuario guardó un hotel. No autoriza:

- ver snapshots privados de otra persona;
- recibir una alerta de una oferta ajena;
- abrir un tracking que el usuario no posee;
- inferir que el hotel tiene precio actualizado para ese usuario.

El inbox puede mostrar una señal general de catálogo únicamente si existe una regla legacy explícita del usuario y el copy mantiene alcance general. Para señales con precio, estancia o baseline privado se exige `tracked_offer_id`/subscription.

## 4. Contrato de item de inbox

La forma V1 compatible mantiene:

```json
{
  "id": "hotel_alert_event:evt_123",
  "source_type": "hotel_alert_event",
  "source_id": "evt_123",
  "category": "price",
  "tone": "success",
  "title": "Ha aparecido una señal favorable",
  "body": "La oferta observada ha bajado frente a tu referencia.",
  "route_label": "Madrid",
  "action_href": "/hoteles?hotel_id=hotel_123",
  "created_at": "2026-08-05T10:00:00Z",
  "read_at": null,
  "is_read": false
}
```

El envelope V2 añade metadata no sensible y explícita. Los `tracked_offer_id`, `rule_id` y `snapshot_id` del ejemplo son referencias privadas no autorizantes: la API actual todavía no los emite en el `action_href`, y aun cuando se incorporen no conceden acceso por aparecer en la URL. El backend debe revalidar ownership en cada lectura y el cliente debe degradar de forma segura si la sesión, oferta o snapshot ya no coinciden.

```json
{
  "state": "success",
  "ownership": {
    "scope": "tracked_offer",
    "relationship": "owner",
    "authorized": true
  },
  "context": {
    "hotel_id": "hotel_123",
    "tracked_offer_id": "opaque-id",
    "rule_id": "opaque-id",
    "snapshot_id": "opaque-id",
    "event_id": "opaque-id"
  },
  "deep_link": {
    "kind": "hotel_tracking_snapshot",
    "href": "/hoteles?hotel_id=hotel_123&tracked_offer_id=opaque-id&snapshot_id=opaque-id&source=notifications"
  },
  "freshness": {
    "status": "observed|stale|unknown",
    "observed_at": "2026-08-05T10:00:00Z"
  },
  "warnings": []
}
```

Los IDs de contexto pueden ser opacos, pero no deben incluir tokens, email, `user_id`, payload raw de provider ni umbrales privados en una URL compartible. Si un identificador exige sesión, la ruta debe degradar de forma segura cuando la sesión cambie.

## 5. Estados del inbox

H27 consume la taxonomía H21 y añade semántica de autorización:

| Estado | Significado | Presentación | Acción |
|---|---|---|---|
| `idle` | no se ha cargado la bandeja | estado inicial | cargar |
| `loading` | consulta en curso | estado Boneyard sin borrar contexto | esperar |
| `success` | items autorizados y válidos | lista normal | abrir/marcar |
| `success_empty` | respuesta válida sin items visibles | empty honesto | volver a reglas o buscar |
| `partial` | alguna fuente falla, otras son utilizables | conservar válidas + aviso | reintentar fuente |
| `stale` | item persistido fuera de freshness preferida | fecha y advertencia | revisar/revalidar |
| `provider_degraded` | evento operativo no confirma precio actual | no decir “precio disponible” | abrir histórico o reintentar |
| `auth_required` | sesión ausente/expirada | conservar intención segura | autenticar |
| `not_allowed/not_found` | entidad ajena, borrada u opaca | no revelar diferencia | volver a inbox |
| `error` | fallo de lectura | no sustituir por empty | reintentar |

Un evento puede ser visible y estar `stale`; el inbox conserva el registro histórico, pero el deep link debe informar que no representa necesariamente el precio actual. Un evento no equivale a delivery externo ni a reserva disponible.

## 6. Deep links canónicos

### 6.1. Clases permitidas

| `kind` | Destino mínimo | Requiere ownership |
|---|---|---:|
| `hotel_detail` | `/hoteles?hotel_id=H` | hotel público o acceso válido |
| `hotel_tracking` | `/hoteles?hotel_id=H&tracked_offer_id=T&source=notifications` | tracking del usuario |
| `hotel_alert_rule` | `/notifications?view=rules&rule_id=R&hotel_id=H` | regla del usuario |
| `hotel_alert_event` | `/hoteles?hotel_id=H&event_id=E&source=notifications` | evento del usuario |
| `hotel_tracking_snapshot` | detalle + `tracked_offer_id` + `snapshot_id` | tracking y snapshot del usuario |

El servidor puede entregar un `href` interno, pero el destino debe volver a verificar los parámetros. Nunca se concede acceso privado por confiar en que el usuario llegó desde una notificación legítima.

### 6.2. Reglas de construcción

- usar `URLSearchParams`/builder canónico, no concatenación de strings sin escape;
- incluir solo contexto necesario para la acción;
- conservar `source=notifications` como contexto de UX/telemetría, no como autorización;
- no incluir `returnUrl` arbitrario;
- si se requiere retorno, usar una allowlist de rutas internas o no incluirlo;
- no pasar IDs de otra cuenta aunque el evento sea visible por un bug legacy;
- si el tracking o snapshot ya no existe, abrir el detalle hotelero público/permitido con warning, no un panel vacío que parezca operativo;
- si el usuario no está autorizado, mostrar `not_found`/`not_allowed` genérico y no nombre, precio, fecha ni regla ajena;
- la navegación externa al partner queda fuera del deep link de inbox y sigue H18/H35: allowlist, disclosure y retorno seguro.

### 6.3. Preservación de H18

Un deep link hotelero desde inbox debe conservar o reconstruir únicamente el contexto permitido:

- `hotel_id` seleccionado;
- `tracked_offer_id` si pertenece al usuario;
- fechas, huéspedes, habitación, régimen y cancelación si ya son parte de la oferta autorizada;
- snapshot/evento seleccionado si sigue disponible;
- origen de navegación no sensible.

No debe inventar filtros de búsqueda, borrar el contexto actual sin confirmación ni serializar datos privados en una URL que el usuario comparta accidentalmente. Si no existe contexto suficiente, abrir el hotel en modo standalone limitado conforme H18.

## 7. Lectura, unread y concurrencia

### 7.1. Estado privado

La lectura es una proyección del usuario:

```text
(user_id, source_type, source_id) → read_at
```

- dos usuarios pueden tener estados de lectura distintos para señales que ambos poseen legítimamente;
- marcar leído no borra ni modifica el evento;
- repetir la operación es idempotente;
- leer un origen ajeno devuelve el mismo `404` genérico;
- no se crea estado de lectura para una fuente que no puede autorizarse;
- `read-all` solo marca elementos visibles/permitidos por la consulta vigente.

### 7.2. Duplicados y eventos nuevos

La identidad visible del item debe derivar de `source_type:source_id`. H26 decide si dos eventos son el mismo cambio; H27 no debe deduplicar por título, hotel, fecha o texto.

Si H26 emite un evento nuevo con fingerprint distinto, aparece como item nuevo aunque el hotel sea el mismo. Si el evento está suprimido por cooldown, no debe aparecer como una notificación visible nueva.

### 7.3. Paginación y límites

Los límites de inbox deben ser explícitos. El summary de navegación debe documentar si es global, paginado o acotado por fuente. Un contador no puede prometer “todas” las señales si solo consulta una ventana limitada.

La paginación V2 debe ordenar por `created_at` e ID estable y evitar duplicados entre páginas. Marcar leído no debe cambiar el orden histórico ni hacer desaparecer el item de la vista `all`.

## 8. Compatibilidad y migración de legacy

### 8.1. Política de exposición

Durante la transición:

| Evento | Acción H27 |
|---|---|
| regla + `user_id` válido | exponer al usuario propietario |
| regla + tracking coherente | exponer con scope `tracked_offer` |
| sin regla, tracking coherente y owner verificable | migrar a relación explícita antes de exponer |
| sin `rule_id` y solo `hotel_id` | no exponer en inbox privado |
| provider error/fallback inválido | no crear/no exponer |
| evento huérfano o inconsistente | cuarentena operativa, métrica y no revelar |

No se debe borrar automáticamente el histórico legacy antes de conservar evidencia operativa, contar huérfanos y definir rollback.

### 8.2. Migración propuesta

1. medir eventos sin `rule_id` y relaciones ambiguas;
2. añadir vínculo explícito a tracking/suscripción o tabla de destinatarios;
3. backfill solo con evidencia inequívoca;
4. marcar `legacy`, `migrated`, `orphaned` o `invalid`;
5. cambiar list/read a joins por ownership explícito;
6. ocultar eventos ambiguos del inbox privado;
7. mantener endpoint de lectura con `404` genérico;
8. activar flag de compatibilidad y observar falsos positivos/negativos;
9. retirar el fallback por `hotel_id` después de completar la ventana de migración;
10. conservar rollback que no vuelva a exponer eventos entre usuarios.

### 8.3. Cache y SSR

Los items y summaries ligados a usuario deben ser `private`/no-store o estar particionados por identidad autenticada. No se pueden reutilizar caches compartidas de búsqueda para:

- items de inbox;
- `read_at`;
- tracking, regla, snapshot o `has_tracking`;
- deep links calculados desde ownership.

## 9. Copy, i18n y accesibilidad

Copy mínimo:

- favorable: “Hay una señal favorable para tu seguimiento”;
- legacy/general: “Hay una actualización sobre este hotel”;
- stale: “Señal guardada del 5 ago.; el precio puede haber cambiado”;
- provider degradado: “No hemos podido confirmar una tarifa nueva”;
- sin contexto: “Abre el hotel para revisar los datos disponibles”;
- no autorizado: no mostrar copy que confirme la existencia de la entidad ajena.

Prohibido:

- “Reserva ahora” como consecuencia automática de un evento;
- “precio garantizado” o “disponibilidad asegurada”;
- “tu oferta” para una regla legacy por hotel;
- “no hay alertas” cuando la API falló;
- mostrar IDs internos, emails o mensajes de provider.

Requisitos:

- ES/EN para títulos, bodies, estados y errores;
- el tono no puede depender solo del color;
- el item tiene nombre accesible, fecha legible, estado de lectura y acción concreta;
- `aria-live` se usa para cambios relevantes, no para toda la lista;
- el deep link devuelve foco al título o a la acción de origen cuando sea posible;
- teclado, Escape, zoom, dark/light y reduced motion pasan H31-H34.

## 10. Observabilidad y seguridad

Registrar eventos allowlisted sin PII:

```text
hotel_inbox_loaded
hotel_inbox_partial
hotel_inbox_item_opened
hotel_inbox_item_marked_read
hotel_inbox_marked_all_read
hotel_inbox_source_rejected
hotel_inbox_legacy_quarantined
hotel_deeplink_built
hotel_deeplink_opened
hotel_deeplink_context_missing
hotel_deeplink_not_allowed
hotel_deeplink_not_found
```

Metadata permitida:

- `source_type`, `event_kind`, `ownership_scope` no sensible;
- `state`, `reason_code`, `has_tracking`, `has_snapshot` booleanos;
- duración, resultado y versión de contrato;
- IDs opacos solo si la política de retención lo permite.

No registrar URLs externas completas, tokens, email, `user_id` en claro, thresholds privados ni payloads raw.

Alarmas mínimas:

- eventos hoteleros sin owner;
- lecturas rechazadas legítimas/ajenas;
- fallback por `hotel_id` usado después de la migración;
- divergencia frontend/backend de categorías/fuentes;
- deep links que pierden contexto o producen 404 inesperados;
- items visibles en más de una cuenta sin relación válida.

## 11. Tests y gates

### Backend unit/integration

- evento con regla solo aparece al `rule.user_id`;
- tracking del mismo hotel de otro usuario no autoriza el evento;
- regla y tracking cruzados se rechazan;
- evento sin `rule_id` no se reparte por `hotel_id`;
- evento legacy inequívocamente migrado conserva owner correcto;
- provider error/fallback inválido no llega al inbox;
- `read` de fuente ajena devuelve el mismo 404 que fuente inexistente;
- `read-all` no escribe estados para items no autorizados;
- repetir `read` es idempotente;
- eventos nuevos con fingerprints distintos no se colapsan en H27;
- summary y paginación respetan su semántica documentada;
- account deletion elimina estados privados sin tocar eventos de otros usuarios.

### Frontend unit/contract

- normaliza `hotel_alert_event` y `community_trending` sin perder identidad; en V1 `notificationInboxModel.ts` todavía excluye `community` de `NotificationCategory` y `community_trending` de `NotificationSourceType`, aunque el backend ya los devuelve;
- descarta items sin `source_type/source_id` válidos;
- acepta solo `action_href` interno allowlisted;
- conserva `read_at`/`is_read` coherentes;
- deep link con contexto abre tracking/snapshot cuando existe;
- contexto ausente degrada a detalle seguro con warning;
- 401/403/404 no se muestran como empty;
- categoría community no rompe summary ni filtros;
- no se serializan tokens, emails ni retornos arbitrarios.

### Browser QA

- abrir una señal hotelera desde inbox lleva al hotel correcto;
- una señal de tracking conserva fechas/condiciones y permite volver a inbox;
- refresh del deep link no filtra ni pierde autorización;
- usuario A no puede abrir evento de usuario B cambiando IDs;
- usuario A no puede listar, contar, marcar como leído ni marcar con `read-all` un evento de usuario B que comparta `hotel_id`;
- marca individual y `read-all` actualizan badge y timeline;
- evento stale/provider degraded muestra copy correcto;
- desktop/mobile, teclado, foco, lector de pantalla, dark/light y reduced motion;
- consola limpia, sin open redirects ni requests duplicados.

## 12. Gates de aceptación H27

H27 podrá considerarse implementada cuando:

1. ningún evento privado se autorice por `hotel_id` solamente, ni en listado, summary, `mark_read` o `read-all`;
2. reglas, tracking, snapshots y eventos tengan ownership trazable;
3. eventos legacy ambiguos queden fuera del inbox privado o migrados con evidencia;
4. `read/unread` sea privado, idempotente y no mute el evento fuente;
5. deep links sean internos, contextuales, allowlisted y reautorizados al abrir;
6. el detalle respete H18 y no exponga tracking/snapshot ajeno;
7. estados partial, stale, provider error, auth y not-found no se conviertan en empty engañoso;
8. backend y frontend compartan categorías, fuentes y envelope sin descartar señales válidas;
9. los límites/summary/paginación indiquen qué ventana representan;
10. tests de aislamiento entre dos usuarios pasen;
11. browser QA verifique apertura, retorno, refresh, lectura y responsive;
12. métricas detecten huérfanos, fallback legacy, rechazos y pérdida de contexto.

**Resultado contractual:** H27 queda definida. La existencia del endpoint de notificaciones, del `read_at` y de un `action_href` básico no basta para declarar la fase implementada; la prueba decisiva es el aislamiento de ownership y el deep link contextual en runtime.
