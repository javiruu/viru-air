# H56 — Plantilla operativa de revisión anual hotelera

**Artefacto:** `HotelAnnualReview`  
**Estado del artefacto:** `evidence_incomplete` — plantilla sin resultados rellenados  
**Tipo:** paquete de evidencia / revisión anual  
**Fuente de verdad contractual:** [H56 — revisión anual, providers, costes y siguiente roadmap](../reference/backend/hoteles-revision-anual-roadmap-h56.md)  
**Roadmap:** [Plan maestro de hoteles](../plans/2026-08-04-hoteles-master-roadmap.md)  
**Fecha de plantilla:** 2026-08-05  

> Esta plantilla no certifica el estado de producción. Las celdas `TBD`, `unknown`, `not_measured` y `contract_only` deben conservarse hasta obtener evidencia real. No sustituirlas por cero, éxito, cobertura o aprobación.

---

## 1. Identidad y alcance de la revisión

```text
review_id: TBD-opaque
review_period_start_utc: TBD
review_period_end_utc: TBD
generated_at_utc: TBD
product_version: TBD
schema_versions: TBD
config_revision_sanitized: TBD
market_scope: TBD
provider_scope: TBD
metric_catalog_version: H04-v1-or-TBD
evidence_expiry: TBD
review_owner: TBD
reviewers: TBD
approver: TBD
decision_status: evidence_incomplete
```

### Convenciones de evidencia

| Estado | Significado | Uso |
|---|---|---|
| `measured` | dato obtenido de una fuente ejecutada, con ventana, denominador y procedencia | puede alimentar una decisión, sujeto a revisión; la existencia de un endpoint o modelo se etiqueta aparte y no equivale a cobertura runtime de producción |
| `approximate` | proxy o muestra parcial con limitaciones explícitas | solo decisión acotada; no comparar como métrica exacta |
| `not_measured` | debería medirse, pero no hay lectura fiable | bloquea claims que dependan de ella |
| `contract_only` | definido en una doc, sin implementación/evidencia runtime | guía de trabajo; no es resultado |
| `unknown` | la existencia, alcance o semántica no pudo verificarse | tratar conservadoramente como ausencia |
| `blocked` | no se puede medir de forma segura por falta de entorno/credencial/owner | registrar bloqueo y siguiente acción |

Cada fila de resultados debe incluir: `source`, `observed_at`, `environment`, `sample/window`, `denominator`, `policy_version`, `status` y `limitation`.

---

## 2. Fuentes ejecutables y contract-only conocidas

| Fuente | Tipo | Qué puede aportar | Estado inicial | Comando/consulta o evidencia |
|---|---|---|---|---|
| `backend/app/api/v1/ux.py` `ALLOWED_EVENTS`/`/ux/events` | código/API | allowlist y persistencia de eventos UX autenticados | `measured` para existencia; no para cobertura | inspección de código + request de fixture |
| `HotelAlertEvent` / `/api/v1/hotels/alert-events` | DB/API | eventos de dominio e inbox hotelero | `measured` en tests; producción TBD | test integración / consulta redacted |
| `backend/app/worker/hotels_sweep.py` | worker/log | flags, provider, runs y ciclo | `measured` para comportamiento local | `python -m app.worker.hotels_sweep --once --provider mock` sobre DB aislada |
| `MakcorpsHotelProviderAdapter` | código/tests | timeout, retry local, errores absorbidos, parser y API key | `approximate`/`contract_only` para runtime externo | tests mock; canary real bloqueado por H07 |
| `SupportFeedback` `/api/v1/support/feedback` | API/DB | feedback explícito de usuarios | `measured` para existencia; volumen TBD | request autenticado + consulta agregada |
| `provider_health_stats.py` | código | patrón de counters de salud | `contract_only` para hoteles | verificar semántica: actualmente orientado a vuelos |
| `H04` | contrato | taxonomía, fórmulas y guardrails | `contract_only` | docs/product/hoteles-metrics-events-h04.md |
| `H07/H08/H37/H41/H43/H45/H55` | contratos/runbooks | provider, coste, observabilidad, flags, release y recovery | `contract_only` salvo evidencia citada | adjuntar refs y fecha |
| `backend/tests/integration/test_hotels_api_flow.py` | tests | happy path Mock, ownership, alert events, tracking, estados HTTP | `measured` para la ejecución concreta | comando pytest + commit |

**Regla:** un test local prueba el comportamiento del código bajo test; no prueba por sí solo cuota, cobertura, SLA, coste o disponibilidad comercial de un provider externo.

---

## 3. Métricas de producto y confianza

