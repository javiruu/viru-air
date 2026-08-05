# H25 — Freshness, confidence y recomendaciones de acción hoteleras

**Estado:** completa como contrato de calidad accionable; implementación backend/frontend, refresh seguro, i18n y QA pendientes  
**Fecha:** 2026-08-05  
**Área:** backend / frontend / producto / providers / accesibilidad / QA  
**Fuente de verdad:** sí para interpretar la recencia, procedencia, confianza y siguiente acción de una observación hotelera  
**Fase del roadmap:** H25  
**Depende de:** [H05 — freshness, procedencia y confidence](hoteles-freshness-provenance-confidence-h05.md), [H19 — precio total y fees](hoteles-price-total-fees-h19.md), [H21 — matriz de estados](../frontend/hoteles-state-matrix-h21.md), [H23 — tracking desde oferta real](hoteles-real-offer-tracking-h23.md), [H24 — histórico y curva](hoteles-price-history-curve-h24.md)  
**Relacionado con:** H06-H09 providers y sweeps, H10-H12 modelo/migración/API, H15-H18 resultados y detalle, H20 comparación, H26 alertas, H27 inbox, H29 lifecycle, H31-H34 UX/a11y/i18n, H36 rendimiento, H40 QA, H41 observabilidad

> H25 responde a “¿cuánto podemos confiar en este dato y qué hago ahora?”. No convierte un timestamp reciente en garantía de disponibilidad, ni una señal estadística corta en una predicción del precio futuro.

## 1. Decisión de alcance

H25 define:

1. freshness contextual de una observación hotelera;
2. procedencia y trazabilidad visibles sin exponer payloads sensibles;
3. confidence de observación y comparabilidad, separadas de identidad del hotel y geocoding;
4. elegibilidad para mostrar precio, comparar, actualizar `current_price` o disparar alertas;
5. recomendaciones de acción prudentes y explicables;
6. refresh manual seguro, cooldown, límites y estados de provider;
7. copy ES/EN, accesibilidad, telemetría y fallback cuando faltan datos;
8. compatibilidad V1 y envelope V2 aditivo.

H25 no implementa por sí misma nuevos campos, scheduler, adapters, alertas, inbox, delivery ni migración completa. H25 fija cómo deben interpretarse cuando H06-H12, H23-H24 y las fases frontend los incorporen.

## 2. Estado actual comprobable

### 2.1. Datos disponibles en V1

`HotelRateSnapshot`/`HotelRateOut` ofrecen actualmente:

```text
provider
provider_run_id
collected_at
availability_status
check_in/check_out
guests
room_label
meal_plan
cancellation_policy
currency
amount
deep_link
tracked_offer_id
```

La lectura honesta de estos campos es limitada:

- `collected_at` es el instante de persistencia/captura local; no demuestra el instante en que el provider comprobó la habitación;
- `provider` identifica un origen lógico, pero no prueba que el dato sea live, bookable o completo;
- `provider_run_id` aporta trazabilidad cuando existe, pero no resume éxito parcial ni calidad de cada rate;
- `availability_status=available` no vence el TTL de H05 ni confirma disponibilidad actual;
- `amount` no significa automáticamente total final según H19;
- `room_label`, régimen y cancelación pueden estar ausentes o ser texto libre;
- `mock`/fixtures son datos de demostración, nunca evidencia live;
- no existen todavía `observed_at`, `expires_at`, `freshness_status`, `provenance_kind`, `conditions_completeness`, `confidence_level`, `confidence_model_version`, `refresh_allowed_at` ni razón estructurada de exclusión.

### 2.2. Señal actual de frontend

`assessHotelSignal()` clasifica una señal de paridad según cantidad de rates y `HotelParityOut`:

```text
none     no hay rates
limited  falta señal, hay menos de dos providers o faltan métricas
scored   existe comparativa con mínimo, máximo y spread
```

