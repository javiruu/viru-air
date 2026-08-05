# H06 — Contrato provider-neutral de hoteles y contract tests

**Estado:** completo como contrato — pendiente de implementación gradual  
**Fecha:** 2026-08-04  
**Área:** backend / arquitectura / providers / QA  
**Fuente de verdad:** sí para la frontera entre providers de hoteles y el dominio de Viru. La implementación puede evolucionar por etapas, pero no debe introducir semántica provider-específica en servicios, API o UI.

**Depende de:** [H05 — procedencia, freshness y confidence](hoteles-freshness-provenance-confidence-h05.md)  
**Relacionado con:** H07 auditoría Makcorps, H08 onboarding de providers, H09 sweeps, H10 modelo canónico de estancia/oferta, H15 contrato de resultados, H35 seguridad de deeplinks.

---

## 1. Propósito y límite de la fase

H06 define una frontera reemplazable entre cualquier fuente externa de hoteles y el dominio de Viru. El dominio debe poder preguntar por hoteles, tarifas y revalidaciones sin conocer nombres de endpoints, formas de payload, códigos de error, límites comerciales o peculiaridades de un provider concreto.

La fase **no integra un provider nuevo**, no decide todavía si Makcorps continuará y no cambia por sí sola el modelo de base de datos. Produce el contrato que H07-H11 y los futuros adapters deben implementar y probar.

### 1.1. Regla de arquitectura

```text
HotelSearch/Tracking domain
        ↓  contrato canónico
Provider gateway / orchestrator
        ↓  adapter aislado
Provider externo
```

Nunca debe ocurrir lo contrario:

- `hotels_service` no debe importar clases concretas de Makcorps;
- la API no debe interpretar `429`, `comparison`, `hotelId` u otros detalles externos;
- el frontend no debe inferir que una lista vacía significa agotado;
- un provider no debe crear directamente entidades de usuario, alertas o favoritos;
- el dominio no debe usar el nombre de un campo externo como contrato público.

### 1.2. Estado real de partida

La implementación actual debe considerarse **V1 compatible**:

| Pieza actual | Evidencia | Limitación que H06 no oculta |
|---|---|---|
| `HotelProviderAdapter` | `backend/app/hotels/contracts.py` | expone listas desnudas y no un envelope común |
| `ProviderHotelRecord` / `ProviderRateRecord` | `backend/app/hotels/contracts.py` | no contienen capacidades, warnings, timestamps, fees, disponibilidad o deeplink por rate |
| `MockHotelProviderAdapter` | `backend/app/hotels/mock_provider.py` | fixture útil para desarrollo; no representa datos live |
| `MakcorpsHotelProviderAdapter` | `backend/app/hotels/makcorps_provider.py` | traduce fallos de request a `None`/listas vacías y usa retries de `requests` |
| `HotelIngestionService` | `backend/app/hotels/ingestion.py` | trabaja con `fetch_hotels()` y persiste sin envelope de partial/error |
| `HotelProviderRun` | `backend/app/infrastructure/db/models.py` | hoy distingue principalmente `running`, `completed` y `failed` |
| tests actuales | `backend/tests/unit/test_hotels_ingestion.py`, `backend/tests/unit/test_hotels_makcorps_provider.py` | prueban parsers y comportamiento V1, pero no un contrato común entre adapters |

**Compatibilidad obligatoria:** H06 no rompe de golpe estos consumidores. La adopción V2 debe tener un adaptador/puente explícito y tests de equivalencia antes de retirar V1.

---

## 2. Objetivos y no objetivos

### Objetivos

1. Definir capacidades declarativas y consultables antes de llamar a un provider.
2. Definir operaciones provider-neutral para catálogo, búsqueda, tarifas, revalidación y deeplink.
3. Devolver siempre un envelope tipado con datos, estado, warnings, errores, trazabilidad y límites.
4. Distinguir vacío válido, parcial, no disponible, error transitorio y error permanente.
5. Hacer que retries, timeouts y rate limits sean decisiones del gateway, no copy-paste de cada adapter.
6. Mantener procedencia, timestamps y condiciones necesarias para H05.
7. Validar deeplinks antes de que lleguen a la UI o a un redirect público.
8. Permitir contract tests reutilizables para Mock, Makcorps y futuros providers.

