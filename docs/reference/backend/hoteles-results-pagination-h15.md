# H15 — Contrato versionado de resultados y paginación hotelera

**Estado:** contrato de API y consumo; implementación V2 pendiente  
**Fuente de verdad:** sí, para envelopes, metadata, warnings, capacidades, estados y paginación de hoteles  
**Fase del roadmap:** H15  
**Dependencias:** H05, H06, H09, H10, H11, H12, H13, H14  
**Consumidores principales:** frontend `/hoteles`, hooks de búsqueda, cards, detalle, tracking y QA

## 1. Propósito y decisión de fase

H15 evita que frontend y backend tengan que adivinar el significado de una lista vacía, un campo ausente o un resultado parcial. Define una respuesta rica y estable para búsquedas, resultados por área, detalle de oferta y futuras capacidades de tracking.

Esta fase es **contractual**. No implementa todavía rutas V2 ni cambia las listas de V1. La implementación debe ser aditiva, probarse junto al cliente actual y poder retirarse mediante flag sin invalidar datos ni consumidores existentes.

La regla principal es:

> La longitud de `data` nunca es el único indicador del estado de una búsqueda.

## 2. Estado actual comprobable

### 2.1. Rutas V1 actuales

Las rutas hoteleras están bajo el prefijo V1 y actualmente devuelven principalmente listas desnudas:

- `GET /hotels/search` → `list[HotelSearchOut]`;
- `GET /hotels/area-search` → `list[HotelAreaSearchResultOut]`;
- `GET /hotels/watchlist` → `list[HotelWatchlistItemOut]`;
- `GET /hotels/alert-events` → `list[HotelAlertEventOut]`;
- `GET /hotels/tracked-offers` → `list[HotelTrackedOfferOut]`;
- `GET /hotels/{hotel_id}/rates` → `list[HotelRateOut]`;
- `GET /hotels/{hotel_id}/parity` → `list[HotelParityOut]`;
- `GET /hotels/tracked-offers/{id}/snapshots` → `list[HotelRateOut]`.

La ruta `area-resolve` y las operaciones de escritura/de detalle devuelven objetos planos, no un envelope de colección común.

### 2.2. Paginación actual

- `HotelSearchQueryIn` y `/hotels/search` aceptan `limit` y `offset`, pero no devuelven `total`, `has_more` ni cursor.
- `alert-events` acepta `limit` y `offset`, pero el cliente de hoteles no recibe metadata de continuación.
- `area-search` no tiene paginación contractual; devuelve toda la lista calculada por el servicio.
- watchlist, tracked offers, rates, snapshots y parity tampoco declaran una estrategia de colección escalable.
- Los límites de entrada reducen el riesgo inmediato, pero no sustituyen metadata ni una política de payload grande.

### 2.3. Estados que hoy se infieren

El frontend actual infiere estados desde listas, excepciones y un booleano `loading`:

- `[]` puede significar consulta válida sin resultados, provider vacío, catálogo sin cobertura o fallo oculto;
- una respuesta parcial de provider puede mezclarse con fallback local sin warning de hotel estructurado;
- `lowest_price=null` no explica si no hubo observación, si el provider falló o si el precio no era comparable;
- `HotelsRequestError` recibe principalmente el mensaje normalizado del helper compartido;
- `apiFetchWithStatus` ya devuelve códigos, detalles, retry y correlation ID para errores, pero los contratos hoteleros V1 no los exponen de forma uniforme;
- el hook `useHotelSearch` mantiene estado efímero y no cancela de forma específica las búsquedas anteriores;
- existe un bug conocido en el helper compartido: `apiFetchWithStatus` sobrescribe actualmente `init.signal` con `controller?.signal`; por tanto, descarta el `AbortSignal` del caller tanto si hay timeout como si no lo hay. H15 exige corregirlo y añadir una regresión antes de afirmar que la cancelación frontend funciona.

H15 no convierte esas limitaciones en capacidades. Las hace visibles y define la migración.

## 3. Versionado y superficie V2

### 3.1. Estrategia

La primera implementación debe crear rutas aditivas V2, usando el prefijo efectivo que resulte del montaje real de routers. Como forma conceptual, no como URL todavía congelada:

