# Roadmap de viaje para Codex v2 - Viru Fare Memory y mejora integral post-Fase 20

**Estado:** vivo  
**Ultima revision:** 2026-06-14  
**Fuente de verdad:** no; plan operativo para agentes  
**Area:** contexto IA / planificacion / backend / quick-search / pricing intelligence  
**Reemplaza:** fases 21-50 del roadmap anterior `codex-travel-roadmap-50-fases.md`  
**Mantiene:** fases 1-20 como trabajo ya completado y no repetible salvo auditoria puntual

## 0. Lectura obligatoria antes de tocar codigo

Este documento no sustituye a la documentacion viva del repo. Codex debe leer primero, de forma selectiva y con foco en la fase activa:

- `AGENTS.md`
- `backend/AGENTS.md`
- `frontend/AGENTS.md`
- `DESIGN.md`
- `README.md`
- `docs/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`
- `docs/overview/project-overview.md`
- `docs/overview/current-state.md`
- `docs/reference/backend/quick-search-contract.md`
- `docs/plans/2026-06-10-quick-search-shared-cache-review-plan.md`
- `docs/product/quick-search.md`
- `docs/product/watchlist.md`
- `docs/product/door-to-door.md`
- `DESIGN.md`

Si un documento vivo contradice este roadmap, gana el documento vivo. Si el codigo contradice ambos, Codex debe reportarlo como drift y no inventar una sintesis optimista.

## 1. Cambio de direccion respecto al roadmap anterior

Las fases 1-20 ya estan completadas. El roadmap anterior recomendaba seguir por puerta a puerta, pero la nueva conversacion introduce una pieza de arquitectura que afecta a casi todo Viru Air:

**Viru Fare Memory:** un sistema de memoria, cache, snapshots, frescura, revalidacion y aprendizaje de volatilidad para precios de vuelos.

Por eso, este v2 hace tres cosas:

1. Congela las fases 1-20 como historia cerrada.
2. Sustituye las fases 21-50 antiguas por una ruta nueva empezando en Fase 21.
3. Mantiene puerta a puerta, hoteles, watchlist y UI, pero los recoloca despues de construir una base sana de precios, cache y confianza.

La razon es simple: si Viru aprende a recordar precios sin mentir, todo mejora. Quick Search gasta menos, Watchlist compara mejor, Alertas disparan con mas criterio, Historico tiene mas valor y Recomendaciones dejan de ser humo con purpurina.

## 2. Principios de producto para Viru Fare Memory

Viru Air no debe comportarse como un scraper ansioso. Debe comportarse como una cabina de decision con memoria:

- recordar busquedas sin convertir memoria en verdad absoluta;
- ahorrar llamadas a proveedores sin esconder incertidumbre;
- distinguir precio verificado, precio visto recientemente, precio caducado y precio historico;
- guardar resultados validos e invalidos;
- aprender patrones de volatilidad por ruta, carrier, fecha y anticipacion;
- no mostrar precios como actuales si no han sido revalidados;
- no activar APIs de pago, scraping activo ni automatismos agresivos sin permiso explicito del usuario;
- mantener microcopy calido y honesto, por ejemplo: `Visto hace 18 min`, `Pendiente de revalidar`, `Precio historico`, `Sin cobertura real del proveedor`.

## 3. Investigacion externa resumida para la arquitectura

Esta seccion es contexto, no contrato legal.

### 3.1 Ryanair y precios dinamicos

Ryanair y otras aerolineas usan precios dinamicos. En la practica, un precio puede cambiar por disponibilidad, demanda, antelacion, temporada, ruta, competencia, ocupacion y decisiones comerciales. Un precio visto por Viru no debe considerarse estable salvo revalidacion reciente.

Hallazgos utiles:

- Estudios academicos y economicos sobre Ryanair han encontrado relacion entre ocupacion/venta de asientos y subida de tarifas. Un resultado citado en divulgacion economica indica que la venta de un asiento adicional se asocia con subida media de tarifa cercana al 3,1%.
- IATA describe la evolucion hacia ofertas dinamicas generadas segun contexto de compra y requisitos del usuario.
- Analisis sectoriales describen que muchas aerolineas ajustan precios por disponibilidad de asientos y calendario de compra.
- Ryanair limita el uso de datos de su web, incluidos horarios y precios, a usos personales/no comerciales salvo consentimiento escrito. Esto obliga a evitar una estrategia basada en scraping directo no aprobado.

Decision tecnica derivada:

> Viru no debe diseñar `precio cacheado = precio actual`. Debe diseñar `precio observado + frescura + confianza + revalidacion`.

### 3.2 Implicacion para la cache

Una cache normal sirve para datos estables. Los precios de vuelo son datos vivos. Por tanto, Viru necesita una cache temporal con semaforo de confianza:

- `fresh`: verificado hace poco y mostrable como actual con cautela.
- `warm`: util para ordenar y orientar, pero necesita revalidacion antes de alertar fuerte.
- `stale`: historico cercano, no actual.
- `expired`: no usar como resultado actual.
- `negative_fresh`: ausencia de resultado vista hace poco.
- `provider_error_fresh`: fallo reciente del proveedor, no repetir llamada en bucle.