### Fuera de H06

- seleccionar el mejor provider comercial;
- prometer cobertura geográfica o disponibilidad final;
- diseñar el ranking de hoteles;
- crear migraciones definitivas de `HotelRateSnapshot`;
- elegir email, push, afiliación o un servicio externo;
- convertir cualquier provider real en una fuente de verdad de reservas.

---

## 3. Contrato conceptual V2

La forma concreta puede ser `dataclass`, modelo Pydantic u otro tipo interno coherente con el backend. Lo obligatorio es la semántica y la estabilidad de los campos, no el nombre de una librería.

### 3.1. Identidad del adapter

Cada adapter declara:

```text
provider_id: str                  # estable, minúsculas, no cambia por endpoint
contract_version: str             # ejemplo: hotel-provider-v2
is_enabled() -> bool
capabilities() -> ProviderCapabilities
```

`provider_id` identifica al origen lógico y no debe incluir API key, región, usuario ni URL dinámica.

### 3.2. Capacidades declarativas

Las capacidades deben ser datos, no detección implícita por excepciones. El siguiente objeto es **hipotético e ilustrativo**; no describe capacidades aprobadas de Makcorps. H07 debe sustituirlo por una matriz basada en documentación, pruebas y observaciones reproducibles.

```json
{
  "provider_id": "provider-under-evaluation",
  "contract_version": "hotel-provider-v2",
  "supports_catalog": null,
  "supports_area_search": null,
  "supports_hotel_rates": null,
  "supports_direct_revalidation": null,
  "supports_parameterized_occupancy": null,
  "supports_multiple_rooms": null,
  "supports_children_ages": null,
  "supports_total_fees": null,
  "supports_room_type": null,
  "supports_meal_plan": null,
  "supports_cancellation_policy": null,
  "supports_availability_status": null,
  "supports_partner_deeplink": null,
  "supports_cursor_pagination": null,
  "supports_idempotency_key": null,
  "max_concurrency": null,
  "declared_rate_limit": {
    "requests_per_window": null,
    "window_seconds": null,
    "source": "provider_docs_or_observed"
  }
}
```

Reglas:

- `false` significa “el adapter no puede garantizarlo”, no “el provider nunca lo hace”.
- `null` significa desconocido; el orchestrator debe tratarlo de forma conservadora.
- No declarar una capacidad solo porque un campo aparece en un payload aislado.
- Las capacidades deben incluir tests que fallen si el adapter devuelve datos incompatibles.
- La UI y el dominio consumen capacidades normalizadas, nunca flags propios de Makcorps.

### 3.3. Operaciones mínimas

Todas las operaciones V2 deben recibir un contexto canónico y devolver `ProviderResult[T]`. El adapter abstracto actual no impone todavía estas firmas: `fetch_hotels()` y `fetch_hotel_rates(...)` coexisten con firmas divergentes entre Mock y Makcorps. H07/H09 deben definir el mapeo operación-por-operación y cubrirlo con tests antes de cambiar el consumidor.

```text
list_catalog(context: CatalogQuery) -> ProviderResult[ProviderHotelRecord]
search_area(context: AreaSearchQuery) -> ProviderResult[ProviderHotelRecord]
get_rates(context: RateQuery) -> ProviderResult[ProviderRateRecord]
revalidate_offer(context: RevalidationQuery) -> ProviderResult[ProviderRateRecord]
build_deeplink(context: DeeplinkQuery) -> ProviderResult[ProviderDeeplink]
```

Una operación puede no estar soportada. En ese caso devuelve un resultado `unsupported_capability`, no una excepción genérica ni una lista vacía indistinguible de “sin resultados”.

#### Contexto canónico común

```text
request_id             identificador de trazabilidad interno
operation              nombre canónico de operación
provider_hotel_id      ID externo opaco, si ya existe
canonical_hotel_id     ID interno, si el dominio ya resolvió matching
area                   destino/coordenadas/radio, sin payload innecesario
check_in/check_out     fechas locales de la estancia
rooms                  número de habitaciones, si aplica
guests                 ocupación normalizada
children_ages          edades, solo si la capacidad y la política lo permiten
currency               ISO-4217 solicitado
timeout_ms             límite de esta operación
idempotency_key        solo para operaciones que puedan mutar estado externo
```