Los labels `stable`, `tensioned` y `breach` describen diferencia entre providers, no freshness, confidence de observación ni recomendación de compra. El badge de provider/paridad no debe reinterpretarse como “precio confiable”.

`useHotelDetail()` carga detalle, rates y parity en paralelo. Si el endpoint de rates falla, coloca `[]`; H21/H25 exigen separar `error`, `empty`, `stale` y `partial` en la evolución del contrato para no transformar un fallo en ausencia de datos.

### 2.3. Promesas actuales que no están respaldadas

La interfaz no puede afirmar hoy, solo por tener un rate:

- “comprobado ahora”;
- “disponible ahora”;
- “precio fiable”;
- “mejor precio”;
- “mínimo histórico”;
- “seguimiento diario”;
- “reserva ahora”;
- “conviene esperar” como predicción estadística.

El copy actual que habla de revisar una señal “cada día” debe migrar a una formulación basada en la última comprobación real hasta que H09 demuestre scheduler y cobertura.

## 3. Vocabulario separado

H25 reutiliza y concreta H05. Nunca colapsar estas dimensiones en un único score o color.

### 3.1. `provenance_kind`

```text
provider_observed      respuesta de provider para la consulta
provider_revalidated   refresh dirigido de una oferta trackeada
cache_current          dato reutilizado dentro de TTL válido
historical_snapshot    observación presentada como histórico
derived                métrica calculada desde observaciones
fixture_demo           mock/fixture de desarrollo o demo
unknown                procedencia no demostrable
unavailable            no existe observación de precio válida
```

Reglas:

- `fixture_demo` no es live aunque su timestamp sea reciente;
- `cache_current` requiere timestamp, TTL y provider de origen visibles para el sistema;
- `derived` conserva referencias a la muestra, ventana y versión de cálculo;
- `historical_snapshot` no se usa para copy de precio actual;
- `unknown` no recibe una etiqueta optimista por defecto.

### 3.2. `freshness_status`

La freshness es relativa a contexto, provider y política vigente:

```text
fresh       dentro del umbral corto y con timestamp válido
recent      válido, pero fuera del umbral corto y dentro del TTL de uso
stale       supera el TTL operativo, aún sirve como contexto
expired     demasiado antiguo para decisión actual
historical  se presenta intencionadamente como histórico
unknown     timestamp o política no calculable
```

Defaults iniciales de H05 para discovery:

| Edad desde `observed_at` o fallback V1 `collected_at` | Estado base | Copy permitido |
|---|---|---|
| 0–30 min | `fresh` | “Comprobado hace menos de 30 min” |
| >30 min–6 h | `recent` | “Comprobado hoy a las …” |
| >6–24 h | `stale` | “Puede haber cambiado; revisar de nuevo” |
| >24 h | `expired` | “Precio histórico; necesita una nueva comprobación” |

Los TTL definitivos son configuración observable por provider y contexto, no constantes inventadas en frontend. Si no hay timestamp válido, el estado es `unknown`.

### 3.3. `confidence_level`

Es una evaluación explicable de la observación completa:

```text
high         procedencia, timestamp, estancia y condiciones suficientes
medium       útil, pero con cache, historial corto o limitación controlada
low          stale, parcial, provider degradado o dudas de comparabilidad
unavailable  no existe base suficiente para evaluar
```

No es:

- valoración del hotel;
- probabilidad de que el precio siga disponible;
- probabilidad de reserva;
- `confidence_score` de matching de hotel/provider;
- `confidence` de resolución geográfica;
- resultado de paridad entre providers.

### 3.4. `comparability_status`

```text
comparable          misma estancia/oferta y condiciones suficientes
legacy_comparison   clave V1 mínima, con dimensiones desconocidas
partial             se puede orientar, pero faltan condiciones
incompatible        no debe entrar en el mismo baseline o ranking
unknown              no se puede determinar
```