```text
<api-prefix>/v2/hotels/search
<api-prefix>/v2/hotels/area-search
<api-prefix>/v2/hotels/watchlist
<api-prefix>/v2/hotels/alert-events
<api-prefix>/v2/hotels/tracked-offers
<api-prefix>/v2/hotels/{hotel_id}/rates
<api-prefix>/v2/hotels/{hotel_id}/parity
```

H15 de implementación debe confirmar si el prefijo efectivo será `/api/v2`, `/api/hotels/v2` u otra composición según `main.py` y los routers instalados. Esa decisión debe quedar en contract tests y documentación de despliegue. No se debe sustituir V1 mediante rewrite silencioso ni cambiar el tipo de respuesta de una ruta existente.

H15 puede comenzar con V2 para búsqueda y `area-search`; el resto de colecciones se incorpora cuando sus campos y ownership estén preparados. Cada endpoint debe publicar su versión de contrato y capability set.

### 3.2. V1 permanece estable

- V1 conserva listas y campos existentes durante la transición.
- No se añade un envelope a V1 si eso rompe consumidores.
- El cliente frontend debe usar un adaptador explícito `V1 list → normalized collection`.
- El adaptador debe distinguir “payload V1 válido” de “payload V2 válido”; nunca aceptar cualquier objeto con `data` como si fuera V2.
- V2 puede tener campos adicionales y metadata sin contaminar los tipos V1.
- La retirada de V1 requiere inventario de consumidores, periodo de compatibilidad, métricas y rollback documentado.

## 4. Envelope V2 de colección

La forma canónica para búsquedas y colecciones es:

```json
{
  "data": [],
  "meta": {
    "contract_version": "hotels.results.v2",
    "request_id": "req_…",
    "generated_at": "2026-08-05T12:00:00Z",
    "result_state": "success",
    "query": {},
    "pagination": {},
    "freshness": {},
    "providers": [],
    "capabilities": {},
    "warnings": []
  }
}
```

### 4.1. Reglas del envelope

- `data` siempre es un array en endpoints de colección, aunque esté vacío.
- `meta` siempre existe en V2 y no se rellena con `null` ambiguo.
- `contract_version` identifica semántica, no solo la URL.
- `request_id` correlaciona respuesta, logs y eventos; no debe ser un token de autorización.
- `generated_at` se serializa en ISO-8601 UTC con `Z`.
- `warnings` es una lista estructurada, no texto concatenado.
- `query` contiene solo el contexto necesario para reproducir la consulta; no contiene `user_id`, email, token, thresholds privados ni payloads completos de sesión.
- `data` no contiene campos privados de ownership. Puede contener booleanos derivados como `has_tracking` cuando la consulta está autenticada y la semántica esté documentada.

### 4.2. Envelope de recurso único

Para un detalle V2 se mantiene la misma metadata, pero `data` es un objeto:

```json
{
  "data": {"id": "hotel_123"},
  "meta": {
    "contract_version": "hotels.resource.v2",
    "request_id": "req_…",
    "result_state": "success",
    "warnings": []
  }
}
```

Un endpoint no debe alternar entre objeto, array y `null` según el caso. Recurso inexistente es un error HTTP 404 con error envelope; no es `data: null` con 200.

## 5. Metadata canónica

### 5.1. Estado del resultado

`meta.result_state` usa estados del resultado lógico, no de freshness ni de provider:

```text
success
empty
partial
```

Semántica:

- `success`: datos válidos y suficientes para el contexto, sin degradación relevante.
- `empty`: la consulta fue válida y terminó correctamente, pero no hay resultados elegibles.
- `partial`: hay resultados válidos, pero una fuente, capability o parte del enriquecimiento falló.

La fuente y frescura se expresan por separado en `meta.freshness`, `meta.providers` y warnings:

- `meta.freshness.state`: `fresh|recent|cached|historical|stale|unknown`;
- `meta.providers[].status`: `ok|empty|timeout|rate_limited|disabled|failed|not_configured`;
- un fallback de provider se señala con `provider_fallback_used` y/o `result_state="partial"`.

Un contexto inválido no es un resultado 200: se devuelve 422 con error envelope y código `invalid_context`. Una falta de autorización es 401/403; un fallo total es 5xx o código de infraestructura apropiado. Así no se mezclan en una sola enumeración estado de datos, procedencia y HTTP.

### 5.2. Query echo seguro

`meta.query` puede incluir:

```json
{
  "mode": "area",
  "destination": {"area_label": "Madrid", "confidence": "high"},
  "check_in": "2026-09-10",
  "check_out": "2026-09-14",
  "guests": 2,
  "currency": "EUR",
  "radius_km": 10,
  "filters": {"min_stars": 4, "max_price": 600},
  "sort": "price"
}
```

No debe incluir coordenadas de precisión innecesaria si `destination_id` o área normalizada bastan para explicar la búsqueda. H35 decide retención y telemetría final.

### 5.3. Freshness

El bloque de freshness deriva de H05 y no inventa una única edad para datos mezclados. `result_state` no cambia por el mero hecho de que el dato sea cached o stale; esa dimensión vive aquí y en los warnings:

```json
{
  "state": "fresh|recent|cached|historical|stale|unknown",
  "observed_at": "2026-08-05T11:58:00Z",
  "age_seconds": 120,
  "expires_at": "2026-08-05T12:08:00Z",
  "mixed": true,
  "requires_revalidation": false
}
```

Si cada resultado tiene una freshness diferente, `meta.freshness.mixed=true` y el resultado debe llevar su propia procedencia/freshness cuando sea material para decidir. `cached` no se presenta como `live`.

### 5.4. Providers consultados

```json
{
  "id": "makcorps",
  "operation": "area_search",
  "status": "ok|empty|timeout|rate_limited|disabled|failed|not_configured",
  "results_count": 12,
  "used_for_results": true,
  "fallback_used": true,
  "latency_ms": 840
}
```

No se incluyen secretos, URLs privadas ni el payload bruto del provider. `status=empty` no equivale a `status=failed` ni a `sold_out`.

### 5.5. Capabilities

Las capabilities anuncian lo que la respuesta respalda, no todo lo que la UI desea mostrar:

```json
{
  "filters": {
    "radius_km": "supported",
    "min_stars": "supported",
    "max_price": "supported_with_unknown_price",
    "cancellation": "unavailable",
    "rooms": "planned"
  },
  "sorts": {
    "price": "supported",
    "distance": "supported",
    "stars": "supported",
    "recommended": "unavailable"
  },
  "actions": {
    "track": "supported",
    "deeplink": "partial",
    "refresh": "planned"
  }
}
```

Valores permitidos:

```text
supported
supported_with_caveat
partial
planned
unavailable
```

La UI no debe activar un filtro que metadata marque como `planned` o `unavailable`.

## 6. Warnings estructurados

H15 reutiliza la idea existente de `ProviderWarning`/`warnings_structured`, adaptada al contrato HTTP:

```json
{
  "code": "provider_timeout",
  "severity": "info|warning|error",
  "message_key": "hotels.warnings.providerTimeout",
  "provider": "makcorps",
  "scope": "collection|result|field",
  "result_ids": [],
  "meta": {"fallback": "shared_cache"}
}
```

Reglas:

- `message_key` permite i18n; el backend no debe imponer copy largo en un idioma.
- `meta` contiene datos técnicos no sensibles y tiene allowlist por código.
- `result_ids` solo se usa para warnings result-level y está limitado para evitar payload excesivo.
- warnings se deduplican por código, provider, scope y metadata estable.
- severidad `error` en warning no significa necesariamente HTTP 500: puede describir un provider fallido dentro de una respuesta partial.

Códigos iniciales recomendados:

```text
provider_timeout
provider_rate_limited
provider_unavailable
provider_empty_result
provider_not_configured
provider_fallback_used
provider_partial_coverage
stale_observation
mixed_freshness
price_unavailable
price_not_comparable
currency_not_supported
tracking_state_unavailable
result_enrichment_partial
pagination_limit_applied
```

## 7. Contrato de resultado hotelero V2

H15 no redefine todavía todos los campos de `StayOffer` de H10, pero exige que cada resultado declare el contexto mínimo y la semántica de precio:

```json
{
  "hotel_id": "hotel_123",
  "canonical_name": "Hotel Example",
  "city": "Madrid",
  "country_code": "ES",
  "stars": 4,
  "distance_km": 1.2,
  "price": {
    "amount": 420.0,
    "currency": "EUR",
    "basis": "total_stay|per_night|unknown",
    "status": "observed|unavailable|not_comparable|stale",
    "observed_at": "2026-08-05T11:58:00Z"
  },
  "stay_context": {
    "check_in": "2026-09-10",
    "check_out": "2026-09-14",
    "guests": 2,
    "rooms": null
  },
  "provider": "mock",
  "has_tracking": false,
  "explanation": {
    "primary_reason": "lowest_observed_price",
    "codes": ["price_context_match"]
  }
}
```

