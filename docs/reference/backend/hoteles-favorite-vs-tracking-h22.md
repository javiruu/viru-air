# H22 — Favorito simple frente a tracking de precio hotelero

**Estado:** contrato de producto/dominio; implementación frontend/backend, migración V2, i18n, inbox y QA pendientes  
**Fecha:** 2026-08-05  
**Área:** producto / backend / frontend / DB / seguridad / privacidad / QA  
**Fuente de verdad:** sí para la semántica de guardar un hotel frente a seguir una oferta  
**Fase del roadmap:** H22  
**Depende de:** H10, H13, H18, H19, H20, H21  
**Relacionado con:** H05 freshness/provenance, H11 migración, H23 tracking reconstruible, H24 histórico, H25 confidence, H26 alertas, H27 inbox, H29 lifecycle, H31-H35 UX/a11y/i18n/legal, H38 ownership y seguridad, H39-H40 QA

> H22 evita que “guardar hotel” y “seguir precio” parezcan la misma acción. Un favorito recuerda una propiedad; un tracking vigila una estancia/oferta concreta. El primero no promete comprobaciones ni alertas. El segundo solo puede presentarse como operativo cuando conserva el contexto necesario y tiene una política real de revalidación.

## 1. Decisión de producto

Viru tendrá dos objetos visibles y deliberadamente distintos:

| Acción visible | Objeto | Qué recuerda | Qué promete | Siguiente fase principal |
|---|---|---|---|---|
| **Guardar hotel** | `HotelWatchlistItem` / favorito | una propiedad concreta | ninguna comprobación periódica ni alerta de precio | H22 |
| **Seguir oferta/precio** | `HotelTrackedOffer` / suscripción | hotel + estancia + condiciones + provider/contexto de precio | solo el seguimiento que el scheduler/provider puedan demostrar | H23 |

Reglas de lenguaje:

- “Guardado”, “favorito” o “en mi lista” no significa “en seguimiento”.
- “Trackear precio”, “seguir oferta” o “seguir esta estancia” solo se usa cuando la persona entiende qué fechas, ocupación, condiciones y fuente se vigilarán.
- “Activo” describe una suscripción elegible para revalidación; no basta con `is_active=true` si faltan fechas, condiciones o capacidad operativa.
- Un hotel puede estar guardado sin estar trackeado.
- Una oferta trackeada puede pertenecer a un hotel que no esté guardado; no se obliga a crear el favorito como efecto lateral.
- Crear, quitar o pausar un objeto no debe modificar silenciosamente el otro.

H22 define la semántica y la migración segura. No implementa todavía la creación completa desde una oferta real, que pertenece a H23.

## 2. Estado actual comprobable

### 2.1. Favorito/watchlist V1

`HotelWatchlistItem` contiene:

```text
id
user_id
hotel_id
label nullable
created_at
```

La base de datos impone unicidad por `(user_id, hotel_id)`. El servicio actual:

- verifica que `hotel_id` existe;
- crea el favorito y devuelve `409 hotel_watchlist_item_already_exists` si se repite;
- lista solo los favoritos del usuario autenticado;
- permite borrar después de comprobar ownership;
- no tiene fechas, ocupación, provider, precio, refresh, snapshot ni regla de alerta.

Por tanto, el comportamiento correcto de V1 es el de un marcador/favorito. No se debe reinterpretar `label` como nombre de una búsqueda ni como configuración de alertas.

La UI actual hidrata el detalle de cada hotel guardado por separado. Puede mostrar el favorito aunque el detalle temporalmente no esté disponible, y debe conservar esa distinción.

### 2.2. Tracking V1

`HotelTrackedOffer` contiene actualmente:

```text
user_id
hotel_id
area_label / origin_query
latitude / longitude / radius_km
check_in / check_out nullable
legacy guests
room_label / meal_plan / cancellation_policy nullable
provider
initial_price / current_price / target_price nullable
currency
is_active
created_at / updated_at
```

