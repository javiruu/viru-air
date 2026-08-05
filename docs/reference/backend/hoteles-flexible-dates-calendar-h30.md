# H30 — Calendario y flexibilidad de fechas hoteleras

**Estado:** completa como contrato; implementación de ventanas, calendario, capabilities, migración V2 y QA pendientes  
**Fecha:** 2026-08-05  
**Área:** producto / backend / frontend / providers / cache / ranking / tracking / QA  
**Fuente de verdad:** sí para la semántica de calendario y búsqueda hotelera flexible  
**Fase del roadmap:** H30  
**Depende de:** [H10 — modelo de estancia y oferta](hoteles-stay-offer-model-h10.md), [H12 — resolución de destino](hoteles-destination-resolution-h12.md), [H13 — formulario y URL state](hoteles-search-form-h13.md), [H14 — filtros y ranking](hoteles-filters-ranking-h14.md), [H15 — resultados y paginación](hoteles-results-pagination-h15.md), [H17 — ranking explicable](hoteles-ranking-explainability-h17.md), [H19 — precio y fees](hoteles-price-total-fees-h19.md)  
**Relacionado con:** H05 freshness, H06 provider-neutral, H08 onboarding, H09 sweeps, H11 migración, H20 comparación, H21 estados, H23 tracking, H24 histórico, H25 confidence, H29 lifecycle, H34 i18n, H37 coste, H40 QA, H41 observabilidad, H43 flags, H48 búsquedas guardadas

> La flexibilidad de fechas no es “buscar sin fechas”. Es una familia de estancias candidatas con reglas explícitas. Si Viru no puede decir qué entrada, salida, noches, ocupación, moneda y condiciones produjeron un precio, no puede presentarlo como una oportunidad comparable.

## 1. Decisión de alcance

H30 define cómo expresar y ejecutar una intención temporal flexible sin romper la búsqueda exacta:

1. modos de fecha y duración;
2. selección de calendario y presentación de alternativas;
3. ocupación y estancia como parte de cada candidato;
4. capabilities reales de cada provider;
5. límites de combinaciones, coste, rate limits y cache;
6. identidad/fingerprint de la consulta temporal;
7. resultado efectivo, precio, freshness y comparabilidad;
8. URL compartible y recuperación segura;
9. ranking, agrupación y filtros de alternativas;
10. interacción con tracking, alertas y búsquedas guardadas;
11. estados partial, unsupported, provider error y no-data;
12. migración V1→V2, flags y gates.

H30 no elige un provider comercial, no garantiza cobertura flexible, no convierte una búsqueda flexible en tracking automáticamente y no cambia la semántica de `HotelTrackedOffer` fijada por H22/H23/H29. La búsqueda exacta sigue siendo el baseline.

## 2. Estado actual comprobable (V1)

### 2.1. Backend

El endpoint hotelero de área acepta actualmente:

```text
latitude
longitude
radius_km
check_in: Date requerido
check_out: Date requerido
guests: int bridge
currency
min_stars
max_price
sort: price | distance | stars
use_provider
```

`HotelAreaSearchQueryIn` exige `check_out > check_in`. No existe en el schema actual un `flexibility_days`, ventana de fechas, mes flexible, duración flexible, fin de semana ni lista de estancias candidatas. `HotelAreaSearchResultOut` devuelve las fechas exactas de la consulta (`check_in`/`check_out`), no un conjunto de fechas efectivas alternativas.

`HotelRatesQueryIn` también trabaja con fechas concretas opcionales y `HotelRateOut` representa una observación para un único par de fechas. El servicio de área busca snapshots con fechas exactas y, cuando se habilita provider, ejecuta el flujo actual de provider para esa estancia; no hay una operación de expansión temporal ni un presupuesto específico para varias estancias.

### 2.2. Frontend

`useHotelSearch` conserva localmente:

```text
checkIn
checkOut
guests
radiusKm
useProvider
```

Aunque el backend acepta `currency`, el hook/panel actual no expone ni mantiene un selector de moneda propio; el flujo opera esencialmente con el default del API/caller. H30 no debe presentar una currency flexible como implementada en frontend hasta que H13/H19/H34 la hagan explícita.

`HotelSearchPanel` usa dos inputs HTML de fecha, valida de forma básica que existan y envía una búsqueda exacta. No existe aún estado de mes visible, modo flexible, duración, matriz de precios ni URL state hotelero completo. El calendario de vuelo y cualquier flexibilidad de Quick Search no son un contrato reutilizable para hoteles.

### 2.3. Consecuencias

Hoy es correcto afirmar:

- búsqueda exacta por estancia;
- validación de rango de fechas;
- ocupación escalar `guests` como bridge;
- resultados/snapshots ligados a esas fechas;
- provider mock/experimental según flag.

Hoy no es correcto afirmar:

- “mejor fecha” o “precio mínimo del mes”;
- calendario hotelero con precios por día;
- búsqueda flexible ejecutada por provider;
- cobertura de todos los fines de semana o duraciones;
- tracking de una ventana como si fuera una oferta concreta;
- que un resultado de otra estancia sea una bajada del tracking exacto del usuario.

## 3. Modelo temporal canónico V2

### 3.1. `TemporalIntent`

La consulta futura debe transportar una estrategia temporal explícita:

```text
TemporalIntent {
  mode: exact | shift_window | flexible_month | weekend_window | duration_window
  anchor_check_in: Date | null
  anchor_check_out: Date | null
  nights: positive integer | null
  check_in_start: Date | null
  check_in_end: Date | null
  month: YYYY-MM | null
  allowed_weekdays: list[0..6] | null
  duration_min_nights: positive integer | null
  duration_max_nights: positive integer | null
  timezone: IANA timezone or destination policy
  max_candidates: bounded integer
}
```

No se permite que dos campos expresen ventanas contradictorias. Cada modo tiene una semántica única:

| Modo | Semántica | No significa |
|---|---|---|
| `exact` | una sola entrada/salida | flexibilidad |
| `shift_window` | desplazar la entrada dentro de una ventana y conservar `nights` | cambiar duración sin decirlo |
| `flexible_month` | entradas del mes indicado con duración fija y límites explícitos | “cualquier fecha” sin coste/límite |
| `weekend_window` | solo combinaciones que cumplen la política de fin de semana y duración | todos los viernes/sábados del calendario |
| `duration_window` | entradas dentro de ventana y noches entre min/max | comparar estancias de distinta duración como un único precio |

`anchor_check_in` y `anchor_check_out` pueden ser opcionales solo en modos que tengan mes/ventana suficiente; un modo sin ancla debe declarar `check_in_start/end`, `nights` o duración y timezone.

### 3.2. Reglas de generación

La expansión a candidatos es determinista y server-side:

1. validar destino, timezone y fechas locales;
2. derivar noches de una estancia exacta o validar `nights` explícitas;
3. generar combinaciones dentro de la ventana inclusiva;
4. descartar fechas pasadas, checkout inválido, límites del provider y estancias imposibles;
5. ordenar candidatos por distancia temporal a la intención, no por precio todavía;
6. aplicar `max_candidates` antes de llamadas externas;
7. conservar la lista de candidatos generada/versionada para reproducir el resultado.

No usar redondeos de UTC para cambiar la fecha local del destino. `check_out` debe ser posterior a `check_in` en la zona horaria declarada.

### 3.3. Duración y comparabilidad

El precio de una estancia de 2 noches no se compara directamente con el total de 5 noches. Todo resultado debe llevar:

```text
actual_check_in
actual_check_out
nights
occupancy
currency_requested
currency_observed
price_semantics: total | per_night | base | unknown
conditions_completeness
```

La UI puede mostrar precio total y precio por noche solo cuando H19 demuestra la semántica. El ranking de “más barato” debe elegir una métrica común y visible:

- total de estancia solo con `nights` iguales;
- por noche solo si el total y las noches son fiables;
- ningún ranking cruzado si fees, moneda o condiciones no son comparables.

## 4. Modos V1 bridge y V2

### 4.1. V1 compatible

Los endpoints exact-date mantienen sus campos y comportamiento. La flexibilidad se introduce de forma aditiva, detrás de flag y con un envelope nuevo, sin reinterpretar una llamada antigua:

```json
{
  "temporal_intent": {
    "mode": "shift_window",
    "anchor_check_in": "2026-09-10",
    "nights": 3,
    "check_in_start": "2026-09-09",
    "check_in_end": "2026-09-11",
    "timezone": "Europe/Madrid",
    "max_candidates": 3
  }
}
```

Los callers legacy que solo envían `check_in/check_out` se normalizan como `mode=exact`. No asumir flexibilidad por ausencia de fechas ni por un checkbox genérico.

### 4.2. V2 objetivo

El request canónico separa:

```text
StayQuery
  destination
  occupancy: rooms/adults/children_ages
  currency
  conditions/preferences
TemporalIntent
  mode + window + nights + timezone + limits
ExecutionPolicy
  provider_scope + max_candidates + budget_class + freshness_policy
```

