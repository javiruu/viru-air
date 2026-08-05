# H24 — Histórico, agregados y curva de precio hotelera

**Estado:** completa como contrato de histórico y presentación; implementación backend/frontend, agregados V2, i18n y QA pendientes  
**Fecha:** 2026-08-05  
**Área:** backend / frontend / producto / accesibilidad / QA  
**Fuente de verdad:** sí para la semántica del histórico de una oferta trackeada, sus agregados, sus gaps y su representación accesible  
**Fase del roadmap:** H24  
**Depende de:** [H05 — freshness, procedencia y confidence](hoteles-freshness-provenance-confidence-h05.md), [H10 — estancia y oferta canónicas](hoteles-stay-offer-model-h10.md), [H19 — precio total y fees](hoteles-price-total-fees-h19.md), [H21 — matriz de estados](../frontend/hoteles-state-matrix-h21.md), [H22 — favorito frente a tracking](hoteles-favorite-vs-tracking-h22.md), [H23 — tracking desde oferta real](hoteles-real-offer-tracking-h23.md)  
**Relacionado con:** H11 migración, H12 API, H15 resultados, H20 habitaciones/régimen, H25 freshness/confidence, H26 alertas, H27 inbox, H29 lifecycle, H31-H34 UX/a11y/i18n, H36 rendimiento, H40 QA, H41 observabilidad

> H24 convierte una colección de snapshots en una respuesta comprensible a “¿cómo ha evolucionado esta oferta y qué significa hoy?”. No convierte un gráfico bonito en evidencia de disponibilidad, ni mezcla estancias o condiciones distintas para fabricar una curva favorable.

## 1. Decisión de alcance

H24 define el contrato para:

1. consultar el histórico privado de una oferta trackeada;
2. ordenar y presentar snapshots con fecha, precio, provider, condiciones y estado;
3. decidir qué observaciones son comparables y elegibles;
4. calcular mínimo, máximo, promedio, mediana y variaciones solo cuando la muestra lo permite;
5. agregar por día sin borrar cambios importantes ni ocultar gaps;
6. representar cambios de provider, disponibilidad, freshness y errores;
7. ofrecer una curva visual y un resumen/tabla equivalente para teclado y lectores de pantalla;
8. explicar historiales cortos, vacíos, parciales, stale, expirados o no comparables;
9. conservar ownership y privacidad de la suscripción;
10. dejar handoffs claros a H25, H26, H27 y H29.

H24 **no** implementa por sí misma nuevas tablas, el scheduler, la revalidación de providers, las alertas, el inbox, el delivery externo ni la migración completa a `HotelOffer`/`StayQuery` V2.

## 2. Estado actual comprobable

### 2.1. Backend V1

Existe `GET /hotels/tracked-offers/{tracked_offer_id}/snapshots`, que:

- exige usuario autenticado;
- resuelve la oferta mediante `get_tracked_offer_or_404`;
- rechaza acceso de otro usuario;
- devuelve una lista de `HotelRateOut` asociada a `tracked_offer_id`;
- ordena por `collected_at` descendente y después por ID;
- no devuelve agregados, paginación, cursor, estado de comparabilidad ni razones de exclusión.

`HotelRateSnapshot` contiene actualmente:

```text
id
hotel_id
tracked_offer_id
provider_run_id
provider
check_in
check_out
guests
room_label
meal_plan
cancellation_policy
currency
amount
availability_status
deep_link
collected_at
```

Estos campos son una base de compatibilidad, pero no prueban que:

- `amount` sea total final o incluya todos los fees;
- dos snapshots sean la misma habitación/oferta;
- `collected_at` sea el instante de observación del provider;
- el snapshot esté fresco o sea reservable;
- `available` siga siendo válido hoy;
- exista una secuencia diaria sin huecos;
- el provider haya respondido en cada sweep.

El modelo actual no tiene todavía `observed_at`, `offer_fingerprint`, `comparability_key`, `freshness_status`, `provenance_kind`, `conditions_completeness`, `confidence_level`, `excluded_reason` ni agregados persistidos. H24 los trata como contrato objetivo, no como capacidades V1 existentes. Además, `sweep_tracked_offers()` puede capturar una excepción del provider como `provider_rates=[]` y caer al snapshot general no enlazado; ese fallback puede crear un snapshot del tracking y actualizar `current_price` aunque el provider dirigido haya fallado. Es un gap V1 bloqueante: H24/H19/H23 exigen conservar el error y no convertirlo en observación elegible.