El adapter nunca recibe credenciales desde el request del usuario; resuelve secretos desde la configuración segura del proceso.

---

## 4. Envelope de resultado

### 4.1. Forma canónica

```json
{
  "contract_version": "hotel-provider-v2",
  "provider_id": "makcorps",
  "operation": "get_rates",
  "request_id": "opaque-request-id",
  "status": "partial",
  "items": [],
  "item_errors": [],
  "warnings": [],
  "error": null,
  "pagination": null,
  "rate_limit": {
    "remaining": null,
    "reset_at": null,
    "retry_after_seconds": null
  },
  "observed_at": null,
  "provider_request_id": null,
  "capabilities_used": ["supports_hotel_rates"],
  "diagnostics": {
    "latency_ms": 0,
    "attempts": 1
  }
}
```

### 4.2. Estados permitidos

| Estado | Significado | Comportamiento del dominio |
|---|---|---|
| `success` | operación completada con datos válidos | puede persistir y presentar según H05 |
| `empty` | provider respondió correctamente sin items aplicables | mostrar “sin resultados”; no llamar a provider error |
| `partial` | hay datos válidos, pero faltan items o capacidades/segmentos fallaron | presentar con warning y metadata de cobertura |
| `unsupported` | la capacidad no existe para este adapter | no reintentar automáticamente; aplicar fallback explícito |
| `rate_limited` | el provider impuso límite o el budget local bloqueó la llamada | respetar `retry_after`; no convertir en vacío/sold out |
| `timeout` | se agotó el timeout de la operación | retry solo si la política lo permite; conservar cache si es elegible |
| `unavailable` | provider/configuración/servicio externo no disponible | degradar honestamente; no afirmar agotado |
| `invalid_response` | payload recibido pero no valida el contrato | no persistir rates inválidos; alertar adapter |
| `failed` | error no recuperable o no clasificado de otra forma | registrar error sanitizado y permitir fallback |

Invariantes:

- `success` y `empty` no tienen `error` fatal.
- `partial` debe incluir al menos un item válido o un `item_error` explícito por segmento; si no, usar `failed`, `timeout`, `unavailable` o `empty` según el caso.
- `rate_limited` no equivale a `empty` ni a `sold_out`.
- `invalid_response` no guarda el payload crudo en respuestas públicas.
- Un envelope nunca filtra API keys, headers de autorización, cookies, URLs firmadas ni secretos.

### 4.3. Warnings estructurados

```json
{
  "code": "provider_partial_results",
  "severity": "warning",
  "retryable": false,
  "scope": "operation",
  "message_key": "hotels.provider_partial_results",
  "provider_code": null
}
```

Códigos mínimos:

- `provider_partial_results`
- `provider_empty_result`
- `provider_timeout_partial`
- `provider_rate_limited`
- `provider_total_outage`
- `provider_unsupported_capability`
- `provider_invalid_item_discarded`
- `provider_conditions_incomplete`
- `provider_deeplink_unavailable`
- `provider_response_degraded`

El `message_key` es para i18n o copy de producto. El adapter no debe enviar mensajes externos sin sanitizar directamente a la UI.

### 4.4. Errores normalizados

```json
{
  "code": "rate_limited",
  "category": "transient",
  "retryable": true,
  "http_status": 429,
  "provider_code": "opaque-provider-code",
  "safe_message_key": "hotels.provider_rate_limited",
  "retry_after_seconds": 60
}
```

Categorías canónicas:

| Código | Categoría | Retry por defecto | Ejemplos |
|---|---|---:|---|
| `configuration_missing` | permanent/configuration | no | API key ausente, provider desactivado |
| `authentication_failed` | permanent/security | no automático | credencial inválida |
| `invalid_request` | permanent/client | no | fechas u ocupación no soportadas |
| `unsupported_capability` | permanent/capability | no | múltiples habitaciones no soportadas |
| `not_found` | permanent/domain | no | ID externo inexistente |
| `rate_limited` | transient/quota | sí, con límite | HTTP 429 o budget local |
| `timeout` | transient/network | sí, limitado | conexión o lectura excedida |
| `network_error` | transient/network | sí, limitado | DNS, conexión reset |
| `provider_5xx` | transient/provider | sí, limitado | error 5xx |
| `invalid_response` | permanent/contract | no inmediato | JSON inesperado, campo inválido |
| `provider_unavailable` | transient/provider | según circuit breaker | caída, bloqueo, captcha |
| `internal_mapping_error` | permanent/domain | no ciego | matching o normalización imposible |
| `unknown` | unknown | no ciego | error no clasificado |