La consulta compartida no contiene `user_id`, email, target price, alert rules ni canales privados. Una búsqueda flexible puede reutilizar resultados compartidos por `stay_query_fingerprint + temporal_intent_fingerprint + execution_policy_version`, pero nunca suscripciones privadas.

## 5. Capabilities de provider

Cada provider debe declarar por operación:

```text
supports_exact_stay
supports_multiple_stays_per_request
supports_flexible_check_in
supports_month_search
supports_weekend_search
supports_variable_nights
supports_rooms_children_ages
supports_total_price
supports_currency
max_date_span_days
max_candidates_per_request
rate_limit_class
cost_class
```

Estados de capability:

```text
supported | unsupported | unknown | limited | disabled
```

Reglas:

- `unknown` no se trata como `supported`;
- un provider `unsupported` no recibe llamadas flexibles silenciosamente convertidas en exactas;
- si solo soporta una estancia por llamada, el gateway puede expandir candidatos con budget y límite, o devolver `limited`;
- si no conserva ocupación/condiciones, el resultado es `partial` y no entra en ranking estricto;
- si el provider no devuelve fechas efectivas, la respuesta no puede presentarse como alternativa flexible;
- `use_provider=true` no prueba capacidad flexible ni autoriza un fan-out ilimitado.

El mock puede generar fixtures deterministas de varias fechas, pero debe rotularse `demo`/`fixture-only` y no sirve como evidencia de cobertura real.

## 6. Coste, cache y ejecución

La expansión flexible puede multiplicar llamadas. Antes de habilitarla se debe definir:

```text
max_candidates por request
max_provider_calls por usuario/ventana
budget por búsqueda
timeout total y por candidato
concurrency limit
cache TTL por fecha/estancia
cancellation/abort policy
```

La clave de cache debe incluir la intención temporal completa, ocupación, moneda, condiciones relevantes, provider policy y versión de contrato. Una consulta exacta no debe devolver accidentalmente una respuesta flexible ni al revés.

Se recomienda:

1. intentar una capability declarada de búsqueda múltiple;
2. si no existe, usar fan-out acotado solo con flag/budget;
3. deduplicar candidatos semánticamente iguales;
4. cancelar llamadas restantes cuando se exceda coste/timeout;
5. devolver `partial` con candidatos y razones omitidas;
6. registrar contadores sin query privada ni payload raw.

Un cache hit antiguo no autoriza a llamar `live` a una alternativa. Freshness es por candidato/estancia, no por la ventana completa.

## 7. Contrato de respuesta

### 7.1. Envelope

```json
{
  "query": {
    "temporal_intent": {
      "mode": "shift_window",
      "nights": 3,
      "check_in_start": "2026-09-09",
      "check_in_end": "2026-09-11",
      "timezone": "Europe/Madrid"
    },
    "occupancy": {"rooms": [{"adults": 2, "children_ages": []}]}
  },
  "capabilities": {
    "mode": "limited",
    "calendar": "supported",
    "tracking_flexible_window": "unsupported"
  },
  "candidates": [
    {
      "check_in": "2026-09-09",
      "check_out": "2026-09-12",
      "nights": 3,
      "lowest_price": 420.0,
      "currency": "EUR",
      "price_semantics": "total",
      "freshness": "recent",
      "conditions_completeness": "partial",
      "provider": "mock",
      "outcome": "success"
    }
  ],
  "omitted_candidates": 2,
  "warnings": ["provider_limited", "conditions_partial"],
  "status": "partial"
}
```

### 7.2. Invariantes

- cada candidato contiene fechas concretas y noches;
- las fechas pertenecen a la intención solicitada;
- la ocupación es la misma o la diferencia está explicitada como unsupported/partial;
- precio, moneda, fees, provider, freshness y condiciones acompañan al candidato;
- `lowest_price` no significa mínimo global si hubo candidatos omitidos;
- `status=partial` y `warnings` son obligatorios cuando hubo provider/coste/cobertura limitada;
- no devolver `[]` como “no hay hoteles” si el provider falló o se canceló la expansión;
- un candidato no autoriza tracking flexible ni alerta sobre otra estancia.

### 7.3. Agrupación visual

La UI puede agrupar por:

- fecha de entrada;
- fin de semana/semana según locale;
- número de noches;
- hotel/oferta comparable.

No debe colapsar candidatos con distinta habitación, régimen, cancelación, moneda o semántica de fees bajo una sola tarjeta “mejor precio”.

## 8. Ranking y explicación

El ranking debe ser estable y explicable:

1. excluir candidatos inválidos o no comparables para la métrica solicitada;
2. separar exactos, alternativas y parciales;
3. respetar la preferencia del usuario: fechas más cercanas, menor total, menor noche o mejor condición;
4. aplicar freshness/confidence antes de llamar “mejor”;
5. desempatar por fecha, hotel canónico y fingerprint estable;
6. mostrar la razón: “3 noches desde el miércoles”, “2 días antes”, “precio por noche comparable”, etc.

Nunca mezclar en un mismo ranking:

- diferentes duraciones sin normalización visible;
- total conocido con total desconocido;
- provider error con sold out;
- fixture con precio observado real;
- ofertas no comparables por habitación, régimen o cancelación.

Los filtros exactos de H14 se aplican después de etiquetar la métrica; `max_price` debe aclarar si es total o por noche. La paginación/cursor de H15 debe incluir `temporal_intent_fingerprint`, `ranking_version` y policy de provider.

## 9. URL, privacidad y restauración

### Parámetros futuros permitidos

```text
in=2026-09-10
out=2026-09-13
date_mode=exact|shift_window|flexible_month|weekend_window|duration_window
flex_days=1
month=2026-09
nights=3
nights_min=2
nights_max=4
timezone=Europe/Madrid
max_candidates=5
```

No serializar parámetros vacíos ni combinaciones contradictorias. Los defaults no deben crear una ventana invisible.

No incluir en URL:

- user ID, email, tokens o API keys;
- target price, alert threshold, canal o regla privada;
- payload raw de provider;
- datos innecesarios de niños/huéspedes;
- IDs privados de tracking.

Una URL flexible debe ser reproducible, pero abrirla no debe disparar automáticamente un fan-out externo si la flag, budget, consentimiento o capability no lo permiten. La restauración debe mostrar la intención y pedir ejecutar cuando corresponda.

El cambio de intención cambia el fingerprint y no debe mezclar resultados de una ventana anterior. Back/forward debe cancelar requests obsoletos y evitar doble ejecución, siguiendo H13.

## 10. Tracking, alertas y búsquedas guardadas

### 10.1. Tracking exacto

H23/H29 siguen gobernando `HotelTrackedOffer`: una suscripción activa representa una estancia/oferta concreta. Desde un resultado flexible:

- CTA “Seguir esta oferta” solo aparece después de elegir un candidato exacto;
- se confirma hotel, fechas efectivas, noches, ocupación, condiciones, provider y precio;
- no se crea tracking con la ventana completa por defecto;
- un cambio posterior de fechas crea otra identidad/version según H29.

### 10.2. Ventana guardada

“Avísame si aparece algo en estas fechas flexibles” sería una suscripción distinta, más cercana a búsqueda guardada de H48. No se implementa ni se llama tracking de precio en H30. Si se diseña más adelante debe definir:

- qué candidatos y rango se vigilan;
- mínimo de noches/condiciones;
- canales/consentimiento H28;
- dedupe y cooldown H26;
- presupuesto de sweeps H09;
- expiración H29;
- disclosure de que puede cambiar la estancia, no solo el precio.

### 10.3. Alertas

Un evento para `check_in=2026-09-09` no puede disparar una alerta de tracking creado para `check_in=2026-09-10` salvo que una suscripción flexible explícita lo autorice. H26 debe recibir la identidad temporal efectiva, no solo hotel y precio.

## 11. Estados de producto

| Estado | Significado | Siguiente acción |
|---|---|---|
| `exact_success` | estancia exacta con resultados | revisar/seguir oferta |
| `flex_success` | candidatos suficientes y comparables | elegir fechas |
| `partial` | algunos candidatos omitidos o campos incompletos | ver advertencia/reintentar |
| `limited` | provider solo admite exact-date o pocos candidatos | elegir fechas exactas |
| `unsupported` | no existe capacidad para el modo | cambiar modo |
| `provider_error` | fallo de provider, no ausencia de hoteles | reintentar/usar exacto |
| `budget_exhausted` | se alcanzó límite de coste/llamadas | reducir ventana/candidatos |
| `empty` | ejecución válida sin candidatos elegibles | ampliar zona/fechas/condiciones |
| `cancelled` | request sustituida o cancelada | ejecutar nueva intención |
| `stale` | datos previos fuera de TTL | refrescar, no llamar live |

Cada estado debe conservar el formulario y ofrecer una acción. `provider_error`, `unsupported` y `empty` no comparten copy.

## 12. Migración y rollout

### H30-A — Contract types

- añadir tipos internos `TemporalIntent`, `CandidateStay`, `ProviderCapability` y `FlexibleSearchEnvelope`;
- normalizar legacy exact-date a `mode=exact`;
- validar combinaciones, timezone, noches y límites;
- crear fingerprints y contract tests sin habilitar provider.

