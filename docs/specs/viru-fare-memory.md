# Viru Fare Memory

**Estado:** vivo  
**Ultima revision:** 2026-07-09
**Fuente de verdad:** si  
**Area:** backend / quick-search / watchlist / pricing intelligence

## Problema

Viru Tracker ya recuerda resultados exactos de Quick Search con cache compartida V2.1, pero todavia no distingue con suficiente precision:

- precio actual verificado;
- precio visto recientemente;
- precio historico;
- ausencia de resultados reciente;
- error de provider reciente.

Sin esa separacion, la plataforma puede ahorrar llamadas, pero aun no puede explicar bien lo que sabe ni lo que ya necesita revalidar.

## Objetivo

Crear una base comun para que Quick Search, Watchlist, Alertas e Historico recuerden precios sin venderlos como verdad absoluta.

## Alcance

Esta spec define:

- el modelo mental de Fare Memory;
- los estados canonicos de frescura;
- el contrato logico de search cache, offer cache, price observations y negative cache;
- la politica inicial de TTL;
- las reglas de revalidacion;
- el warmup de arranque;
- las metricas minimas;
- el impacto esperado en producto.

## No objetivos

- scraping activo de Ryanair o de cualquier web no autorizada;
- compra o simulacion de compra;
- prediccion agresiva de precios;
- reescribir Quick Search desde cero;
- sustituir el historico actual de watchlist en esta fase;
- activar llamadas masivas al arrancar.

## Base existente obligatoria

La fuente de verdad actual para cache compartida es `QuickSearchCacheEntry` y su servicio asociado en backend. Fare Memory debe extender esta base o construir sobre ella de forma aditiva. Queda prohibido crear una segunda cache paralela con semantica duplicada.

Persistencia base disponible desde la Fase 26:

- `quick_search_cache_entry` extendida con campos de fingerprint, frescura y confianza;
- `flight_offer_cache_entry` para identidad de oferta;
- `flight_price_observation` para historico de observaciones;
- `quick_search_negative_cache_entry` para ausencias y fallos reutilizables.

Decision de privacidad actual:

- las tablas globales de memoria (`QuickSearchCacheEntry`, `FlightOfferCacheEntry`, `FlightPriceObservation`, `QuickSearchNegativeCacheEntry`) no deben guardar `user_id`;
- la personalizacion vive en `FlightWatch`, `PriceSnapshot`, reglas de alerta y preferencias de usuario;
- una busqueda personal puede alimentar memoria global solo con datos tecnicos de ruta/provider/precio, nunca con identidad de usuario, email, token, target price privado o notas personales;
- cualquier backfill desde memoria global a watchlist debe crear datos personales nuevos en el dominio de watchlist, no enlazar usuarios a entradas globales reutilizables.

## Modelo mental

Fare Memory separa cuatro niveles:

1. **Busqueda**: lo que pide el usuario.
2. **Resultado de busqueda**: la respuesta observada para esa busqueda en un momento concreto.
3. **Oferta**: el vuelo o itinerario normalizado que puede reaparecer en varias busquedas.
4. **Observacion de precio**: el precio visto para una oferta en un instante concreto.

## Capas de cache y memoria

| Capa | Tabla / dominio | Pregunta que responde | Privacidad |
|---|---|---|---|
| Request cache | `QuickSearchCacheEntry` | Si una busqueda canonica por provider sigue siendo reutilizable | Global, sin usuario |
| Negative cache | `QuickSearchNegativeCacheEntry` | Si una ausencia o fallo reciente evita repetir una llamada | Global, sin usuario |
| Offer memory | `FlightOfferCacheEntry` + `FlightPriceObservation` | Que oferta/precio ha visto Viru y cuando | Global, sin usuario |
| Watchlist snapshots | `FlightWatch` + `PriceSnapshot` | Que sigue un usuario y que historico personal ve | Personal, con usuario |
| Revalidation jobs | `RevalidationJob` | Que rutas deben refrescarse sin bloquear la UI | Operacional; no debe exponer usuario salvo que el caso lo requiera y este justificado |

La regla practica es: cache global para hechos tecnicos reutilizables; watchlist para intencion personal.

## Estados canonicos de frescura