El bridge V1 puede seguir exponiendo `lowest_price`, `currency`, `provider`, `check_in`, `check_out`, `guests` y `has_tracking`. El adaptador V1→V2 debe marcar campos no presentes como `unknown`, nunca inventar `basis`, freshness, fees, cancellation ni availability.

## 8. Paginación

### 8.1. Elección contractual

V2 usará cursor opaco para colecciones potencialmente dinámicas:

```json
"pagination": {
  "mode": "cursor",
  "limit": 20,
  "returned": 20,
  "total": null,
  "has_next": true,
  "next_cursor": "h2c1.…",
  "previous_cursor": null,
  "sort": "price",
  "snapshot_token": "search_…"
}
```

- `next_cursor` es opaco, versionado, con expiración y firmado o protegido contra manipulación.
- El cliente no decodifica ni construye cursores.
- `snapshot_token` mantiene la coherencia de orden cuando el conjunto cambia; no contiene datos privados legibles.
- `total` es opcional y puede ser `null` cuando contarlo sea caro o no fiable.
- `returned` siempre es el número real de elementos de `data`.
- `has_next=false` implica que no hay siguiente cursor utilizable.

### 8.2. Bridge temporal de offset

V1 conserva `limit`/`offset`. Durante la migración, V2 puede aceptar un parámetro de compatibilidad o traducir internamente offset a cursor, pero:

- la respuesta V2 sigue entregando cursor opaco;
- no se promete estabilidad si el backend usa offset contra un conjunto mutable;
- la traducción debe limitar profundidad y evitar consultas costosas por offsets enormes;
- se mide el uso del bridge para poder retirarlo.

No se debe llamar “cursor real” a un token que expone `{offset: 20}` sin firma y sin política de expiración. Si la primera implementación lo usa como stepping stone, debe declararlo en `meta.pagination.mode="cursor_bridge"` y mantener el mismo contrato de opacidad para el cliente.

### 8.3. Orden y estabilidad

El cursor se calcula sobre el orden completo, incluyendo desempates de H14:

```text
(sort_key, stable_hotel_id)
```

Cambiar filtros u orden invalida el cursor anterior. Un cursor de otra query, versión, usuario o capability set debe devolver `cursor_invalid`/`pagination_context_mismatch`, no resultados mezclados.

### 8.4. Límites

- `limit` mínimo 1 y máximo definido por endpoint/coste;
- el backend puede aplicar un máximo menor y emitir `pagination_limit_applied`;
- no se devuelve un payload ilimitado por omitir `limit`;
- el frontend no debe paginar localmente una colección que el backend ha truncado sin metadata;
- payloads grandes se cubren con tests de memoria, latencia y serialización.

## 9. Errores HTTP V2

Los errores deben seguir la convención existente de `ApiError`/`error_envelope`:

```json
{
  "status": 422,
  "code": "invalid_date_range",
  "message": "Request validation failed.",
  "details": [
    {"field": "check_out", "code": "form.dates.invalid_order"}
  ],
  "correlation_id": "corr_…",
  "retry_after_sec": null
}
```

Códigos mínimos:

```text
invalid_context
invalid_date_range
invalid_occupancy
invalid_currency
invalid_filter
invalid_sort
cursor_invalid
cursor_expired
provider_unavailable
hotel_not_found
not_allowed
rate_limit_exceeded
internal_error
```

Reglas:

- no devolver 200 con un error escondido en `data=[]`;
- no devolver stack traces, secretos ni payloads externos;
- `correlation_id` debe poder localizar el request en logs redacted;
- `retry_after_sec` solo aparece cuando la repetición tiene sentido;
- mensajes visibles se resuelven por código/message key en frontend, no se copian directamente de excepciones Python;
- una respuesta `partial` útil usa 200 + warnings; un fallo total usa error HTTP.

## 10. Cancelación y búsquedas repetidas

### 10.1. Frontend

El adaptador V2 y el hook deben:

1. crear un `AbortController` por búsqueda;
2. abortar la petición anterior antes de lanzar una nueva;
3. mantener el `signal` del caller al combinarlo con timeout interno;
4. asignar un `request_id` o contador monotónico por búsqueda;
5. descartar respuestas cuyo request ya no sea el activo;
6. no mostrar “error” por una cancelación intencionada;
7. conservar la última búsqueda válida mientras llega la nueva respuesta;
8. exponer `loading_phase` y `result_state` sin volver a `[]` durante cada transición.

La corrección del helper compartido de timeout/cancelación debe tener su propio test de regresión; H15 no debe asumir que pasar `signal` ya funciona en todos los caminos.

### 10.2. Backend

- aceptar `x-correlation-id`/request ID conforme a la infraestructura existente;
- no comenzar una llamada externa costosa si la validación ya falló;
- cooperar con disconnect/cancelación ASGI cuando sea compatible con el worker;
- imponer timeout y budget por provider aunque el cliente cancele;
- no dejar locks, sesiones DB ni jobs de provider abiertos tras cancelación;
- una cancelación no escribe un resultado parcial como si fuera éxito.

El backend no necesita inventar un endpoint de cancelación para una request HTTP normal. Si una operación se convierte en job asíncrono, H09/H23 deben definir cancelación/idempotencia por job.

## 11. N+1, ownership y seguridad de datos

### 11.1. N+1

La respuesta V2 debe construirse con una consulta por lote o estrategia equivalente para:

- hoteles y coordenadas;
- mejor snapshot/precio compatible;
- provider/freshness;
- estado de tracking del usuario autenticado;
- favoritos/watchlist si se incluye.

No se permite un `SELECT` o request provider por cada card dentro del serializador. Los contract tests deben contar queries en casos representativos y detectar regresiones.

### 11.2. Ownership

- El backend deriva el usuario del token; ningún query param ni payload de lectura acepta `user_id` como autoridad.
- `has_tracking`, `is_watched` y similares son proyecciones del usuario autenticado, no datos públicos globales.
- Las consultas se filtran por ownership antes de construir la proyección.
- Un cursor de una cuenta no es reutilizable en otra.
- Errores de un recurso ajeno no deben revelar si existe mediante diferencias de payload no justificadas.
- Nunca incluir `user_id`, email, alert thresholds o notas privadas en una colección pública de resultados.

## 12. Compatibilidad frontend/backend

### 12.1. Tipos separados

Crear tipos V2 separados, por ejemplo:

```text
HotelCollectionV2<T>
HotelResultsMetaV2
HotelPaginationV2
HotelWarningV2
HotelCapabilitySetV2
HotelApiErrorV2
```

No mutar `HotelAreaSearchResultOut` ni `HotelSearchOut` para que representen simultáneamente V1 y V2. El adaptador puede producir un modelo de vista común, pero debe conservar `source_contract="v1"|"v2"` y marcar la pérdida de metadata.

### 12.2. Migración progresiva

1. congelar fixtures V1 actuales;
2. añadir schemas V2 sin cambiar rutas V1;
3. implementar adaptadores backend/cliente y contract tests;
4. activar V2 solo para búsqueda detrás de flag;
5. comparar shadow payloads sin cambiar la UI;
6. migrar `useHotelSearch` y estados de resultados;
7. activar `area-search` y después colecciones secundarias;
8. medir errores, latencia, payload, estado partial y uso del bridge;
9. retirar V1 solo con evidencia y rollback.

### 12.3. Shadow compare

El shadow compare debe comparar solo campos semánticamente equivalentes:

- IDs y orden estable;
- count devuelto;
- precio/moneda/contexto;
- provider y freshness cuando V1 los tenga;
- `has_tracking` con el mismo usuario;
- estado de filtrado y sort.

No se marca como divergencia que V2 añada warnings, capabilities o metadata que V1 no tenía. Las discrepancias se redaccionan y no deben incluir credenciales ni querys completas.

## 13. Tests y gates de aceptación

### 13.1. Schemas y serialización

- colección vacía conserva `data=[]` y `meta.result_state="empty"`;
- recurso ausente devuelve 404 con error envelope;
- datetimes salen en UTC `Z`;
- `null` se usa solo con semántica documentada;
- warnings se deduplican y conservan i18n key;
- capabilities coinciden con filtros/sorts realmente aplicados;
- el envelope no expone ownership privado.

### 13.2. Paginación