## 4. Compatibilidad con el estado actual

El documento anterior ya detecto que Quick Search tiene cache compartida persistente documentada como V2.1. Por eso este roadmap no pide construir otra cache paralela desde cero.

Regla critica:

> Antes de crear tablas o servicios nuevos, Codex debe auditar la cache existente y decidir si extenderla, normalizarla o migrarla. Prohibido duplicar una segunda cache con otro nombre solo porque sea mas comodo.

Areas que deben considerarse ya existentes:

- Quick Search con request estructurada.
- Cache compartida persistente V2.1.
- Historico de precios y watchlist.
- Alertas.
- Providers de vuelo y degradacion.
- UI dual dark/light con identidad calida.
- Door-to-door con providers reales/parciales/stubs ya auditados en Fase 20.

## 5. Modelo mental nuevo

Viru debe separar cuatro conceptos que ahora suelen mezclarse:

1. **Busqueda:** lo que pide el usuario.
2. **Resultado de busqueda:** el payload devuelto para esa busqueda en un momento concreto.
3. **Oferta:** un vuelo o itinerario individual normalizado que puede aparecer en varias busquedas.
4. **Observacion de precio:** el precio visto para una oferta en un momento concreto.

Ejemplo:

- Usuario A busca `LEI -> FCO`, con destinos cercanos, el 2026-07-20.
- Viru encuentra `LEI -> BGY`, `AGP -> CIA`, `ALC -> FCO`, algunos validos y otros sin resultado.
- Usuario B busca algo parecido.
- Viru puede reutilizar ofertas y negativas, pero solo si comunica frescura y revalida cuando toque.

## 6. Estados canonicos de frescura

Codex debe proponer o implementar estos estados en backend antes de exponerlos en UI:

| Estado | Significado | Uso UI/API |
|---|---|---|
| `fresh` | Precio revalidado dentro del TTL activo | Puede mostrarse como precio actual observado |
| `warm` | Precio probablemente util, pero no garantizado | Mostrar con copy `visto hace X` y boton/revalidacion |
| `stale` | Precio viejo o fuera de TTL | Solo historico o pista, no decision fuerte |
| `expired` | Precio no reutilizable | No usar en resultados actuales |
| `negative_fresh` | Sin resultados confirmado hace poco | Evita repetir llamadas inutiles |
| `negative_stale` | Ausencia de resultados vieja | Puede disparar nueva busqueda |
| `provider_error_fresh` | Fallo reciente de proveedor | Backoff, no bombardear proveedor |
| `provider_error_stale` | Fallo viejo | Puede reintentarse |

## 7. TTL inicial recomendado

Los TTL deben empezar conservadores y ser ajustables por configuracion.

| Antelacion salida | TTL precio valido | Motivo |
|---|---:|---|
| Mas de 90 dias | 12 h | Menos urgencia, cambios menos criticos para decision inmediata |
| 60-90 dias | 8 h | Buen equilibrio entre ahorro y utilidad |
| 30-60 dias | 4 h | Empieza zona util para compra |
| 14-30 dias | 2 h | Mayor volatilidad esperable |
| 3-14 dias | 45 min | Precio sensible y decision cercana |
| 24-72 h | 15 min | Riesgo alto de cambio |
| Menos de 24 h | 5 min | Cache casi solo anti-spam |
| Resultado negativo | 15-60 min | No repetir combinaciones inutiles |
| Error provider | 5-15 min + backoff | Evitar bucles de fallo |

Regla de oro:

> Un TTL largo no significa verdad larga. Significa que Viru acepta reutilizar memoria para orientar, pero debe etiquetar frescura.

## 8. Campos minimos recomendados

### 8.1 Search Cache

Campos orientativos:

- `id`
- `search_fingerprint`
- `canonical_request_json`
- `request_hash_version`
- `provider_set`
- `user_scope`: `global`, `user`, `anonymous_session` si aplica
- `result_payload_json`
- `result_count`
- `valid_result_count`
- `invalid_result_count`
- `negative_result_count`
- `observed_at`
- `expires_at`
- `freshness_status`
- `confidence_score`
- `created_at`
- `updated_at`

### 8.2 Offer Cache

Campos orientativos:

- `id`
- `offer_fingerprint`
- `provider`
- `carrier`
- `flight_number`
- `origin_airport`
- `destination_airport`
- `departure_at`
- `arrival_at`
- `duration_minutes`
- `stops_count`
- `booking_url_hash` o `deeplink_signature` si procede
- `source_kind`: `provider`, `deeplink`, `mock`, `manual`, `derived`
- `created_at`
- `updated_at`

### 8.3 Price Observation

Campos orientativos:

- `id`
- `offer_id`
- `search_cache_id` nullable
- `provider`
- `price_amount`
- `currency`
- `fare_family` nullable
- `baggage_included` nullable
- `seats_left` nullable si el provider lo da legalmente
- `observed_at`
- `expires_at`
- `freshness_status`
- `confidence_score`
- `validation_status`: `observed`, `revalidated`, `provider_partial`, `estimated`, `historical_only`
- `price_changed_since_last_seen`
- `delta_abs`
- `delta_pct`

