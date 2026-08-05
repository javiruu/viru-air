# H07 — Auditoría Makcorps y decisión de continuidad

**Estado:** completo como auditoría y decisión condicionada — implementación y canary pendientes  
**Fecha:** 2026-08-04  
**Área:** backend / producto / providers / costes / operación  
**Fuente de verdad:** sí para la decisión sobre el uso de Makcorps en `/hoteles` hasta que una auditoría posterior la sustituya con nueva evidencia.

**Depende de:** [H05 — procedencia, freshness y confidence](hoteles-freshness-provenance-confidence-h05.md), [H06 — contrato provider-neutral](hoteles-provider-neutral-contract-h06.md)  
**Relacionado con:** H08 providers adicionales, H09 sweeps, H10 modelo de estancia/oferta, H15 resultados, H19 fees, H35 legal/deeplinks, H37 coste/rendimiento, H41 observabilidad.

---

## 1. Decisión ejecutiva

### Decisión: **CONTINUAR LIMITADO / NO APROBAR COMO PROVIDER PRINCIPAL**

Makcorps se conserva como adapter opcional y objeto de evaluación, pero **no queda aprobado** como:

- fuente principal de discovery para usuarios;
- base de una promesa de tracking diario/horario;
- fuente de disponibilidad actual confirmada;
- fallback equivalente a un proveedor con ocupación, habitaciones, niños, fees y condiciones completas;
- proveedor de deeplinks seguros o atribución afiliada.

Puede avanzar en un modo **experimental y controlado** únicamente cuando se cumplan los bloqueos de la sección 12. Hasta entonces:

- el mock sigue siendo válido para fixtures, desarrollo y QA, siempre rotulado como `fixture_demo`;
- el `.env.example` mantiene Makcorps desactivado por defecto mediante las flags existentes; cada entorno real debe auditar su configuración efectiva;
- no se rediseña `/hoteles` alrededor de su cobertura publicitaria;
- no se presenta un `429`, timeout o respuesta vacía como “sin disponibilidad”;
- no se declara que el tracking real está listo para lanzamiento.

Esta decisión no dice que Makcorps sea inútil. Dice que **la evidencia disponible no permite prometer estabilidad, cobertura ni comparabilidad suficiente para el producto objetivo**.

---

## 2. Niveles de evidencia

Para evitar mezclar marketing, código y pruebas reales, H07 clasifica cada afirmación así:

| Nivel | Significado | Puede sostener una promesa de producto |
|---|---|---:|
| `A — oficial verificable` | documentación pública oficial accesible y fechada | solo la capacidad descrita, no SLA/cobertura operativa implícita |
| `B — código local` | comportamiento comprobable en el adapter/tests del repositorio | sí para el código local, no para el provider externo real |
| `C — runtime histórico` | ejecución real registrada en docs/HISTORY con fecha o contexto | evidencia de una observación concreta; no garantía actual |
| `D — hipótesis/pendiente` | requiere credenciales, plan contratado, canary o prueba repetible | no |

### Regla de interpretación

- Una afirmación `A` de “200+ OTAs” no equivale a cobertura útil para una ciudad, estancia o mercado concreto.
- Una prueba `C` de autenticación no equivale a estabilidad.
- Un parser `B` que acepta un campo no demuestra que el provider lo devuelva de forma consistente.
- Un campo ausente en el adapter no se rellena con una inferencia optimista.

---

## 3. Fuentes consultadas y evidencia oficial

**Fecha de consulta:** 2026-08-04.