Conservar `provider_code` y un diagnóstico interno sanitizado cuando exista, pero no usarlo como contrato de negocio. El error público debe ser estable aunque el provider cambie sus códigos.

---

## 5. Modelos normalizados de datos

### 5.1. Hotel provider-neutral

```text
provider_hotel_id       string opaco y no vacío
raw_name                string no vacío
raw_address             string nullable
city                    string
country_code            ISO-3166-1 alpha-2 cuando exista
latitude/longitude      opcionales y validados
stars                   opcional, rango válido
provider_metadata       interno, redacted y no público por defecto
```

El matching con `HotelProperty` pertenece al dominio/mapping service. Un `provider_hotel_id` no es automáticamente un `hotel_id` interno.

### 5.2. Rate provider-neutral

```text
provider_hotel_id       string
check_in/check_out      fechas canónicas
guests/rooms            ocupación efectiva
children_ages           nullable; no inventar edades
amount                  importe positivo o resultado sin precio explícito
currency                ISO-4217 válido
room_label              nullable
meal_plan               nullable
cancellation_policy     nullable
fees                    estructura nullable; distinguir included/unknown
availability_status     vocabulary H05
observed_at             timestamp del provider o captura claramente marcada
deep_link               objeto validado o null
conditions_completeness H05
provider_offer_id       opaco si existe
```

Si el provider solo devuelve una cifra sin saber si incluye impuestos, el rate puede persistirse como `partial`, pero no como “precio final”. Si no hay importe válido, no fabricar un `ProviderRateRecord` con cero.

### 5.3. Provider deeplink

```text
url                    URL absoluta validada
provider_id            origen lógico
partner_id             opcional y normalizado
label_key              copy i18n, no HTML arbitrario
expires_at              nullable si la URL expira
tracking_context_id     opaco, sin PII ni secretos
```

Un deeplink no confirma precio ni disponibilidad. H18/H19/H35 deben mostrar el disclosure correspondiente.

---

## 6. Retries, timeout, rate limits y circuit breaker

### 6.1. Timeout

Cada operación tiene timeout explícito, acotado y observable. Nunca depender del timeout infinito de la librería HTTP.

El timeout debe aparecer en métricas/logs como configuración, no como información sensible. El gateway debe evitar que el timeout de un provider consuma todo el presupuesto de la request de usuario.

### 6.2. Clasificación de retry

Por defecto:

- reintentar como máximo errores `timeout`, `network_error`, `provider_5xx` y `rate_limited` cuando exista `Retry-After` razonable;
- no reintentar a ciegas `authentication_failed`, `invalid_request`, `unsupported_capability`, `not_found` o `invalid_response`;
- aplicar exponential backoff con jitter y máximo global de intentos;
- no duplicar retries en adapter, gateway y worker sin un presupuesto compartido;
- una búsqueda de usuario puede tener menos retries que un sweep batch;
- un retry no debe cambiar silenciosamente fechas, ocupación, moneda o condiciones.

La política definitiva se calibra en H07/H09. H06 solo fija la clasificación y la obligación de presupuestar.

### 6.3. Rate limit

El envelope propaga, cuando el provider lo permite:

```text
remaining
limit
reset_at
retry_after_seconds
source: provider_header | provider_payload | local_budget | unknown
```

Si el provider no informa cuota, el sistema debe aplicar un límite local conservador. Un 429 debe producir métrica, warning y estado explícito. Nunca ocultarlo convirtiéndolo en `empty`.

### 6.4. Circuit breaker y fallback

El gateway puede abrir un circuito por provider/operación cuando los fallos superen un umbral documentado. Al abrirlo:

- no llamar innecesariamente al provider;
- devolver `unavailable` o `rate_limited` según causa;
- servir cache/histórico solo con H05 visible;
- permitir half-open/recovery controlado;
- no convertir datos viejos en “live”.

El fallback entre providers solo se activa si las capacidades permiten comparar la misma estancia. Un provider que no soporta niños, habitaciones o fees no es fallback equivalente para ese contexto.

---

## 7. Resultados parciales, vacíos y errores

### 7.1. Matriz de significado

| Situación | Resultado V2 | UI/servicio debe hacer |
|---|---|---|
| provider responde 200 y 0 hoteles para consulta válida | `empty` | sugerir ampliar zona/fechas; no mostrar error técnico |
| 2 de 3 páginas válidas | `partial` | mostrar 2 páginas y warning de cobertura |
| algunos rates tienen importe inválido | `partial` + `provider_invalid_item_discarded` | conservar válidos, contar descartados |
| provider responde 429 | `rate_limited` | reintentar según `Retry-After`; no “agotado” |
| provider timeout sin datos | `timeout` | cache elegible o reintento explícito |
| provider timeout después de datos válidos | `partial` + timeout warning | servir datos válidos con edad visible |
| credencial ausente | `unavailable`/`configuration_missing` | no reintentar en cada request; alerta operativa |
| JSON incompatible | `invalid_response` | no persistir rates; abrir incidente del adapter |
| provider no soporta operación | `unsupported` | usar fallback declarado o explicar limitación |

### 7.2. Regla de persistencia

Solo se persisten items que pasan validación canónica. Cada snapshot persistido debe conservar, directamente o mediante referencias futuras:

- provider y provider run;
- estancia/ocupación;
- timestamp de observación o fallback explícitamente documentado;
- estado de disponibilidad;
- condiciones conocidas/desconocidas;
- resultado parcial y warnings relevantes;
- fuente del deeplink si existe.

Un error de provider no debe crear un snapshot “sold out” ni una bajada artificial.

---

## 8. Deeplinks seguros

Los deeplinks son navegación externa, no redirecciones arbitrarias.

### Reglas obligatorias

1. Permitir únicamente `https` salvo excepción revisada explícitamente.
2. Validar hostname contra allowlist del provider/partner configurada en backend.
3. Rechazar `javascript:`, `data:`, `file:`, URLs relativas ambiguas y esquemas personalizados no aprobados.
4. No aceptar un hostname controlado por el usuario como destino de redirect.
5. No incluir API keys, cookies, access tokens, emails, IDs internos de usuario ni payloads completos de búsqueda.
6. Codificar parámetros y limitar longitud.
7. Firmar o generar el URL en backend cuando el partner lo requiera; no confiar en un `deep_link` arbitrario enviado desde el cliente.
8. Validar redirect otra vez justo antes de entregar/abrir si existe un endpoint de redirección.
9. Registrar dominio/partner y outcome, nunca query secrets o URL completa si contiene datos sensibles.
10. Mostrar al usuario que sale de Viru y que el precio puede cambiar.

Si no se puede validar un deeplink, el rate sigue pudiendo mostrarse como observación, pero `deep_link=null` y warning `provider_deeplink_unavailable`.

---

## 9. Orchestrator/gateway y responsabilidades

| Responsabilidad | Adapter | Gateway/orchestrator | Dominio/servicio | API/UI |
|---|---:|---:|---:|---:|
| traducir payload externo | sí | no | no | no |
| declarar capacidades | sí | consume | no redefine | presenta consecuencia |
| timeout HTTP | respeta | fija presupuesto | no | no |
| retries de red | puede exponer datos | decide política | no duplica | no |
| clasificar error | propone detalle | normaliza código | decide fallback | copy semántico |
| matching hotel ↔ entidad | no | no | sí | no |
| freshness/confidence H05 | aporta señales | propaga | calcula/aplica | presenta |
| persistir snapshots | no | devuelve resultado | sí | no |
| ownership de usuario | no | no | sí | no |
| deeplink allowlist | genera candidato | valida contrato | aplica seguridad de dominio | abre con disclosure |
| métrica/correlation ID | aporta provider request ID | conserva | enlaza con run | puede aportar client ID |