### 8.4 Negative Cache

Campos orientativos:

- `id`
- `negative_fingerprint`
- `scope`: `route`, `date`, `provider`, `airport_pair`, `search_request`
- `reason`: `no_route`, `no_availability`, `invalid_airport_pair`, `provider_unsupported`, `provider_timeout`, `rate_limited`, `bad_request`, `country_only_no_match`
- `provider`
- `canonical_request_json`
- `observed_at`
- `expires_at`
- `freshness_status`
- `retry_after_at`
- `hit_count`

## 9. Reglas de seguridad, legalidad y coste

Codex no debe:

- activar scraping directo de Ryanair;
- usar servicios externos de scraping de pago;
- simular compra o reserva;
- saltarse terminos de uso;
- guardar datos personales innecesarios;
- mezclar cache global con datos de usuario privados;
- esconder errores de proveedor como `sin resultados`;
- mostrar precios caducados como confirmados;
- generar llamadas masivas al arrancar.

Codex si puede:

- construir infraestructura de cache y frescura;
- añadir flags apagados por defecto;
- usar mocks y fixtures;
- registrar observaciones de precios ya obtenidas por providers existentes;
- proponer proveedores oficiales o compatibles;
- documentar limitaciones y decision points.

## 10. Boot y warmup: regla anti-estampida

Al arrancar el proyecto, Viru no debe refrescar todo. Debe ejecutar un plan de warmup con prioridades:

1. Watchlists activas con alertas habilitadas.
2. Rutas con precio cerca del umbral de alerta.
3. Busquedas populares recientes.
4. Ofertas `warm` cerca de pasar a `stale`.
5. Rutas con alta volatilidad historica.
6. Rutas de salida cercana.
7. Resultados negativos muy consultados y ya caducados.

Debe incluir:

- limite maximo de jobs por arranque;
- jitter aleatorio;
- rate limit por provider;
- backoff por error;
- lock para evitar dos workers refrescando lo mismo;
- modo dry-run;
- metricas de hits, misses y llamadas evitadas.

## 11. Plan v2 por fases

Las fases 1-20 quedan cerradas. Las fases siguientes son la nueva ruta operativa.

### Bloque I - Viru Fare Memory: investigacion y contrato

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 21 | Auditar la cache existente de Quick Search V2.1 y el historico de precios. | Mapa de modelos, servicios, endpoints, tests y gaps. Sin codigo nuevo salvo docs. |
| 22 | Crear spec `Viru Fare Memory`. | Documento en `docs/specs` o `docs/engineering`, con estados de frescura y riesgos. |
| 23 | Definir contrato API de frescura para resultados de vuelo. | Contract doc y tests de serializacion si ya hay schemas. |
| 24 | Definir normalizacion de fingerprints de busqueda. | Tests unitarios de igualdad/diferencia entre requests. |
| 25 | Definir normalizacion de fingerprints de oferta. | Tests con vuelos iguales en busquedas distintas. |

### Fase 21 - Auditoria de cache existente

**Objetivo real**

Antes de construir nada, localizar exactamente que existe ya en cache compartida, historico de precios y watchlist.

**Preguntas que debe responder Codex**

- Que tablas/modelos existen ya para cache de quick-search?
- Que se guarda: payload completo, resultados normalizados, solo hash, metadata?
- Existe TTL real o solo persistencia?
- Se guarda precio por oferta o solo por respuesta?
- Hay cache negativa?
- Hay diferencia entre fallo provider, cero resultados y ruta invalida?
- Que tests ya cubren cache?
- Que partes de `docs/plans/2026-06-10-quick-search-shared-cache-review-plan.md` estan hechas?

**Entregable**

Un informe corto dentro del documento de fase o en `docs/plans/` con tabla:

| Pieza | Existe | Archivo | Riesgo | Decision |
|---|---|---|---|---|

**No hacer**

- No crear migraciones todavia.
- No renombrar tablas.
- No tocar providers.
- No cambiar payload visible.

**Verificacion**

- `python -m pytest backend/tests/unit/test_quick_search_cache_models.py -q` si existe.
- Tests cercanos encontrados por busqueda.
- `git diff` solo docs si la fase es puramente auditoria.

### Fase 22 - Spec `Viru Fare Memory`

**Objetivo real**

Convertir la idea de memoria de tarifas en contrato tecnico y producto.

**Debe incluir**

- problema;
- alcance;
- no objetivos;
- riesgos legales/coste;
- estados `fresh`, `warm`, `stale`, `expired`;
- cache exacta, offer cache y negative cache;
- TTL inicial;
- reglas de revalidacion;
- boot warmup;
- metricas;
- impacto en Quick Search, Watchlist, Alertas e Historico;
- copy UI recomendado;
- decision de no scraping activo.

**Verificacion**

- Link desde `docs/INDICE_UNICO.md` y `docs/DOCS_INVENTORY.md` si el repo lo exige para docs nuevas.
- No contradice `quick-search-contract.md`.
- Revisa terminos: precio cacheado nunca se llama precio confirmado si no esta revalidado.