Una observación puede ser `fresh + partial`, o `recent + comparable`; freshness y comparabilidad no se sustituyen mutuamente.

## 4. Cálculo de freshness y confidence

### 4.1. Fuente temporal

Prioridad de timestamps objetivo:

1. `observed_at` producido por provider;
2. timestamp del request/response validado;
3. `collected_at` como fallback V1 etiquetado;
4. `unknown` si no hay valor plausible.

Un timestamp futuro, inválido o con timezone no resoluble no recibe `fresh`. Debe registrarse warning y quedar `unknown`.

`finished_at` de `HotelProviderRun` no sustituye al timestamp de cada rate. El momento de persistencia tampoco demuestra que el partner acabara de verificar la oferta.

### 4.2. Elegibilidad mínima

Para tratar una observación como actualizable o accionable debe cumplir:

1. estancia y ocupación compatibles;
2. moneda y semántica de importe compatibles;
3. provider/run trazables;
4. `availability_status` no sea `provider_error`, timeout, rate limit o `unknown` cuando se exige disponibilidad;
5. freshness no sea `expired` o `unknown` para una decisión actual;
6. condiciones suficientes según H19/H10;
7. provenance no sea `fixture_demo`;
8. la observación pertenezca a la oferta/serie correcta de H23-H24.

Una observación que falla una condición puede seguir visible como histórico o contexto, pero no debe alimentar el mismo baseline.

### 4.3. Modelo explicable objetivo

Cuando existan campos V2, el score interno puede componerse de:

```text
freshness_score       30 %
provenance_score      25 %
match_score           20 %
conditions_score      15 %
provider_health_score 10 %
```

```text
observation_score =
  0.30 * freshness_score
+ 0.25 * provenance_score
+ 0.20 * match_score
+ 0.15 * conditions_score
+ 0.10 * provider_health_score
```

El score no se muestra necesariamente como número. Si se persiste, debe incluir `confidence_model_version`, inputs resumidos y razón de degradación.

Hard caps:

- fixture/demo → máximo `low`;
- `expired` o freshness `unknown` → máximo `low` para decisión actual;
- provider error → `unavailable` para precio actual;
- condiciones desconocidas → máximo `low` para comparación;
- moneda o estancia incompatibles → `unavailable`;
- un único provider no impide mostrar un precio, pero impide afirmar paridad.

## 5. Recomendaciones de acción

### 5.1. Principio

H25 recomienda una **siguiente acción segura**, no una decisión financiera garantizada. La recomendación debe derivarse de evidencia de H24, freshness de H05, condiciones de H19 y estado de H21.

Valores objetivo:

```text
review_now          revisar/refrescar porque el dato es stale, parcial o cambió
keep_monitoring     seguir observando; evidencia insuficiente para otra acción
wait_for_signal     esperar una nueva observación cuando falta baseline o continuidad
insufficient_data   no hay base para orientar
open_partner        solo si deeplink, disclosure, freshness y condiciones lo permiten
```

`book_now` no es un valor permitido de H25 mientras Viru no tenga una garantía contractual de reserva y disponibilidad. Abrir partner (`open_partner`) no significa recomendar reservar.

### 5.2. Matriz determinista inicial

| Evidencia | Acción | Explicación mínima |
|---|---|---|
| sin observaciones o error de carga | `insufficient_data` | “No hay una observación comprobable” |
| provider error/timeout o freshness `unknown` | `review_now` o `insufficient_data` | “No se pudo comprobar; no significa agotado” |
| `expired` o `stale` con refresh permitido | `review_now` | “Puede haber cambiado; revisa de nuevo” |
| una observación, sin baseline comparable | `keep_monitoring` | “Hay poco histórico para valorar tendencia” |
| histórico corto/gapped y condiciones parciales | `keep_monitoring` | “Sigue observando; faltan datos comparables” |
| observación comparable, fresca, con deeplink seguro | `open_partner` como acción técnica | “Revisar oferta en el partner; el precio puede cambiar” |
| tendencia favorable pero muestra pequeña/gaps | `keep_monitoring` | “Señal favorable, todavía no concluyente” |
| provider cambiado o condiciones incompatibles | `review_now` | “La comparación anterior ya no es equivalente” |