La unicidad declarada es `(user_id, hotel_id, check_in, check_out, guests, provider)`. Las fechas pueden ser `NULL`; la unicidad efectiva con `NULL` depende del motor y puede permitir duplicados. La identidad tampoco incluye habitación, régimen, cancelación, moneda ni semántica de fees.

El endpoint V1 acepta una creación con fechas y precio ausentes. El servicio solo crea snapshot inicial cuando hay fechas y `current_price`; de lo contrario queda una suscripción sin observación inicial. El hook actual puede crearla desde una card de hotel con la tarifa más barata seleccionada, o sin contexto si no hay una tarifa válida. Ese flujo es insuficiente para declarar tracking operativo y queda bloqueado por H23.

El sweep actual procesa ofertas activas con fechas no nulas, toma una tarifa del provider o un snapshot general, crea snapshot enlazado y actualiza `current_price`. **Gap bloqueante V1:** si la llamada al provider lanza una excepción, el código la convierte en `provider_rates=[]` y puede continuar con el snapshot general más barato; así puede crear una nueva observación y actualizar `current_price` aunque el provider haya fallado. H22/H05/H21 prohíben tratar ese error como una observación válida: hasta corregirlo, el caso debe quedar `provider_error`/`unavailable`, sin snapshot elegible, sin cambio de `current_price` y sin alerta de bajada.

Una oferta activa sin fechas queda fuera del sweep sin que necesariamente la UI lo explique. El hecho de que una fila tenga `is_active=true` no corrige esa falta de contexto.

El hook `useTrackedOffers` ignora silenciosamente el fallo de carga de la lista porque trata tracking como secundario. H21 exige que un error no se convierta en empty silencioso; H22 mantiene esa obligación para la superficie de tracking.

### 2.3. Inbox y alertas actuales

`HotelAlertRule` puede apuntar a `hotel_id` y opcionalmente a `tracked_offer_id`. **Gap bloqueante V1:** `create_alert_rule()` no verifica actualmente que el `tracked_offer_id` pertenezca al usuario autenticado ni que corresponda al `hotel_id` de la regla; H26/H27/H38 deben cerrar esa comprobación antes de considerar la regla operativa.

Hay eventos de sweep con `rule_id=null`. La resolución actual de algunos eventos permite incluir todos los eventos del hotel si el usuario tiene una oferta trackeada para ese hotel. Esto es comportamiento actual no apto para un inbox privado: no prueba que el evento se haya generado para su oferta ni que la señal sea privada de ese usuario.

Hasta H26/H27, una señal privada nueva debe exigir ownership inequívoco por regla/oferta/suscripción. No se puede compartir un evento por `hotel_id` como atajo si otro usuario sigue el mismo hotel.

### 2.4. Borrado de cuenta y borrado de tracking

El borrado de cuenta elimina los favoritos y tracked offers del usuario junto con sus entidades hoteleras privadas según el flujo actual. `delete_tracked_offer` realiza borrado duro; el PATCH permite `is_active=false`, que funciona como pausa técnica pero no tiene todavía copy, auditoría ni semántica de histórico definida.

H22 no convierte el borrado duro en archivado automáticamente. H29 decidirá la política final, retención, undo, expiración y cascadas. Mientras tanto, cualquier UI debe llamar “dejar de seguir” o “eliminar seguimiento” solo con el comportamiento realmente implementado, nunca prometer recuperación si el backend borra.

## 3. Modelo semántico canónico

### 3.1. Favorito simple

```text
FavoriteHotel {
  favorite_id
  user_id                 ownership privado
  canonical_hotel_id      HotelProperty.id
  label                   opcional, descriptivo
  created_at
}
```

Invariantes:

- `canonical_hotel_id` debe existir y ser un ID interno, no un `provider_hotel_id`.
- El favorito pertenece a un único usuario.
- La clave natural mínima es `(user_id, canonical_hotel_id)`.
- No contiene fechas, huéspedes, precio, currency, provider, target, alert rule ni deeplink.
- No entra en sweeps ni genera eventos por sí solo.
- El favorito puede existir aunque el detalle de catálogo esté temporalmente `unavailable`.
- Quitar el favorito no elimina una oferta trackeada del mismo hotel.
- Crear el tracking no crea obligatoriamente el favorito.