El adapter no debe decidir si una oferta dispara una alerta. El dominio tampoco debe volver a llamar a un endpoint externo para “comprobar” un campo que el adapter no declaró.

---

## 10. Compatibilidad y migración V1 → V2

### Paso 0 — Contrato y fixtures

- Añadir tipos V2 sin borrar `HotelProviderAdapter` V1.
- Crear payloads canónicos de éxito, vacío, partial, 429, timeout, invalid response y deeplink inválido.
- Definir un `LegacyAdapterBridge` o equivalente que traduzca listas V1 a envelopes V2 con limitaciones explícitas.
- El bridge V1 no puede distinguir por sí solo `empty` de `timeout`, `unavailable` o `rate_limited` cuando el adapter ya absorbió la excepción y devolvió `None`/`[]`; se necesita instrumentación/clasificación previa o un cambio mínimo del adapter. Esa limitación debe permanecer visible durante la transición.
- Todo resultado bridged desde V1 debe marcar las señales ausentes como `unknown`, no como `success` optimista.

### Paso 1 — Adapter mock

- Implementar V2 sobre el mock para validar la forma completa.
- Marcar siempre `provenance_kind=fixture_demo` según H05.
- Conservar tests V1 y añadir tests de equivalencia solo para campos compatibles.

### Paso 2 — Adapter Makcorps

- Mapear HTTP/timeout/429/invalid payload a error normalizado.
- No devolver `[]` para todos los fallos: distinguir `empty` de `unavailable`, `timeout` y `rate_limited`.
- Declarar capacidades realmente observadas; `supports_total_fees`, habitaciones, niños, cancelación y deeplink no se asumen.
- Preservar provider request ID si existe, sin guardar secretos.
- El modelo actual solo transporta `deep_link` como string nullable en `HotelRateSnapshot`; `ProviderRateRecord` no lo transporta y no existe allowlist/validación en la capa hotelera. Hasta H07/H35, cualquier deeplink debe considerarse no aprobado y puede quedar en `null`.
- H07 debe validar esta implementación con evidencia de cobertura y límites.

### Paso 3 — Ingestión y sweep

- H09/H10 adoptan `ProviderResult` y persisten status/warnings/run de forma compatible.
- `HotelProviderRun` evoluciona para admitir al menos `partial` y `skipped`, sin reinterpretar `completed` como “todos los items válidos”.
- El worker mantiene el comportamiento existente para providers V1 durante la transición.

### Paso 4 — Retirada de V1

Solo después de:

- todos los adapters activos pasan la matriz V2;
- ingestion, area search y revalidation consumen envelopes;
- tests de regresión y API pasan;
- H07 decide provider/coste/cobertura;
- no quedan callers de listas desnudas fuera del bridge;
- existe rollback o compatibilidad de despliegue.

---

## 11. Matriz mínima de contract tests

La matriz se ejecuta contra cada adapter con fixtures controlados. No reemplaza tests específicos del parser.

### 11.1. Identidad y capacidades

- `provider_id` estable, no vacío y sin secretos.
- `contract_version` conocido.
- `is_enabled()` no hace una llamada externa inesperada.
- capacidades devueltas son serializables y coherentes.
- una operación no soportada devuelve `unsupported` y warning canónico.
- `max_concurrency` y límites no son negativos ni ilimitados accidentalmente.

### 11.2. Datos válidos

- hotel con ID/nombre/ciudad válidos se normaliza sin perder identidad externa;
- rate con fecha válida, salida posterior, ocupación válida, importe positivo y moneda ISO pasa;
- condiciones presentes se conservan sin traducir valores desconocidos a defaults optimistas;
- timestamp, provider run/request ID y provenance se propagan;
- IDs externos permanecen opacos y no se confunden con IDs internos;
- raw payload interno no aparece en una respuesta pública por defecto.

### 11.3. Payloads inválidos y seguridad

- hotel sin ID se descarta con `provider_invalid_item_discarded`;
- importe `0`, negativo, NaN o currency inválida no se persiste;
- fechas invertidas no producen rate;
- payload top-level incorrecto produce `invalid_response` o `empty` según contrato, nunca éxito silencioso;
- campos excesivamente largos se recortan/rechazan según política sin romper el proceso;
- secrets, auth headers y raw tokens no aparecen en logs ni errores;
- texto externo no se convierte en HTML ejecutable.