| Métrica | Fórmula/denominador | Ventana/segmento | Estado | Resultado | Fuente/evidencia | Limitación |
|---|---|---|---|---|---|---|
| Search completion rate | `hotel_search_completed / hotel_search_submitted` | TBD | `not_measured` | TBD | H04 + instrumentación | `/ux/events` actual no contiene necesariamente eventos hoteleros |
| Useful result rate | búsquedas `success/partial` con resultados / completadas | TBD | `not_measured` | TBD | H04 | falta pipeline hotelero completo |
| Tracking creation rate | trackings creados / flujos iniciados elegibles | TBD | `not_measured` | TBD | H04/H23 | separar intención de creación confirmada |
| Tracking survival | activos a 7/30 días excluyendo expiración legítima | TBD | `not_measured` | TBD | DB/tracking | requiere ventana histórica fiable |
| Alert actionable rate | alertas abiertas con acción / alertas abiertas | TBD | `not_measured` | TBD | H04/H26-H28 | evento persistido no equivale a delivery |
| Feedback trust rate | feedback de precio/condición / oportunidades de feedback | TBD | `not_measured` | TBD | SupportFeedback/H52 | falta denominador de oportunidades |
| Freshness visible | resultados con freshness / resultados elegibles | TBD | `not_measured` | TBD | H05/H41 | instrumentación y envelope pendientes |
| Provider error rate | errores provider / llamadas intentadas | TBD | `approximate` | TBD | logs Makcorps/tests | no hay ledger hotelero persistente |
| Cross-user leak count | relaciones privadas visibles a otra cuenta | fixture two-user | `measured` solo por test | TBD | H38/H39/integration tests | no equivale a producción continua |
| Fixture-only production rate | resultados demo en entorno no demo / resultados | TBD | `not_measured` | TBD | provenance | requiere estado de procedencia persistido |

### Lectura obligatoria

No convertir `TBD` en `0%`, “sin errores” o “no aplica”. Si no existe denominador o la instrumentación cambió durante la ventana, usar `approximate`, `not_measured` o `blocked`.

---

## 4. Provider y mercado

### 4.1 Ficha de provider

Repetir por `mock`, `makcorps` y cada candidato real que se llegue a probar:

```text
provider_id: TBD
mode: fixture_only | manual | canary | live
status: fixture_only | candidate | approved_limited | approved_live | paused | sunset | review_required
owner: TBD
contract_source_and_accessed_at: TBD
terms_privacy_retention: TBD
market_scope: TBD
capabilities: TBD
known_exclusions: TBD
requests: TBD
attempts: TBD
429: TBD
5xx: TBD
timeouts: TBD
latency_p50_p95: TBD
valid_rate: TBD
comparability_rate: TBD
mapping_ambiguity_rate: TBD
cost_source_unit_total: TBD
quota_source_remaining: TBD
incident_refs: TBD
kill_switch: TBD
last_reviewed_at: TBD
next_review_at: TBD
recommendation: TBD
```

**Baseline conocido:** Makcorps permanece limitado/experimental por H07; el Mock solo prueba fixtures; no rellenar el bloque como `approved_live` sin canary y términos reales.

### 4.2 Ficha de mercado

```text
market_id: TBD
MarketSpec_version: TBD
territory/cities: TBD
locale/currency/timezone: TBD
provider_scope: TBD
capability_matrix_ref: H54/TBD
coverage_by_city_scope: TBD
identity_quality_ref: H53/TBD
cost_budget: TBD
support_owner: TBD
state: investigated | fixture_only | manual_canary | limited_live | approved_live | paused | retired
entry_decision: TBD
exit_decision: TBD
```

No declarar un mercado `approved_live` porque exista en el geocoder, una fixture o una respuesta HTTP 200.

---

## 5. Costes y operación

| Capa | Unidad | Volumen | Precio unitario | Total | Estado | Fuente | Limitación |
|---|---|---:|---:|---:|---|---|---|
| Provider/API | mapping/city/hotel/revalidation/sweep | TBD | `unknown`/TBD | TBD | `not_measured` | H37/H07 + plan real | no extrapolar de endpoints no usados |
| Infraestructura | DB/worker/storage/logs/metrics/backups | TBD | TBD | TBD | `not_measured` | proveedor/entorno | separar fixture/staging/prod |
| Monetización | clicks/attribution/feed/ledger/reconciliation | TBD | TBD | TBD | `not_measured` | H50/partner | click no es booking ni revenue |
| Delivery | intentos/canal/retries | TBD | TBD | TBD | `contract_only` | H28 | HotelAlertEvent no prueba delivery externo |