### Fase 23 - Contrato API de frescura

**Objetivo real**

Definir como backend comunica frescura sin obligar a la UI a adivinar.

**Campos propuestos en cada resultado o metadata**

```json
{
  "freshness": {
    "status": "fresh",
    "observed_at": "2026-06-14T10:15:00Z",
    "expires_at": "2026-06-14T12:15:00Z",
    "age_seconds": 420,
    "confidence_score": 0.91,
    "source": "provider_cache",
    "requires_revalidation": false
  }
}
```

**Reglas**

- Si falta precio, `price` debe ser `null`, no `0`.
- Si falta duracion, no inventar `0 min`.
- Si el precio viene de cache, decirlo.
- Si es historico, decirlo.
- Si el provider fallo, no convertirlo en ausencia silenciosa.

**Verificacion**

- Tests de schema/serializer.
- Tests de compatibilidad con frontend normalizer.

### Fase 24 - Fingerprint de busqueda

**Objetivo real**

Crear una clave estable que detecte busquedas iguales aunque el orden de campos o defaults varie.

**Debe normalizar**

- IATA uppercase;
- fechas ISO;
- pasajeros;
- moneda;
- nearby origins/destinations;
- country-only flags;
- filtros que afectan al resultado real;
- provider set;
- idioma solo si cambia copy/payload, no si no afecta datos;
- version de algoritmo.

**Casos de test**

- `lei` y `LEI` producen mismo fingerprint.
- campos opcionales en default no cambian fingerprint.
- cambiar fecha cambia fingerprint.
- cambiar nearby destinations cambia fingerprint.
- cambiar pasajeros cambia fingerprint.
- ida/vuelta genera fingerprints por leg y por grupo si procede.

### Fase 25 - Fingerprint de oferta

**Objetivo real**

Permitir que una misma oferta sea reconocida aunque aparezca en varias busquedas.

**Debe incluir**

- provider;
- carrier;
- flight number si existe;
- origin/destination;
- departure/arrival;
- stops;
- segmentos si hay itinerario compuesto;
- source kind;
- version.

**Reglas**

- No usar precio dentro del fingerprint de oferta. El precio es observacion, no identidad.
- Si no hay flight number, usar segmentos y horarios.
- Si el provider da IDs opacos, guardarlos, pero no depender solo de ellos si no son estables.

### Bloque J - Implementacion backend de cache inteligente

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 26 | Implementar o extender modelos persistentes necesarios. | Migracion Alembic, tests de modelo, rollback si aplica. |
| 27 | Implementar Search Cache exacta con TTL y freshness. | Hit/miss tests, no cambia contrato visible sin version. |
| 28 | Implementar Negative Cache. | Tests de no route, no availability, provider error y rate-limit. |
| 29 | Implementar Offer Cache y Price Observations. | Tests de dedupe oferta y multiples observaciones. |
| 30 | Integrar freshness en respuesta Quick Search. | Backend contract tests + frontend normalizer tests. |
| 31 | Revalidacion bajo demanda antes de decisiones sensibles. | Tests: alerta no dispara con stale sin revalidar. |
| 32 | Politica de TTL dinamico por antelacion. | Unit tests por rangos de fecha y provider. |
| 33 | Backoff y rate limit por provider. | Tests de error repetido y retry_after. |
| 34 | Metricas de cache y llamadas evitadas. | Logs/metrics sin secretos, tests de counters si existen. |
| 35 | Documentar flags y variables de entorno. | `.env.example` si procede + docs. |

### Fase 26 - Modelos y migraciones

**Objetivo real**

Extender lo existente de forma aditiva. Si ya hay tablas, preferir migraciones pequeñas antes que rediseño total.

**Posibles tablas nuevas o extendidas**

- `quick_search_cache_entries`
- `flight_offer_cache_entries`
- `flight_price_observations`
- `quick_search_negative_cache_entries`
- `fare_memory_revalidation_jobs`

Nombres reales deben adaptarse al repo.

**Reglas de datos**

- Migraciones aditivas.
- No borrar historico.
- Indices por fingerprint, provider, departure_at, expires_at.
- Constraints para evitar duplicados obvios.
- `price_amount` nullable si el resultado no trae precio.

**Verificacion**

- `python -m alembic check`
- Tests de modelo.
- Migracion aplicada en SQLite local si el repo lo permite.

### Fase 27 - Search Cache exacta

**Objetivo real**

Cuando una busqueda sea literalmente igual, reutilizar payload si esta dentro de politica de frescura.

**Reglas**

- Si `fresh`, responder desde cache y marcar `cache_hit=true`.
- Si `warm`, puede responder rapido pero marcar `requires_revalidation=true`.
- Si `stale`, no usar como actual salvo modo historico.
- Si `expired`, tratar como miss.

**Tests**

- cache hit exacto;
- cache miss por fecha distinta;
- cache miss por passenger count;
- cache warm expone freshness;
- payload no pierde metadata.

### Fase 28 - Negative Cache

**Objetivo real**

Guardar lo que no merece repetir ahora mismo.

**Casos**