| Estado | Significado | Uso |
|---|---|---|
| `fresh` | Precio revalidado dentro de TTL activo | Mostrable como precio actual observado |
| `warm` | Precio util para orientar, no para decidir fuerte | Requiere copy honesto y opcion de revalidar |
| `stale` | Precio viejo pero todavia informativo | Solo como historico o pista |
| `expired` | Dato no reutilizable | No debe salir como resultado actual |
| `negative_fresh` | Ausencia de resultado observada hace poco | Evita repetir consultas inutiles |
| `negative_stale` | Ausencia antigua | Puede permitir nuevo fetch |
| `provider_error_fresh` | Fallo reciente del provider | Activa backoff y evita bucles |
| `provider_error_stale` | Fallo antiguo | Puede reintentarse |

## Contratos logicos

### Search Cache

Memoria de busqueda exacta reutilizable por fingerprint de busqueda canonica y por unidades exactas de provider.

Campos minimos esperados:

- `search_fingerprint`
- `canonical_request_json`
- `provider_set`
- `result_payload_json`
- `observed_at`
- `expires_at`
- `freshness_status`
- `confidence_score`

### Offer Cache

Identidad estable de una oferta sin incluir precio en el fingerprint.

Campos minimos esperados:

- `offer_fingerprint`
- `flight_instance_fingerprint`
- `provider`
- `carrier`
- `carrier_code`
- `flight_number` si existe
- `origin_airport`
- `destination_airport`
- `departure_at`
- `arrival_at`
- `stops_count`
- `source_kind`

Convencion actual de `carrier_code` derivado:

- si el provider entrega un carrier explicito, se normaliza en mayusculas y se usa como fuente primaria;
- Ryanair se persiste como `FR`;
- Vueling se persiste como `VY`;
- si el provider no es conocido y no hay carrier explicito, se usa el `provider` normalizado en mayusculas como fallback estable.

Decision actual sobre `flight_number` en providers publicos:

- Ryanair: los parsers actuales no exponen un numero de vuelo real ni hay fixture local vigente que lo demuestre con los endpoints ya usados;
- Vueling: el fixture actual trae `flightID` y `carrierCode`, pero `flightID` no esta tratado todavia como contrato de numero de vuelo fiable;
- hasta verificar esos campos con evidencia suficiente, `flight_number` permanece nullable y la identidad estable de salida se apoya en `flight_instance_fingerprint`.

### Price Observations

Historico de precio ligado a una oferta.

Decision actual de implementacion:

- si una misma oferta reaparece en otra busqueda con el mismo precio, Viru guarda una nueva observacion igualmente para conservar la linea temporal de avistamientos;
- `price_changed_since_last_seen` solo se activa cuando el importe cambia frente a la observacion anterior de esa oferta.
- si la misma oferta, provider, moneda y precio se observa de nuevo dentro de 30 segundos, se omite como duplicado reciente para evitar inflar historial por reintentos inmediatos.

Campos minimos esperados:

- `offer_id`
- `search_cache_id` nullable
- `price_amount`
- `currency`
- `observed_at`
- `expires_at`
- `freshness_status`
- `confidence_score`
- `validation_status`
- `price_changed_since_last_seen`
- `delta_abs`
- `delta_pct`

### Negative Cache

Memoria de ausencias y fallos para evitar repetir consultas de poco valor.

Campos minimos esperados:

- `negative_fingerprint`
- `scope`
- `reason`
- `provider`
- `canonical_request_json`
- `observed_at`
- `expires_at`
- `freshness_status`
- `retry_after_at`
- `hit_count`

Primera integracion real desde la Fase 28:

- `no_availability` evita repetir una ruta sin vuelos durante una ventana corta reutilizable;
- `provider_timeout`, `provider_error` y `provider_total_outage` aplican backoff mas corto y conservan warnings canonicos;
- la ausencia por provider no debe presentarse como ausencia silenciosa de mercado.

## TTL inicial recomendado

| Antelacion salida | TTL |
|---|---:|
| > 90 dias | 12 h |
| 60-90 dias | 8 h |
| 30-60 dias | 4 h |
| 14-30 dias | 2 h |
| 3-14 dias | 45 min |
| 24-72 h | 15 min |
| < 24 h | 5 min |
| resultado negativo | 15-60 min |
| error de provider | 5-15 min + backoff |