- primera página, siguiente cursor y fin de colección;
- cursor expirado, manipulado, de otra query, otro usuario u otro sort;
- cambios en dataset no duplican ni saltan resultados dentro del snapshot token;
- límite por endpoint y límite aplicado documentado;
- total opcional no se interpreta como cero cuando es `null`;
- payload grande mantiene latencia/memoria bajo el presupuesto H37.

### 13.3. Provider y estados

- provider OK, vacío, timeout, 429, disabled y fallback local;
- error parcial no se convierte en `sold_out`;
- `stale`, `cached`, `partial` y `provider_unavailable` se distinguen;
- precio desconocido no es precio cero;
- moneda/contexto incompatibles producen warning o exclusión explícita;
- provider no puede sobrescribir un resultado de otro contexto.

### 13.4. Frontend

- adaptador consume V1 y V2 con tipos separados;
- URL/refresh/back-forward conserva cursor solo cuando el contexto coincide;
- nueva búsqueda cancela o invalida la anterior;
- respuesta antigua no pisa resultados nuevos;
- cancelación no muestra toast de error;
- `aria-live` anuncia estado, warnings y continuidad;
- UI no muestra filtros/sorts que capabilities marcan como no disponibles;
- retry usa `retry_after_sec` y no crea una tormenta de requests.

### 13.5. Integración y seguridad

- auth y ownership entre dos usuarios;
- no aceptar `user_id` para ampliar alcance;
- no filtrar datos privados en query echo, cursor, logs o warnings;
- correlation ID estable entre frontend, API y logs;
- contract tests de payloads V1 congelados y V2 versionados;
- rollback de flag V2 a V1 sin perder búsqueda ni tracking.

## 14. Observabilidad

Registrar sin PII innecesaria:

- `hotel_results_contract_version`;
- `hotel_results_state`;
- `hotel_results_warning_code`;
- `hotel_results_provider_status`;
- `hotel_results_page_requested`;
- `hotel_results_cursor_invalid`;
- `hotel_results_cancelled`;
- `hotel_results_stale_response_discarded`;
- latencia backend/provider/serialización;
- tamaño de `data` y bytes de payload;
- queries SQL por request en muestras controladas;
- porcentaje V1/V2, shadow divergence y fallback.

No registrar cursores descifrables, tokens, emails, thresholds ni coordenadas exactas salvo necesidad operativa justificada.

## 15. Handoffs

- **H05:** aplicar freshness, provenance, availability y confidence sin mezclar sus vocabularios.
- **H06:** reutilizar provider-neutral warnings, capacidades, errores y fallback.
- **H09:** coordinar timeouts, budgets, leases y cancelación de operaciones externas; por eso es dependencia operativa de la implementación H15.
- **H10/H11:** mapear StayQuery/StayOffer, migración y snapshots sin perder compatibilidad.
- **H12/H13:** transportar destination resolution, URL state y validación en `meta.query` sin datos privados.
- **H14:** reflejar filtros, orden, `price_status` y explicaciones realmente aplicadas.
- **H16:** consumir cards sin inferir precio, freshness o estado desde campos ausentes.
- **H17:** transportar ranking, tie-breakers y explicación versionada.
- **H21:** representar empty/partial/error/stale con acciones siguientes.
- **H23/H24:** devolver contexto suficiente para tracking, histórico y refresh.
- **H35/H38:** revisar privacidad, ownership, cursor, correlation ID y deeplinks.
- **H37/H39:** medir payload, N+1, concurrencia, carga y matriz de contract tests.
- **H41/H43:** instrumentar, versionar, flaggear y apagar V2 de forma segura.

## 16. Gate H15

H15 podrá considerarse implementada cuando:

1. búsqueda y `area-search` tengan una V2 aditiva con envelope documentado;
2. `data`, `meta`, estados, warnings y capabilities estén cubiertos por schemas y tests;
3. la paginación sea limitada, estable y segura, con cursor opaco o bridge explícitamente etiquetado;
4. V1 siga funcionando y exista adaptador probado;
5. frontend pueda distinguir empty, partial, stale, cached, provider unavailable y error sin adivinar;
6. cancelación y respuestas obsoletas estén cubiertas en hook/helper y E2E;
7. no existan N+1 ni fugas de ownership en los paths principales;
8. payloads grandes, provider fallido y rollback de flag estén verificados;
9. la documentación de H15, roadmap, índices y contract tests permanezcan sincronizados.
