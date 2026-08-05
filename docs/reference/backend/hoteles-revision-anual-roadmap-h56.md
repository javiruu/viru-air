# H56 — Revisión anual de producto, providers, costes y siguiente roadmap hotelero

**Estado:** COMPLETA como contrato de gobernanza y revisión; revisión anual ejecutada, instrumentación completa, provider aprobado, reconciliación financiera y siguiente roadmap pendientes  
**Fecha:** 2026-08-05  
**Área:** producto / analítica / backend / frontend / providers / costes / negocio / legal / seguridad / QA / operación  
**Fuente de verdad:** sí para revisar el estado de `/hoteles`, renovar o retirar decisiones y aprobar el siguiente ciclo  
**Fase del roadmap:** H56  
**Depende de:** H04, H07, H08, H37, H41, H43, H45, H49, H50, H51, H52, H53, H54, H55  
**Relacionado con:** H01 visión, H05 confianza, H06 provider-neutral, H09 sweeps, H10/H11 modelo y migración, H22 favoritos/tracking, H26-H29 alertas/delivery/lifecycle, H32-H40 UX/QA/seguridad/operación
**Artefactos operativos iniciales:** [plantilla de revisión anual](../../qa/hoteles-h56-annual-review-template.md) · [plantilla de DecisionRecord](../../qa/hoteles-h56-decision-record-template.md) · [primer baseline local](../../qa/hoteles-h56-annual-review-2026-08-05.md) · [DecisionRecord inicial](../../qa/hoteles-h56-decision-record-2026-08-05.md)  
**Handoff:** No existe una H57 predefinida. La revisión aprobada debe crear o seleccionar el siguiente ciclo como artefacto versionado y enlazarlo desde su `DecisionRecord`; su existencia no implica aprobación.

> H56 es el mecanismo que evita que `/hoteles` acumule features, providers, flags y costes sin volver a preguntar si siguen aportando valor. Una revisión anual no es un resumen de actividad: es una decisión fechada, con denominadores, evidencia, owners, riesgos, reversibilidad y una priorización explícita del siguiente ciclo.

---

## 1. Propósito y frontera

H56 debe responder, con evidencia suficiente para el alcance revisado:

1. ¿La experiencia ayuda a encontrar, entender y vigilar una estancia mejor que en la revisión anterior?
2. ¿Los datos y estados degradados siguen siendo honestos?
3. ¿Qué providers, mercados y capacidades merecen continuar, limitarse, sustituirse o retirarse?
4. ¿Cuál es el coste por búsqueda, observación, tracking, alerta y retorno, separado por provider y entorno?
5. ¿Las métricas miden operaciones reales o solo clicks y contratos documentales?
6. ¿Los experimentos y personalización aportaron aprendizaje sin empeorar confianza, privacidad, accesibilidad o coste?
7. ¿La monetización, si existe, está reconciliada y sigue separada del ranking editorial?
8. ¿Qué flags, adapters, contratos, migraciones, fixtures y código ya no tienen owner o justificación?
9. ¿Qué riesgos de continuidad, seguridad, legal, soporte y deuda bloquean el siguiente paso?
10. ¿Qué se debe hacer después, qué queda explícitamente fuera y qué no se debe volver a construir por inercia?

### Dentro de H56

- paquete de evidencia anual y calidad de datos/métricas;
- revisión de funnel, retención, confianza, soporte, costes y operación;
- revalidación de providers, mercados, capabilities, cuotas, terms y privacidad;
- revisión de flags, experimentos, personalización, monetización y código muerto;
- decision record por provider/mercado/capability y por iniciativa importante;
- renovación, promoción, remediación, throttling, pausa, sunset o rechazo;
- backlog priorizado y roadmap siguiente con dependencias, presupuesto y gates;
- cadencia de revisiones intermedias y condiciones de reabrir decisiones.

### Fuera de H56

- declarar implementadas métricas, SLO, canary, provider, afiliación o drills porque el contrato los enumera;
- elegir un servicio externo sin investigación, aprobación y plan de salida;
- modificar código, borrar flags o archivar documentación sin un owner y un decision record;
- fijar objetivos universales sin baseline, denominador y contexto;
- confundir el número de features entregadas con valor para la persona;
- usar una mejora de clicks para justificar una regresión de veracidad, privacidad, accesibilidad o coste.

