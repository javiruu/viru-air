# Viru Fare Memory

**Estado:** vivo  
**Ultima revision:** 2026-06-14  
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

## Modelo mental

Fare Memory separa cuatro niveles:

1. **Busqueda**: lo que pide el usuario.
2. **Resultado de busqueda**: la respuesta observada para esa busqueda en un momento concreto.
3. **Oferta**: el vuelo o itinerario normalizado que puede reaparecer en varias busquedas.
4. **Observacion de precio**: el precio visto para una oferta en un instante concreto.

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
- `provider`
- `carrier`
- `flight_number` si existe
- `origin_airport`
- `destination_airport`
- `departure_at`
- `arrival_at`
- `stops_count`
- `source_kind`

### Price Observations

Historico de precio ligado a una oferta.

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