### H30-B — Fixtures deterministas

- ampliar mock con candidatos de varias fechas, duraciones y condiciones;
- rotular cada fixture como demo/no-live;
- probar omisiones, errores, rate limits, partial y budget;
- no usar fixture para declarar cobertura comercial.

### H30-C — Frontend calendario

- selector exacto primero;
- toggle de flexibilidad con explicación de coste/semántica;
- calendario/matriz accesible solo cuando el envelope declara capability;
- mostrar fechas efectivas, noches, precio y freshness;
- conservar URL, back/forward, foco, mobile, ES/EN y reduced motion.

### H30-D — Provider canary

- medir una sola capability y mercado limitado;
- presupuesto por búsqueda y límites de concurrencia;
- comparar exact-date frente a candidatos flexibles;
- validar mapping, ocupación, fees, condiciones y deeplink;
- rollback a exact-date sin borrar cache ni historial.

### H30-E — Activación progresiva

Orden recomendado:

1. exact-date con envelope V2;
2. `shift_window` pequeño, noches fijas;
3. matriz/calendario de pocos candidatos;
4. `flexible_month` solo con cobertura y presupuesto;
5. `weekend_window`/duraciones variables después de evidencia;
6. búsqueda guardada flexible en H48, separada de tracking.

Cada paso requiere flag, métricas y kill switch. La ausencia de capability debe degradar a exact-date o explicar bloqueo, nunca ejecutar fan-out implícito.

## 13. Tests y gates

### Backend/provider

- exact-date mantiene contrato V1;
- `check_out > check_in` y noches son deterministas;
- cada modo genera solo candidatos dentro de su ventana;
- `shift_window` conserva noches;
- `duration_window` etiqueta cada duración y no mezcla totales sin normalizar;
- timezone del destino evita desplazamientos de fecha;
- occupancy rooms/adults/children se conserva o marca partial;
- provider unsupported/unknown no se trata como supported;
- provider error/429/timeout no se convierte en empty/sold_out;
- max candidates, timeout, budget y concurrency se respetan;
- cache exacta y flexible no colisionan;
- fingerprints separan intención, estancia efectiva y provider policy;
- resultado flexible devuelve `check_in`/`check_out` efectivos, noches, precio, moneda, condiciones y freshness;
- omitted candidates y warnings impiden reclamar mínimo global;
- cursor incluye intent/ranking/policy version;
- dos usuarios pueden compartir cache de consulta sin mezclar ownership.

### Frontend/E2E

- exact-date funciona sin activar flexibilidad;
- toggle flexible explica qué cambia y cuántas noches se conservan;
- calendario no muestra precios si capability está ausente;
- alternativas muestran fechas concretas y noches;
- total y por noche no se confunden;
- partial/limited/unsupported/provider error/empty tienen copy distinto;
- filtros y sort respetan la métrica elegida;
- seleccionar candidato exacto abre CTA de tracking con contexto completo;
- no se crea tracking de ventana por accidente;
- URL flexible restaura estado sin ejecutar fan-out doble;
- back/forward y refresh no mezclan resultados obsoletos;
- mobile, teclado, foco, lector de pantalla, dark/light, ES/EN y reduced motion pasan.

### Gate de aceptación H30

H30 podrá considerarse implementada cuando:

1. exact-date siga siendo estable y se normalice como `TemporalIntent=exact`;
2. cada modo flexible tenga semántica, límites, timezone y validación propia;
3. capabilities de provider sean declarativas y respetadas;
4. ninguna llamada flexible exceda budget, candidatos, timeout o rate limit;
5. cada resultado incluya fechas efectivas, noches, ocupación, precio, moneda, condiciones y freshness;
6. `partial`, `limited`, `unsupported`, `provider_error`, `budget_exhausted` y `empty` sean distinguibles;
7. ranking y filtros no mezclen estancias/duraciones/condiciones incompatibles;
8. cache, fingerprints, cursor y URL separen la intención flexible de la exacta;
9. una búsqueda flexible no cree tracking ambiguo: primero se elige una estancia exacta;
10. mock/fixtures estén rotulados y exista canary de provider real antes de publicitar cobertura;
11. rollback a exact-date sea posible mediante flag sin perder contexto;
12. browser, accesibilidad, i18n, privacidad y observabilidad tengan evidencia.

**Resultado contractual:** H30 queda definida. V1 continúa soportando búsquedas hoteleras exactas con `check_in`, `check_out` y `guests`; no existe todavía calendario flexible hotelero ni capacidad de provider validada para ventanas. La implementación V2, el canary y su evidencia quedan pendientes.