- ruta sin vuelos;
- airport pair invalido;
- country-only sin match;
- provider no soporta ruta;
- timeout reciente;
- rate limit;
- respuesta vacia con provider sano.

**Regla critica**

`provider_error` no es igual que `no_results`. La UI y logs deben poder distinguirlo.

**Tests**

- negative cache evita llamada externa;
- negative cache caducada permite reintento;
- provider error usa backoff corto;
- no availability usa TTL normal de negativo;
- `hit_count` sube.

### Fase 29 - Offer Cache y Price Observations

**Objetivo real**

Separar la identidad del vuelo del precio observado.

**Reglas**

- Una oferta puede tener muchas observaciones de precio.
- Una busqueda puede producir varias ofertas.
- Una oferta puede aparecer en varias busquedas.
- El historico debe construirse con observaciones, no sobrescribiendo el precio anterior.

**Tests**

- misma oferta en dos busquedas crea una oferta y dos asociaciones/observaciones;
- precio nuevo genera nueva observacion;
- precio igual puede generar observacion o actualizar metadata segun decision documentada;
- `price_changed_since_last_seen` correcto.

### Fase 30 - Freshness en Quick Search

**Objetivo real**

La API empieza a decir la verdad temporal.

**UI minima permitida si toca frontend**

- Badge `Visto hace X min`.
- Tooltip/copy `Este precio viene de memoria de tarifas y puede cambiar al revalidar`.
- Estado `Revalidando...` si hay llamada activa.
- No usar rojo para stale salvo error real. Usar `warning` suave.

**Verificacion**

- Contract tests backend.
- Normalizer frontend.
- Snapshot/visual solo si cambia UI visible.

### Fase 31 - Revalidacion bajo demanda

**Objetivo real**

Antes de alertas, guardados sensibles o decision fuerte, Viru debe intentar revalidar si el dato no es `fresh`.

**Eventos que fuerzan revalidacion**

- disparar alerta de bajada;
- usuario guarda watchlist desde resultado `warm/stale`;
- usuario pulsa `Actualizar precio`;
- precio cerca de umbral;
- ruta con salida cercana.

**Tests**

- alerta no se dispara con stale sin revalidacion;
- si revalidacion confirma bajada, alerta se dispara;
- si revalidacion sube precio, se registra delta y no se miente;
- si provider falla, se genera evento honesto.

### Fase 32 - TTL dinamico

**Objetivo real**

TTL por antelacion, provider y volatilidad basica.

**Primera version**

- Solo reglas deterministas por departure_at y source_kind.
- No ML.
- Configurable por env o settings internos.

**Tests**

- rangos de antelacion;
- timezone UTC vs local;
- provider mock no contamina prod;
- salida pasada nunca fresh.

### Fase 33 - Backoff y rate limit

**Objetivo real**

Evitar que Viru se coma a si mismo cuando un provider falla.

**Reglas**

- backoff por provider;
- retry_after_at;
- limite de concurrencia;
- jitter;
- logs con causa;
- no secretos en logs.

**Tests**

- dos fallos seguidos aumentan espera;
- fallo de un provider no bloquea todos si no procede;
- rate limit se expone como warning, no como cero resultados.

### Fase 34 - Metricas

**Metricas utiles**

- cache_hit_rate;
- cache_miss_rate;
- negative_cache_hit_rate;
- provider_calls_avoided;
- stale_served_count;
- revalidation_success_count;
- revalidation_price_changed_count;
- provider_error_rate;
- avg_price_age_seconds;
- warmup_jobs_skipped_due_rate_limit.

**Verificacion**

- Tests de counters si hay infraestructura.
- Si no hay, logs estructurados y doc de observabilidad.

### Fase 35 - Flags y configuracion

**Variables posibles**

- `FARE_MEMORY_ENABLED=false`
- `FARE_MEMORY_SEARCH_CACHE_ENABLED=true`
- `FARE_MEMORY_OFFER_CACHE_ENABLED=false` al principio si se despliega por fases
- `FARE_MEMORY_NEGATIVE_CACHE_ENABLED=true`
- `FARE_MEMORY_BOOT_WARMUP_ENABLED=false`
- `FARE_MEMORY_MAX_BOOT_JOBS=25`
- `FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE=...`

**Regla**

Todo lo nuevo debe poder apagarse sin romper Quick Search.

### Bloque K - Scheduler, boot warmup y aprendizaje de volatilidad

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 36 | Diseñar cola/job model de revalidacion. | Spec de job, idempotencia y locks. |
| 37 | Implementar revalidacion manual segura. | Endpoint/servicio interno con tests y rate limit. |
| 38 | Implementar boot warmup en dry-run. | Logs de candidatos, cero llamadas externas por defecto. |
| 39 | Activar warmup controlado para watchlists activas. | Tests con limite, jitter y lock. |
| 40 | Calcular volatilidad basica por ruta/oferta. | Tests de delta, frecuencia de cambio y score. |
| 41 | Usar volatilidad para ajustar prioridad, no para prometer prediccion. | Tests de ranking de jobs. |
| 42 | Crear panel/admin log tecnico si ya existe superficie adecuada. | Sin exponer datos sensibles ni saturar UI. |

