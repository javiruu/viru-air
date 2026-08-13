# H48 — Búsquedas guardadas y compartibles sin fuga privada

**Estado:** implementación local parcial verificada: parser/restauración URL, persistencia privada CRUD, ownership, idempotencia y lifecycle active/paused/delete cubiertos; share tokens públicos, expiración productiva, cache avanzada y QA E2E pendientes
**Fecha:** 2026-08-10
**Área:** producto / frontend / backend / privacidad / navegación / i18n / QA  
**Fuente de verdad:** sí para la semántica de búsquedas hoteleras reproducibles, guardadas y compartibles  
**Fase del roadmap:** H48  
**Depende de:** [H03 — arquitectura y URL state](../../product/hoteles-information-architecture-h03.md), [H10 — StayQuery](hoteles-stay-offer-model-h10.md), [H13 — formulario y recuperación](hoteles-search-form-h13.md), [H14 — filtros y orden](hoteles-filters-ranking-h14.md), [H15 — resultados](hoteles-results-pagination-h15.md), [H22 — favorito frente a tracking](hoteles-favorite-vs-tracking-h22.md), [H27 — inbox y deep links](hoteles-private-inbox-deeplinks-h27.md), [H29 — lifecycle](hoteles-lifecycle-pause-edit-expire-delete-h29.md), [H34 — i18n](../frontend/hoteles-localization-dates-currency-timezones-h34.md), [H35 — privacidad y deeplinks](hoteles-legal-privacy-disclosure-deeplinks-h35.md), [H40 — browser QA](../frontend/hoteles-visual-manual-crossbrowser-qa-h40.md), [H47 — Mis hoteles](../frontend/hoteles-mis-hoteles-reengagement-h47.md)  
**Handoff:** [H49 — personalización prudente](../../plans/2026-08-04-hoteles-master-roadmap.md#fase-h49--personalización-prudente)

> H48 separa una intención de búsqueda que puede compartir cualquiera de una suscripción privada que solo puede gestionar su propietario. Una URL con destino y fechas no es tracking, no es alerta y no concede acceso a datos de cuenta.

## 1. Decisión de arquitectura

H48 define tres objetos distintos:

| Objeto | Propósito | Ownership | Puede compartirse |
|---|---|---|---|
| **Shareable Search URL** | reconstruir una consulta anónima y reproducible | ninguno | sí, si solo contiene estado permitido |
| **Saved Hotel Search** | recuperar una consulta recurrente desde la cuenta | usuario autenticado | no directamente; compartir su estado requiere generar una URL anónima |
| **HotelTrackedOffer / alert rule** | observar una estancia/oferta y reaccionar a cambios | usuario autenticado | no; solo se comparte una vista pública equivalente si existe contrato explícito |

La fuente de verdad de la consulta es una `StayQuery` canónica. La búsqueda guardada referencia esa consulta y preferencias de lifecycle; no copia snapshots, targets, reglas ni datos de inbox. `HotelTrackedOffer` mantiene su propia identidad privada y no se usa como sustituto de Saved Hotel Search.

### 1.1. No objetivos

H48 no implementa por sí sola:

- una OTA, reserva, partner o deeplink externo;
- tracking, alertas, email, push o delivery;
- conversión automática de una búsqueda guardada en tracking;
- un nuevo provider hotelero;
- una URL que exponga `user_id`, email, token, target, threshold, regla, snapshot privado o payload raw;
- llamadas automáticas a provider real al abrir un enlace compartido o cargar una lista guardada;
- una ruta nueva obligatoria: la URL canónica continúa siendo `/hoteles`.

## 2. Baseline real comprobable

### 2.1. Estado hotelero actual

El bloque local implementado en esta iteración añade `HotelSavedSearch` y los endpoints privados `GET/POST /hotels/saved-searches`, `GET/PATCH/DELETE /hotels/saved-searches/{id}`. El payload está limitado a `hotel-search-v1` y a parámetros de búsqueda allowlisted; el fingerprint se calcula sobre JSON canónico ordenado. Crear es idempotente por usuario y fingerprint, y todas las lecturas/mutaciones comprueban ownership. Restaurar desde la UI vuelve a pasar por el parser/builder URL allowlisted y no marca `searched`, no conserva selección privada y no ejecuta provider automáticamente.

`frontend/src/modules/hotels/hooks/useHotelSearch.ts` mantiene en React:

- `query`, `city`, `searchMode`;
- `areaQuery`, `areaSuggestions`, `areaResolved`;
- `checkIn`, `checkOut`, `guests`, `radiusKm`, `useProvider`;
- `results`, `areaResults`, `selectedHotelId`, `errorMessage`.

La implementación local añade `frontend/src/modules/hotels/hotelSearchUrlState.ts` como parser/builder URL-driven, `api.ts` con el CRUD autenticado de búsquedas guardadas y `useSavedHotelSearches.ts`/`HotelSavedSearchesPanel.tsx` para guardar, restaurar, pausar y eliminar desde `/hoteles`. La respuesta devuelve siempre el payload canónico normalizado. Restaurar no ejecuta provider implícitamente; la búsqueda explícita sigue siendo una acción separada.

### 2.2. Capacidades reutilizables, no equivalentes

`frontend/src/modules/shared/useRouteState.ts` contiene sanitización y URL state para Quick Search y Watchlist de vuelos. Es un patrón reutilizable, no un contrato hotelero ya implementado. Sus parámetros IATA (`origin`, `destination`) no deben copiarse como si fueran destino, zona o `StayQuery`.

H03/H13 ya definen parámetros hoteleros objetivo (`destination`, `destination_type`, `area`, `check_in`, `check_out`, `guests`, `radius`, `currency`, filtros, orden, `hotel_id`, `panel`). H48 convierte la parte local soportada por el radar en un contrato versionado; los campos aún no respaldados por la UI/API siguen fuera de la allowlist efectiva.

### 2.3. Auth actual

La ruta `/hoteles` está bajo `(private)` y los endpoints de datos de cuenta usan usuario autenticado. `frontend/src/modules/shared/auth.ts` persiste tokens en `localStorage`; `AuthProvider` expone el usuario si el shell lo proporciona. H48 no mueve ni redefine el sistema de auth. Sí exige que una búsqueda guardada privada no se confunda con una URL pública y que logout/expiración no deje una copia privada en una URL compartida o cache común.

## 3. Contrato canónico de `StayQuery`

### 3.1. Versionado y campos

La consulta serializable usa un esquema explícito, por ejemplo `hotel-search-v1`. El nombre exacto de la query param de versión debe mantenerse estable una vez publicado.

```json
{
  "schema": "hotel-search-v1",
  "mode": "name|area",
  "query": "Hotel Sol",
  "city": "Madrid",
  "area": "Madrid Centro",
  "destination_type": "city|neighborhood|landmark|airport|region",
  "country_code": "ES",
  "destination_source": "internal_catalog|user_selected|legacy_centroid",
  "destination_id": "opaque-public-catalog-id-or-null",
  "latitude": null,
  "longitude": null,
  "check_in": "2026-09-10",
  "check_out": "2026-09-13",
  "rooms": 1,
  "adults": 2,
  "children": 0,
  "children_ages": [],
  "guests": 2,
  "radius_km": 10,
  "currency": "EUR",
  "sort": "price|distance|stars",
  "filters": {
    "min_stars": null,
    "max_price": null,
    "cancellation": null,
    "meal_plan": null,
    "provider": null
  }
}
```

Reglas:

- `query`/`city` y `area` no se envían juntos como si fueran la misma resolución si el modo no los soporta;
- `destination_id/type` solo se conservan en la superficie pública si pertenecen al catálogo/contrato público y su asociación es verificable; `destination_source` es metadato interno de resolución y no se emite en URL, fingerprint público, clipboard ni analítica;
- `latitude/longitude` no se serializan por defecto si una selección tipada basta; si se admiten como legacy, se validan rango, precisión y asociación;
- `check_in`/`check_out` son fechas civiles ISO, nunca timestamps del usuario;
- `rooms/adults/children/children_ages` se activan solo cuando H10/H13 los soporten; `guests` queda como bridge explícito y no se interpreta como estructura confirmada;
- `currency` es ISO-4217 observada/solicitada, sin FX implícito;
- solo se serializan filtros y orden realmente soportados por H14/H15;
- `hotel_id`, `tracked_offer_id`, `rule_id`, `snapshot_id` y `event_id` son selección/contexto, no parte de una búsqueda pública por defecto;
- no se serializan `user_id`, email, target, thresholds, alert channels, auth tokens, raw provider, cache keys privadas ni notas de cuenta.

### 3.2. Tabla normativa de parámetros públicos

El builder y el parser deben compartir una única tabla normativa. No se permite que cada componente invente aliases adicionales:

| Concepto | Parámetro canónico V1 | Lectura de aliases históricos | Público en URL | Regla |
|---|---|---|---:|---|
| versión | `v=hotel-search-v1` | ninguno fuera de la allowlist | sí | versión desconocida no ejecuta provider |
| modo | `mode` | `search_mode` solo si se publica y valida | sí | `name` o `area` |
| texto nombre/ciudad | `query`, `city` | aliases aprobados por H13 | sí | limpiar longitud y caracteres |
| zona | `area` | aliases aprobados por H12/H13 | sí | requiere modo/selección coherentes |
| tipo destino | `destination_type` | ninguno por defecto | sí | enum allowlisted |
| país | `country` | `country_code` durante bridge | sí | ISO-3166 allowlisted |
| fechas | `in`, `out` | `check_in`, `check_out` durante bridge | sí | fechas civiles ISO |
| ocupación bridge | `guests` | ninguno | sí | no equivale a rooms/adults confirmados |
| ocupación estructurada | `rooms`, `adults`, `children`, `children_ages` | solo tras H10/H13 | sí | no mezclar valores contradictorios |
| radio | `radius` | `radius_km` durante bridge | sí | catálogo permitido |
| moneda | `currency` | ninguno | sí | ISO-4217, sin FX implícito |
| orden/filtros | `sort`, `min_stars`, `max_price`, etc. | solo aliases versionados H14/H15 | sí | solo capacidades respaldadas |
| selección pública | `hotel_id` | ninguno | condicional | solo ID de catálogo público y detalle permitido |
| contexto privado | `tracked_offer_id`, `rule_id`, `snapshot_id`, `event_id` | ninguno | no | solo deep links autenticados H27/H47 |

`destination_id` no se incluye en la URL pública por defecto. Solo puede exponerse si H12 clasifica formalmente ese identificador como **ID de catálogo público**, no secuencial sensible, sin ownership y estable para compartir. Si no existe esa clasificación, se comparte `area/query/country/type` sanitizado y el servidor vuelve a resolver la intención.

### 3.3. Canonicalización

Antes de construir URL, hash o registro:

1. eliminar campos vacíos y defaults definidos por contrato;
2. normalizar `country_code` del payload interno a `country` antes de canonicalizar y generar URL o fingerprint; `country_code` solo se acepta como alias de lectura durante el bridge;
3. normalizar nombres de enum a allowlist lowercase;
4. ordenar claves y listas donde el orden no tenga semántica;
5. normalizar fechas a `YYYY-MM-DD` sin aplicar timezone;
6. normalizar moneda a uppercase;
7. ordenar filtros de forma determinista;
8. validar rangos y rechazar valores inválidos o ignorarlos con warning seguro;
9. serializar con un formato estable y versionado;
10. producir `stay_query_fingerprint` sin `user_id`, tiempo, token ni datos privados.

El mismo estado semántico debe producir la misma URL canónica y fingerprint, aunque los parámetros lleguen en otro orden. Cambiar una dimensión que puede alterar resultados debe producir otra fingerprint.

## 4. Shareable Search URL

### 4.1. Forma recomendada

La primera opción es una URL `/hoteles` con query params públicos, pequeños y versionados:

```text
/hoteles?v=hotel-search-v1&mode=area&area=Madrid%20Centro&destination_type=neighborhood&country=ES&in=2026-09-10&out=2026-09-13&guests=2&radius=10&currency=EUR&sort=price
```

Nombres de parámetros (`in/out`, `radius`, etc.) deben cerrarse en el builder y conservar alias de lectura para deep links históricos si ya se publicaron. No crear una segunda sintaxis manual en otro componente.

La URL representa intención de búsqueda, no resultado garantizado. Puede mostrar resultados cacheados/elegibles si existen, pero no debe prometer que el mismo provider responda en el futuro.

### 4.2. Token público opcional

No se necesita token para compartir una consulta que cabe de forma segura en la URL. Si el futuro producto requiere ocultar parámetros públicos, añadir un token aleatorio, opaco, de alcance read-only y TTL limitado:

```text
/hoteles?share=<opaque-random-token>
```

El token debe resolver server-side a una `StayQuery` pública sin ownership privado. No usar IDs secuenciales, user IDs, hashes reversibles, JWT con datos, tokens de sesión ni un ID de `HotelTrackedOffer`. La revocación/expiración y la respuesta `not_found` genérica deben estar definidas antes de publicar enlaces.

El token no autoriza detalles privados, snapshots, alertas, tracking, targets ni inbox. Si una consulta pública se deriva de una búsqueda guardada, el servidor debe extraer solo los campos permitidos y no reutilizar el registro privado como respuesta compartida.

### 4.3. Filtro de privacidad

Antes de emitir la URL:

- eliminar campos privados y no soportados;
- rechazar valores que parezcan tokens, emails o payloads serializados;
- limitar longitud y cardinalidad de listas;
- no incluir `hotel_id` privado como si fuera público cuando la selección requiera auth;
- no incluir `returnUrl` arbitrario ni URL externa;
- no incluir `source=notifications` si no es necesario para una URL pública;
- añadir `share=1` o equivalente solo si ayuda a copy/telemetry y no actúa como autorización.

El frontend puede construir la URL como convenience, pero un endpoint/server action que publique tokens debe repetir la sanitización y validar ownership antes de derivar el estado.

## 5. Búsqueda guardada privada

### 5.1. Modelo objetivo

```text
SavedHotelSearch {
  id: opaque-private-id
  user_id: owner-only
  schema_version
  stay_query_fingerprint
  canonical_query_payload
  label_private nullable
  mode: exact | flexible
  status: active | paused | expired | deleted
  created_at
  updated_at
  last_used_at nullable
  expires_at nullable
  source: manual | imported | restored
}
```

La búsqueda guardada contiene intención de consulta, no una copia de:

- snapshots privados;
- target price;
- alert rule;
- notification event;
- auth token;
- raw provider payload;
- email o perfil de cuenta.

`label_private` es opcional y nunca se comparte automáticamente. `exact` significa que se conserva la estancia/filtros indicados; `flexible` solo puede existir si H30/H10 definen la semántica de fechas flexibles. No llamar “flexible” a una búsqueda exacta con fechas modificadas por defecto.

### 5.2. Ownership y lifecycle

- crear, listar, editar, pausar, restaurar y eliminar exige sesión y ownership server-side;
- `id` es opaco y no aparece en una URL pública;
- el mismo fingerprint puede existir para dos usuarios sin compartir labels, historial, targets o alertas;
- duplicados del mismo usuario se resuelven por política explícita: reutilizar, fusionar o permitir con labels distintos;
- `paused` no ejecuta provider calls ni crea alertas;
- `expired` conserva solo lo permitido por H29/H35 y ofrece crear una nueva búsqueda;
- `deleted` no reaparece por cache, retry o deep link antiguo;
- `expires_at` y retención deben estar aprobados antes de guardar datos nuevos en producción;
- exportación/borrado de cuenta debe incluir saved searches y sus caches privadas.

Una búsqueda guardada no es una alerta activa. Para recibir eventos hace falta una regla/tracking separado con H22-H29 y consentimiento por canal según H28.

### 5.3. Auth y sesión

Si el usuario pulsa guardar sin sesión:

1. conservar la intención de búsqueda de forma no sensible;
2. pedir auth en el momento de la mutación;
3. volver a `/hoteles` con query canónica, no con un payload privado completo;
4. reanudar una sola vez e idempotentemente;
5. si cancela o expira, dejar la búsqueda sin guardar y ofrecer continuar.

La búsqueda pública compartible no puede convertirse en una búsqueda guardada de otra cuenta porque alguien cambie un ID en la URL. La respuesta de una búsqueda guardada ajena debe ser genérica (`not_found`/`not_allowed`).

## 6. Restore, back-forward y refresh

### 6.1. Restauración pública

Al abrir una URL compartida:

1. parsear y validar versión/params;
2. canonicalizar sin lanzar errores de render;
3. hidratar el formulario;
4. mostrar el contexto de búsqueda;
5. no ejecutar provider real automáticamente solo por mount;
6. cargar resultados locales/cacheados solo si el contrato permite hacerlo sin llamada externa;
7. esperar acción explícita `Buscar`/`Comprobar tarifas` para provider live;
8. si la consulta es inválida o antigua, conservar campos seguros y explicar qué debe corregirse.

### 6.2. Restauración de búsqueda guardada

Al abrir una búsqueda guardada autenticada:

- autorizar primero el registro y después devolver el payload canónico;
- hidratar formulario, filtros, orden y modo;
- mostrar `last_used_at`, freshness de resultados si existe y estado de la búsqueda;
- no mezclar resultados de otro fingerprint;
- no ejecutar provider live en mount salvo que una policy explícita y consentimiento lo permitan; por defecto requiere acción explícita;
- si un hotel/rate ya no existe, mantener la query y mostrar fallback por destino/criterios;
- si el registro expiró o fue borrado, devolver estado genérico y no reconstruirlo desde cache.

### 6.3. Browser history

- `router.replace` para canonicalizar/normalizar edición sin una entrada por tecla;
- `router.push` al submit deliberado o compartir cuando el usuario espera volver;
- back/forward restaura el fingerprint y no duplica búsquedas;
- una respuesta tardía no sobrescribe resultados de otra query;
- eliminar `hotel_id/panel` al cambiar la búsqueda si la selección ya no pertenece al contexto;
- no usar un `returnUrl` arbitrario para recuperar el punto anterior.

## 7. Provider calls, cache y analítica

### 7.1. No llamadas implícitas

Compartir, guardar o abrir una búsqueda no equivale a pedir rates live. La implementación debe distinguir:

```text
parse/restore      → no provider call
load public cache  → solo cache elegible, si existe
explicit search    → endpoint de búsqueda permitido
explicit live check → provider sujeto a flags, budget y H43/H45
```

Una búsqueda guardada tampoco debe crear un sweep. Tracking/sweep pertenece a H09/H23 y exige un objeto distinto.

### 7.2. Cache

- cache pública de consultas por fingerprint canónico, sin user ID ni datos de cuenta;
- cache privada de SavedHotelSearch particionada por usuario o `no-store`;
- nunca usar la cache de un usuario para completar labels, targets, alertas o resultados privados de otro;
- incluir schema/provider/policy version donde sea necesario para evitar mezclar contratos;
- respetar TTL/freshness y marcar stale, no convertir cache vieja en live;
- invalidar al cambiar schema o eliminar búsqueda privada.

### 7.3. Analítica y logs

Eventos allowlisted, sin payload completo:

```text
hotel_search_url_created
hotel_search_url_opened
hotel_search_url_canonicalized
hotel_search_restore_started
hotel_search_restore_succeeded
hotel_search_restore_failed
hotel_saved_search_created
hotel_saved_search_opened
hotel_saved_search_updated
hotel_saved_search_paused
hotel_saved_search_deleted
hotel_search_share_token_created
hotel_search_share_token_rejected
hotel_search_provider_call_explicit
hotel_search_provider_call_blocked_implicit
```

Propiedades: `schema_version`, `mode`, `outcome`, `state`, `reason_code`, número bucket de filtros/resultados, locale, tema, viewport y fingerprint opaca/hash aprobado. No registrar URL completa, `share` token, email, user ID crudo, target, thresholds, child ages, raw provider, auth token ni cache key privada.

## 8. i18n, accesibilidad y UX

- “Guardar búsqueda” y “Compartir búsqueda” son acciones distintas de “Guardar hotel”, “Seguir precio” y “Crear alerta”;
- el copy explica si el enlace es público/read-only o si la búsqueda está sincronizada con la cuenta;
- una URL compartida no revela que existe una búsqueda guardada privada;
- estados `idle`, `restoring`, `invalid`, `stale`, `auth_required`, `not_found`, `error` y `success` tienen copy ES/EN;
- errores no se muestran como “no hay hoteles”;
- el formulario conserva labels, `aria-describedby`, focus al error y anuncio de restauración;
- “Buscar” sigue siendo acción explícita después de restore cuando pueda producir provider call;
- botones de guardar/compartir tienen estado pending/success/error, no toasts como única evidencia;
- mobile, dark/light, teclado, zoom 200%, reduced motion y targets de 48 px siguen H32-H34/H40;
- no se muestran tokens ni IDs privados en aria-labels, títulos, clipboard o analytics.

## 9. Tests y evidencia

### Unit/contract

- canonicalización determinista aunque cambie el orden de params/JSON;
- `StayQuery` rechaza fechas inválidas, moneda/radius/filtros no allowlisted y coordenadas inconsistentes;
- URL pública excluye user, email, target, threshold, tracking, rule, snapshot y token de sesión;
- versión desconocida degrada con estado `unsupported_version`, no ejecuta provider;
- parser acepta aliases históricos solo con allowlist y produce canonical URL;
- share token, si se añade, es opaco, aleatorio, read-only, TTL y no autoriza recursos privados;
- guardado requiere auth y ownership; usuario B no puede leer/editar/eliminar A;
- búsquedas exactas y flexibles tienen semántica y fingerprints distintos;
- búsqueda guardada no se convierte en tracking/alerta;
- delete/expire no reaparece por cache/retry;
- restore no llama provider implícitamente;
- explicit search sí puede llamar al endpoint permitido con fingerprint correcto;
- telemetry redacts URL/token/user/private fields.

### Integration/browser

1. completar búsqueda hotelera;
2. canonicalizar URL y copiar/enviar el enlace;
3. abrirlo en una sesión sin historial;
4. comprobar formulario restaurado sin llamada provider implícita;
5. pulsar Buscar y verificar que la llamada ocurre una sola vez;
6. guardar búsqueda autenticada;
7. refrescar/listar/editar/pausar/eliminar con ownership;
8. usuario B intenta abrir ID/token de A y recibe fallback genérico;
9. cambiar fechas/filtros produce nueva fingerprint;
10. back/forward no pierde contexto ni duplica requests;
11. usar H44 demo y provider off: todo queda rotulado y fail-closed;
12. repetir ES/EN, dark/light, móvil, teclado y zoom.

### Gate H48

H48 podrá considerarse implementada cuando:

1. una URL compartible reconstruye una `StayQuery` pública sin PII ni ownership;
2. la URL tiene schema/versionado, canonicalización, allowlist y aliases definidos;
3. restaurar una URL no ejecuta provider live ni crea tracking/alerta automáticamente;
4. una búsqueda guardada privada tiene CRUD, ownership, lifecycle, retención y cache aislada;
5. búsqueda exacta, flexible, favorito, tracking y alerta no se confunden;
6. auth/re-auth conserva intención y reanuda una mutación una sola vez/idempotentemente;
7. back/forward/refresh restauran el estado sin requests duplicados;
8. errores, stale, unsupported version, not-found y provider off conservan contexto y no se convierten en empty engañoso;
9. analítica, logs, clipboard y deeplinks no filtran tokens, PII ni campos privados;
10. no se realizan llamadas implícitas al provider al montar/abrir/guardar;
11. tests de dos usuarios, cache, TTL, share token opcional y browser QA pasan;
12. H47 recibe una búsqueda restaurable y H49 puede consumir preferencias sin cambiar la semántica de la query.

**Resultado H48:** el parser/restauración URL y la persistencia privada CRUD local están implementados con tests de canonicalización, dos usuarios, idempotencia, validación de privacidad y no ejecución implícita. El lifecycle local usa `active/paused` y DELETE físico; no se presenta como archivado ni expiración productiva. Siguen pendientes los share tokens públicos, expiración/retención productiva, cache privada avanzada, re-auth, browser QA y provider live.