---

## 2. Baseline actual comprobable

H56 se construye sobre estas evidencias ya documentadas. Las partes marcadas como pendientes no deben reaparecer en el informe anual como si fueran resultados medidos.

| Área | Evidencia actual | Qué sí permite afirmar | Qué sigue sin demostrarse |
|---|---|---|---|
| Métricas/eventos | H04 define taxonomía, fórmulas, denominadores, guardrails y reutilización de `trackEvent`/`trackUxEvent` | existe una semántica de medición y privacidad de referencia | instrumentación hotelera completa, dedupe, exposición fiable, dashboards y métricas causales |
| Feedback | H52 define feedback contextual, triage, severidad, ownership, correcciones, TTA/TTT/TTFA/TTR y QA | hay una taxonomía para aprender de problemas de confianza | flujo implementado completo, inbox/triage automático y métricas de feedback de producción |
| Makcorps | H07 lo mantiene limitado/experimental por 429, mismatch de IDs, errores absorbidos, coste/cuota desconocidos y deeplinks no aprobados | existe una decisión condicionada y lista de bloqueos | estabilidad, cobertura, coste, canary y aprobación como provider principal |
| Providers adicionales | H08 deja candidatos en `candidate_pending_canary` y Mock como `fixture_only` | existe una matriz de onboarding y evidencia oficial inicial | cuenta/plan, contrato real, canary, coste y provider productivo aprobado |
| Coste/rate limits | H37 define benchmark, cuota, locks, budget y circuit breaker como contrato | hay criterios para medir economía operativa | ledger de coste hotelero, límites live y benchmark de producción completo |
| Observabilidad | H41 define eventos, cardinalidad, redaction, health y SLO candidatos | hay vocabulario y diseño de observabilidad | métricas persistentes, dashboards, alertas y SLO activos |
| Flags/canary | H43 define perfiles y kill switches; H45 documenta workflow canary nominal | existe una política de activación y rollback | resolver central, cohortes, traffic split, canary hotelero y rollback ejecutado |
| Personalización | H49 limita la personalización a `recommended`, explícita y reversible | hay guardrails contra ranking oculto | perfil hotelero, motor `recommended`, explicación y controles implementados |
| Monetización | H50 separa PartnerLink, AttributionIntent, ConversionReport y ledger | existe política de independencia editorial y privacidad | partner aprobado, deeplink allowlisted, consentimiento, conversion feed y reconciliación financiera |
| Experimentos | H51 define spec, asignación, exposición, guardrails y análisis | existe contrato para no llamar A/B a un flag manual | motor de asignación sticky, exposición, SRM, tripwires y decision records ejecutados |
| Catálogo/mercados | H53/H54 definen matching, calidad, MarketSpec, capabilities, entrada y salida | existe control documental para identidad y expansión | gold set operativo, registro live, cobertura validada y mercados adicionales aprobados |
| Continuidad | H55 define backup/restore, RPO/RTO, leases, reconciliación y drills | existe protocolo de recuperación y criterios de evidencia | backup restaurable, RTO/RPO medidos, worker productivo y drill pasado |

**Regla de baseline:** el informe H56 debe añadir para cada afirmación `source`, `observed_at`, `environment`, `sample/window`, `denominator`, `policy_version` y nivel de confianza. Si falta alguno, la afirmación queda `unknown`, `not_measured` o `contract_only`, no se rellena por inferencia.

---

## 3. Paquete de evidencia anual

La revisión comienza con un artefacto versionado, por ejemplo `HotelAnnualReview` o equivalente. No es obligatorio usar este nombre, pero deben existir las mismas fronteras:

```text
HotelAnnualReview {
  review_id: opaque-stable-key
  review_period_start_utc
  review_period_end_utc
  generated_at_utc
  product_version
  schema_versions
  config_revision_sanitized
  market_scope
  provider_scope
  data_sources
  metric_catalog_version
  evidence_expiry
  owners
  reviewers
  decision_status: draft | evidence_incomplete | approved | superseded
  decision_record_ref
}
```

### 3.1. Evidencia mínima