| Fuente | Nivel | Hecho verificable | Qué no demuestra |
|---|---|---|---|
| [Makcorps Documentation](https://docs.makcorps.com/) — redirige a [documentation](https://www.makcorps.com/documentation/) | A | API HTTP/JSON; endpoints documentados para `/city`, `/hotel`, `/booking`, `/expedia`, `/roomtype`, `/mapping` y `/account`; la página describe precios desde más de 200 OTAs | SLA, latencia, cobertura por mercado, disponibilidad real, fees completos o deeplinks |
| [Makcorps Documentation — Hotel Price APIs](https://www.makcorps.com/documentation/) | A | `/city` devuelve hoteles de una ciudad con vendors baratos; `/hotel` devuelve vendors por hotel; `/mapping` proporciona IDs; `/account` informa créditos restantes | cuota exacta actual, semántica de cada campo en todos los payloads, contrato de errores, Retry-After o paginación completa |
| [Makcorps homepage](https://www.makcorps.com/) | A | publicita Hotel Price API para seguir tarifas de más de 200 OTAs y una oferta inicial de llamadas gratuitas | capacidad contractual, cobertura garantizada, precio actual de producción o estabilidad |
| [Makcorps terms](https://www.makcorps.com/terms/) | A | licencias/servicios pueden facturarse por periodos; el sitio declara materiales “as is”, sin garantía de exactitud o actualización; los precios pueden cambiar | SLA, límite de requests, soporte, indemnidad, derechos de uso de datos o afiliación específicos del endpoint |
| `backend/app/hotels/makcorps_provider.py` | B | el adapter usa `/mapping`, `/city` y `/hotel`, API key por query parameter, timeout configurable de 10 s por defecto y hasta 2 retries configurados para 429/5xx; el flujo de área puede ejecutar hasta cinco llamadas concurrentes | que esos endpoints sigan disponibles o que los parámetros sean completos/estables |
| `HISTORY.md`, `docs/qa/hotels-pending-closeout.md` | C | una prueba real conectó/autenticó, pero recibió `429` en `/mapping` | que el 429 se haya resuelto o que el plan actual tenga capacidad suficiente |

### Información oficial no encontrada en las páginas accesibles

Quedan como `D — pendiente` y bloquean una aprobación amplia:

- cuota exacta por minuto/hora/día/mes del plan que usaría Viru;
- precio actual por operación y coste efectivo de `/mapping`, `/city`, `/hotel`, `/roomtype`;
- SLA, latencia objetivo, ventana de soporte y política de recuperación;
- semántica contractual de `Retry-After`, headers de cuota y códigos de error;
- cobertura operativa por país/ciudad, fechas futuras y ocupación;
- garantías sobre impuestos, fees, cancelación, habitaciones, niños y disponibilidad;
- contrato de deeplinks/affiliate attribution para abrir un partner;
- retención, uso permitido y exportación de payloads de OTAs para este caso.

La página oficial sí menciona que `/booking` cuesta 1 crédito por request y `/expedia` 2 créditos por request, pero Viru no usa esos endpoints hoy. No se debe extrapolar ese coste a `/mapping`, `/city`, `/hotel` o `/roomtype`.

---

## 4. Inventario del adapter actual

### 4.1. Endpoints usados

| Operación Viru | Endpoint | Parámetros enviados por el adapter | Estado H07 |
|---|---|---|---|
| resolver ciudad | `/mapping` | `name`, `api_key` | implementado, pero sufrió 429 real; el resultado puede mezclar `GEO` y fallback a cualquier tipo |
| resolver hotel | `/mapping` | `name`, `api_key` | implementado; no hay prueba real reproducible de precisión/ambigüedad |
| búsqueda de ciudad | `/city` | `cityid`, `checkin`, `checkout`, `adults`, `rooms=1`, `cur`, `pagination`, `api_key` | implementado; solo se solicita una página por llamada |
| rates dirigidos | `/hotel` | `hotelid`, `checkin`, `checkout`, `adults`, `rooms=1`, `cur`, `api_key` | implementado; respuesta se reduce a importe/moneda/ocupación |
| `/booking`, `/expedia`, `/roomtype`, `/account` | no usados | — | no aprobar capacidades de estos endpoints por existir en la documentación |

### 4.2. Capacidades demostradas por código, no por contrato comercial

| Capacidad | Evidencia local | Clasificación prudente |
|---|---|---|
| buscar por ciudad mediante ID | `/city` y parser implementados | `implemented-unverified-runtime` |
| buscar rates por hotel y fechas | `/hotel` y `fetch_hotel_rates()` | `implemented-unverified-runtime` |
| adultos | `adults=guests` | parcial: el dominio llama `guests`, pero no modela ocupación completa |
| habitaciones | siempre `rooms=1` | no soportada para producto general |
| niños/edades | no se envían | no soportada |
| moneda | `cur=currency` | implementada superficialmente; falta prueba de moneda real y validación de respuesta |
| fees/impuestos | parser suma `price + tax` | no comparable hasta verificar si `price`/`Totalprice` ya incluyen impuestos |
| habitación | lee `room_type` en `/city`; no lo obtiene de forma confiable en `/hotel` | parcial |
| régimen | lee `meal` en `/city` | parcial |
| cancelación | lee `cancellation` si aparece | no garantizada |
| disponibilidad explícita | no se conserva; rates inválidos/sold-out pueden terminar como lista vacía | no soportada |
| deeplink | no se genera ni transporta desde `ProviderRateRecord` | no soportada |
| paginación completa | acepta `page`, pero el flujo no recorre `totalpageCount` | no soportada |
| revalidación dirigida de tracking | existe método, pero el sweep le pasa el ID interno de hotel | bloqueada por mismatch de identidad |
| idempotencia | GETs sin idempotency key | no aplicable/ no demostrada |

---

## 5. Hallazgos técnicos bloqueantes

### H07-01 — El ID usado por tracking no coincide con el ID esperado por Makcorps

`MakcorpsHotelProviderAdapter.fetch_hotel_rates()` documenta que `hotel_id` debe ser el `provider_hotel_id` de Makcorps. El flujo de `sweep_tracked_offers()` en `backend/app/services/hotels_service.py` le pasa `offer.hotel_id`, que es el ID interno de `HotelProperty`.

En cambio, `area_search` sí construye un `alias_map` de `HotelProviderAlias` y llama al adapter con el ID externo. Son dos contratos diferentes para la misma operación.

**Impacto:** el refresh dirigido de una oferta trackeada puede devolver vacío/error aunque exista un alias válido. El código captura la excepción y continúa con una lista vacía, por lo que la UI/worker no obtiene una señal clara de fallo.

**Bloqueo:** no aprobar tracking Makcorps hasta resolver el mapeo y añadir un test de integración que pruebe `HotelProperty → HotelProviderAlias → provider_hotel_id → rate`.

### H07-02 — Los fallos externos se convierten en `None`/`[]`

`_get()` captura cualquier excepción, registra un warning y devuelve `None`. `fetch_hotel_rates()` transforma ese resultado en `[]`; `fetch_hotels()` transforma el fallo en `ValueError` genérico. Además, `area_search` captura excepciones y devuelve fallback/ausencia de rate, y el sweep dirigido captura el fallo antes de continuar. Esto impide distinguir de forma fiable:

- `empty` válido;
- `429` después de retry;
- timeout;
- 5xx;
- error de autenticación;
- JSON inválido.

**Impacto:** el dominio puede caer a snapshots antiguos o presentar ausencia de rates sin una causa accionable. En `area_search` las excepciones se capturan como listas vacías y en el sweep dirigido se hace fallback, por lo que el error puede quedar silencioso. Esto contradice el envelope H06 y no permite calcular provider health con calidad.

**Bloqueo:** migrar a clasificación V2 o introducir una capa de error observable antes de usar Makcorps para tracking público.

### H07-03 — Retry interno sin presupuesto compartido ni `Retry-After`

El adapter configura `Retry(total=2, status_forcelist=[429, 500, 502, 503, 504])` con backoff, pero no expone al dominio:

- número real de intentos;
- `Retry-After`;
- remaining/reset;
- causa final;
- latencia por operación.

Además, `area_search` puede lanzar hasta cinco requests concurrentes por lote y el sweep puede recorrer múltiples ofertas.

**Impacto:** riesgo de amplificar un rate limit, coste no visible y dificultad para hacer backoff/circuit breaker de forma global.

**Bloqueo:** límite local por provider/operación, propagación de cuota y métricas antes de aumentar concurrencia.

### H07-04 — La búsqueda por ciudad no garantiza cobertura completa

El adapter admite `page`, pero la llamada operativa obtiene una sola página. Aunque el payload pueda incluir `totalHotelCount`/`totalpageCount`, no existe un recorrido de páginas en el adapter o la ingestión.

**Impacto:** “resultados de ciudad” puede ser un subconjunto sesgado. No se puede medir cobertura por mercado con el comportamiento actual.

**Bloqueo:** probar paginación/limites reales y definir presupuesto máximo por operación antes de usar `/city` como catálogo completo.

### H07-05 — Condiciones y total no son comparables todavía

En `/city`, el parser suma `price + tax`. En `/hotel`, busca la primera clave que coincide con `priceN` o `TotalpriceN` y después suma `taxN`. La semántica de `price`, `Totalprice` y `tax` no está validada contra un contrato de respuesta estable.

El modelo normalizado pierde vendor/OTA, fees separados, moneda devuelta, ocupación completa, room ID y política de cancelación en muchos casos.

**Impacto:** no se puede afirmar “precio total”, “mejor precio” o paridad entre vendors sin una prueba de comparabilidad.

**Bloqueo:** fixtures oficiales/versionados o canary que confirme semántica de importes y condiciones; corregir parser si `Totalprice` ya incluye impuestos.

### H07-06 — No hay disponibilidad ni deeplink aprobados

Un vendor sin importe válido se descarta. No se conserva un estado explícito `sold_out`, `limited`, `unknown` o `provider_error`. `ProviderRateRecord` no contiene deeplink y `HotelRateSnapshot.deep_link` solo es un string nullable que no pasa allowlist hotelera.

**Impacto:** no hay base para alertas de disponibilidad ni CTA externo seguro.

**Bloqueo:** H06/H35 y pruebas contractuales específicas.

### H07-07 — La API key viaja en query parameters

El adapter fusiona `api_key` con los parámetros de cada GET. Los tests verifican que el logger propio no imprime la clave, pero eso no cubre proxies, access logs, métricas HTTP, tracing, herramientas de debugging o proveedores intermedios que registren la URL completa.

**Impacto:** riesgo de exposición de secreto fuera del logger de aplicación y dificultad para demostrar minimización de datos.

**Bloqueo:** H35/Security debe revisar si Makcorps permite header auth u otra forma segura; mientras tanto, redactar URLs en cada capa y no activar trazas que capturen query params.

---

## 6. Matriz de auditoría por dimensión

| Dimensión | Evidencia actual | Estado | Prueba necesaria para aprobar |
|---|---|---|---|
| autenticación | API key por query param; test local de `is_enabled`; runtime histórico autenticó | parcial | canary sin exponer key, rotación y manejo 401/403 |
| mapping ciudad/hotel | parser y tests locales; 429 real en `/mapping` | bloqueada | prueba repetible de tasa de éxito, ambigüedad y cooldown |
| cobertura geográfica | claim oficial de 200+ OTAs; sin dataset local | desconocida | matriz por mercado prioritario, ciudad, fechas y tipos de estancia |
| `/city` | parser local y campos de paginación | parcial | paginación completa, límites y cobertura sin sesgo |
| `/hotel` | parser local de vendors numerados | parcial | semántica de precios/taxes/Totalprice y estabilidad de payload |
| fechas | se envían `checkin/checkout` | parcial | casos de fechas cercanas, futuras, inválidas y timezone |
| ocupación | adultos; rooms fija a 1 | limitada | habitaciones múltiples, niños y edades o exclusión explícita |
| moneda | se envía `cur`; parser no valida respuesta | limitada | EUR/USD/GBP y respuesta de currency real |
| fees/impuestos | suma `tax`; sin modelo de fees | bloqueada | contrato de inclusión/exclusión por endpoint y vendor |
| habitación/régimen | algunos campos en `/city` | limitada | cobertura y equivalencia entre `/city`/`/hotel` |
| cancelación | campo opcional en parser | desconocida | porcentaje de respuestas con política válida y semántica |
| disponibilidad | no se persiste explícitamente | bloqueada | estados explícitos y test de sold out/provider error |
| deeplinks/affiliate | no implementado | bloqueada | contrato oficial, allowlist, generación y disclosure |
| latencia | timeout 10 s; sin métricas reales | desconocida | p50/p95/p99 por endpoint y mercado bajo cuota permitida |
| rate limits | 429 histórico en mapping; retry local 2 | bloqueada | límites del plan, Retry-After, canary controlado y circuit breaker |
| coste | free trial/free calls publicitados; tarifas exactas no verificadas | desconocido | plan contratado, coste por operación, presupuesto y alertas |
| SLA/soporte | no encontrado en fuentes accesibles | desconocido | compromiso contractual o asumir sin SLA |
| privacidad/uso de datos | terms/privacy generales; API key en query params | bloqueada | revisión legal del payload, retención, uso comercial y redacción de URLs |
| observabilidad | logs de error sin secreto; no envelope V2 | limitada | request ID, status, attempts, latency, cost y redaction |

---

## 7. Pruebas locales existentes y qué demuestran

`backend/tests/unit/test_hotels_makcorps_provider.py` cubre de forma útil:

- provider ID y activación por API key;
- parsing de `/city` con hoteles y rates;
- respuesta vacía/malformada;
- importes inválidos;
- errores 500/429/timeout;
- parsing de `/hotel` con vendors numerados;
- símbolos de moneda en strings;
- mapping GEO/HOTEL;
- ausencia del secreto en logs.

Estas pruebas son **unitarias con sesión mock**. No demuestran:

- disponibilidad actual del endpoint;
- cuota real, coste o Retry-After;
- latencia;
- cobertura por ciudad/país;
- precisión de mapping;
- paginación completa;
- condiciones comparables;
- deeplink o afiliación;
- que el ID del tracking se traduzca correctamente.

El test suite debe conservarse y extenderse dentro de H06/H09/H39, pero no usarlo como sustituto de un canary real controlado.

---

## 8. Presupuesto y control de coste

Mientras no exista una cuota/precio de cuenta verificable, el presupuesto operativo de Makcorps debe tratarse como **cero requests automáticos de producción**.

### Política provisional

1. `HOTEL_PROVIDER=mock` por defecto.
2. `HOTEL_FEATURE_ENABLED=false` y `HOTEL_SWEEP_ENABLED=false` por defecto se mantienen.
3. No activar Makcorps en un worker periódico.
4. Toda prueba real requiere ventana temporal, ciudad/IDs definidos, límite de requests y owner.
5. No usar concurrencia de cinco workers para un canary sin autorización del plan y cuota.
6. Registrar antes/después: requests intentados, retries, 2xx, 4xx, 429, 5xx, timeouts, items, rates válidos y coste estimado.
7. Cortar el canary ante 429 repetido, coste no observable, respuesta incompatible o falta de `Retry-After` gestionable.
8. Consultar `/account` solo si el contrato y permisos de la cuenta lo permiten; no guardar ni mostrar la respuesta con secretos.

### Presupuesto mínimo que debe existir antes del go

```text
monthly_request_budget
monthly_credit_budget
per_operation_cost: mapping/city/hotel/roomtype
max_requests_per_search
max_requests_per_sweep
max_concurrency
max_retries
429_cooldown
circuit_breaker_threshold
owner_and_alert_channel
```

Ninguno de esos valores debe inventarse a partir de la oferta de prueba o de la mención de 1/2 créditos de endpoints que Viru no utiliza.

---

## 9. Plan de canary propuesto

El canary debe ejecutarse solo tras resolver H07-01 y añadir clasificación V2 mínima.

### Diseño

- 3–5 ciudades representativas del mercado inicial.
- 3 estancias: corta, media y fecha futura.
- ocupación de 1 habitación/2 adultos como caso actualmente soportado;
- una consulta inexistente/ambigua;
- una moneda adicional si el plan lo permite;
- mínimo de llamadas definido por cuota y presupuesto, no por conveniencia;
- sin datos de usuarios reales ni children ages hasta aprobación de privacidad.

### Medidas por operación

```text
mapping_success_rate
mapping_ambiguity_rate
city_success_rate
hotel_success_rate
empty_rate
partial_rate
provider_error_rate
429_rate
5xx_rate
timeout_rate
p50/p95/p99 latency
hotels_received
rates_received
rates_valid
rates_with_total_semantics
rates_with_room/meal/cancellation
freshness_observation_integrity
```

### Criterios orientativos de salida

Estos umbrales son **propuesta para aprobación**, no resultados actuales:

- cero secretos en logs;
- cero llamadas con ID interno en lugar de provider ID;
- 429 siempre visible y con cooldown;
- error total no aparece como `empty` ni `sold_out`;
- paginación y límites conocidos;
- p95 dentro del presupuesto de UX acordado;
- cobertura mínima por mercado definida por producto;
- condiciones comparables para el porcentaje de rates que se rankeen;
- coste por búsqueda/sweep bajo el presupuesto aprobado;
- deeplink solo si pasa H35, si no permanece ausente;
- rollback a mock/cache/histórico sin romper lectura.

No se fija un porcentaje universal de éxito porque depende del mercado, plan y caso de uso; H07 debe producir esa cifra con datos, no copiarla de otra integración.

---

## 10. Decisión por caso de uso

| Caso | Decisión actual | Condición de reapertura |
|---|---|---|
| desarrollo local | aprobado con mock; Makcorps solo manual | fixture/canary controlado |
| QA parser/contrato | aprobado con mocks | añadir fixtures V2 y contract tests |
| discovery de una ciudad | experimental, no público | mapping + city estables, paginación, cuota y cobertura medidas |
| búsqueda por área en tiempo real | no aprobado como default | alias correcto, límite local, partial/error explícitos y latencia medida |
| tracking dirigido | bloqueado | resolver ID externo, envelope V2, snapshots trazables y canary |
| sweep periódico | bloqueado | H09 con locks, budget, circuit breaker, retries y health check |
| alertas de precio | bloqueado para claims actuales | observaciones elegibles H05 y dedupe H26 |
| alertas de disponibilidad | no aprobado | disponibilidad explícita y separada de error |
| deeplink/affiliate | no aprobado | contrato oficial + allowlist H35 + disclosure |
| proveedor principal | rechazado por ahora | superar matriz completa, revisión de producto/coste y seguridad de credenciales |
| fallback universal | rechazado | comparar capacidades por estancia; no asumir equivalencia |

---

## 11. Acciones requeridas antes de reabrir la decisión

1. Corregir el mapeo de identidad del tracking: siempre usar `HotelProviderAlias.provider_hotel_id` para Makcorps.
2. Introducir clasificación de errores compatible con H06: `empty`, `rate_limited`, `timeout`, `unavailable`, `invalid_response`, `failed`.
3. Propagar `Retry-After`, attempts, latencia, request ID y razón final sin secretos.
4. Sustituir el retry aislado por un presupuesto coordinado entre adapter, area search y worker.
5. Implementar o descartar explícitamente paginación `/city` con evidencia de límites.
6. Validar semántica de `price`, `Totalprice` y `tax`; no sumar dos veces impuestos.
7. Preservar currency, vendor, fees y condiciones suficientes para comparar.
8. Declarar rooms/children/cancellation/availability como no soportados mientras no haya evidencia.
9. Añadir `deep_link` solo después de allowlist y contrato de partner; hasta entonces `null`.
10. Crear contract tests V2 contra Mock y Makcorps.
11. Ejecutar canary con presupuesto y captura de métricas.
12. Obtener precio/cuota/terms comerciales del plan real y registrarlos sin secretos.
13. Revisar legal/privacy para payloads de hoteles y uso de datos externos.
14. Revisar la exposición de `api_key` en query params y garantizar redacción en proxies, logs, métricas y tracing.
15. Actualizar H07 con fecha, cuenta/plan abstracto, muestra, resultados y decisión revisada.

---

## 12. Gate H07

H07 queda completo como auditoría y decisión cuando:

- la matriz separa evidencia oficial, código local, runtime histórico y unknowns;
- los endpoints usados están inventariados sin atribuir capacidades no demostradas;
- 429 histórico, timeout/retry y fallos absorbidos están documentados;
- el mismatch entre IDs internos y provider IDs queda señalado como bloqueo;
- cobertura, paginación, fees, disponibilidad, deeplinks, coste y SLA tienen estado explícito;
- existe una decisión `CONTINUAR LIMITADO / NO PROVIDER PRINCIPAL` defendible;
- hay política provisional de cero requests automáticos y presupuesto/canary de reapertura;
- se enumeran acciones concretas para H08/H09/H10/H15/H19/H35/H37/H41;
- no se expone ninguna credencial ni se afirma que Makcorps sea estable.

**Resultado H07:** auditoría aprobada y decisión condicionada. Makcorps permanece como adapter opcional experimental; el producto no puede declarar tracking real estable hasta cerrar los bloqueos técnicos y operativos.
