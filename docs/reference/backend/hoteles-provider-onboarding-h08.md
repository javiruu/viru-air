# H08 — Matriz de providers adicionales y política de onboarding

**Estado:** evaluación documental completa; candidatos registrados en configuración fail-closed, gate de onboarding de producción abierto
**Fecha:** 2026-08-04  
**Área:** backend / arquitectura / producto / proveedores / costes  
**Fuente de verdad:** sí para la comparación de candidatos y los requisitos de entrada de providers hoteleros adicionales.

**Depende de:** [H05 — freshness, procedencia y confidence](hoteles-freshness-provenance-confidence-h05.md), [H06 — contrato provider-neutral](hoteles-provider-neutral-contract-h06.md), [H07 — auditoría Makcorps](hoteles-makcorps-audit-h07.md)  
**Relacionado con:** H09 sweeps, H10 estancia/oferta, H11 migración de datos, H15 resultados, H19 fees, H35 seguridad/deeplinks, H37 coste/rendimiento, H41 observabilidad y H43 rollout.

---

## 1. Propósito y decisión de fase

H08 evalúa si conviene añadir providers hoteleros más allá de Mock y Makcorps, usando exactamente la frontera definida en H06. No integra credenciales, no activa llamadas externas y no convierte claims comerciales en capacidades de producto.

### Decisión H08

**Abrir onboarding condicionado; no aprobar todavía un provider comercial como principal de producción.**

La matriz deja dos candidatos con prioridad de investigación para una siguiente prueba controlada —no es una recomendación ni una aprobación—:

1. **Hotelbeds / HBX Group**, por la documentación visible de availability, rates, precios finales, políticas de cancelación y flujo de recheck.
2. **LiteAPI / Nuitee Connect**, por la disponibilidad de sandbox y el flujo explícito search → prebook → book.

Ambos quedan en estado `candidate_pending_canary`, no `approved`:

- faltan credenciales de evaluación gestionadas de forma segura;
- faltan pruebas reproducibles con las estancias y mercados de Viru;
- faltan coste, cuota, latencia, errores y política de salida medidos para el plan real;
- no se ha validado todavía la seguridad y legalidad de deeplinks, afiliación o booking;
- ningún candidato se puede presentar como fallback equivalente hasta comparar la misma ocupación, condiciones y semántica de precio.

**Makcorps** mantiene la decisión H07: adapter experimental y limitado, no provider principal. **Mock** y `local_scrape` cubren el modo gratuito/local: `local_scrape` parsea JSON-LD de una copia HTML guardada y nunca contacta URLs remotas. Ambos sirven para fixtures, captura local y QA; no deben describirse como cobertura live.

La configuración ejecutable reconoce `booking_demand` y `liteapi` como candidatos, con flags individuales, presupuesto diario `0` y secretos vacíos en `backend/.env.example`. El resolver bloquea ambos con `provider_credentials_missing` si falta cualquier secreto requerido y con `provider_adapter_unavailable` aunque las credenciales estén presentes: no existe todavía un adapter canary ni se realiza I/O externo.

`osm_overpass` está implementado únicamente para catálogo: requiere `staging_canary` o `prod_gradual`, `HOTEL_PROVIDER_OSM_OVERPASS_ENABLED=true`, un rectángulo de como máximo `0.1` grados por eje, ciudad, país y un `User-Agent` identificable. Consulta exclusivamente `https://overpass-api.de/api/interpreter`, no hereda proxies y limita la respuesta a 100 hoteles y 512 KiB. Su presupuesto diario queda en `0` por defecto y no puede usarse para buscar tarifas, revalidar una oferta ni alimentar tracking periódico.

El gate de producto “al menos un provider usable para el caso priorizado y un fallback honesto” queda **abierto** hasta que un candidato complete el canary y la revisión H35/H37/H41.

---

## 2. Regla de evidencia

Cada celda de la matriz usa una de estas etiquetas:

| Etiqueta | Significado | Uso permitido |
|---|---|---|
| `A — oficial visible` | hecho observado en documentación oficial accesible el 2026-08-04 | puede guiar el diseño del adapter, no garantiza producción |
| `B — contrato pendiente` | la capacidad parece parte del producto, pero requiere cuenta, contrato o documentación privada | no se declara capacidad V2 hasta probarla |
| `C — código local` | comportamiento ya presente en Viru | no demuestra que un provider externo responda así |
| `D — desconocido` | no se ha podido verificar sin credenciales, prueba o fuente suficiente | se trata como ausente/conservador |
| `E — propuesta` | criterio interno de onboarding o aceptación | no es resultado medido |