### Fase 36 - Job model de revalidacion

**Objetivo real**

Evitar revalidaciones duplicadas y permitir trabajo seguro por lotes.

**Campos orientativos**

- `id`
- `job_type`: `manual`, `watchlist`, `alert_threshold`, `boot_warmup`, `popular_search`
- `target_type`: `search`, `offer`, `route`
- `target_fingerprint`
- `provider`
- `priority`
- `status`: `queued`, `running`, `done`, `skipped`, `failed`
- `scheduled_at`
- `started_at`
- `finished_at`
- `lock_token`
- `attempt_count`
- `last_error_code`

### Fase 37 - Revalidacion manual

**Objetivo real**

Permitir que un usuario o flujo interno refresque una oferta sin depender de boot.

**Regla UI**

Boton o accion debe decir algo como `Actualizar precio`, no `Confirmar compra`.

**Tests**

- stale -> revalidation -> fresh;
- provider error -> warning;
- rate limit -> no llamada duplicada;
- usuario no puede refrescar datos privados de otro si aplica.

### Fase 38 - Boot warmup dry-run

**Objetivo real**

Al arrancar, Viru calcula que refrescaria, pero no llama providers todavia.

**Entregable**

- logs o reporte con candidatos;
- flag off por defecto;
- test de seleccion de candidatos;
- documentacion operacional.

### Fase 39 - Warmup controlado

**Objetivo real**

Permitir warmup real solo con limites estrictos.

**Prioridades**

1. Watchlist activa con alerta.
2. Precio cerca de umbral.
3. Salida cercana.
4. Alta volatilidad.
5. Busqueda popular reciente.

**Tests**

- max jobs respetado;
- jitter aplicado;
- lock evita duplicado;
- provider en backoff se salta.

### Fase 40 - Volatilidad basica

**Objetivo real**

Medir si una ruta/oferta cambia mucho sin venderlo como bola de cristal.

**Metricas**

- cambios por dia;
- delta medio;
- delta maximo;
- tiempo medio entre cambios;
- direccion dominante reciente;
- numero de observaciones suficientes.

**Regla**

Si hay pocas observaciones, mostrar `datos insuficientes`.

### Fase 41 - Prioridad basada en volatilidad

**Objetivo real**

Usar volatilidad para decidir que refrescar antes.

**No hacer**

- No decir `comprara ahora porque subira seguro`.
- No generar predicciones agresivas.
- No ocultar incertidumbre.

**Copy permitido**

- `Esta ruta ha cambiado varias veces recientemente`.
- `Conviene revalidar antes de decidir`.
- `Pocas observaciones todavia`.

### Fase 42 - Observabilidad tecnica

**Objetivo real**

Dar a desarrolladores una ventana de salud: no una UI publica confusa.

**Opciones**

- logs estructurados;
- endpoint admin si ya existe auth/admin;
- doc de queries SQL utiles;
- reporte CLI.

## Bloque L - UI y experiencia de frescura

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 43 | Diseñar microcopy de frescura en Quick Search. | ES consistente, no infantil, estados semanticos. |
| 44 | Implementar badges de frescura en resultados. | Tests render + dark/light si visible. |
| 45 | Añadir accion `Actualizar precio` donde tenga sentido. | Loading, disabled, error, success y rate-limit. |
| 46 | Integrar frescura en Watchlist e Historico. | Tests de snapshots y copy con pocos datos. |
| 47 | Integrar frescura en Alertas. | Alertas no prometen precio no revalidado. |
| 48 | QA visual completo de frescura. | Desktop/mobile, dark/light, focus, consola limpia. |

### Reglas UI para Bloque L

- Usar `success`, `warning`, `error`, `info`, nunca `warn` nuevo.
- Light mode no debe ser blanco generico.
- Dark mode no debe volverse lugubre.
- No saturar cada card con badges.
- Preferir copy pequeño y claro.
- Tooltip o detalle expandible para explicar sin ensuciar.
- Si `price=null`, no mostrar `0,00`.
- Si `duration=null`, no mostrar `--:--` como si fuera dato.

### Ejemplos de microcopy

| Caso | Copy recomendado |
|---|---|
| `fresh` | `Precio verificado hace 4 min` |
| `warm` | `Visto hace 38 min. Revalida antes de decidir.` |
| `stale` | `Precio historico. Puede haber cambiado.` |
| `provider_error_fresh` | `Proveedor sin respuesta. Conservamos la ultima señal.` |
| `negative_fresh` | `Sin resultados visto hace poco.` |
| rate limit | `Demasiadas consultas seguidas. Reintentamos luego.` |

## Bloque M - Puerta a puerta recolocada y compatible