### 3.2. Suscripción de tracking

Conceptualmente, H23 debe evolucionar `HotelTrackedOffer` hacia:

```text
TrackedOfferSubscription {
  tracking_id
  user_id
  canonical_hotel_id
  stay_query_fingerprint
  offer_fingerprint o provider_scope
  occupancy/contexto completo
  room_signature
  meal_plan
  cancellation_signature
  currency
  initial_observation_id
  last_eligible_observation_id
  target_price nullable
  lifecycle_state
  created_at / updated_at
}
```

Una suscripción no debe contener secretos ni convertirse en la identidad de una consulta compartida. `user_id`, thresholds, labels, canales y notas privadas quedan fuera de fingerprints compartidos.

Una suscripción es **evaluable** solo cuando conserva, como mínimo:

- hotel canónico;
- entrada y salida válidas;
- ocupación que el producto pueda reconstruir, aunque sea bridge V1 etiquetado;
- moneda válida;
- provider o `any_eligible` explícito;
- condiciones conocidas o estado `unknown` visible;
- política de freshness/provenance;
- snapshot inicial o estado explícito `pending_context`/`pending_first_observation`.

No se debe presentar como “seguimiento activo” una fila que solo tiene hotel, provider por defecto y precio nulo.

### 3.3. Estados de lifecycle

H22 define estos estados de producto, aunque V1 pueda almacenarlos mediante `is_active` y campos auxiliares:

| Estado | Significado | ¿Entra en sweep? | ¿Puede generar alerta? | UI mínima |
|---|---|---:|---:|---|
| `pending_context` | Falta estancia/condición necesaria | no | no | Completar fechas y detalles |
| `pending_first_observation` | Contexto válido, aún sin snapshot elegible | según policy | no hasta observar | Primera comprobación pendiente |
| `active` | Contexto completo y policy de revalidación habilitada | sí, si scheduler/capability disponible | sí, solo con snapshot elegible | Seguimiento activo + última comprobación |
| `partial` | Se guarda la intención, pero faltan dimensiones o provider | no como tracking completo | no evaluable | Seguimiento incompleto |
| `stale` | Histórico existe, pero fuera de TTL preferido | puede revalidar | no hasta revalidar, salvo policy explícita | Última comprobación antigua |
| `paused` | Usuario o policy detuvo comprobaciones | no | no | En pausa; histórico conservado |
| `expired` | La estancia terminó o la policy la cerró | no | no | Finalizado; ver histórico |
| `archived` | Se conserva fuera de vistas activas | no | no | Archivado, si H29 lo implementa |
| `deleted` | Eliminado conforme a política de retención | no | no | No se expone como existente |
| `unavailable` | Provider/capability impide comprobar ahora | no hasta recuperación | no | No se puede comprobar ahora |

`is_active=true` es una representación legacy, no una prueba suficiente de `active`. La transición a V2 debe ser aditiva y auditable.

### 3.4. Favorito y tracking en la misma pantalla

| Situación | Acción principal | Copy permitido | Copy prohibido |
|---|---|---|---|
| Hotel no guardado/no trackeado | guardar o ver oferta | “Guardar hotel”, “Ver ofertas” | “Seguir” si no hay oferta/contexto |
| Hotel guardado, sin tracking | abrir detalle o completar búsqueda | “Guardado”, “Seguir esta oferta” tras contexto | “Seguimiento activo” |
| Tracking válido activo | revisar o editar tracking | “Siguiendo esta estancia”, “Última comprobación…” | “Guardado” como única explicación |
| Tracking incompleto | completar contexto | “Seguimiento incompleto”, “Completar fechas” | “Activo”, “Te avisaremos” |
| Tracking pausado | reactivar o consultar histórico | “En pausa” | “Eliminado” si se conserva |
| Provider caído/stale | revisar/reintentar | “Última observación…”, “No se pudo comprobar” | “Sin hoteles”, “agotado”, “precio actual confirmado” |