### 2.2. Frontend V1

La vista actual tiene dos superficies relacionadas, pero no equivalentes:

- `HotelPriceTimeline` recibe `detail.rates`, es decir, rates generales del hotel seleccionado; ordena por `collected_at` y muestra una lista de provider, fecha, importe y habitación. No es todavía el histórico privado de una oferta concreta.
- `HotelTrackedOfferSnapshots` carga el endpoint privado al expandir un seguimiento y muestra una lista de importe, provider, disponibilidad y fecha. Actualmente convierte un error de carga en `snapshots=[]`, por lo que puede presentar un fallo HTTP como “aún no hay registros”. H24 exige separar `empty` de `error`.

Actualmente no hay una curva matemática, SVG con puntos, mediana/promedio, variación contra baseline, agrupación diaria, detección visible de gaps ni tabla equivalente específica del histórico. El texto “registros diarios” de la i18n actual tampoco está respaldado por un scheduler diario garantizado. El contrato H24 no debe describir esas funciones como implementadas.

### 2.3. Consecuencia de producto

La UI actual puede ser útil como lista de observaciones, pero no permite afirmar de forma completa:

- “este es el mínimo histórico”;
- “el precio bajó X %”;
- “la oferta está más barata que antes”;
- “se revisó cada día”;
- “el proveedor mantuvo la misma habitación”;
- “no hubo disponibilidad durante el hueco”.

Hasta implementar H24/H25, el copy debe preferir “observaciones registradas” e indicar la fecha concreta.

## 3. Unidad de histórico e identidad

### 3.1. El histórico pertenece a una suscripción/oferta concreta

La unidad primaria es:

```text
tracked_offer_id
+ offer/stay identity
+ provider scope
+ comparable conditions
```

Un histórico de `hotel_id` abstracto no es suficiente para una curva de precio. No se mezclan automáticamente:

- fechas diferentes;
- ocupaciones diferentes;
- habitaciones diferentes;
- regímenes diferentes;
- políticas de cancelación diferentes;
- monedas o semánticas de importe incompatibles;
- providers distintos cuando el provider forma parte de la oferta seguida.

### 3.2. Clave de comparabilidad objetivo

La migración H10/H11 debe conducir a una clave equivalente a:

```text
comparability_key = hash(
  canonical_hotel_id
  + check_in + check_out
  + canonical_occupancy
  + room_signature
  + meal_plan_normalized
  + cancellation_signature
  + currency_or_conversion_context
  + fee_semantics
  + provider_scope
)
```

La clave no contiene `user_id`, email, label, threshold, canal ni timestamp de captura.

En V1, la aproximación mínima es:

```text
hotel_id + check_in + check_out + guests + currency + provider
```

Debe etiquetarse como `legacy_comparison`, porque no demuestra equivalencia de habitación, régimen, cancelación ni fees. Si alguna dimensión crítica es desconocida, los snapshots pueden aparecer como “relacionados”, pero no como la misma oferta comparable.

### 3.3. Inmutabilidad semántica

Si cambian fechas, huéspedes, habitación, régimen, cancelación, moneda o provider scope, no se reescribe silenciosamente la curva existente. El sistema debe:

1. crear una nueva identidad de oferta/consulta; o
2. marcar el histórico anterior como cerrado y comenzar una nueva serie; o
3. mostrar una separación visible entre segmentos.

H29 gobierna la pausa, edición, expiración y borrado de la suscripción. H24 solo define cómo evitar que una mutación cambie retrospectivamente el significado de la curva.

## 4. Elegibilidad de snapshots

### 4.1. Snapshot apto para una curva de precio

Un snapshot puede entrar en métricas de precio si, como mínimo:

- pertenece a la oferta trackeada consultada;
- tiene importe positivo y moneda válida;
- coincide con la identidad de estancia vigente o está etiquetado con la misma clave legacy;
- no representa `provider_error`, timeout, rate limit ni ausencia de resultado;
- su semántica de importe es compatible con la métrica solicitada;
- tiene timestamp válido, usando `collected_at` como fallback V1;
- no es un fixture de demo en una superficie de producto;
- conserva provider y trazabilidad al run cuando estén disponibles.

### 4.2. Snapshot visible pero no elegible

Los datos no elegibles no se borran ni se convierten en cero. Pueden mostrarse en el detalle o tabla con una razón:

```text
provider_error
unavailable
sold_out_without_price
incompatible_stay
incompatible_conditions
currency_mismatch
unknown_price_semantics
stale_for_current_decision
fixture_demo
invalid_timestamp
```

Un snapshot sin precio puede aportar un evento de disponibilidad, pero no entra en mínimo, máximo, media, mediana ni variación monetaria.

### 4.3. Provider error

Un error de provider no equivale a precio cero, sold out ni caída de precio. H24 exige que:

- se conserve el gap o evento de error si existe evidencia del run;
- la curva no interpole silenciosamente un valor;
- la UI explique que no se pudo comprobar ese periodo;
- `current_price` no se actualice por un error, según H19/H23;
- una alerta no use ese registro como baseline o nueva observación elegible.

## 5. Modelo de serie y gaps

### 5.1. Orden canónico

La API puede conservar el orden V1 descendente por compatibilidad. Para calcular y representar una curva, el cliente o backend debe construir una serie ascendente por `observed_at` o, en V1, `collected_at`, con desempate estable por ID.

Nunca ordenar fechas como texto sin interpretar timezone/fecha. Si dos snapshots comparten instante, se conserva el orden determinista y se decide explícitamente si son duplicados de ingestión o dos observaciones.

### 5.2. Qué es un gap

Un gap es un intervalo donde no hay una observación válida para la política esperada de comprobación. H24 no afirma periodicidad solo porque la UI diga “diario”.

Tipos mínimos:

```text
no_observation       no hubo snapshot elegible
provider_error       el provider falló o no pudo validarse
out_of_scope         la oferta ya no estaba activa o la estancia expiró
incompatible_data    hubo datos, pero no corresponden a la serie
unknown              no hay evidencia suficiente para clasificar
```

El gap se calcula solo si existe una política esperada de frecuencia proveniente de H09/H25. Si no existe scheduler garantizado —como ocurre en la base V1 actual—, se presenta “sin observación registrada entre … y …”, no “el precio no cambió” ni “registro diario”.

### 5.3. No interpolación engañosa

La línea visual puede mostrar un hueco, punto discontinuo o segmento punteado. Nunca se dibuja una línea continua que sugiera un precio observado durante un periodo sin datos. Si el producto permite una interpolación puramente visual, debe:

- estar desactivada por defecto;
- etiquetarse como estimación;
- quedar fuera de todas las métricas y alertas;
- anunciarse al lector de pantalla y a la tabla.

## 6. Agregados y métricas

### 6.1. Muestra elegible

Cada métrica debe declarar:

```text
sample_size_total
sample_size_eligible
excluded_count
metric_window
comparability_key/version
currency
price_semantics
```

`sample_size_total` cuenta observaciones recibidas; `sample_size_eligible` cuenta las que realmente entran en la métrica. No ocultar exclusiones detrás de una cifra redondeada.

### 6.2. Mínimo y máximo

`min_price` y `max_price` se calculan sobre importes elegibles, comparables, positivos y de la misma moneda/semántica.

Reglas:

- no calcular si no hay observaciones elegibles;
- no mezclar `amount_base` con `amount_total`;
- no afirmar “mínimo histórico” si la ventana o la serie está incompleta sin indicarlo;
- si hay providers distintos, incluirlos solo cuando el `provider_scope` y condiciones lo permitan;
- conservar snapshot/fecha/provider que originó el mínimo y máximo.

Copy válido:

- “Mínimo observado en este histórico”;
- “Máximo observado en las observaciones disponibles”.

Copy condicionado:

- “mínimo de toda la estancia” solo si la serie y la ventana están completas bajo una política conocida.

### 6.3. Promedio y mediana

El promedio es la media aritmética de la muestra elegible. La mediana es el valor central tras ordenar importes elegibles; con muestra par se usa la media de los dos centrales con la precisión de backend.

Defaults de presentación:

- `n=0`: no disponible;
- `n=1`: se puede mostrar el valor como única observación, pero no presentarlo como tendencia;
- `n=2`: se puede mostrar dispersión descriptiva, no una señal fuerte;
- `n>=3`: habilitar promedio/mediana si las observaciones son comparables;
- la mediana debe preferirse como centro resistente a outliers cuando el copy diga “precio habitual”.

Estos umbrales son contrato inicial y deben versionarse si H25/H41 los recalibran.

### 6.4. Variaciones

Las variaciones permitidas son:

```text
vs_initial       frente al snapshot inicial elegible de la misma identidad
vs_previous      frente al snapshot elegible anterior
vs_minimum       frente al mínimo elegible de la ventana/histórico
```

Fórmula de porcentaje, cuando el baseline es positivo y comparable:

```text
percent_change = ((current - baseline) / baseline) * 100
```

No calcular variación si:

- falta baseline;
- el baseline es cero, negativo o de otra moneda;
- cambió la semántica base/total;
- cambiaron estancia o condiciones relevantes;
- el provider cambió sin una política que lo permita;
- una de las observaciones es error, fixture o no elegible.

Toda variación debe conservar `baseline_snapshot_id`, `current_snapshot_id`, razón de elegibilidad y versión de cálculo.

### 6.5. Agregación diaria

La agregación diaria reduce ruido de múltiples capturas, pero no debe ocultar cambios de provider o disponibilidad.

Cada bucket diario conserva:

```text
bucket_date en timezone de producto/destino definida
first_observed_at
last_observed_at
eligible_count
total_count
min_price
max_price
median_price
average_price
representative_snapshot_id
providers_seen
availability_states
has_gap_or_error
```

La selección de `representative_snapshot_id` debe ser determinista y documentada. Default recomendado:

1. último snapshot elegible del día;
2. si hay empate, el de mayor calidad/freshness;
3. si persiste el empate, ID estable.

La UI debe poder expandir un día para ver múltiples observaciones cuando cambien precio, provider, condiciones o disponibilidad. El agregado no reemplaza al histórico raw.

## 7. Cambios de provider y condiciones

### 7.1. Provider cambiado

Un provider distinto no se trata automáticamente como subida o bajada de la misma oferta. La serie debe conservar una marca `provider_changed` y separar segmentos cuando el provider forma parte de la identidad.

Si la política `provider_scope=any_eligible` permite comparar providers, la UI debe mostrarlo como “observaciones de distintos proveedores” y aplicar la comparabilidad de H10/H19. Sin esa política, no calcular `vs_previous` atravesando el cambio.

### 7.2. Condiciones cambiadas

Cambios en room, meal plan, cancelación, fees, ocupación o moneda deben producir:

- nueva segmentación de serie;
- estado `incompatible_conditions`; o
- comparación solo si existe normalización explícita y auditable.

No usar texto igual como prueba suficiente de misma habitación. No asumir que `room_label=null` equivale a habitación estándar.

### 7.3. Disponibilidad

`available`, `limited`, `sold_out`, `unknown` y `provider_error` se visualizan como estados, no como precios. Un día puede tener precio disponible y después sold out; el histórico debe mostrar ambas señales sin convertir sold out en cero.

## 8. Contrato API objetivo

### 8.1. Compatibilidad V1

`GET /tracked-offers/{id}/snapshots` puede seguir devolviendo `list[HotelRateOut]` durante la migración. Los clientes antiguos deben continuar funcionando y no deben inferir agregados por contar filas sin evaluar comparabilidad.

### 8.2. Respuesta V2 propuesta

La evolución objetivo es un envelope aditivo similar a:

```json
{
  "tracked_offer_id": "opaque-id",
  "series": {
    "identity": {
      "comparability_key": "opaque-key",
      "status": "legacy_comparison",
      "check_in": "2026-09-10",
      "check_out": "2026-09-13",
      "guests": 2,
      "currency": "EUR",
      "provider_scope": "mock"
    },
    "points": [
      {
        "snapshot_id": "opaque-snapshot",
        "observed_at": "2026-08-05T10:00:00Z",
        "amount": 420.0,
        "currency": "EUR",
        "price_semantics": "unknown",
        "provider": "mock",
        "availability_status": "available",
        "eligibility": "eligible",
        "conditions_completeness": "partial"
      }
    ],
    "gaps": [],
    "segments": []
  },
  "aggregates": {
    "sample_size_total": 1,
    "sample_size_eligible": 1,
    "min_price": 420.0,
    "max_price": 420.0,
    "median_price": null,
    "average_price": null,
    "currency": "EUR",
    "price_semantics": "unknown"
  },
  "comparisons": {
    "vs_initial": null,
    "vs_previous": null,
    "vs_minimum": null
  },
  "freshness": {
    "status": "unknown",
    "policy_version": null
  }
}
```

Los nombres son contrato objetivo, no campos actualmente disponibles. La respuesta debe:

- omitir o devolver `null` cuando una métrica no sea calculable;
- no serializar cero como sustituto de desconocido;
- incluir razones de exclusión de forma agregada sin filtrar payloads crudos;
- mantener IDs opacos y ownership por `tracked_offer_id`;
- evitar devolver datos de otra suscripción aunque el hotel sea el mismo.

### 8.3. Paginación y ventana

H24 debe soportar una ventana explícita (`from`, `to`) y un límite razonable. Para históricos largos, H36/H41 deben decidir cursor, agregación por rango y límites de coste. Un endpoint que devuelve toda la serie sin límite no debe convertirse en el contrato permanente.

## 9. Presentación frontend y accesibilidad

### 9.1. Curva visual

La curva debe comunicar, como mínimo:

- eje temporal con locale;
- eje monetario con moneda y semántica;
- puntos observados, no una decoración continua;
- estado de disponibilidad y provider mediante texto/tooltip accesible, no solo color;
- gaps como discontinuidad visible;
- cambios de provider/condiciones como separadores o anotaciones;
- indicador de última observación y freshness;
- leyenda que explique qué está incluido en las métricas.

No usar un SVG o canvas sin alternativa textual. No usar verde para sugerir ahorro si la comparación no es elegible.

### 9.2. Tabla/resumen equivalente

Toda gráfica debe tener una alternativa accesible en DOM:

- tabla o lista de observaciones ordenada;
- fecha/hora, importe, moneda, provider, estado y elegibilidad;
- condiciones relevantes cuando estén disponibles;
- indicación de gap y razón;
- resumen de agregados y muestra;
- relación semántica mediante `aria-describedby` o estructura equivalente.

La alternativa no se oculta solo para usuarios de lector de pantalla; puede abrirse con “Ver datos” y sirve para inspección, móvil y exportación futura.

### 9.3. Interacción

Requisitos mínimos:

- navegación por teclado de puntos/segmentos;
- foco visible y no dependiente del color;
- tooltip que no sea la única fuente de información;
- texto de estado anunciado cuando cambia la ventana o la carga;
- respetar `prefers-reduced-motion`;
- no bloquear scroll horizontal del móvil por una gráfica;
- targets táctiles de al menos 48 px según el contrato móvil del proyecto;
- loading, error, empty, partial y stale con copy i18n ES/EN.

### 9.4. Copy de estados

Semántica mínima, siempre pasada por i18n:

- sin datos: “Aún no hay observaciones para esta oferta”;
- una observación: “Solo hay una observación; todavía no hay tendencia”;
- histórico corto: “Histórico corto: interpreta la variación con cautela”;
- gap: “No hay una comprobación registrada en este intervalo”;
- provider error: “El proveedor no respondió; no significa que se agotara”;
- stale: “La última observación puede haber cambiado”;
- condiciones parciales: “Faltan condiciones para comparar del todo”;
- cambio de provider: “Cambió el proveedor observado; la comparación puede no ser equivalente”;
- demo: “Datos de demostración; no representan disponibilidad real”.

Prohibido sin evidencia suficiente:

- “precio garantizado”;
- “mínimo histórico” cuando la ventana tiene gaps no explicados;
- “bajó X %” con baseline incompatible;
- “seguimiento diario” sin scheduler probado;
- “disponible ahora” desde un snapshot viejo o fixture.

## 10. Estados de la superficie

H24 combina la matriz H21 con la semántica del histórico:

| Estado | Significado | Acción segura |
|---|---|---|
| `loading` | se está leyendo la serie privada | mantener contexto y permitir cancelar/reintentar |
| `empty` | no hay snapshots para esa oferta | explicar que aún no hay observaciones; no mostrar cero |
| `short_history` | hay una o dos observaciones | mostrar puntos y limitar claims de tendencia |
| `ready` | hay muestra elegible suficiente | mostrar curva, tabla y agregados aplicables |
| `partial` | parte de los datos es incompatible/excluida | mostrar válidos y razones resumidas |
| `gapped` | faltan observaciones según política conocida | discontinuidad + intervalo + reintento si aplica |
| `stale` | última observación supera TTL contextual | advertencia y acción de refresco, sin borrar histórico |
| `error` | falló la carga del endpoint | conservar la oferta y ofrecer reintento; no convertir en empty |
| `expired` | la estancia ya no es actual | conservar histórico como histórico y desactivar claims actuales |

Los estados pueden coexistir: por ejemplo `ready + gapped + stale`.

## 11. Privacidad, ownership y caché