- funnel y retorno: búsquedas iniciadas/completadas, resultados útiles, detalle, favorito, tracking creado, alertas abiertas, acciones y partner clicks;
- calidad: freshness, provenance, partial/stale/error, comparabilidad, feedback de precio/condiciones y mapping ambiguity;
- tracking: activos, pausados, expirados, snapshots elegibles, revalidaciones y alertas trazables;
- operación: runs, leases, retries, 429, timeout, coste, backlog, delivery y recovery evidence;
- providers/mercados: capability matrix, cobertura por scope, cuota, latencia, coste, términos y fecha de revisión;
- privacidad/seguridad: redaction, ownership, incidentes, accesos, retención y cambios legales;
- UX: browser/a11y/performance, mobile, locale, theme, errores y feedback contextual;
- experimentos/personalización: specs, exposición, cohortes, guardrails, resultados, resets y rollbacks;
- monetización: links, disclosure, consentimientos, conversion reports, refunds/reversals y reconciliación si aplica;
- deuda: flags, adapters, dependencias, migraciones, contratos sin owner, código muerto candidato y documentación drift;
- continuidad: backup/restore, RPO/RTO observados, drills, postmortems y acciones abiertas.

### 3.2. Calidad del dato

La plantilla inicial de QA mantiene el paquete en `evidence_incomplete` hasta que se ejecute una revisión real: [hoteles-h56-annual-review-template.md](../../qa/hoteles-h56-annual-review-template.md). Las decisiones deben partir de [hoteles-h56-decision-record-template.md](../../qa/hoteles-h56-decision-record-template.md), sin aprobar providers o mercados por defecto.

Cada métrica debe acompañarse de:

```text
numerator
 denominator
eligible_population
window
segment
sampling_or_exclusions
dedupe_policy
missingness
source_event_versions
confidence
```

El informe debe señalar explícitamente:

- eventos perdidos o duplicados;
- cambios de schema durante la ventana;
- tráfico fixture/demo, QA, bots o provider off;
- cambios de flags/configuración;
- denominadores inestables;
- mercados con poca muestra;
- provider outages y ventanas sin observación;
- métricas que solo son proxies;
- gaps de instrumentación que hacen imposible una conclusión.

No se compara un año contra otro si la definición, población o instrumentation cambió sin una reconciliación documentada.

---

## 4. Revisión de producto y confianza

### 4.1 Valor del journey

Revisar el flujo completo, no pantallas aisladas:

```text
entrada → búsqueda → resultado comparable → detalle → favorito/tracking
→ histórico/alerta → retorno → acción externa o decisión informada
```

Preguntas mínimas:

- ¿Dónde abandona la persona y con qué estado?
- ¿Cuántas búsquedas recuperan un empty/partial/stale/error de forma honesta?
- ¿Se crean trackings desde ofertas reconstruibles o filas ambiguas?
- ¿El histórico ayuda a decidir o solo añade superficie?
- ¿Las alertas provocan acción o ruido?
- ¿La persona distingue favorito, tracking, evento persistido y delivery?
- ¿El copy sigue diciendo la verdad cuando provider/mercado está pausado?
- ¿El precio mostrado conserva fees, moneda, condiciones y freshness suficientes?
- ¿La experiencia ES/EN, mobile, dark/light y a11y mantiene la misma capacidad?

### 4.2 Trust review

Una iniciativa no puede promoverse si mejora conversión mientras empeora materialmente:

- veracidad del precio/disponibilidad;
- freshness/provenance/comparabilidad;
- ownership o privacidad;
- accesibilidad;
- coste o latencia;
- spam/noise de alertas;
- claridad del partner/disclosure;
- posibilidad de recuperar o retirar la decisión.

Las métricas de confianza no se descartan como “edge cases”: son guardrails de producto.

---

## 5. Revisión de providers, mercados y capabilities

### 5.1 Ficha anual de provider

Cada provider y modo (`mock`, manual, canary, live) debe tener una ficha con:

```text
provider_id
status: fixture_only | manual | candidate | approved_limited | approved_live | paused | sunset
owner
contract_source_and_accessed_at
terms/privacy/source_retention
markets_and_scope
capabilities_and_exclusions
requests_attempts_429_5xx_timeout
latency_p50_p95
valid_rate_and_comparability
mapping_success_ambiguity_duplicate_rate
cost_source_unit_and_total
quota_source_and_remaining
incident_history
kill_switch_and_rollback
last_reviewed_at
next_review_at
recommendation
```