La card, el detalle, la watchlist y la futura cuenta deben usar el mismo vocabulario y no dos botones que hagan cosas distintas con el mismo texto.

## 4. Acciones y transiciones

### 4.1. Guardar y quitar favorito

**Guardar hotel**:

1. Validar hotel canónico y sesión.
2. Crear o devolver la relación `(user_id, hotel_id)` de forma idempotente en UX.
3. Mostrar confirmación local: “Hotel guardado”.
4. No crear snapshot, tracking, alerta ni llamada a provider.
5. Actualizar card, detalle y panel de guardados sin alterar resultados ni ranking.

**Quitar favorito**:

1. Confirmar ownership por item y usuario.
2. Quitar solo el favorito.
3. Mantener tracking, snapshots y alertas si existen.
4. No convertir automáticamente tracking en favorito ni viceversa.
5. Si la UI ofrece undo, debe existir una operación real y segura; no simular recuperación después de un DELETE duro.

### 4.2. Convertir favorito en tracking

La conversión debe ser una acción explícita desde detalle/lista de favoritos:

```text
favorito
  → elegir estancia/contexto
  → seleccionar oferta/condiciones
  → revisar resumen
  → confirmar tracking
  → pending_first_observation | active | partial
```

La conversión no debe:

- copiar fechas antiguas de la URL sin confirmarlas;
- elegir una tarifa distinta de la que la persona revisó;
- rellenar fees, habitación o cancelación desconocidas como si fueran conocidas;
- crear múltiples trackings por doble click o retry;
- compartir la configuración privada con otro usuario;
- activar alertas antes de que H23/H26 puedan evaluar un snapshot comparable.

Si solo existe el hotel y no la estancia, la acción debe llevar a completar búsqueda, no crear silenciosamente un tracking incompleto. Si se permite guardar una intención incompleta por compatibilidad, se etiqueta `pending_context` y no aparece como activo.

### 4.3. Crear tracking desde una oferta

H22 fija la UX, H23 fija el contrato de datos:

- la CTA no debe estar disponible como “seguir precio” si no existe oferta/contexto mínimo;
- la confirmación debe mostrar hotel, fechas, noches, huéspedes/habitaciones, habitación, régimen, cancelación, moneda, provider y precio observado o “pendiente”;
- debe quedar claro si se vigila un provider concreto o cualquier provider elegible;
- el precio inicial no es necesariamente mínimo histórico;
- el snapshot inicial debe tener `observed_at`, provenance y freshness cuando exista;
- el resultado de creación debe indicar `active`, `pending_first_observation`, `partial` o `duplicate`, no solo devolver una fila opaca.

### 4.4. Pausa, reactivación y eliminación

H22 reserva el lifecycle final a H29, pero fija estas reglas:

- **Pausar** conserva snapshot, histórico y configuración; no entra en sweep ni alerta.
- **Reactivar** exige validar que las fechas no hayan pasado y que la policy/provider siga disponible.
- **Eliminar** no significa pausar. Si es borrado duro, el copy debe decir eliminar y la UI no debe prometer histórico recuperable.
- **Expirar** por check-out no debe convertirse en error ni borrar automáticamente el histórico.
- **Archivar** solo se puede mostrar si existe estado persistido y una ruta de recuperación definida.
- Cambiar fechas, ocupación, habitación, régimen, cancelación o provider puede cambiar la identidad de oferta; H23/H29 deben crear nueva versión o nueva suscripción, no mutar silenciosamente la serie histórica.

## 5. Identidad, duplicados y concurrencia

### 5.1. Favoritos

La unicidad `(user_id, hotel_id)` es correcta para el favorito simple. La API debe seguir devolviendo un error estable o una respuesta idempotente acordada; el frontend nunca debe crear dos filas por doble submit.

### 5.2. Trackings

La clave V1 `(user_id, hotel_id, check_in, check_out, guests, provider)` es insuficiente porque:

- permite ambigüedad con `NULL`;
- no incluye room/meal/cancelación/currency/fee semantics;
- confunde provider concreto con scope de providers;
- no expresa lifecycle/versiones ni oferta exacta.