Reglas:

- Un número de propiedades, OTAs o idiomas no demuestra cobertura útil en una ciudad, fecha, ocupación o moneda concreta.
- Una página de marketing no demuestra SLA, cuota, latencia ni semántica de fees.
- Un endpoint documentado no demuestra que el plan de Viru tenga acceso a él.
- Un campo que aparece en un ejemplo no se declara soportado de forma estable hasta pasar fixtures y contract tests.
- `D` se traduce a `unknown`, nunca a `false` con una falsa certeza ni a `true` por inferencia.

---

## 3. Fuentes oficiales consultadas

Fecha de consulta de esta fase: **2026-08-04**. Algunas notas de investigación auxiliares pueden traer fechas de acceso distintas; esta tabla solo atribuye hechos a las URLs oficiales enlazadas y no usa esas fechas auxiliares como prueba de vigencia contractual.

| Candidato | Fuentes oficiales usadas | Evidencia visible | Límites de la evidencia |
|---|---|---|---|
| Hotelbeds / HBX Group | [Developer Portal](https://developer.hotelbeds.com/), [Booking API](https://developer.hotelbeds.com/documentation/hotels/booking-api/) | La documentación describe `/hotels` para availability, `/checkrates` para revalidar ofertas `recheck` y `/bookings` para confirmación, modificación y cancelación. También afirma que los precios de Booking API son finales e incluye suplementos/descuentos; puede devolver fees de cancelación en availability. | La página consultada no fija el plan comercial de Viru, cuota efectiva, SLA, cobertura por mercado, deeplink affiliate ni acceso de evaluación. |
| LiteAPI / Nuitee Connect | [API overview](https://docs.liteapi.travel/reference/overview) | La documentación visible describe disponibilidad y tarifas live, búsqueda → prebook → book, sandbox semejante a producción y contenido de millones de propiedades. | Coste real, cuotas de producción, condiciones de uso, cobertura por mercado, autenticación concreta, afiliación y deeplink requieren revisar cuenta y páginas específicas antes de aprobar. |
| Booking.com Demand API | [Demand API — Get started](https://developers.booking.com/demand/docs) | La documentación distingue `Content only`, `Search, look and redirect`, `Search, look and book`, post-booking y reporting; exige completar un access checklist. | No se asume acceso abierto, comisión, cuota, cobertura de Viru, términos de redirect ni disponibilidad de cada versión sin aprobación de partner. |
| Amadeus Self-Service Hotels | [Developers portal](https://developers.amadeus.com/) | El portal oficial existe como punto de entrada para APIs Self-Service. La referencia concreta de hoteles no fue legible en esta consulta automatizada. | Endpoint, ocupación, fees, límites, sandbox y deeplink quedan `D` hasta verificar la referencia y una cuenta de prueba. No se copian cifras de terceros. |
| Expedia Rapid | [Rapid Developer Hub](https://developers.expediagroup.com/rapid/home) | El sitio oficial del hub fue accesible como portal de Rapid. La página de entrada no expuso en esta consulta los detalles contractuales de hotel search. | Parámetros, acceso, coste, límites, sandbox, booking y deeplinks quedan `D/B` hasta revisión de partner y documentación específica. |
| Makcorps | [Documentation](https://www.makcorps.com/documentation/), auditoría H07 | Ya existe adapter, pero H07 registró 429 real en `/mapping`, mismatch de IDs, errores absorbidos, ausencia de deeplink aprobado y desconocimiento de coste/cuota. | No se reabre ni se eleva de categoría por aparecer en esta matriz. |

El catálogo `gravity_index` se consultó como comprobación de servicios. No produjo una recomendación hotelera específica ni una integración utilizable; devolvió servicios de búsqueda general, que no cumplen por sí solos el contrato de precios y disponibilidad hotelera. Por tanto, la selección se basa en documentación oficial de cada candidato y no en una recomendación automática del catálogo.

---

## 4. Requisitos provider-neutral derivados de H06/H07

Un candidato solo puede entrar en onboarding si puede mapear, con evidencia, estas operaciones:

| Operación H06 | Requisito mínimo para el candidato |
|---|---|
| `list_catalog` | catálogo o IDs externos reproducibles, identidad estable y política de sincronización |
| `search_area` | ciudad, coordenadas, radio o destino equivalente; límites y paginación conocidos |
| `get_rates` | fechas exactas, ocupación completa soportada o exclusión explícita, moneda y condiciones |
| `revalidate_offer` | recheck/prebook o mecanismo equivalente con estado y precio actuales |
| `build_deeplink` | URL generada/recibida con hostname permitido, disclosure y sin secretos; puede ser `unsupported` |

Debe devolver `ProviderResult[T]` y distinguir al menos `success`, `empty`, `partial`, `unsupported`, `rate_limited`, `timeout`, `unavailable`, `invalid_response` y `failed`.

### Capacidades que no se pueden omitir en la comparación

- habitaciones múltiples;
- adultos, niños y edades cuando el producto los permita;
- moneda solicitada y moneda efectivamente devuelta;
- precio base, impuestos, fees incluidos/desconocidos y total;
- tipo de habitación, régimen y condiciones;
- cancelación con fechas y penalizaciones;
- disponibilidad separada de error del provider;
- paginación y límites de resultados;
- identidad `provider_hotel_id` separada de `HotelProperty.id`;
- request ID, latency, attempts y rate-limit metadata;
- privacidad, retención y redacción de credenciales;
- deeplink/affiliate como capacidad independiente del precio.

Si un candidato no soporta una dimensión, puede ser útil para un caso acotado, pero no es fallback equivalente para cualquier estancia.

---

## 5. Matriz comparativa de candidatos

| Dimensión | Hotelbeds | LiteAPI | Booking Demand | Amadeus Self-Service | Expedia Rapid | Makcorps H07 | Mock local |
|---|---|---|---|---|---|---|---|
| Estado H08 | `candidate_pending_canary` | `candidate_pending_canary` | `access_gated` | `research_pending` | `commercial_pending` | `limited_experimental` | `fixture_only` |
| Search/availability | `A`: `/hotels` documentado | `A`: search de hoteles documentado | `A`: search/look/redirect documentado | `D` en esta auditoría | `D` en esta auditoría | `B/C`: `/city`, `/hotel` en adapter | `C`: fixture |
| Fechas exactas | `A`: availability recibe estancia | `A`: live rates para fechas pasadas | `B`: requiere probar request schema | `D` | `D` | `C`: envía check-in/out | fixture configurable |
| Ocupación completa | `A/B`: la documentación de portal debe probar rooms/pax/ages en canary | `A/B`: occupancy se pasa al search; schema exacto pendiente | `B`: previsto por tipo de integración, pendiente de cuenta | `D` | `D` | `C`: adultos; rooms fija a 1 y sin niños | fixture configurable |
| Precio total/fees | `A`: afirma precios finales e incluye suplementos/descuentos | `A/B`: promete live pricing; breakdown exacto pendiente | `B` | `D` | `D` | bloqueado por H07-05 | solo fixture, no live |
| Cancelación | `A/B`: cancellation fees pueden aparecer en availability | `B`: probar política por rate | `B` | `D` | `D` | parcial/no garantizada | fixture |
| Revalidación | `A`: `/checkrates` para `recheck` | `A`: prebook antes de book | `B`: look/book o redirect según acceso | `D` | `D` | no aprobada por H07 | no aplicable |
| Paginación/límites | `B`: medir límites del plan | `B`: medir límites de sandbox/producción | `B` | `D` | `D` | incompleta H07-04 | no aplica |
| Deeplink | `D`: API booking, no asumir deeplink | `D`: booking API, no asumir affiliate | `A/B`: redirect es una integración documentada, allowlist y términos pendientes | `D` | `D` | no aprobado H07-06 | no |
| Acceso | evaluación/partner por confirmar | sandbox visible; producción por confirmar | access checklist y partner approval | cuenta Self-Service por confirmar | partner onboarding | key existente pero 429 histórico | sin credencial |
| Coste/cuota | `D/B`: obtener plan real | `D/B`: obtener plan real | `D/B`: contrato/affiliate | `D` | `D/B` | desconocido, cero automático | cero externo |
| Latencia/SLA | `D` | `D` | `D` | `D` | `D` | timeout local 10 s, sin SLA | local |
| Riesgo de integración | medio: contrato rico, onboarding formal | medio: onboarding rápido, coste/semántica por probar | alto: acceso y términos | medio/alto: evidencia incompleta | alto: comercial | alto: bloqueos H07 | bajo para QA |
| Caso apto hoy | ninguno en producción | ninguno en producción | no sin partner | ninguno | ninguno | discovery manual limitado | desarrollo y QA |

### Lectura de la matriz

- Hotelbeds es el candidato técnico más prometedor para comparar rates y condiciones, pero no se aprueba sin canary y cuenta de evaluación.
- LiteAPI es el candidato con menor fricción inicial para un sandbox, pero “sandbox disponible” no equivale a coste sostenible ni cobertura comparable.
- Booking.com Demand API es especialmente relevante si el producto decide priorizar `search/look/redirect`; su acceso y términos de partner son un gate, no un detalle de implementación.
- Amadeus y Expedia se mantienen como líneas de investigación, no como capacidades disponibles.
- Makcorps no se usa para rellenar las celdas desconocidas de otros providers.

---

## 6. Decisión por caso de uso

| Caso de uso | Provider permitido ahora | Decisión |
|---|---|---|
| fixtures, desarrollo y QA | Mock | aprobado; siempre `fixture_demo` |
| captura HTML local | `local_scrape` | aprobado; sin credenciales ni requests remotos; solo acepta precio total si el marcado lo declara explícitamente |
| pruebas de parser V2 | Mock + fixtures versionados de candidatos | aprobado sin requests externos |
| discovery público de catálogo | `osm_overpass` en canary explícito | permitido solo para un área pequeña y presupuesto positivo; no equivale a cobertura de precios |
| rates de una estancia exacta | ninguno comercial | bloqueado hasta probar fees/ocupación/condiciones |
| revalidación de una oferta | ninguno | bloqueado hasta checkrate/prebook y resultado V2 |
| tracking periódico | ninguno | bloqueado; H09 necesita budget, locks y health |
| fallback por timeout/429 | Mock/cache/histórico H05 con disclosure | permitido solo como degradación honesta, nunca “live” |
| deeplink externo | ninguno hotelero | bloqueado hasta H35; Booking redirect es candidato, no aprobación |
| Makcorps manual | solo canary autorizado | limitado por H07, sin worker automático |

No se puede usar un candidato con solo catálogo o precios sin condiciones como fallback de un provider que sí soporte ocupación y cancelación. El fallback debe comparar el mismo `StayQuery`; si no, el resultado se etiqueta como cobertura distinta, no como alternativa equivalente.

---

## 7. Política de onboarding en seis gates

Cada provider nuevo debe pasar todos los gates o quedar limitado a fixtures/manual.

### Gate 1 — Acceso y términos

- owner técnico y owner de producto identificados;
- cuenta de evaluación separada de producción;
- términos, privacidad, uso de datos y afiliación revisados;
- credenciales fuera del repositorio, logs y URLs;
- coste por operación y cuota escritos con fuente y fecha;
- kill switch y contacto de soporte definidos.

**Salida:** `access_pending`, `rejected` o `ready_for_contract`.

### Gate 2 — Capability evidence

Para cada capability H06 registrar:

```text
source_url
source_accessed_at
plan_or_account_scope
observed_or_documented
fixture_or_request_id_redacted
confidence: A/B/C/D
known_exclusions
```

No se marca `true` una capability por marketing ni por un único payload aislado.

### Gate 3 — Adapter y contrato

- adapter aislado, sin imports desde dominio a provider concreto;
- `ProviderResult` V2 y errores normalizados;
- identity mapping con `provider_hotel_id` opaco;
- timeout, retry y circuit breaker presupuestados fuera del parser;
- redaction de URLs, headers, tokens y payloads;
- deeplink `unsupported` hasta pasar allowlist H35;
- no se guarda un rate inválido o un error como `empty`/`sold_out`.

### Gate 4 — Fixtures y contract tests

Mínimo por candidato:

- éxito con una estancia de 1 habitación/2 adultos;
- vacío válido;
- múltiples habitaciones o exclusión explícita;
- niños/edades o exclusión explícita;
- taxes/fees incluidos, excluidos y desconocidos;
- cancelación flexible y no reembolsable;
- recheck/prebook si aplica;
- paginación y límite;
- 401/403, 429 con `Retry-After`, 5xx, timeout y JSON inválido;
- resultado parcial;
- deeplink válido, no permitido y ausente;
- garantía de que no aparece secreto en logs.

### Gate 5 — Canary y presupuesto

- activar solo en entorno controlado;
- máximo de requests, concurrencia y retries previamente escritos;
- canary de 3–5 mercados prioritarios y estancias representativas;
- registrar p50/p95/p99, error rate, 429, timeout, coste, rates válidos y completitud;
- detener ante coste no observable, 429 repetido, schema incompatible, secretos expuestos o degradación no clasificable;
- comparar resultados con invariantes de H05, no solo con cantidad de hoteles.

### Gate 6 — Rollout y salida

- flag por provider y operación;
- `dry_run`/manual antes de worker periódico;
- rollout gradual y porcentaje de tráfico explícito;
- fallback a Mock/cache/histórico sin migración irreversible;
- dashboard y alertas H41;
- runbook de revocación de credenciales y desactivación;
- revisión a 7 y 30 días antes de ampliar el caso de uso.

**Salida final:** `approved_limited`, `approved_production`, `paused` o `rejected`.

---

## 8. Flags, presupuesto y kill switches

H08 no crea una plataforma central nueva de flags. Sigue la convención viva de variables de entorno descrita en `docs/reference/feature-flags.md`.

Cuando se implemente un candidato, la forma mínima debe ser equivalente a:

```text
HOTEL_FEATURE_ENABLED=false
HOTEL_SWEEP_ENABLED=false
HOTEL_PROVIDER=mock
HOTEL_PROVIDER_ORDER=mock
HOTEL_PROVIDER_<ID>_ENABLED=false
HOTEL_PROVIDER_<ID>_SEARCH_ENABLED=false
HOTEL_PROVIDER_<ID>_REVALIDATION_ENABLED=false
HOTEL_PROVIDER_<ID>_DEEPLINK_ENABLED=false
HOTEL_PROVIDER_<ID>_DAILY_REQUEST_BUDGET=0
HOTEL_PROVIDER_<ID>_MAX_CONCURRENCY=1
HOTEL_PROVIDER_<ID>_MAX_RETRIES=0
```

Los nombres concretos se fijarán en H09/H43 tras revisar la configuración existente; este bloque es política de activación, no un cambio ya implementado.

### Presupuesto mínimo antes de cualquier request automático

```text
provider_id
plan_scope
window: day/month
hard_request_limit
estimated_units_per_request
max_search_requests
max_revalidation_requests
max_concurrency
max_retry_attempts
429_cooldown
cost_alert_threshold
owner
kill_switch
```

Si el provider no expone coste o cuota, el límite automático es **cero**. Las pruebas manuales deben tener un número de requests autorizado y un owner.

---

## 9. Deduplicación, precedencia y comparabilidad

Añadir providers no significa sumar listas sin control.

### Identidad

1. conservar `provider_id + provider_hotel_id` como identidad de origen;
2. resolver a `HotelProperty` mediante `HotelProviderAlias`;
3. nunca pasar `HotelProperty.id` a un adapter que espera ID externo;
4. si el matching es ambiguo, mantener `is_ambiguous` y no mezclar rates automáticamente.

### Dedupe de rates

Una oferta solo puede compararse si coincide en:

```text
canonical_hotel_id
check_in/check_out
rooms + guests + children_ages
currency
room_label o room_id cuando exista
meal_plan
cancellation_policy
fee_completeness
observed_at/freshness
```

Si falta una dimensión, se agrupa como oferta relacionada pero no se declara “la misma tarifa”.

### Orden

El ranking futuro debe priorizar, en este orden:

1. estancia/ocupación coincidente;
2. freshness y procedencia H05;
3. completitud de condiciones;
4. precio comparable;
5. confianza de matching;
6. calidad de deeplink/acción, si está aprobada;
7. provider como último desempate, nunca como favoritismo oculto.

Un provider no puede ganar por devolver más items si sus fees o condiciones son desconocidos.

---

## 10. Plan de canary para Hotelbeds y LiteAPI

El canary se ejecutará solo después de aprobar Gates 1–4 y obtener credenciales de prueba. No se deben inventar llamadas ni activar el worker para producir esta evidencia.

### Muestra

- 3–5 ciudades europeas prioritarias;
- una estancia corta, una media y una fecha futura;
- 1 habitación/2 adultos como baseline;
- una consulta con 2 habitaciones si la capacidad está documentada;
- niños solo si el contrato permite edades;
- EUR y una moneda secundaria si está permitido;
- un hotel conocido y una zona con varios resultados;
- casos de vacío, timeout simulado y respuesta inválida mediante fixtures.

### Métricas

```text
search_success_rate
empty_rate
partial_rate
rate_limited_rate
timeout_rate
invalid_response_rate
mapping_success_rate
p50/p95/p99_latency
hotels_received
rates_received
rates_valid
rates_with_currency
rates_with_fee_semantics
rates_with_cancellation
rates_with_room_and_meal
revalidation_success_rate
cost_per_search
cost_per_revalidation
freshness_integrity
```

### Criterios de aceptación propuestos

Son gates internos a aprobar, no resultados actuales:

- cero API keys, tokens o URLs sensibles en logs/traces;
- cero uso de IDs internos donde se exige ID externo;
- `429`, timeout y unavailable siempre distinguibles de `empty`;
- cada rate rankeado conserva semántica de fees y cancelación suficiente;
- el presupuesto no se supera en una búsqueda ni durante el canary;
- la latencia p95 se mantiene dentro del presupuesto de UX aprobado;
- el fallback no afirma disponibilidad live cuando sirve cache o fixture;
- rollback funciona con flags sin borrar snapshots;
- deeplinks solo aparecen tras H35.

Los umbrales numéricos de cobertura, latencia y coste los fijará producto con los datos del mercado inicial; no se copian porcentajes universales.

---

## 11. Plan de salida y reversibilidad

Un provider se pausa inmediatamente si ocurre cualquiera de estos eventos:

- credencial expuesta o URL con secreto observada;
- coste o cuota no observable;
- 429 repetido sin `Retry-After` manejable;
- schema incompatible o rates inválidos persistidos;
- errores externos convertidos en vacío/sold out;
- caída de la calidad H05 por datos sin freshness/provenance;
- discrepancia material de precio/fees/cancelación;
- incumplimiento de términos o instrucción del partner;
- latencia que bloquea la experiencia y no tiene degradación segura.

La salida debe:

1. desactivar la flag del provider;
2. bloquear jobs nuevos y esperar/terminar los existentes con timeout;
3. conservar snapshots históricos con su provider y timestamp;
4. servir cache/histórico elegible con disclosure;
5. ocultar deeplinks del provider pausado;
6. revocar/rotar credenciales si aplica;
7. registrar causa, ventana, requests/coste y owner;
8. permitir reactivación solo tras repetir Gates 2, 4 y 5.

No eliminar automáticamente aliases ni históricos al pausar un provider.

---

## 12. Handoff a fases siguientes

| Fase | Trabajo recibido de H08 |
|---|---|
| H09 | construir gateway/sweep con budget, locks, clasificación de errores y canary; no activar producción por defecto |
| H10 | modelar `StayQuery`, `ProviderResult`, rate comparable e identidad externa/interna |
| H11 | migrar timestamps, warnings, conditions y provenance sin perder históricos |
| H15 | exponer `partial`, `rate_limited`, `timeout` y `unsupported` sin listas ambiguas |
| H19 | modelar fees/impuestos y evitar doble suma o claims de total |
| H35 | revisar API keys en URLs, allowlist, redirects, partner terms y disclosure |
| H37 | medir coste, latencia, concurrencia y rendimiento por provider |
| H41 | instrumentar outcomes, budget, request ID sanitizado y provider health |
| H43 | implementar flags, canary, rollout gradual y kill switches |

### Gate pendiente de H08

H08 podrá considerarse “onboarding aprobado” solo cuando uno de Hotelbeds o LiteAPI, o un candidato posterior, aporte:

- cuenta/plan y permisos verificables;
- matriz de capacidades con evidencia A/B/C;
- adapter V2 y contract tests;
- fixtures de éxito, vacío, partial, 429, timeout e invalid response;
- canary dentro de presupuesto;
- coste, cuota y latencia observados;
- comparación H05 aceptable para el caso prioritario;
- revisión H35/H37/H41 aprobada;
- rollback probado.

**Resultado H08:** existe una matriz comparable y una política de entrada/salida reutilizable. No existe todavía aprobación de provider comercial ni integración de producción. Esa ausencia es intencional y mantiene el riesgo bajo para H09–H11.