Implementacion actual desde Fase 32:

- los resultados `ready` de quick search usan TTL dinamico por `travel_date`;
- `empty`, `degraded`, `negative_*` y `provider_error_*` mantienen TTL base separados;
- providers tecnicos de test como `mock` o `fixture` quedan capados a una ventana corta para no contaminar comportamiento de produccion;
- una salida con `travel_date` pasada no debe serializarse como `fresh`.

## Regla de verdad temporal

Un TTL largo no convierte un precio en precio confirmado. Solo autoriza a Viru a reutilizar memoria con semantica explicita de frescura.

## Revalidacion

Viru debe intentar revalidar cuando el dato no sea `fresh` y el flujo implique una decision sensible, por ejemplo:

- disparo de alertas;
- guardado a watchlist desde resultado `warm/stale`;
- accion manual `Actualizar precio`;
- precio cerca de umbral;
- ruta con salida cercana.

## Warmup de arranque

Si se implementa warmup, debe empezar en dry-run y seguir estas prioridades:

1. Watchlists activas con alertas.
2. Rutas cerca de umbral.
3. Busquedas populares recientes.
4. Ofertas `warm` cerca de `stale`.
5. Rutas con volatilidad alta.

Requisitos minimos:

- maximo de jobs por arranque;
- jitter;
- rate limit por provider;
- backoff;
- lock anti-duplicado;
- flag off por defecto.

## Rollout y flags

Estado de rollout actual:

- la memoria durable existe y puede usarse por capas, pero la activacion debe ser gradual;
- el warmup de arranque permanece desactivado por defecto;
- Redis se considera una capa opcional futura, no una dependencia obligatoria de la memoria durable;
- cualquier activacion que aumente llamadas a providers debe tener limite, backoff y verificacion explicita.

Flags relevantes:

| Flag | Default | Uso | Riesgo | Recomendacion |
|---|---:|---|---|---|
| `QUICK_SEARCH_SHARED_CACHE_ENABLED` | `false` | Activa reutilizacion persistente de Quick Search en `search.py` | Servir memoria compartida sin observar frescura | Mantener off en prod hasta canary con metricas |
| `QUICK_SEARCH_SHARED_CACHE_READY_TTL_SECONDS` | `86400` | TTL base legacy para resultados `ready`; la politica dinamica puede acortarlo por fecha | TTL demasiado largo si se usa sin freshness | Conservar como fallback, no como verdad de precio |
| `QUICK_SEARCH_SHARED_CACHE_EMPTY_TTL_SECONDS` | `7200` | TTL base para respuestas vacias | Ocultar recuperacion de proveedor si se abusa | Mantener menor que ready |
| `QUICK_SEARCH_SHARED_CACHE_DEGRADED_TTL_SECONDS` | `1800` | TTL base para resultados degradados | Repetir degradacion como si fuera estable | Mantener corto |
| `QUICK_SEARCH_NEGATIVE_CACHE_TTL_SECONDS` | `1800` | TTL de ausencias reutilizables | Convertir ausencia reciente en ausencia de mercado | Mostrar warnings y permitir reintento cuando expire |
| `QUICK_SEARCH_NEGATIVE_PROVIDER_ERROR_TTL_SECONDS` | `600` | TTL inicial de errores de provider | Bucles de retry o bloqueo excesivo | Mantener corto con backoff |
| `QUICK_SEARCH_NEGATIVE_PROVIDER_ERROR_MAX_TTL_SECONDS` | `3600` | Techo de backoff para errores de provider | Silenciar demasiado tiempo un provider recuperado | No subir sin datos operativos |
| `FARE_MEMORY_ENABLED` | `true` | Master switch del dominio Fare Memory | Apagarlo desactiva subcapas aunque sus flags esten true | Usar para rollback amplio |
| `FARE_MEMORY_SEARCH_CACHE_ENABLED` | `true` | Permite escritura/lectura de cache exacta por `search_fingerprint` | Duplicar cache si se usa fuera de la base compartida | Mantener aditivo sobre `QuickSearchCacheEntry` |
| `FARE_MEMORY_OFFER_CACHE_ENABLED` | `true` | Permite persistir ofertas y observaciones | Guardar datos personales por error | Mantener sin `user_id` |
| `FARE_MEMORY_NEGATIVE_CACHE_ENABLED` | `true` | Permite negative cache persistente | Tratar error como ausencia silenciosa | Conservar reason/warnings canonicos |
| `FARE_MEMORY_BOOT_WARMUP_ENABLED` | `false` | Agenda warmup al arrancar | Coste/stampede al boot | Mantener off salvo canary |
| `FARE_MEMORY_MAX_BOOT_JOBS` | `25` | Limita jobs de warmup | Sobrecarga si se sube sin rate limit | Ajustar junto a rate limit |
| `FARE_MEMORY_BOOT_WARMUP_JITTER_SECONDS` | `30` | Distribuye jobs al arrancar | Picos si es 0 en multi-worker | Mantener jitter en entornos compartidos |
| `FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE` | `60` | Recorta jobs por provider | Saturar provider si sube demasiado | Cambiar solo con observabilidad |
| `WATCHLIST_STARTUP_REFRESH_ENABLED` | `true` | Mantiene refresh de watchlist existente | Llamadas al arranque si hay muchas rutas | Mantener dedupe por `RevalidationJob` |
| `WATCHLIST_STARTUP_REFRESH_MAX_AGE_SECONDS` | `14400` | Umbral de stale para priorizar startup refresh | Documentacion desalineada rompe expectativas | Fuente actual: `backend/.env.example` |