Las fases antiguas de puerta a puerta no desaparecen. Se recolocan despues de Fare Memory porque door-to-door tambien sufrira el mismo problema: precios, horarios y disponibilidad no deben parecer confirmados si son deeplinks, stubs o datos parciales.

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 49 | Revisar modelo de tramo y campos falsos. | Tests render/formateo: no `--:--`, no `0,00` falso. |
| 50 | Estados honestos de cobertura y proveedor. | Warnings visibles: no coverage, partial, deeplink only. |
| 51 | Acciones externas fiables por tramo. | URL builders, `target=_blank`, `rel=noreferrer`, copy sin promesa de compra. |
| 52 | Buffers y riesgo de conexion. | Unit tests de margen ajustado y scoring. |
| 53 | GTFS/open data: cobertura, feeds, cache y errores. | Tests GTFS + runbook. |
| 54 | UX visual puerta a puerta. | Browser dark/light, desktop/mobile, timeline y sticky bar. |
| 55 | QA integral puerta a puerta. | Runbook completo + reporte de limitaciones. |

## Bloque N - Radar hotelero compatible con memoria y frescura

Hoteles ya tiene mucha base. No se debe reconstruir. Hay que consolidar visual, sweeps y honestidad de provider/cache.

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 56 | Auditoria post-cierre de `/hoteles`. | Contrastar spec, code, tests y pendientes reales. |
| 57 | Cerrar verificacion visual pendiente. | Browser dark/light/responsive, screenshots si procede. |
| 58 | Revisar sweeps hoteleros y scheduler. | Runbook, worker, flags y tests sin secretos. |
| 59 | Copy honesto de provider real/mock/cache. | No prometer disponibilidad falsa. |
| 60 | Pulido responsive comp sets/tracked offers. | Browser + build/typecheck frontend. |
| 61 | Scoring hotelero con datos insuficientes. | Tests de scoring y casos sin observaciones. |

## Bloque O - Watchlist, alertas e historico con memoria de tarifas

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 62 | Auditoria watchlist tras Fare Memory. | Tests existentes + mapa de dependencia de precios. |
| 63 | Historico mas util: min, max, media, tendencia y frescura. | Tests de calculo y snapshots insuficientes. |
| 64 | Alertas con revalidacion obligatoria segun estado. | Tests de stale/warm/fresh antes de disparar. |
| 65 | Cooldown y digest con eventos de revalidacion. | Tests backend alerts/prices/watchlist. |
| 66 | QA integral watchlist-alertas-historico. | Crear ruta, ver historico, regla, evento, pausar/borrar. |

## Bloque P - Providers, contratos y fiabilidad

| Fase | Objetivo | Verificacion minima |
|---|---|---|
| 67 | Auditoria providers de vuelos post-cache. | Registry, env vars, errores, rate limits y tests. |
| 68 | Normalizacion de errores providers. | Timeout/error/empty/rate-limit con warnings canonicos. |
| 69 | Contratos frontend-backend de busqueda. | Typecheck + backend contract tests. |
| 70 | Consolidacion final y handoff. | Suites razonables, browser core, docs, HISTORY si aplica, push limpio. |

## 12. Mapa de incompatibilidades corregidas

| Elemento del roadmap anterior | Problema tras esta conversacion | Decision v2 |
|---|---|---|
| Fase 21 empezaba en campos falsos de puerta a puerta | No contempla Fare Memory, que afecta antes a Quick Search, Watchlist y Alertas | Recolocada a Fase 49 |
| Fase 42 revisaba cache compartida tarde | La cache pasa a ser nucleo del producto | Convertida en Bloques I-J desde Fase 21 |
| Redis hot layer pronto | Puede distraer de persistencia/frescura real | Solo despues de medir y con flag, no prioridad actual |
| Warmup implicito al boot | Riesgo de estampida y coste | Dry-run primero, limites, jitter, locks y flag off |
| Precio cacheado reutilizable sin semantica fuerte | Puede mentir al usuario | Freshness obligatorio antes de UI fuerte |
| Providers parciales puerta a puerta | Pueden mostrar precision falsa | Se mantienen, pero con honestidad de fuente y cobertura |
| Alertas basadas en snapshots viejos | Pueden avisar con precio caducado | Revalidacion obligatoria segun estado |

## 13. Checklist de cierre por fase

Cada fase debe terminar con:

1. Objetivo de fase escrito.
2. Archivos leidos.
3. Estado actual observado.
4. Cambio minimo viable.
5. Tests adecuados.
6. Si hay migracion: Alembic check o limitacion explicita.
7. Si hay API: contract tests o payload observado.
8. Si hay UI: dark/light, responsive si aplica, foco y consola.
9. `git diff` revisado.
10. Commit Conventional Commit en `main` si el usuario pidio cambio real.
11. Push si queda completado y el workflow lo exige.
12. Informe con evidencia, no frases tipo `deberia funcionar`.

## 14. Comandos base sugeridos

### Backend general

```powershell
cd C:\Users\javiru\Desktop\viru-air\backend
python -m pytest
python -m alembic check
```

### Backend focalizado Fare Memory

Los nombres exactos dependeran de los tests creados:

```powershell
cd C:\Users\javiru\Desktop\viru-air\backend
python -m pytest tests/unit/test_quick_search_cache_models.py -q
python -m pytest tests/unit/test_fare_memory_fingerprints.py -q
python -m pytest tests/unit/test_fare_memory_ttl.py -q
python -m pytest tests/integration/test_quick_search_freshness_contract.py -q
```

### Frontend