### 11.4. Estados de provider

- respuesta válida vacía → `empty`;
- error 429 → `rate_limited`, `retryable=true`, `Retry-After` propagado si existe;
- timeout → `timeout`, no lista vacía disfrazada;
- error de red → `network_error`/`unavailable` según capa;
- HTTP 5xx → retry acotado y resultado normalizado;
- HTTP 4xx de request → `invalid_request`/`authentication_failed`, sin retry ciego;
- respuesta parcial → items válidos + `item_errors`/warnings;
- respuesta incompatible → `invalid_response` y ningún rate inválido persistido.

### 11.5. Idempotencia y observabilidad

- retries no duplican llamadas mutantes cuando la operación admite idempotency key;
- cada resultado conserva `request_id` y operación;
- `attempts` y `latency_ms` son coherentes;
- no se registran URL completa ni parámetros sensibles;
- métricas separan `empty`, `partial`, `timeout`, `rate_limited`, `invalid_response` y `failed`;
- circuit breaker evita llamadas cuando está abierto y permite recuperación controlada.

### 11.6. Deeplinks

- URL `https` de hostname permitido pasa;
- dominio no permitido, esquema peligroso, URL relativa u host controlado por usuario se rechazan;
- parámetros se codifican y no incluyen secretos/PII;
- ausencia de deeplink devuelve rate válido con warning, no error total;
- el redirect público vuelve a validar la allowlist;
- el copy de salida externa no promete precio final ni disponibilidad.

### 11.7. Compatibilidad V1

- el adapter V1 actual sigue pasando sus tests durante la transición;
- el bridge no convierte ausencia de timestamp en `fresh`;
- `[]` legacy se etiqueta según el contexto conocido y no se interpreta automáticamente como `empty` cuando proviene de una excepción;
- los payloads antiguos de API siguen serializando campos actuales;
- el cambio puede desplegarse y revertirse sin perder snapshots existentes.

---

## 12. Evidencia requerida para cerrar H06

La fase se cierra como contrato cuando existe:

1. una interfaz V2 documentada y provider-neutral;
2. capacidades declarativas con semántica conservadora;
3. envelope de éxito, vacío, partial, timeout, rate limit, unsupported e invalid response;
4. taxonomía de errores y política de retry/timeout/rate limit;
5. modelo de deeplink seguro y separado de disponibilidad/precio;
6. puente de compatibilidad V1 definido;
7. matriz de contract tests reutilizable;
8. handoff explícito a H07-H11 y H15/H35;
9. límites reales de Mock, Makcorps y `HotelProviderRun` documentados;
10. referencias documentales verificadas y sin afirmar que el código ya soporta V2.

### No se puede declarar con H06

- “Makcorps es suficiente”;
- “hay cobertura global”;
- “los precios son live”; 
- “todos los rates tienen fees o cancelación”; 
- “el worker ya reintenta de forma segura”; 
- “los deeplinks son confiables” sin pasar H35;
- “tracking real listo para lanzamiento”.

## 13. Handoff por fase

| Fase | Handoff de H06 |
|---|---|
| H07 | medir Makcorps con esta matriz, declarar capacidades y decidir continuidad |
| H08 | comparar candidatos con el mismo envelope y contract tests |
| H09 | aplicar retry/budget/locks al worker y ampliar estados de `HotelProviderRun` |
| H10 | conectar rate result con entidad canónica de estancia/oferta |
| H11 | migrar/persistir timestamps, warnings, provenance y dedupe sin perder históricos |
| H13-H15 | exponer estados de resultado sin hacer que frontend adivine por listas vacías |
| H16-H21 | mostrar partial, freshness y condiciones sin copy de disponibilidad falsa |
| H23-H28 | usar revalidación y snapshots elegibles para tracking/alertas |
| H35 | revisar allowlist, redirect, afiliación, privacidad y disclosure |
| H41 | medir cada outcome y provider sin PII/secrets |

**Resultado H06:** contrato aprobado. La implementación V2 queda pendiente de H07-H11 y no se debe presentar como capacidad ya disponible en producción.