`unknown` o `not measured` no equivale a capacidad, cobertura, estabilidad o value for money. Un `approved_live` sin evidencia vigente debe degradarse a `review_required` o `paused` según riesgo.

### 5.2 Decisiones posibles

Para cada provider, mercado y capability emitir exactamente una decisión principal:

Los estados canónicos persistidos son `renew_promote`, `remediate_throttle`, `pause_contain`, `sunset_deprecate` y `reject_keep_fixture`; las etiquetas humanas pueden mostrarse como “renew/promote”, “remediate/throttle”, “pause/contain”, “sunset/deprecate” y “reject/keep_fixture”.

- **`renew_promote`:** continuar o ampliar solo el alcance demostrado;
- **`remediate_throttle`:** conservar limitado mientras se corrigen gaps, cuota, coste o calidad;
- **`pause_contain`:** detener llamadas, deeplinks, delivery o mercado sin borrar históricos;
- **`sunset_deprecate`:** retirar adapter/flag/capability con migración y comunicación;
- **`reject_keep_fixture`:** no abrir producción; conservar únicamente Mock/fixtures/manual.

Cada decisión debe incluir motivo, evidencia, scope, owner, fecha efectiva, expiración y rollback/exit path.

### 5.3 Entrada y salida

H54 es la fuente para mercados. H56 no puede ampliar una ciudad/país solo porque el provider conteste o la métrica agregada parezca buena. Revisar:

- MarketSpec y estado actual;
- cobertura por ciudad/temporada/ocupación/estancia;
- identidad H53 y tasa de ambigüedad;
- precio/fees/cancelación/moneda/timezone;
- coste, latencia, límites y soporte;
- términos, privacidad y deeplinks;
- feedback y confianza por mercado;
- kill switch, rollback y recovery evidence.

Un mercado puede seguir activo con scope reducido, quedar `paused` o retirarse. Retirar no autoriza borrar históricos, aliases, feedback, tracking o evidencia de decisiones.

---

## 6. Revisión de costes y FinOps hotelero

Separar siempre tres costes:

1. **Provider/API:** mapping, city, rates, revalidación y sweeps;
2. **Producto/infraestructura:** DB, worker, storage, logs, métricas, traces, backups y delivery;
3. **Negocio/monetización:** partner clicks, atribución, feeds, ledger, reconciliación, refunds y payout.

Por cada coste registrar:

```text
cost_source
currency
unit
volume
unit_price_or_unknown
period
allocated_scope
actual_or_estimated
owner
budget
variance
```

### Gates de coste

- Si `unit_price_or_unknown=unknown`, no presentar coste preciso ni ampliar tráfico automático.
- Comparar coste por búsqueda, resultado útil, tracking activo, snapshot elegible, alerta accionable y partner click, no solo gasto total.
- Separar dev/staging/fixture de producción.
- Incluir retries, fallos, mapping y health probes en el coste del provider.
- Incluir observabilidad, backup/restore y retención en el coste de operación.
- Explicar picos por canary, outage, replays o migración.
- Cada provider/mercado tiene budget, owner, alert threshold, kill switch y plan de reducción.
- El coste no justifica ocultar warnings, saltarse redaction o reducir retención legal.

### Decisión económica

Una feature/provider solo se promueve si el valor incremental y la calidad justifican el coste dentro del presupuesto aprobado. Si faltan conversiones o ingresos reconciliados, usar utilidad/retención/confianza y marcar `business_value_not_observed`, no inventar ROI.

---

## 7. Revisión de experimentos, personalización y monetización

### 7.1 Experimentos H51

Para cada experimento revisar:

- hypothesis/spec/version/owner/status;
- control/variant, assignment unit, stickiness y exposure real;
- numerador/denominador, ventana, exclusiones y sample size;
- SRM, novelty, cambios de provider/flags y datos faltantes;
- primary metric y guardrails de confianza, privacidad, a11y, coste y rendimiento;
- rollback/kill switch y decision record;
- aprendizaje válido, inconcluso o inválido;
- si procede, `ship`, `iterate`, `hold`, `revert` o `retire`.