H23/H11 deben introducir una identidad canónica aditiva:

```text
tracking_identity =
  user_id privado
  + canonical_hotel_id
  + stay_query_fingerprint
  + offer_fingerprint o provider_scope
```

Reglas:

- el fingerprint compartido nunca incluye `user_id`;
- dos usuarios pueden observar la misma consulta sin compartir tracking ni alertas;
- el mismo usuario puede seguir dos ofertas del mismo hotel si cambian estancia o condiciones;
- un retry con la misma identidad devuelve/recupera el tracking existente, no crea otro;
- una identidad incompleta no entra en la unicidad fuerte como si fuera completa;
- las operaciones concurrentes deben resolver duplicado por constraint/transacción, no solo por un `if` previo.

## 6. Ownership, privacidad e inbox

### 6.1. Reglas de autorización

Cada lectura y mutación privada debe filtrar por `current_user.id` en la consulta o comprobar ownership antes de devolver cualquier dato:

- listar/leer/editar/eliminar favoritos;
- listar/leer/editar/eliminar trackings;
- leer snapshots asociados a tracking;
- crear/editar/eliminar reglas de alerta;
- resolver eventos y deep links privados;
- acceder a estados de conversión o preferencias.

Un ID válido de otro usuario debe producir `404` indistinguible cuando convenga o `403` estable según la política, sin filtrar existencia, fechas, precio, labels o provider.

### 6.2. Eventos de hotel

Un evento con `rule_id=null` no puede resolverse por `hotel_id` solamente. La futura relación mínima debe ser una de:

```text
alert_event → alert_rule.user_id
alert_event → tracked_offer_id → user_id
alert_event → private subscription identity
```

Si un evento no tiene ownership determinable, no entra en inbox privada; se registra como evento operativo no entregable o se migra con revisión. Nunca se replica a todos los usuarios que siguen ese hotel.

### 6.3. Cache y URLs

No introducir en cache compartida, SSR reutilizable, URL pública o telemetry:

- `user_id`, email o tokens;
- target price, thresholds, labels privados o notas;
- `tracking_id` privado sin contrato seguro;
- selección de comp set privada;
- payload raw de provider;
- deeplink arbitrario.

Los envelopes con `has_tracking`, estado privado o datos de cuenta deben ser `private`/no-store cuando puedan cruzar límites de usuario.

### 6.4. Borrado de cuenta

La eliminación de cuenta debe cubrir favoritos, trackings, reglas, eventos privados, snapshots privados y estados derivados conforme a H11/H27/H29, con retención legal mínima si aplica. Los identificadores compartidos de provider/cache no deben contener ownership y no se borran globalmente por borrar una cuenta.

## 7. Contrato API V1→V2

### 7.1. Compatibilidad V1

Se conservan temporalmente:

- `GET/POST/DELETE /hotels/watchlist`;
- `GET/POST/PATCH/DELETE /hotels/tracked-offers`;
- `GET /hotels/tracked-offers/{id}/snapshots`;
- `is_active` como bridge técnico;
- `check_in/check_out` nullable solo para leer legacy y migrar con warning;
- `HotelAreaSearchResultOut.has_tracking` como señal privada autenticada, nunca cacheada globalmente.

La compatibilidad V1 no autoriza copy de “seguimiento activo” para una fila incompleta.

### 7.2. Envelope V2 objetivo

El contrato futuro debe separar favorito y tracking, por ejemplo:

```json
{
  "favorite": {
    "id": "favorite-id",
    "hotel_id": "canonical-hotel-id",
    "label": null,
    "created_at": "2026-08-05T10:00:00Z"
  },
  "tracking": {
    "id": "tracking-id",
    "state": "pending_first_observation",
    "hotel_id": "canonical-hotel-id",
    "stay_query_fingerprint": "opaque",
    "offer_fingerprint": null,
    "provider_scope": "any_eligible",
    "has_initial_observation": false,
    "capabilities": {
      "pause": true,
      "resume": false,
      "edit": false,
      "delete": true,
      "create_alert": false
    },
    "ownership": "current_user",
    "warnings": ["first_observation_pending"]
  }
}
```