Antes de activar tráfico automático deben existir `budget`, `owner`, `alert_threshold`, `kill_switch` y `rollback`. Un coste desconocido se trata como desconocido, no como cero.

---

## 6. Instrumentación, feedback y experimentos

### Eventos actuales a verificar

- `dashboard_view`, `quick_search_executed`, `watchlist_refresh`, `alert_created`, `alert_triggered`, `search_empty_results` en la allowlist actual de `/ux/events`;
- eventos de dominio `HotelAlertEvent`, separados de comportamiento UX;
- `SupportFeedback` con `feedback_type=bug|idea|general`;
- logs de sweep `hotel_sweep_cycle`, `hotel_sweep_disabled` y errores del job.

**Gap conocido:** H04 define eventos `hotel_*`, pero la allowlist actual de `backend/app/api/v1/ux.py` no demuestra todavía esa taxonomía hotelera completa. No contabilizar métricas H04 como instrumentadas hasta cerrar ese gap.

### Experimentos/personalización/monetización

| Área | Estado inicial | Evidencia necesaria |
|---|---|---|
| H51 experimentos | `contract_only` | spec, asignación, exposure, SRM, guardrails, rollback y decision record |
| H49 personalización | `contract_only` | perfil, `recommended`, explicación, reset/delete, cache isolation |
| H50 monetización | `contract_only`/`not_operational` | partner aprobado, links allowlisted, consent, feed, ledger y reconciliación |
| H52 feedback | `measured` para endpoint/modelo; outcomes TBD | consultas agregadas, triage, severidad, TTA/TTT/TTFA/TTR |

---

## 7. Flags y deuda

### Ficha de flag

```text
flag_name: TBD
current_effective_value: TBD
source: env/config/code
owner: TBD
readers_and_entrypoints: TBD
scope: TBD
last_changed_at: TBD
last_exercised_at: TBD
telemetry: TBD
kill_switch_dependency: TBD
expiry_or_review_at: TBD
decision: keep_active | keep_fixture | deprecate | remove | unknown
```

Prioridad inicial de auditoría:

- `HOTEL_FEATURE_ENABLED`;
- `HOTEL_PROVIDER`;
- `HOTEL_SWEEP_ENABLED`;
- `HOTEL_SWEEP_INTERVAL_SECONDS`;
- `HOTEL_PROVIDER_TIMEOUT_SECONDS`;
- `HOTEL_PROVIDER_MAX_RETRIES`;
- `HOTEL_PROVIDER_CACHE_TTL_SECONDS`;
- `HOTEL_GEOCODER_ENABLED`;
- `MAKCORPS_API_KEY` (existencia/configuración, nunca valor);
- `HOTEL_MOCK_FIXTURE_PATH`;
- `NOTIFICATION_WORKER_ENABLED` como control separado.

**Advertencia:** H43 documenta que algunos entrypoints leen flags de forma distinta y que el job directo puede saltarse `HOTEL_SWEEP_ENABLED`. No marcar el kill switch como verificado solo por inspeccionar `.env`.

---

## 8. Checklist de calidad del paquete

- [ ] periodo, commit, schema/config revision y entorno registrados;
- [ ] datos fixture/demo separados de staging/live;
- [ ] cada métrica tiene fórmula y denominador;
- [ ] eventos duplicados/perdidos y cambios de schema anotados;
- [ ] provider/mercado tienen scope, capability, coste, quota y owner;
- [ ] no se confunde `HotelAlertEvent` con delivery;
- [ ] no se confunde click con booking/revenue;
- [ ] no se presenta Mock como live;
- [ ] no se presentan contratos como implementación;
- [ ] flags auditadas en API, worker y job directo;
- [ ] feedback agregado y redacted;
- [ ] privacidad, términos y retención revisados;
- [ ] release/rollback/recovery evidence adjunta;
- [ ] revisión crítica y QA completados;
- [ ] `DecisionRecord` creado para cada decisión real;
- [ ] siguiente roadmap enlazado desde las decisiones aprobadas;
- [ ] fecha de expiración de la evidencia registrada.

---

## 9. Resultado de esta plantilla

```text
review_id: TBD-opaque
status: evidence_incomplete
measured_claims: TBD
approximate_claims: TBD
not_measured_claims: TBD
contract_only_claims: TBD
blocked_claims: TBD
provider_decisions: none_yet
market_decisions: none_yet
next_roadmap: not_created
approver: TBD
```

Esta plantilla está lista para rellenarse con una ejecución real. Hasta entonces, el estado correcto es `evidence_incomplete`.