Un flag manual sin exposición medible no produce evidencia causal. Un resultado con SRM o tracking roto no debe alimentar el roadmap como ganador.

### 7.2 Personalización H49

Revisar por separado:

- declared, contextual e inferred;
- orden objetivo `price/distance/stars` frente a `recommended`;
- explicación, límites, cold start, reset/delete y cache isolation;
- fairness/neutralidad, stale/partial/demo y provider off;
- opt-out, retención y eventos redacted;
- si el perfil aporta valor o solo complejidad/deuda.

Si no existe perfil y motor implementados, registrar `contract_only` y no crear una plataforma por inercia.

### 7.3 Monetización H50

Revisar:

- partner registry, términos, disclosure y consentimiento;
- PartnerLink/AttributionIntent/ConversionReport/Ledger;
- distinguir clicks, conversiones, bookings, stays, refunds y reversals;
- budget de API separado del budget de atribución;
- reconciliación, variancias, fraude, payout y revocación;
- independencia de ranking y slots patrocinados;
- kill switch y salida sin romper discovery.

Si no existe partner aprobado/feed/ledger, la conclusión correcta es `not_operational`, no una estimación de ingresos basada en clicks.

---

## 8. Auditoría de flags, dependencias y código muerto

### 8.1 Ficha de flag

Cada flag candidata debe registrar:

```text
flag_name
owner
default
environments
readers_and_entrypoints
scope
last_changed_at
last_exercised_at
telemetry
kill_switch_dependency
expiry_or_review_at
remove_or_keep_decision
```

Auditar especialmente:

- flags que no tienen reader;
- flags cuyo nombre ya no coincide con su alcance;
- flags off que ocultan código nunca probado;
- flags que no controlan todos los entrypoints (API/worker/job directo);
- flags legacy de providers/mercados retirados;
- flags con secretos o valores efectivos no auditables;
- flags que pueden quedar activas tras restart/canary sin evidencia.

### 8.2 Código y dependencias

No borrar código solo porque no tenga tráfico reciente. Clasificar cada candidato:

- `keep_active`: reader y owner comprobados;
- `keep_fixture`: útil para H44/QA, no producción;
- `deprecate`: reemplazo definido y ventana de compatibilidad;
- `remove`: sin callers, tests ni contrato, con rollback/commit identificable;
- `unknown`: no tocar hasta reconstruir dependencia.

Revisar adapters, migraciones, schemas, helpers analytics, campos legacy, tests snapshot, dependencies NPM/Python, runbooks y docs. Eliminar una flag o adapter debe tener una comprobación de que no es kill switch, rollback path o compatibilidad V1.

---

## 9. Decision record y gobernanza

### 9.1 Registro mínimo

```text
DecisionRecord {
  decision_id
  review_id
  scope: product | provider | market | capability | flag | experiment | code | cost
  subject
  state: renew_promote | remediate_throttle | pause_contain | sunset_deprecate | reject_keep_fixture
  evidence_refs
  observed_period
  known_unknowns
  risk_summary
  owner
  approver
  effective_at
  expires_at
  rollback_or_exit_path
  follow_up_ticket
  next_review_at
}
```

No se considera una decisión aprobada si solo aparece en una conversación o en una fila sin owner/evidencia/fecha.

### 9.2 Roles

Como mínimo:

- Producto: valor, prioridad, copy y jobs;
- Backend/DB: contratos, datos, migraciones e integridad;
- Infra/FinOps: coste, capacidad, backups, workers y recovery;
- Security/Legal: privacidad, terms, ownership, secretos y deeplinks;
- QA/Accessibility: pruebas, browser, estados y no regresión;
- Negocio: partners, afiliación, ledger y reconciliación;
- Support: feedback, severidad, comunicación y follow-up;
- Approver: acepta riesgo residual y decide el siguiente ciclo.

La organización concreta puede combinar roles, pero no puede omitir las responsabilidades.

---

## 10. Cadencia y revisión continua

H56 es anual como decisión de roadmap, pero no espera doce meses para detectar un incidente:

- **por release/canary:** flags, smoke, rollback, errores, coste y guardrails H45;
- **mensual o por presupuesto:** provider quota, gasto, 429/timeout, backlog, incidents y kill switches;
- **trimestral o ante cambio material:** terms/privacy, capabilities, mercados, partner, schema y deuda crítica;
- **anual:** paquete completo, decisiones, archivo documental y nuevo roadmap.