Reglas del envelope:

- nunca serializar `user_id` en una superficie pública si no es imprescindible;
- `state` y `warnings` son obligatorios para interpretar ausencia de contexto;
- `has_tracking` no sustituye a `tracking_state` cuando haya más de un tracking o estados parciales;
- `create_alert=false` hasta que H26 pueda evaluar la suscripción;
- V1 puede usar fallback conservador, pero debe instrumentar cuántas filas son legacy/incompletas;
- el bridge debe permitir comparar V1/V2 sin duplicar tracking ni snapshots.

## 8. Frontend y copy

### Resultados

Cada card debe poder mostrar dos indicadores independientes:

```text
[Guardar hotel]     Guardado / Guardar
[Seguir oferta]     Siguiendo esta estancia / Completar fechas / Seguir precio
```

La acción de guardar debe estar disponible aunque no haya una oferta válida. La acción de tracking debe depender del contexto mínimo y explicar qué se seguirá.

No usar “Añadir a seguimiento” para el favorito. La nomenclatura actual `addToWatchlist: "Añadir a seguimiento"` es ambigua y debe migrar en H34/H31 a “Guardar hotel” o “Añadir a guardados”.

### Detalle

El orden recomendado es:

1. resumen de estancia y precio observado;
2. CTA de guardar hotel;
3. CTA de seguir esta oferta;
4. estado de tracking existente para esa identidad;
5. alertas solo si la oferta es evaluable;
6. histórico y acciones secundarias.

El detalle debe conservar la selección H18 y no cerrar por un error de mutación. Un error de refresh del tracking no puede borrar el favorito ni la selección.

### Paneles y cuenta

- Panel “Hoteles guardados”: lista de propiedades, fecha de guardado, etiqueta y detalle disponible/no disponible.
- Panel “Seguimientos”: lista de estancias/ofertas, estado lifecycle, última observación, provider scope y CTA de gestionar.
- No mezclar ambos en una sola lista titulada “seguimientos”.
- Un favorito vacío y un tracking vacío son estados distintos y tienen CTA distintos.
- Un error de carga de tracking se muestra como error recuperable, no como “no tienes seguimientos”.
- Un tracking `pending_context` debe pedir completar datos, no mostrar precio actual vacío como si fuera válido.

### Inbox

Una alerta debe decir si corresponde a:

- una oferta/estancia concreta;
- un hotel guardado con una señal general, solo si esa capacidad se define posteriormente;
- una regla de usuario.

Mientras H26/H27 no resuelvan ownership de eventos de sweep sin `rule_id`, no presentar esos eventos como alertas personales confirmadas.

## 9. Migración y compatibilidad

### H22-A — Inventario

Clasificar cada fila existente:

```text
favorite_only
tracking_complete
tracking_legacy_incomplete
tracking_duplicate_candidate
tracking_expired
tracking_owner_unverifiable
```

No borrar filas durante el inventario. Generar métricas y lista de revisión con IDs redacted fuera de entornos autorizados.

### H22-B — Normalización de copy y señales

- Renombrar visualmente favorito/watchlist sin cambiar la API todavía.
- Separar badges `saved` y `tracking_state`.
- Dejar de usar `has_tracking=true` como único estado si puede haber varias ofertas.
- Mostrar legacy incompleto como `pending_context` o `partial`, nunca como activo.
- Eliminar silencios de `useTrackedOffers.refreshTrackedOffers` y mapear error/empty según H21.

### H22-C — Bridge de datos

- Mantener `HotelWatchlistItem` como tabla de favorito simple.
- Añadir estado/fingerprint/versiones de tracking de forma aditiva en H11/H23.
- Marcar `guests` como bridge legacy; no inventar rooms/children.
- No crear snapshots iniciales para tracking sin fechas y precio observados válidos.
- No actualizar `current_price` por una respuesta de provider error, timeout, rate limit o disponibilidad no evaluable.
- Resolver duplicados antes de añadir constraints nuevas, con dry-run y rollback.