La tabla es política inicial auditable. H41 puede recalibrar umbrales, pero debe versionar el cambio y mostrar qué segmentos se ven afectados.

### 5.3. Razones estructuradas

La API no debe enviar solo copy libre. La recomendación objetivo incluye:

```json
{
  "action": "keep_monitoring",
  "confidence": "medium",
  "reason_code": "short_history",
  "reason_params": {
    "eligible_observations": 2,
    "last_observed_at": "2026-08-05T10:00:00Z"
  },
  "evidence": {
    "freshness_status": "recent",
    "comparability_status": "comparable",
    "sample_size_eligible": 2,
    "baseline_snapshot_id": null,
    "policy_version": "hotel-action-v1"
  },
  "next_safe_action": "refresh_when_allowed"
}
```

`reason_code` debe ser allowlisted e i18n lo traduce. No incluir raw provider payload, secretos, emails ni URLs no validadas.

### 5.4. Prohibiciones

No recomendar `open_partner` si:

- no hay deeplink allowlisted;
- el precio está expired o es fixture;
- la estancia enviada no coincide;
- faltan disclosure o condiciones mínimas;
- el provider devolvió error;
- el dato es solo una agregación no vinculada a la oferta.

No usar frases como:

- “compra ahora”; 
- “este precio no volverá”; 
- “seguro que bajará”; 
- “es el mejor momento”; 
- “disponible garantizado”; 
- “precio final” si H19 no demuestra semántica total.

## 6. Refresh seguro y límites

### 6.1. Cuándo ofrecer refresh

El botón/acción de refresh solo aparece si:

- la consulta es reconstruible;
- el provider está habilitado y el alias es válido;
- no existe cooldown activo;
- el usuario tiene ownership cuando se trata de tracking privado;
- el coste/rate limit permite la llamada;
- no hay otra revalidación equivalente en curso.

La acción debe explicar si revalida provider, lee cache o simplemente vuelve a cargar la vista.

### 6.2. Contrato objetivo de refresh

```text
refresh_status: idle | allowed | in_flight | throttled | failed | completed
last_refresh_at
next_refresh_allowed_at
refresh_reason: stale | user_requested | provider_recovery | initial_load
provider_status: available | degraded | unavailable | unknown
```

Un refresh rechazado por cooldown devuelve estado accionable y, cuando sea seguro, `Retry-After`/`next_refresh_allowed_at`. No se reintenta en bucle desde frontend.

### 6.3. Resultado del refresh

- éxito con rate elegible → actualizar la vista y conservar el histórico;
- éxito parcial → mostrar datos válidos y warning;
- provider error → mantener último dato elegible, marcar `provider_error`, no poner cero ni `sold_out`;
- timeout/rate limit → `throttled` o `failed`, no ocultar contexto;
- respuesta incompatible → conservar baseline y registrar `incompatible_conditions`;
- respuesta fixture/mock → conservar `fixture_demo`, nunca promoverla a live.

El gap detectado en V1 donde `sweep_tracked_offers()` convierte una excepción del provider en `provider_rates=[]` y usa un snapshot general como fallback debe corregirse antes de considerar el refresh confiable. Un error dirigido no puede actualizar `current_price` con una observación no equivalente.

## 7. Contrato API objetivo y compatibilidad

### 7.1. V1

Durante la migración se mantienen `provider`, `provider_run_id`, `collected_at`, `availability_status`, `amount` y los endpoints existentes. Los clientes antiguos:

- no deben inferir freshness positiva si faltan bloques nuevos;
- no deben interpretar parity como confidence;
- no deben convertir `[]` de error en “sin observaciones” sin conocer el estado de la request;
- deben mostrar el fallback contextual de H21.