Fases de rollout:

1. Baseline y contratos verdes sin cambiar runtime.
2. Activacion en tests con fixtures y providers controlados.
3. Dev/local con cache compartida y metricas visibles.
4. Canary de bajo volumen con logs de hit/miss y errores de provider.
5. Produccion gradual solo si no sube el error rate ni se degrada la verdad de frescura.

## Metricas minimas

- `cache_hit_rate`
- `cache_miss_rate`
- `negative_cache_hit_rate`
- `provider_calls_avoided`
- `stale_served_count`
- `revalidation_success_count`
- `revalidation_price_changed_count`
- `provider_error_rate`
- `avg_price_age_seconds`

## Impacto por area

### Quick Search

- podra responder mas rapido reutilizando memoria;
- no debera mostrar un precio cacheado como confirmado si no esta `fresh`;
- necesitara un envelope de frescura por resultado.

### Watchlist

- seguira usando `PriceSnapshot` en la fase actual;
- mas adelante podra enlazar snapshots con observaciones de oferta.

### Alertas

- no deben dispararse solo por snapshots viejos;
- deberan revalidar segun frescura.
- implementacion actual: si el ultimo `PriceSnapshot` de una watch esta marcado como `is_stale`, la evaluacion de alertas intenta una revalidacion puntual antes de disparar reglas; si el provider falla, se crea un evento honesto y no se dispara una alerta de precio como si estuviera confirmada.

### Historico

- pasara de fotografias por watch a observaciones reutilizables por oferta.

## Copy recomendado

- `Precio verificado hace 4 min`
- `Visto hace 38 min. Revalida antes de decidir.`
- `Precio historico. Puede haber cambiado.`
- `Proveedor sin respuesta. Conservamos la ultima senal.`
- `Sin resultados visto hace poco.`

## Riesgos y limites

- riesgo legal si se deriva hacia scraping activo no aprobado;
- riesgo de coste si se hace warmup sin limites;
- riesgo de mentira de producto si se expone cache sin frescura;
- riesgo tecnico si se duplican caches en lugar de extender la base existente.

## Decision explicita de legalidad y coste

Viru Fare Memory no autoriza:

- scraping activo de Ryanair;
- APIs de pago nuevas sin permiso expreso;
- automatismos agresivos al boot;
- conversion de errores de provider en `sin resultados`.

## Dependencias de implementacion

Antes de crear tablas nuevas, deben existir:

1. fingerprint de busqueda canonica;
2. fingerprint de oferta sin precio;
3. envelope de frescura documentado y probado;
4. auditoria cerrada de la cache existente.
