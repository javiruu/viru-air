# H54 — Mercados hoteleros: criterios de entrada, operación y salida

**Estado:** COMPLETA como contrato de expansión/operación; implementación de registro de mercados, matrices por provider, canary y QA pendientes  
**Fecha:** 2026-08-05  
**Área:** producto / backend / providers / datos / localización / costes / seguridad / operación / QA  
**Fuente de verdad:** sí para evaluar, activar, limitar, pausar y retirar mercados hoteleros de `/hoteles`  
**Fase del roadmap:** H54  
**Depende de:** H07, H08, H12, H34, H37, H38, H41, H42, H43, H44, H45, H53  
**Relacionado con:** H05 freshness/provenance/confidence, H06 provider-neutral, H09 sweeps, H10 estancia/oferta, H15 resultados, H19 fees, H20 comparación, H35 legal/deeplinks, H39 tests, H52 feedback/confianza

**Handoff:** [H55 — hardening de continuidad y disaster recovery](../../plans/2026-08-04-hoteles-master-roadmap.md#fase-h55--hardening-de-continuidad-y-disaster-recovery)

> H54 evita abrir un país o ciudad porque el geocoder la reconoce, el provider devuelve alguna propiedad o existe una bandera de configuración. Un mercado es una promesa operativa: debe tener identidad geográfica, cobertura medible, precio/condiciones interpretables, localización suficiente, presupuesto, soporte y una salida reversible.

---

## 1. Propósito y frontera

La unidad de expansión no es “un país” en abstracto. Es una combinación explícita de:

```text
market_id
  = territorio + ciudades/zonas + moneda/locale/timezone
  + provider scope + capacidades + política de rollout
```

Un mercado puede estar:

- **investigado:** hay hipótesis y fuentes, pero no se sirve públicamente;
- **fixture_only:** existe cobertura para desarrollo/QA sin provider live;
- **manual_canary:** pruebas limitadas con owner, presupuesto y fechas;
- **limited_live:** caso de uso restringido, con disclosure y métricas;
- **approved_live:** capacidades y gates aprobados para el alcance declarado;
- **paused:** suspendido por riesgo, coste, calidad o términos;
- **retired:** retirado con fallback y registro de motivo.

### 1.1. Dentro de H54

- Definición de mercado, perímetro, ciudades prioritarias y casos de uso.
- Matriz provider/mercado/capability con evidencia y fecha.
- Calidad de identidad H53, cobertura, geodata y resolución H12.
- Precio, fees, ocupación, habitación, régimen, cancelación y disponibilidad H10/H19.
- Locale ES/EN, moneda de origen, fechas civiles, timezone y copy H34.
- Coste, rate limits, concurrencia, latencia y budget H37.
- Legal/privacy/deeplinks H35, observabilidad H41, flags H43 y release H45.
- Canary, criterios de entrada/salida, rollback y soporte.
- Métricas de calidad, producto, confianza, operación y feedback H52.

### 1.2. Fuera de H54

- No integra un provider comercial por sí sola.
- No inventa cobertura por país, ciudad, idioma, moneda o afiliación.
- No convierte un geocoder en catálogo de hoteles.
- No decide que un mercado es “global” por tener una respuesta HTTP 200.
- No fija umbrales universales de conversión o ingresos antes de aprobar denominadores y objetivos.
- No habilita automáticamente workers, deeplinks, email, push o afiliación.
- No reemplaza la revisión legal, de seguridad, coste, release o soporte de H35/H38/H41/H45.

---

## 2. Baseline real del repositorio

### 2.1. Capacidades observables actuales

- `ProviderHotelRecord` ya transporta nombre, dirección, ciudad, país, coordenadas, estrellas y rates.
- Mock es provider de fixtures para desarrollo, demo y QA; no demuestra cobertura live.
- Makcorps tiene adapter de `/mapping`, `/city` y `/hotel`, pero H07 documenta 429, mismatch entre IDs interno/externo, paginación incompleta, fees/condiciones no comparables, ausencia de deeplink aprobado y coste/cuota desconocidos.
- `area_resolve` usa catálogo interno y fallback Nominatim; H12 exige tratarlo como resolución de destino, no como prueba de cobertura hotelera.
- `HotelProperty` filtra por país/ciudad y coordenadas; el repositorio no expone una matriz de mercados aprobados con cobertura, freshness y capabilities verificadas.
- La consulta V1 acepta `city`, `country_code`, radio, moneda y `use_provider`; aceptar un parámetro no equivale a aprobar el mercado.
- `HOTEL_FEATURE_ENABLED`, `HOTEL_SWEEP_ENABLED`, `HOTEL_PROVIDER` y `HOTEL_GEOCODER_ENABLED` son controles V1; H43 aún requiere un resolver unificado por request, operación y mercado.
- H34 define V1 ES/EN, moneda de origen y fechas/timezones, pero mantiene gaps de implementación en locale hardcodeado, pluralización y fechas civiles.
- H37 define metodología de budget/rate limits/locks/cost; no es una medición de capacidad externa ni aprobación comercial.
- H45 define smoke/canary/rollback, pero la existencia del contrato no prueba que un mercado concreto haya pasado el canary.
- H53 define identidad, aliases, matching y evidencia de calidad; un mercado no puede activarse si el mapping de sus propiedades es ambiguo sin control.

### 2.2. Lo que no se demuestra hoy

No existe evidencia suficiente de que el repositorio tenga actualmente:

- un `HotelMarketRegistry` o configuración equivalente versionada por mercado;
- una allowlist de países/ciudades hoteleras aprobadas con owner y fecha de revisión;
- cobertura live verificada por ciudad, temporada, ocupación, moneda y provider;
- thresholds aprobados de entrada/salida por mercado;
- un canary real de mercado con tráfico, coste y rollback medidos;
- una matriz estable de capabilities por provider y mercado;
- scheduler/sweeps automáticos seguros para un mercado nuevo;
- soporte de habitaciones múltiples, niños/edades, fees, cancelación y deeplinks en todos los mercados;
- SLO/latencia/coste demostrados por mercado;
- runbook de soporte específico para la expansión;
- mecanismo para retirar un mercado sin borrar histórico ni dejar CTAs engañosos.

Por tanto, H54 es un contrato de decisión y control; no declara que ningún mercado adicional esté live por haber sido mencionado en código, fixtures o documentación comercial.

---

## 3. Entidad de mercado y matriz de capabilities

### 3.1. `MarketSpec` objetivo

```text
market_id                  slug interno estable y versionado
territory_code             ISO-3166/territorio aprobado
name                       etiqueta de producto localizada
scope_type                 country | region | city_cluster | city | area
scope_refs                 ciudades/zonas/códigos opacos allowlisted
default_currency           código ISO-4217 observado o configurado
supported_locales          ES/EN V1 u otros aprobados
property_timezones         IANA, si aplica
provider_scope             providers y orden permitido
status                     investigated | fixture_only | manual_canary | limited_live | approved_live | paused | retired
policy_version             versión de entrada/salida
owner                      equipo/rol, no PII
reviewed_at                fecha de revisión
```

`MarketSpec` no contiene API keys, emails, thresholds privados de usuarios, textos raw de provider ni coordenadas privadas.

### 3.2. `MarketProviderCapability`

Cada combinación mercado/provider/capability necesita estado y evidencia:

```text
market_id
provider_id
capability              mapping | search_area | rates | revalidate | deeplink | sweep
occupancy_scope         rooms/adults/children/ages
price_scope             base/fees/total/currency
condition_scope         room/meal/cancellation
availability_scope
coverage_scope          cities/season/market segments
status                  supported | partial | unsupported | unknown | blocked
source_kind             official | contract | fixture | canary | runtime | inferred
source_ref_redacted
observed_at
policy_version
known_exclusions
```

`unknown` se trata como ausencia para la decisión; nunca como capacidad positiva. `partial` puede servir para un caso explícitamente limitado, pero no para un CTA o claim más amplio.

### 3.3. Matriz mínima antes de activar

| Dimensión | Pregunta que debe responderse |
|---|---|
| identidad | ¿H53 puede mapear propiedades sin conflicto y con alias externo estable? |
| cobertura | ¿Qué ciudades/zonas y qué porcentaje de resultados elegibles se observan? |
| estancia | ¿Fechas, noches, habitaciones, adultos, niños y edades están soportados o excluidos claramente? |
| precio | ¿Se sabe qué incluye el importe, moneda devuelta, impuestos y fees? |
| condiciones | ¿Room, régimen y cancelación son comparables y visibles? |
| disponibilidad | ¿`sold_out`, `unknown`, `provider_error` y `available` están separados? |
| freshness | ¿Existe timestamp, TTL y estado de fuente? |
| resolución | ¿H12 evita ambigüedad y geocoder no se confunde con cobertura? |
| locale | ¿ES/EN, copy, fechas civiles, currency y timezone pasan H34? |
| operación | ¿Budget, rate limit, locks, retries, breaker y health están medidos? |
| seguridad/legal | ¿Ownership, redaction, terms, redirects y deeplinks pasan H35/H38? |
| release | ¿Smoke, canary, kill switch, rollback y soporte pasan H45? |

---

## 4. Criterios de entrada por capas

Un mercado no entra directamente en `approved_live`. Debe progresar por capas y cada capa puede detenerse.

### Gate A — Definición y demanda

- perímetro geográfico explícito;
- ciudades/zonas prioritarias y por qué;
- hipótesis de usuario y job H01;
- idioma/locale de la interfaz;
- moneda de origen y política de presentación;
- timezone de propiedad/estancia cuando sea material;
- exclusiones conocidas;
- owner, fecha de revisión y policy version;
- no usar demanda o popularidad como sustituto de calidad de datos.

**Salida:** `market_spec_draft` o `rejected_scope`.

### Gate B — Identidad y cobertura

- H53 shadow matching o gold set de la muestra;
- aliases provider sin conflictos;
- duplicados/falsos merges bajo control aprobado;
- geodata válida o estado `unknown` explícito;
- matriz de hoteles observados por ciudad/mercado/provider;
- muestra de temporada y fechas suficiente para el caso declarado;
- no abrir todo el país si solo se probó una ciudad.

**Salida:** `identity_ready`, `limited_scope` o `blocked_quality`.

### Gate C — Capacidad de estancia y precio

Para el alcance exacto que se va a mostrar:

- fechas y noches válidas;
- ocupación soportada, incluida la exclusión explícita de rooms/children si falta;
- currency devuelta y presentada sin conversión implícita;
- base/fees/total sin doble suma;
- habitación, régimen y cancelación con completitud conocida o copy parcial;
- disponibilidad separada de error/provider outage;
- freshness/provenance/confidence H05;
- H19/H21 no permiten claims que excedan la evidencia.

**Salida:** `capability_ready`, `fixture_only` o `blocked_semantics`.

### Gate D — Locale, legal y seguridad

- ES/EN y copy de estados principales pasan H34;
- fechas civiles no se desplazan por timezone;
- `property_timezone`/`user_timezone` no se mezclan;
- términos del provider, uso de datos y retención revisados;
- deeplink ausente si no pasa allowlist H35;
- ownership, SSRF, secretos y abuse controls H38;
- feedback/soporte y comunicación de limitaciones preparados.

**Salida:** `trust_ready` o `blocked_legal_security`.

### Gate E — Operación y coste

- budget duro por búsqueda, revalidación y sweep;
- rate limits, `Retry-After`, concurrencia y backoff observados o conservadores;
- locks/leases y dedupe H09/H37;
- provider health, request ID sanitizado y outcome H41;
- flags por provider/operación/mercado y kill switch H43;
- no activar scheduler periódico solo porque la búsqueda manual funcione;
- runbook de incidentes y soporte H42 preparado.

**Salida:** `ops_ready` o `blocked_cost_reliability`.

### Gate F — Release canary

- fixtures y contract tests de éxito, empty, partial, timeout, 429, invalid response;
- smoke del flujo exacto de mercado;
- canary manual o tráfico interno con presupuesto;
- observación suficiente para el alcance, no solo una respuesta;
- rollback que apaga el mercado sin borrar históricos;
- decisión owner/QA/producto registrada según H45.

**Salida:** `manual_canary`, `limited_live`, `approved_live` o `rejected`.

---

## 5. Criterios de salida, pausa y retirada

### 5.1. Motivos de pausa inmediata

Pausar mercado/provider/operación si ocurre cualquiera:

- secreto, token o URL privada expuesta;
- ownership o deeplink inseguro;
- mapping ambiguo que contamina tracking/snapshots;
- precio/fees/cancelación materialmente incorrectos;
- provider error presentado como empty, sold out o live;
- `429`/coste no observable o sobrepresupuesto;
- latencia que rompe el presupuesto sin fallback seguro;
- caída de cobertura por debajo del scope declarado;
- schema drift o respuesta inválida no clasificada;
- incumplimiento legal/contractual del provider;
- feedback H52 P0/P1 o guardrail H51 sin contención;
- falta de owner, monitorización o rollback ejecutable.

### 5.2. Salida ordenada

1. marcar `paused`/`retired` con reason code y timestamp;
2. desactivar flags de mercado, provider, búsqueda, revalidación, sweep y deeplink según scope;
3. detener jobs nuevos y cerrar leases de forma segura;
4. conservar snapshots, feedback, aliases y métricas con procedencia;
5. servir fallback solo si es elegible y etiquetado (`cached`, `historical`, `fixture_demo`, `unavailable`);
6. retirar CTAs/deeplinks que ya no se pueden respaldar;
7. comunicar la limitación sin afirmar que el mercado no existe;
8. rotar/revocar credenciales si procede;
9. registrar impacto, coste, usuarios/superficies afectadas y owner;
10. reabrir únicamente repitiendo los gates afectados y un canary.

### 5.3. No borrar por retirar

Retirar un mercado no autoriza a:

- borrar snapshots históricos;
- eliminar aliases o casos H52;
- mezclar un provider diferente como si fuera la misma observación;
- convertir histórico en live;
- mantener un botón de seguimiento que no pueda ejecutarse;
- cambiar retrospectivamente precio, moneda o condiciones.

---

## 6. Canary y criterios cuantitativos

H54 no fija porcentajes universales sin un baseline. Cada `MarketSpec` debe registrar umbrales aprobados y denominadores. Como mínimo, el canary debe medir:

```text
mapping_success_rate
mapping_ambiguity_rate
duplicate/identity_conflict_rate
coverage_by_city_and_scope
results_with_valid_coordinates
rates_received
rates_with_valid_currency
rates_with_fee_semantics
rates_with_room_meal_cancellation
availability_state_integrity
freshness_integrity
empty_vs_error_separation
partial_rate
provider_error_rate
429_rate
timeout_rate
p50/p95/p99_latency
cost_per_search
cost_per_revalidation
sweep_success/partial/failed
feedback_price_condition_rate
tracking_creation_eligibility
rollback_time
```

### 6.1. Regla de denominadores

Cada porcentaje debe decir:

- población: búsquedas, hoteles, ofertas, snapshots, requests o usuarios;
- mercado/provider/operation;
- fechas y ventana;
- fixture vs canary vs runtime;
- policy version;
- exclusiones y datos faltantes.

No declarar “cobertura 90%” si el denominador son solo propiedades que el provider devolvió. No declarar “éxito 100%” con una muestra de una llamada.

### 6.2. Criterios de promoción

Los valores concretos los aprueban Producto/Backend/QA/Operación, pero la promoción requiere como mínimo:

- ningún P0 abierto;
- cero secretos en evidencias;
- cero uso de ID interno como ID externo;
- `empty`, `partial`, `provider_error`, `timeout`, `429` y `unavailable` diferenciados;
- precio rankeado con moneda/semántica/conditions suficientes;
- identity conflict y ambiguity dentro del límite aprobado;
- coste y latencia dentro de budget;
- rollback probado en el mismo scope;
- H34/H35/H38/H41/H43/H45 con evidencia;
- soporte H52 listo para recibir reportes del mercado.

No se promociona un mercado solo porque mejoren clicks, CTR, partner revenue o volumen de resultados si empeoran veracidad, privacidad, disponibilidad o coste.

---

## 7. Registro de decisiones y ownership

Cada mercado debe tener un decision record con:

```text
market_id
scope
provider_scope
capability_matrix
policy_version
entry_evidence_refs_redacted
canary_window
budget
thresholds + denominators
owner/product/qa/security sign-off
status transition history
pause/exit reasons
rollback evidence
next review date
```

No guardar API keys, tokens ni datos personales en el registro. Una decisión posterior no reescribe la anterior: añade nueva versión.

### Roles mínimos

- Producto: job, alcance y claims.
- Backend/Data: identidad, provider, precio y migración.
- Infra/Operación: budget, health, flags y recovery.
- Frontend/i18n: copy, locale, fechas y estados.
- Security/Legal: datos, secrets, SSRF, terms y deeplinks.
- QA: fixtures, contract tests, browser, canary y rollback.
- Support: comunicación, feedback H52 y triage del mercado.

Un owner de mercado no debe aprobar solo su propio go; P0/P1 requiere revisión cruzada.

---

## 8. Tests y evidencia de cierre

### Unitarios

- MarketSpec valida scope, códigos, locale, moneda, timezone, estados y policy version;
- capability `unknown` no se considera supported;
- mercado sin provider/cobertura suficiente queda bloqueado;
- provider error/429/timeout no se transforma en empty/sold_out;
- currency/fees/room/meal/cancellation incompletos producen `partial` o `blocked` según el claim;
- geocoder válido sin catálogo no equivale a coverage;
- flags off no hacen requests externos;
- budget/concurrency/retries tienen límites;
- salida no borra históricos ni aliases;
- rollback es idempotente y no duplica snapshots;
- métricas llevan denominador, ventana y policy.

### Integración

- mercado limitado a una ciudad no responde como país completo;
- provider ID se resuelve mediante alias H53;
- alias ambiguo bloquea rates/tracking dirigido;
- búsquedas V1 mantienen compatibilidad y source/freshness correctos;
- locale ES/EN, moneda de origen y fecha civil pasan H34;
- 401/403/404 no revelan configuración o datos de otro mercado/usuario;
- canary registra outcomes y cost sin secretos;
- pause/retire apaga jobs, flags y deeplinks del scope correcto;
- fallback no se presenta como live.

### QA/release

- smoke del mercado en desktop/mobile, dark/light, ES/EN y viewports relevantes;
- estados idle/loading/success/empty/partial/stale/error/unavailable;
- búsqueda por ciudad, zona, fechas, ocupación y moneda soportadas;
- resultado, detalle, favorito, tracking, alertas, inbox, feedback y deeplink si están dentro del scope;
- H40 browser evidence y H45 canary/rollback evidence;
- H41 dashboards/alerts y H42 recovery runbook;
- fixture payloads, traces y logs redacted;
- prueba de salida con provider 429, timeout, schema drift, coste excesivo y mapping ambiguity.

### Gate H54

H54 puede declararse implementada solo cuando:

1. existe un `MarketSpec`/registro equivalente versionado y con owner;
2. el scope geográfico no excede la cobertura probada;
3. H53 demuestra identidad/matching suficiente para ese mercado;
4. cada capability del provider tiene evidencia y exclusiones explícitas;
5. precio, fees, condiciones, ocupación, disponibilidad y freshness no exceden la evidencia;
6. H34/H35/H38 cubren locale, fechas, monedas, privacidad, secrets, SSRF y deeplinks;
7. H37/H41/H43 demuestran presupuesto, health, flags y kill switch;
8. H44/H45 aportan fixtures, smoke, canary y rollback;
9. H52 está preparado para feedback y correcciones de confianza;
10. existen criterios cuantitativos con denominadores y decisión firmada;
11. la salida/pausa conserva datos, retira promesas y puede ejecutarse sin despliegue destructivo;
12. H55 recibe la evidencia necesaria para recovery drill.

**Estado de cierre documental:** contrato aprobado; no se declara ningún mercado adicional `approved_live` hasta que una implementación futura aporte un decision record, canary y evidencia de todos los gates. La existencia de un `country_code`, geocoder, fixture o respuesta provider no constituye por sí sola aprobación de mercado.