### 7.2. Envelope V2 aditivo

```json
{
  "freshness": {
    "status": "recent",
    "observed_at": "2026-08-05T10:00:00Z",
    "collected_at": "2026-08-05T10:00:02Z",
    "age_seconds": 420,
    "expires_at": "2026-08-05T16:00:00Z",
    "policy_version": "hotel-freshness-v1"
  },
  "provenance": {
    "kind": "provider_revalidated",
    "provider": "makcorps",
    "provider_run_id": "opaque-run-id"
  },
  "confidence": {
    "level": "medium",
    "score": null,
    "model_version": "hotel-observation-v1",
    "reasons": ["conditions_partial"]
  },
  "recommendation": {
    "action": "keep_monitoring",
    "reason_code": "short_history",
    "policy_version": "hotel-action-v1"
  },
  "refresh": {
    "status": "allowed",
    "next_refresh_allowed_at": null
  }
}
```

Los bloques son objetivo V2 y pueden ser `null`/ausentes durante transición. Ausencia significa `unknown`, no `fresh`, `high` ni `allowed`.

## 8. Frontend, copy e interacción

### 8.1. Jerarquía visible

Junto al precio o señal, la UI debe poder mostrar:

1. importe y moneda;
2. estancia resumida;
3. última comprobación con locale;
4. procedencia humana si aporta contexto;
5. estado de disponibilidad;
6. limitación de condiciones/fees;
7. recomendación y razón;
8. acción segura: revisar, seguir, reintentar o abrir partner con disclosure.

### 8.2. Estados visuales

No usar solo color. El texto, icono/aria-label y acción deben distinguir:

```text
fresh/recent
stale/expired
provider_error
partial/unknown
fixture_demo
high/medium/low/unavailable confidence
refresh allowed/throttled/failed
```

`stable` de paridad no equivale a `high confidence`; ambos pueden coexistir como señales separadas.

### 8.3. Copy mínimo ES/EN

| Código | ES | EN |
|---|---|---|
| `fresh` | “Comprobado recientemente” | “Checked recently” |
| `recent` | “Comprobado hoy a las …” | “Checked today at …” |
| `stale` | “Puede haber cambiado; revisar de nuevo” | “It may have changed; review again” |
| `expired` | “Precio histórico; necesita una nueva comprobación” | “Historical price; check again” |
| `provider_error` | “El proveedor no respondió; no significa que esté agotado” | “The provider did not respond; this does not mean sold out” |
| `insufficient_data` | “Aún no hay datos suficientes para orientar” | “There is not enough data to guide you yet” |
| `keep_monitoring` | “Sigue observando: el histórico aún es corto” | “Keep monitoring: the history is still short” |
| `review_now` | “Revisa de nuevo: el dato puede haber cambiado” | “Review again: the data may have changed” |
| `open_partner` | “Revisar oferta en el partner” | “Review offer on partner” |
| `fixture_demo` | “Datos de demostración; no representan disponibilidad real” | “Demo data; not real availability” |

El copy se genera desde `reason_code` y parámetros, no desde heurísticas de arrays vacíos.

## 9. Privacidad, caché y observabilidad

- El confidence de una oferta trackeada respeta ownership de `tracked_offer_id`.
- La cache compartida puede reutilizar observaciones anónimas/comparables, pero no thresholds, labels, recomendaciones privadas ni estado de usuario.
- Un agregado privado no se sirve como público solo porque el hotel coincida.
- Logs registran provider, run, freshness, outcome, reason code y latencia sin raw payload ni secretos.
- Métricas mínimas: porcentaje de resultados con freshness visible, stale/expired, provider error, refresh throttled, refresh success, confidence unavailable, recommendation acceptance y discrepancia al abrir partner.
- Las métricas de recomendación no deben interpretarse como prueba de que la acción fue correcta; miden utilidad y posibles sesgos.