Un provider, mercado o partner debe revisarse antes de la fecha anual si cambia terms, precio, API schema, cuota, host, privacidad, incidente o capacidad.

---

## 11. Siguiente roadmap: criterios de aprobación

El roadmap siguiente debe ser un documento versionado o una sección fechada, no una lista infinita de deseos. Para cada iniciativa registrar:

```text
initiative_id
problem_or_job
evidence_ref
expected_value
cost_and_capacity
dependencies
privacy/security/legal_review
rollback_path
owner
milestone/gate
not_do_or_defer_reason
```

### Priorización

Ordenar por una combinación explícita de:

- impacto en búsqueda, decisión, tracking, retorno o confianza;
- evidencia de dolor y frecuencia;
- reducción de riesgo/coste/deuda;
- esfuerzo y capacidad disponible;
- dependencias y reversibilidad;
- calidad del dato y claridad de la métrica;
- impacto en mercados/providers y soporte.

No priorizar una feature porque está de moda, porque otra IA la propuso o porque hay un contrato escrito. Un contrato `COMPLETA` no es evidencia de valor ni autorización de implementación.

### Gates de entrada

Una iniciativa no entra en el ciclo siguiente si:

- no tiene problema/job y evidencia;
- no tiene owner y capacidad;
- depende de un provider/servicio no investigado;
- no tiene privacidad/security/legal review cuando corresponde;
- no tiene rollback o plan de retirada;
- la métrica no puede medirse con denominador;
- empeora un P0/P1 conocido sin una decisión explícita;
- confunde fixture/demo con live;
- amplia mercado sin H54;
- promete tracking/delivery sin H09/H26-H28/H55.

### Salidas válidas

El siguiente roadmap puede:

- implementar un contrato pendiente;
- cerrar un P0/P1 de confianza/seguridad/operación;
- hacer un canary limitado;
- sustituir o retirar un provider;
- reducir coste o deuda;
- mejorar un flujo existente;
- archivar/posponer una idea;
- no hacer nada en un área si la evidencia no justifica inversión.

---

## 12. Criterios de cierre H56

H56 está contractualmente completa cuando:

1. existe una plantilla de revisión con periodo, scope, fuentes, owners, expiración y estado;
2. cada métrica incluye denominador, ventana, exclusiones, calidad y nivel de confianza;
3. providers, mercados y capabilities tienen ficha y decisión, sin convertir unknown en aprobación;
4. costes API, infraestructura y monetización están separados y tienen fuente/owner/budget;
5. experimentos, personalización y monetización se revisan con guardrails y no sobreclaims;
6. flags y código muerto se clasifican sin borrar kill switches o compatibilidad legacy;
7. cada decisión tiene evidence refs, owner, approver, fecha, expiración y rollback/exit path;
8. existe una cadencia mensual/trimestral/anual y trigger de revisión extraordinaria;
9. el siguiente roadmap tiene iniciativas, dependencias, capacidad, gates, no-go y razones de aplazamiento;
10. la documentación canónica e índices apuntan al contrato y no hay enlaces rotos.

### H56 implementada vs contractualmente completa

H56 podrá declararse **implementada** solo cuando exista un primer `HotelAnnualReview` aprobado y fechado que:

- use datos reales del periodo, no solo contratos;
- muestre qué métricas están `measured`, `approximate`, `not_measured` o `contract_only`;
- emita decision records por provider/mercado/capability/flag/experimento relevante;
- apruebe, limite o retire algo con owner y fecha;
- publique el siguiente roadmap con al menos una decisión de no hacer;
- tenga revisión de producto, backend/DB, infra/FinOps, security/legal, QA/a11y, negocio y support;
- conserve evidencia redacted y un camino de rollback/exit.

**Resultado H56 actual:** contrato de gobernanza aprobado. No se declara ejecutada la revisión anual, aprobado ningún provider comercial, medida una métrica causal completa, reconciliado un ledger financiero ni aprobado el siguiente roadmap. El siguiente ciclo debe empezar por producir el paquete de evidencia y el primer `DecisionRecord` real; después debe crearse y enlazarse el artefacto versionado del ciclo que resulte aprobado.