### H22-D — Inbox y ownership

- Auditar eventos antiguos sin `rule_id` y tratarlos como no entregables en inbox privada hasta resolver su ownership.
- Asociar nuevos eventos a una regla o tracked offer con ownership inequívoco.
- Validar en creación y edición que `tracked_offer_id.user_id == current_user.id` y que el hotel de la regla coincide con el de la oferta.
- Excluir eventos no atribuibles de inbox privada hasta migrarlos o marcarlos como operativos.
- Añadir pruebas de dos usuarios siguiendo el mismo hotel.

### H22-E — Salida de migración

La migración H22 no se cierra por renombrar botones. Debe demostrar:

- favorito y tracking tienen acciones, estados y listas distintas;
- un favorito no activa sweeps ni alertas;
- un tracking incompleto no se muestra como activo;
- duplicados y doble submit son deterministas;
- ownership evita datos cruzados;
- el histórico se conserva al pausar y la eliminación respeta la política real;
- V1 continúa serializando y el bridge V2 es reversible.

## 10. Eventos y métricas

Eventos mínimos versionados, sin PII:

```text
hotel_favorite_created
hotel_favorite_duplicate
hotel_favorite_removed
hotel_favorite_detail_opened
hotel_tracking_cta_viewed
hotel_tracking_context_incomplete
hotel_tracking_create_started
hotel_tracking_create_succeeded
hotel_tracking_create_duplicate
hotel_tracking_create_blocked
hotel_tracking_state_viewed
hotel_tracking_paused
hotel_tracking_resumed
hotel_tracking_deleted
hotel_tracking_load_error
hotel_tracking_legacy_detected
hotel_tracking_ownership_denied
hotel_private_event_excluded
```

Propiedades permitidas:

- `surface`, `state`, `reason_code`, `provider_scope`, `has_context`, `has_initial_observation`, `has_previous_data`, `state_version`;
- fingerprints opacos, no query completa;
- duración, outcome y código HTTP estable;
- no email, user ID crudo, precio objetivo, notas, raw provider ni URL externa.

Métricas:

- conversión favorito → tracking válido;
- porcentaje de tracking creado con contexto completo;
- tracking `pending_context` y tiempo hasta completar;
- duplicados por retry/doble submit;
- favoritos quitados sin afectar tracking;
- tracking pausado/reactivado/eliminado;
- errores de ownership y eventos privados excluidos;
- filas legacy incompletas y snapshots iniciales ausentes;
- carga de tracking con error frente a empty real.

## 11. Accesibilidad, legal y seguridad

- Los botones “Guardar hotel” y “Seguir oferta” tienen nombres distintos, estados `aria-pressed` o `aria-busy` correctos y no dependen solo del color.
- El estado “guardado” se anuncia sin afirmar seguimiento.
- El modal/hoja de confirmación de tracking enfoca el resumen y devuelve foco a la card/detalle tras cerrar.
- Un tracking incompleto explica qué dato falta y ofrece la acción concreta.
- Las fechas, huéspedes, moneda y provider se presentan con locale/timezone correctos.
- El copy informa de que Viru observa precios y que el partner puede cambiar el precio final.
- Las reglas de alertas no se crean sin consentimiento/acción explícita del usuario.
- Ownership se comprueba en backend; no confiar en `user_id` del payload.
- Los IDs privados y estados de tracking no se filtran en URL, cache compartida, SSR reutilizable o logs.
- Tests cubren IDOR, dos usuarios con el mismo hotel, borrado de cuenta, 401/403/404, replay y doble submit.

## 12. Tests y gate H22

### Unitarios y backend