## 10. Handoffs

| Fase | Entrega H25 |
|---|---|
| H06-H09 | timestamps del provider, health, scheduler, cooldown, outcome parcial y refresh dirigido |
| H10-H12 | campos V2, fingerprints, doble lectura/escritura y compatibilidad |
| H19 | semántica de total, fees y elegibilidad de importe |
| H23-H24 | oferta reconstruible, baseline, muestra, gaps y segments |
| H26 | alertas solo sobre observaciones y baselines elegibles |
| H27 | eventos con ownership y reason code inequívocos |
| H29 | lifecycle, pausa, expiración, nueva identidad y retención |
| H31-H34 | badges, copy, recomendaciones, responsive, i18n y a11y |
| H36 | cache, coste, cooldown y límites de refresh |
| H40 | pruebas contract, unitarias, integración, visuales y accesibilidad |
| H41 | métricas de freshness, confidence, recomendaciones, provider degradation y refresh |

## 11. Tests y evidencias requeridos

### Backend/unitarios

- freshness en límites 30 min, 6 h, 24 h y timezone;
- timestamp nulo, futuro, inválido y fallback `collected_at` etiquetado;
- fixture/mock nunca `fresh` de producto;
- provider error no es `sold_out`, cero ni observación elegible;
- confidence separado de parity, identity matching y geocoder;
- hard caps y razones deterministas;
- recomendación con 0, 1, 2, 3+ observaciones, gaps y condiciones parciales;
- baseline incompatible no produce `vs_initial`/`vs_previous`;
- refresh cooldown, provider degraded, retry-after y no-loop;
- fallback dirigido no usa snapshot general tras excepción del provider;
- recomendación `open_partner` bloqueada sin deeplink/disclosure/condiciones;
- payload V1 y envelope V2 aditivo.

### Frontend/a11y

- `empty`, `error`, `stale`, `expired`, `partial`, `unknown` no comparten copy engañoso;
- parity `stable` no se anuncia como confidence `high`;
- última comprobación y procedencia son legibles en locale;
- keyboard/screen reader recibe estado, razón y acción;
- color no es la única señal;
- `prefers-reduced-motion` respeta refresh y transición;
- botón refresh deshabilita durante in-flight y anuncia cooldown;
- mobile mantiene contexto y no crea acciones imposibles;
- ES/EN cubren códigos allowlisted.

### Producto/operación

- revisión humana de cada recommendation reason code;
- evidencia de TTL y scheduler real por provider;
- dashboards separan datos demo, cache, provider, error y observación válida;
- runbook define cuándo refrescar, cuándo esperar y cuándo no mostrar precio actual;
- experimento de recomendación no usa “book now” como claim sin aprobación legal/producto.

## 12. Gate H25

H25 puede considerarse implementada cuando:

- freshness, provenance, confidence, comparability y parity están separadas en API y UI;
- el timestamp y TTL son explícitos y no se confunden con disponibilidad;
- las recomendaciones son códigos estructurados, explicables y limitadas por evidencia;
- no existe `book_now`/garantía implícita sin contrato aprobado;
- refresh tiene ownership, cooldown, coste, estado y fallback seguro;
- provider error no actualiza precio ni se presenta como sold out;
- mock/cache/histórico aparecen con procedencia correcta;
- estados error/empty/stale/partial/expired no se mezclan;
- copy ES/EN, a11y, reduced motion y tabla/resumen cumplen H21/H31-H34;
- observabilidad mide calidad y resultados sin exponer datos privados;
- V1 sigue funcionando mientras H10-H12 y H25 evolucionan aditivamente.

**Resultado H25:** contrato aprobado. La aplicación V1 actual solo ofrece timestamp, provider y señal de paridad limitada/scored; no se declara freshness accionable, confidence de observación, refresh seguro ni recomendaciones implementadas hasta cerrar H06-H12, H23-H24, H31-H36 y H40-H41.