- Solo el propietario de `tracked_offer_id` puede consultar su histórico privado.
- El endpoint no se autoriza por `hotel_id`.
- No compartir snapshots privados en cache público ni SSR reutilizable entre usuarios.
- Si se cachean agregados, la clave debe incluir identidad privada o el agregado debe derivarse de datos compartidos sin `user_id`; nunca mezclar labels, targets o reglas.
- Un ID opaco no sustituye la comprobación de ownership.
- La tabla y curva no deben exponer raw payload, API keys, emails ni tokens de provider.
- Exportaciones futuras deben respetar borrado, retención y lifecycle de H29.

## 12. Handoffs

| Fase | Entrega H24 |
|---|---|
| H11 | columnas/tablas para fingerprints, observed_at, elegibilidad y agregados; backfill sin inventar datos |
| H12 | envelope V2, ventana, paginación y compatibilidad de schemas |
| H20 | normalización de habitación, régimen y cancelación para segmentar series |
| H25 | TTL, freshness, confidence y política de observación válida |
| H26 | alertas solo sobre puntos y baselines elegibles; dedupe de cambios |
| H27 | eventos de histórico con ownership inequívoco y deep links privados |
| H29 | cierre, pausa, expiración, nueva identidad al editar y borrado/retención |
| H31-H34 | UX, visualización, i18n, responsive y accesibilidad |
| H36 | límites de ventana, downsampling y coste de series largas |
| H40 | pruebas unitarias, integración, contract, a11y y visuales |
| H41 | métricas de muestras, exclusiones, gaps, latencia y provider degradation |

## 13. Tests y evidencias requeridos

### Backend/unitarios

- orden cronológico estable y fechas límite;
- mínimo, máximo, media y mediana con `n=0,1,2,3` y muestras pares;
- moneda y semántica incompatibles quedan fuera;
- baseline ausente, cero, negativo o incompatible no produce porcentaje;
- provider error no crea punto elegible ni actualiza `current_price`;
- sold out no se convierte en importe cero;
- cambios de provider y condiciones separan segmentos;
- gaps no se rellenan silenciosamente;
- agregación diaria conserva `total_count`, `eligible_count`, providers y estados;
- ownership impide leer el histórico de otro usuario;
- ventana/límite no filtra snapshots de otra oferta.

### Integración/API

- `GET /tracked-offers/{id}/snapshots` mantiene compatibilidad V1;
- endpoint privado devuelve 403/404 según política para otro usuario/ID;
- envelope V2 no filtra datos privados ni raw payload;
- error de provider se representa como estado, no como lista vacía engañosa;
- snapshot inicial de H23 queda en la serie con timestamp y contexto disponible;
- borrado/pausa de H29 aplica la política de retención correspondiente.

### Frontend/a11y

- estados empty, short, ready, partial, gapped, stale, expired y error tienen copy ES/EN;
- la tabla equivalente contiene la misma información que la curva;
- lector de pantalla recibe importe, fecha, provider, estado y gap;
- teclado puede alcanzar cada punto o el resumen equivalente;
- `prefers-reduced-motion` evita animaciones esenciales;
- móvil no pierde la tabla ni crea scroll horizontal accidental;
- no se usan solo colores para ahorro, error, provider o disponibilidad;
- no se muestra “mínimo histórico”, “bajó” o “diario” sin elegibilidad y evidencia.

## 14. Gate H24

H24 puede considerarse implementada cuando:

- el histórico está ligado a una identidad de estancia/oferta y no a un hotel abstracto;
- snapshots comparables y no comparables se distinguen;
- mínimo, máximo, mediana, promedio y variaciones tienen muestra, ventana y semántica explícitas;
- la agregación diaria conserva gaps, providers, condiciones y estados;
- provider error, sold out y ausencia de snapshot no se convierten en precio cero;
- no se interpola una observación inexistente como si fuera real;
- la curva tiene tabla/resumen accesible equivalente;
- loading, empty, short, partial, stale, gapped, expired y error tienen recuperación segura;
- ownership y caché privado están cubiertos por tests;
- V1 sigue funcionando mientras V2 migra de forma aditiva;
- observabilidad mide exclusiones, gaps, muestras, latencia y degradación de provider.

**Resultado H24:** contrato aprobado. La implementación V1 actual sigue siendo una lista de snapshots y no se declara curva histórica implementada hasta cerrar H11/H12/H25/H31-H34/H36/H40.