- unicidad favorita por usuario/hotel;
- favorito no crea snapshot ni tracking;
- tracking completo crea snapshot inicial solo si la observación es válida;
- tracking sin fechas/precio se clasifica como incompleto y no entra en sweep;
- `is_active=false` no entra en sweep ni alerta;
- excepción/timeout/rate limit del provider no cae al snapshot general como si fuera éxito, no crea snapshot elegible y no actualiza `current_price`;
- `create_alert_rule` rechaza `tracked_offer_id` ajeno o incoherente con `hotel_id`;
- duplicado concurrente devuelve resultado estable;
- cambio de condiciones altera fingerprint o crea nueva versión;
- snapshots y alertas respetan ownership;
- evento sin `rule_id` no se comparte por hotel entre usuarios;
- borrado de cuenta no deja datos privados accesibles;
- migración de `NULL` y constraints funciona en SQLite/PostgreSQL.

### Frontend

- guardar hotel funciona sin fechas;
- seguir precio exige contexto y muestra resumen;
- favorito y tracking tienen badges/copy independientes;
- retry no duplica entidades;
- tracking error no aparece como empty;
- tracking incompleto ofrece completar, no “activo”;
- pausa/eliminación reflejan la semántica real;
- lista de favoritos conserva hoteles cuyo detalle no está disponible;
- estado privado no se cachea ni aparece en URL pública;
- foco, teclado, reduced motion, dark/light y ES/EN son correctos.

### Integración/E2E

```text
buscar hotel
  → guardar hotel
  → comprobar panel de guardados
  → seleccionar fechas/oferta
  → revisar resumen
  → crear tracking
  → comprobar panel de seguimientos
  → simular refresh/error/stale
  → pausar o eliminar sin alterar favorito
```

Casos obligatorios:

- dos usuarios guardan y siguen el mismo hotel;
- usuario A no ve tracking, snapshots ni inbox de B;
- hotel guardado sin rates;
- tracking con fechas pero sin precio;
- tracking con tarifa y snapshot inicial;
- provider caído después de una observación válida;
- doble click y retry ante 409;
- refresh de `/hoteles` y regreso desde H18;
- borrado de cuenta y reintento con IDs antiguos.

### Gate contractual

H22 se puede marcar completa como contrato cuando:

1. favorito y tracking tienen nombres, acciones y paneles distintos;
2. el favorito no promete refresh, histórico ni alertas;
3. el tracking solo se etiqueta activo si el contexto y la policy lo permiten;
4. la conversión es explícita y no duplica entidades;
5. estados pending/partial/paused/stale/unavailable están definidos;
6. ownership de lectura, mutación, snapshots e inbox es inequívoco;
7. eventos sin `rule_id` no se comparten por `hotel_id`;
8. migración V1→V2 conserva datos y tiene rollback;
9. copy ES/EN, a11y, privacidad y legal están especificados;
10. tests cubren empty/error, concurrency, IDOR, dos usuarios y lifecycle.

**Resultado contractual:** H22 queda definido como contrato de semántica y migración. La implementación frontend/backend, los cambios de esquema, la creación de tracking desde una oferta real y el cierre de inbox quedan pendientes de H23/H26/H27/H29 y sus gates.

## 13. Handoff

| Fase | Entrega H22 |
|---|---|
| H11 | resolver unicidad con `NULL`, fingerprints, columnas de estado, backfill y rollback sin perder históricos |
| H13/H18 | conservar búsqueda/detalle y separar CTA de favorito frente a tracking |
| H19 | usar solo precios/fees elegibles; no llamar total a un valor legacy desconocido |
| H21 | mapear empty/error/stale/unavailable sin borrar contexto ni convertir tracking incompleto en activo |
| H23 | crear tracking desde una oferta real, snapshot inicial y estado de creación reconstruible |
| H24-H25 | histórico y freshness por estancia/oferta, no por hotel abstracto |
| H26 | reglas solo sobre snapshots comparables y tracking evaluable; dedupe por ownership |
| H27 | inbox con fuente privada inequívoca y deep link al tracking correcto |
| H29 | pausa, edición, expiración, archivado, borrado y undo según capacidad real |
| H31-H34 | copy, jerarquía visual, responsive, accesibilidad e i18n |
| H38-H40 | ownership, seguridad, tests y browser QA |

**No se declara H22 implementada hasta que la evidencia confirme que “guardar hotel” y “seguir oferta” son dos productos distintos en código, API y UI real.**