```powershell
cd C:\Users\javiru\Desktop\viru-air\frontend
npm test
npm run lint
npm run build
```

### Quick Search focalizado

```powershell
cd C:\Users\javiru\Desktop\viru-air\frontend
npm test -- tests/quick-search-dual-regression.test.tsx tests/quick-search-visible-results.test.ts tests/quick-search-response-normalizer.test.ts
```

### Puerta a puerta

```powershell
cd C:\Users\javiru\Desktop\viru-air\backend
python -m pytest tests/integration/test_door_to_door.py tests/unit/test_door_to_door_gtfs_transit.py tests/unit/test_door_to_door_deeplinks.py -q
```

### Release guard

```powershell
cd C:\Users\javiru\Desktop\viru-air
powershell -ExecutionPolicy Bypass -File .\scripts\release_guard.ps1 -AllowDirtyWorktree
```

## 15. Prompt corto para darle a Codex al empezar la Fase 21

```text
Estamos en Viru Air. Las fases 1-20 del roadmap anterior ya estan completadas. Usa el nuevo roadmap v2: `docs/prompts/codex-travel-roadmap-v2-fare-memory.md`.

Empieza por la Fase 21: auditar la cache existente de Quick Search V2.1 y el historico de precios antes de construir nada. No dupliques caches. No crees migraciones. No actives scraping ni APIs de pago. Lee `AGENTS.md`, `backend/AGENTS.md`, `frontend/AGENTS.md`, `DESIGN.md`, `docs/reference/backend/quick-search-contract.md`, `docs/plans/2026-06-10-quick-search-shared-cache-review-plan.md` y los modelos/servicios/tests reales de quick-search, prices, watchlist y alerts.

Entregable: informe tecnico con tabla de que existe, donde esta, que cubren los tests, que falta para Viru Fare Memory y que decision recomiendas para fases 22-26. Verifica con tests existentes de cache si los hay. Si hay drift documental, reportalo con fuente preferida.
```

## 16. Prompt largo para Codex si se quiere ejecutar todo el bloque I-J

```text
Objetivo: implementar progresivamente Viru Fare Memory, un sistema de cache y memoria de tarifas para Viru Air.

Contexto:
- Fases 1-20 ya estan completadas.
- No reconstruyas Quick Search desde cero.
- El roadmap antiguo queda sustituido por `codex-travel-roadmap-v2-fare-memory.md` a partir de la Fase 21.
- Quick Search ya tiene cache compartida persistente V2.1, por tanto primero audita y extiende, no dupliques.
- Viru debe ahorrar llamadas a providers, recordar resultados validos e invalidos y mostrar frescura temporal sin mentir.

Restricciones:
- No scraping activo de Ryanair.
- No APIs de pago ni servicios externos nuevos sin permiso.
- No mostrar precio cacheado como confirmado si no esta fresh.
- No convertir provider error en no results.
- No migraciones destructivas.
- Todo debe poder apagarse por flags.
- Mantener UI calida, clara, aeronautica y dual-theme.

Ejecuta fases pequeñas:
1. Audita cache/historico actual.
2. Crea spec Viru Fare Memory.
3. Define freshness contract.
4. Implementa fingerprints de search y offer con tests.
5. Extiende modelos si procede con migracion aditiva.
6. Implementa Search Cache exacta con TTL.
7. Implementa Negative Cache.
8. Implementa Offer Cache + Price Observations.
9. Integra freshness en Quick Search.
10. Añade revalidacion bajo demanda y TTL dinamico.

Cierre obligatorio:
- Tests backend focalizados.
- Contract tests si cambia API.
- Frontend normalizer tests si cambia payload visible.
- Alembic check si hay migracion.
- Documentacion actualizada.
- Informe con evidencia concreta.
```

## 17. Resultado esperado de producto

Cuando este roadmap avance, Viru deberia poder decir cosas como:

- `Este precio esta verificado hace 3 minutos.`
- `Este precio lo vimos hace 2 horas. Te lo enseño como pista, no como promesa.`
- `No repetimos la consulta porque Ryanair fallo hace 4 minutos. Reintentaremos despues.`
- `Esta ruta suele moverse bastante. Conviene revalidar antes de guardarla.`
- `No hay resultados vistos hace poco para esta combinacion, pero podemos reintentarlo.`

Ese es el salto: de buscador que pregunta siempre, a copiloto que recuerda, duda bien y no vende humo. Pequeña torre de control, con bufanda de terciopelo y cronometro serio.

## 18. Cierre de este documento

Este v2 deja una direccion nueva y compatible:

- Fases 1-20: cerradas.
- Fases 21-48: nueva columna vertebral de memoria, cache, frescura, revalidacion y UI honesta.
- Fases 49-55: puerta a puerta, ahora compatible con honestidad de datos.
- Fases 56-61: hoteles, consolidacion visual y provider/cache.
- Fases 62-66: watchlist, alertas e historico sobre memoria de tarifas.
- Fases 67-70: providers, contratos y cierre final.

La siguiente fase recomendada ya no es la antigua Fase 21. La nueva siguiente fase es:

> **Fase 21 - Auditar la cache existente de Quick Search V2.1 y el historico de precios.**
