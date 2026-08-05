# H51 — Experimentos hoteleros con hipótesis y guardrails

**Estado:** COMPLETA como contrato de producto/analítica/release; motor de experimentación, asignación sticky, exposición, tripwires y QA automatizado pendientes  
**Fecha:** 2026-08-05  
**Área:** producto / analítica / frontend / backend / QA / privacidad / accesibilidad / operación  
**Fuente de verdad:** sí para diseñar, aprobar, ejecutar y cerrar experimentos de `/hoteles`  
**Fase del roadmap:** H51  
**Depende de:** [H04 — métricas y eventos](../../product/hoteles-metrics-events-h04.md), [H21 — estados y recuperación](hoteles-state-matrix-h21.md), [H35 — legal, privacidad y consentimiento](../backend/hoteles-legal-privacy-disclosure-deeplinks-h35.md), [H40 — browser QA](hoteles-visual-manual-crossbrowser-qa-h40.md), [H43 — flags, canary y kill switches](../backend/hoteles-flags-canary-killswitch-h43.md), [H45 — release y rollback](../backend/hoteles-release-canary-smoke-rollback-h45.md), [H49 — personalización prudente](hoteles-personalizacion-prudente-h49.md), [H50 — monetización y afiliación](../backend/hoteles-monetizacion-afiliacion-atribucion-h50.md)  
**Handoff:** [H52 — feedback de usuarios y correcciones de confianza](../../plans/2026-08-04-hoteles-master-roadmap.md#fase-h52--feedback-de-usuarios-y-correcciones-de-confianza)

> H51 permite aprender sobre la experiencia sin sacrificar veracidad, privacidad, accesibilidad, coste, seguridad ni capacidad de volver atrás. Un aumento de clicks no compensa una UI que oculta fees, confunde tracking con favorito o presenta datos demo como live.

## 1. Decisión de alcance

H51 define el contrato para experimentar con cambios de producto hotelero:

- hipótesis falsables y decisión previa de éxito/fallo;
- variante/control, unidad de asignación y stickiness;
- exposición real en el punto donde la variante se muestra;
- métrica primaria, denominador, ventana y guardrails;
- tamaño de muestra, MDE, potencia, stopping y análisis;
- privacidad, consentimiento, minimización y redaction;
- igualdad funcional de ES/EN, dark/light, mobile, teclado, zoom y lector de pantalla;
- flags, canary, kill switch, rollback y compatibilidad con H43/H45;
- novelty effect, SRM y calidad de datos;
- decision record inmutable y paquete de evidencia.

H51 no introduce por sí sola un proveedor A/B, SDK externo, CMP, sistema de identidad ni servicio de analítica. La implementación debe reutilizar helpers y contratos existentes, o justificar una decisión posterior con revisión de coste, privacidad, salida y seguridad.

### 1.1. No objetivos

H51 no permite experimentar con:

- veracidad de precios, freshness, provenance, disponibilidad o estados demo;
- wording que oculte fees, afiliación, partner, variación de precio o límites del provider;
- consentimiento, derechos de privacidad, ownership, autenticación o seguridad;
- accesibilidad mínima, foco, teclado, contraste, reduced motion o información equivalente;
- contenido legal obligatorio, disclosure o política de retención;
- `price`, `distance` o `stars` como órdenes objetivos de H17;
- `affiliate_bonus`, comisión, margen, payout o partner priority ocultos;
- datos personales sensibles o inferencias de perfil;
- una conversión de clicks en booking, revenue o confianza sin evidencia contractual;
- cambios irreversibles de esquema, histórico, tracking, alertas o lifecycle.

Un test puede estudiar copy, jerarquía o CTA únicamente si las dos variantes conservan la misma verdad, condiciones, disclosure, capacidad y accesibilidad.

## 2. Estado actual comprobable

### 2.1. Flags y rollout

`docs/reference/feature-flags.md` confirma que Viru no usa hoy un sistema centralizado único de feature flags. Las activaciones se controlan principalmente por variables de entorno y runbooks de dominio.

H43 define flags hoteleras y perfiles `local_demo`, `local_fixture`, `staging_canary`, `prod_off` y `prod_gradual`, pero deja explícito que:

- la resolución unificada API/worker/job está pendiente;
- ausencia de flag no es todavía fail-closed en todos los caminos;
- no existe selector real de cohortes, porcentajes o regiones para hoteles;
- el workflow canary genérico de H45 es scaffolding, no tráfico dividido probado;
- el cambio de entorno puede requerir reinicio para procesos ya arrancados.

Por tanto, un flag global o un entorno distinto no puede llamarse automáticamente experimento A/B. Mientras no exista asignación y exposición, el resultado es `flagged_release` o `manual_canary`, no experimento causal.

### 2.2. Analytics y UX tracking

`frontend/src/modules/shared/analytics.ts` expone `trackEvent` hacia gtag, Plausible y PostHog cuando existen. Convierte propiedades a primitivas, pero no aplica todavía una allowlist hotelera ni añade automáticamente `schema_version`.

`frontend/src/lib/uxTracking.ts` expone `trackUxEvent` para usuarios autenticados y envía metadata compactada a `/ux/events`. No demuestra aún `event_id`, `search_session_id`, dedupe de Strict Mode/retry o una identidad de exposición experimental.

`backend/app/api/v1/ux.py` mantiene una allowlist general (`ALLOWED_EVENTS`) y persiste eventos autenticados. H04 documenta que la taxonomía hotelera, las propiedades redacted y la allowlist específica todavía requieren implementación y tests.

Estos helpers son piezas reutilizables, no una infraestructura experimental completa. H51 no declarará métricas causales a partir de eventos sin exposición, denominador, dedupe y calidad verificadas.

### 2.3. Métricas actuales y gaps

H04 ya define funnel, métricas de utilidad, confianza, retención, operación y negocio, además de guardrails para veracidad, freshness, comparabilidad, alertas, privacidad, accesibilidad, rendimiento, coste y ownership.

Lo que aún no se demuestra:

- asignación determinista a control/variante;
- stickiness entre sesiones/dispositivos;
- evento de exposición en el momento de render efectivo;
- vínculo entre exposición, búsqueda y resultado sin PII;
- cálculo por variante con denominadores fiables;
- SRM, intervalos, MDE, potencia o stopping documentados;
- tripwire automático que apague una variante;
- decision record inmutable y firmado por owner/QA;
- suite browser que verifique que las variantes mantienen el contrato.

## 3. Ficha obligatoria de experimento

Ningún experimento puede arrancar con una descripción de “probar un cambio”. Debe existir una ficha versionada:

```text
ExperimentSpec {
  experiment_id: opaque-stable-key
  schema_version
  title
  owner_product
  owner_engineering
  owner_qa
  status: draft | approved | running | paused | stopped | shipped | reverted
  hypothesis
  target_population
  exclusions
  control_definition
  variant_definitions
  assignment_unit
  assignment_method
  stickiness_policy
  exposure_event
  primary_metric
  primary_denominator
  secondary_metrics
  guardrails
  minimum_detectable_effect
  power_target
  significance_policy
  analysis_window
  minimum_runtime
  stop_rules
  privacy_and_consent_basis
  accessibility_requirements
  cost_budget
  rollback_action
  decision_record_ref
  created_at
  approved_at nullable
  expires_at nullable
}
```

### 3.1. Hipótesis falsable

La hipótesis debe tener esta forma:

> En [población], cambiar [intervención] frente a [control] cambiará [métrica primaria] en [dirección y magnitud mínima] durante [ventana], sin cruzar [guardrails].

Ejemplo válido:

> En usuarios autenticados que completan una búsqueda hotelera con resultados, una CTA primaria “Seguir precio” junto a la oferta, frente al control actual, aumentará la tasa de creación confirmada de tracking en al menos 5% relativo durante 14 días, sin empeorar error de creación, abandono, feedback de precio, accesibilidad ni coste por búsqueda.

Ejemplo inválido:

> Probar un diseño más bonito y ver si funciona.

Una hipótesis no puede ocultar que la variante cambia semántica, disponibilidad, precio, consentimiento o derechos.

### 3.2. Variantes

Cada variante debe declarar:

- qué cambia exactamente;
- qué permanece idéntico;
- screenshots o wireframes de desktop/mobile;
- copy ES/EN;
- estados idle/loading/success/empty/partial/stale/error/auth;
- comportamiento de teclado, lector de pantalla, zoom y reduced motion;
- flag/selector que la activa;
- rollback a control sin migración destructiva.

Control no significa “versión antigua desconocida”: debe congelarse una referencia de código/configuración para poder reproducirla.

## 4. Asignación, stickiness y exposición

### 4.1. Unidad de asignación

La unidad debe corresponder al journey que se quiere medir:

| Caso | Unidad recomendada | Regla |
|---|---|---|
| onboarding o primera victoria | sesión anónima efímera o usuario autenticado | no mezclar una persona consigo misma en variantes durante la ventana |
| CTA de tracking | usuario autenticado o sesión estable | conservar variante hasta crear/abandonar el flujo |
| copy de alerta/inbox | usuario autenticado | stickiness durante el lifecycle de la alerta |
| ranking recomendado | usuario + query fingerprint | nunca contaminar órdenes objetivos |
| partner/afiliación | cohorte aprobada y consentida | no asignar si consentimiento requerido está ausente |
| rendimiento/provider | entorno o cohorte técnica | separar del experimento de UX y registrar configuración |

No usar email, nombre, `user_id` crudo ni datos sensibles como valor de bucket exportado.

### 4.2. Asignación determinista

La asignación futura debe ser estable y reproducible:

```text
bucket = hash(experiment_id + pseudonymous_assignment_key) % 10000
```

Requisitos:

- algoritmo y versión documentados;
- rangos de variante declarados antes de arrancar;
- exclusiones aplicadas antes de asignar;
- control/variante mutuamente excluyentes;
- `holdout` opcional y explícito;
- no reasignar por refresh, render o cambio de orden de resultados;
- cambiar población, pesos o algoritmo crea nueva versión del experimento;
- identidad anónima expira según política y no se usa para reconstruir perfil oculto.

Hasta que este mecanismo exista, usar solo cohortes manuales/allowlist de bajo riesgo y etiquetar la evidencia como `manual_canary`, no como A/B generalizable.

### 4.3. Exposición efectiva

Registrar exposición solo cuando la persona realmente pudo ver/usar la variante:

- la ruta/superficie alcanzó el estado visible relevante;
- el elemento no quedó oculto por loading, error, viewport o permiso;
- se conoce `experiment_id`, versión, variante, superficie, locale, tema y dispositivo;
- se deduplica por sesión/usuario y experimento según contrato;
- no se dispara exposición por precarga, prefetch, componente desmontado o asignación sin render.

Evento objetivo:

```text
hotel_experiment_exposed {
  schema_version
  experiment_id
  experiment_version
  variant
  surface
  exposure_state: rendered | interactive
  assignment_unit: session | user | query
  locale
  device_class
  theme
  consent_state
  pseudonymous_exposure_ref
}
```

No incluir query completa, email, token, `hotel_id` innecesario, tracking ID, target, children ages, URL externa o payload de provider.

## 5. Métricas y análisis

### 5.1. Métrica primaria

Toda métrica primaria debe declarar:

- evento numerador;
- unidad/denominador elegible;
- ventana desde exposición;
- población y exclusiones;
- dirección esperada;
- MDE o umbral relevante;
- cómo se tratan retries, duplicados, cancelaciones y estados partial/stale;
- si mide intención, operación confirmada o resultado de dominio.

Ejemplos:

```text
tracking_creation_rate
= unique hotel_tracking_created
  / unique eligible hotel_tracking_started with exposure

useful_search_rate
= searches with completed status success|partial and result_count > 0
  / unique eligible hotel_search_submitted

partner_click_rate
= unique validated hotel_partner_clicked
  / details with approved deeplink and required disclosure
```

Un click no es booking; un `tracking_started` no es tracking creado; una alerta persistida no es delivery; una exposición no es interacción.

### 5.2. Métricas secundarias

Pueden incluir:

- apertura de detalle;
- comprensión de contexto de precio;
- favorito creado;
- tracking creado y fallo de creación;
- retorno por alerta;
- tiempo hasta resultado;
- uso de filtros;
- explicación abierta;
- reset/desactivación;
- feedback de precio/condición;
- stale/partial/error rate;
- coste por búsqueda o sweep;
- latencia p50/p95.

No convertir una métrica secundaria en primaria después de mirar resultados sin registrar un cambio de spec y nueva ventana.

### 5.3. Calidad estadística

Antes de lanzar, el owner debe decidir:

- tamaño mínimo de muestra o regla de no inferencia con muestra baja;
- MDE y potencia objetivo;
- horizonte fijo o método secuencial aprobado;
- tratamiento de múltiples variantes/múltiples métricas;
- ventana de maduración y novelty effect;
- exclusión de bots, QA interno, fixtures y tráfico no elegible;
- prueba de SRM (Sample Ratio Mismatch);
- intervalo de confianza o criterio de decisión;
- qué significa “inconcluso”.

No detener por el primer resultado favorable ni declarar ganador por superar cero con muestra insuficiente. Si hay SRM, exposición duplicada, cambio de provider o ruptura de tracking, el resultado es inválido o requiere reinicio.

### 5.4. Novelty y persistencia

Separar:

- efecto de novedad de los primeros días;
- comportamiento estabilizado después de exposición repetida;
- usuarios nuevos frente a recurrentes;
- primera búsqueda frente a retorno por tracking/alerta.

El reporte debe mostrar la evolución temporal y no ocultar que una variante solo funcionó mientras era nueva.

## 6. Guardrails no negociables

Un experimento se pausa, revierte o queda inválido si cruza un límite aprobado, aunque la métrica primaria mejore.

| Área | Guardrail mínimo | Acción |
|---|---|---|
| Veracidad | aumento de `fixture_only`, copy live sin evidencia, precio/final/availability mal rotulado | apagar variante inmediatamente |
| Freshness/provenance | subida de stale/unknown sin warning o procedencia perdida | pausar y revisar |
| Comparabilidad | feedback de condiciones/fees incompatibles o ranking no auditable | revertir |
| Privacidad | PII, URL completa, token, query raw, edad de menores o payload provider | apagar, preservar evidencia redacted, incidente H42 |
| Consentimiento | atribución/cookie/telemetry no permitida | bloquear finalidad comercial |
| Ownership | acceso o acción cross-user | P0, detener experimento |
| Accesibilidad | foco perdido, teclado bloqueado, contraste/regresión, reduced motion ignorado | no promover |
| i18n | copy faltante, fechas/moneda incorrectas, overflow ES/EN | pausar variante |
| Rendimiento | p95, error rate, requests o bundle fuera de presupuesto | rollback técnico |
| Coste | provider/API o atribución sobre budget | kill switch de operación |
| Alertas | duplicados, ruido o evento sin snapshot/owner | detener retorno |
| Partner | deeplink no allowlisted, disclosure ausente, click confundido con booking | bloquear salida |

Los umbrales numéricos se fijan por experimento con H04/H35/H37/H40/H43/H45. No se inventa un porcentaje universal como evidencia actual.

### 6.1. Guardrails de no inferioridad

Para seguridad, confianza, accesibilidad y veracidad se debe definir una banda de no inferioridad. Una variante que mejora conversión pero empeora materialmente cualquiera de estas dimensiones no es ganadora.

No se admite “compensar” una fuga de privacidad con más tracking ni una regresión de accesibilidad con más clicks.

## 7. Consentimiento y privacidad

- La analítica esencial y la experimentación de producto deben clasificarse por finalidad antes de instrumentarse.
- Si el experimento usa cookies, identificadores persistentes, partner attribution o perfilado, necesita el consentimiento/basis aprobado por H35/H50.
- La ausencia de consentimiento no debe expulsar a la persona del flujo principal ni cambiarle una condición de precio.
- Puede usarse control privacy-safe sin atribución comercial, sesión efímera o no participar, según política aprobada.
- No usar experimentos para eludir opt-out, retención o borrado.
- El bucket visible en logs/analytics debe ser opaco y mínimo.
- Reset de personalización H49 elimina sus señales sin cambiar una asignación necesaria para una exposición ya registrada; el reporte debe documentar este caso.
- Cambiar de cuenta, logout o expiración invalida contexto privado y no puede reutilizar la variante/caches de otra cuenta sin política explícita.

## 8. Variantes, i18n y accesibilidad

Cada variante debe tener equivalencia funcional:

- mismo precio observado, condiciones, freshness, warnings y disclosure;
- mismos filtros y posibilidad de volver a orden objetivo;
- mismo acceso por teclado y lector de pantalla;
- labels, `aria-describedby`, `role=status/alert` y retorno de foco verificados;
- textos ES/EN completos, no traducción de último momento;
- números, fechas, monedas y pluralización por locale;
- dark/light con contraste equivalente;
- mobile y zoom 200% sin overflow ni CTA escondida;
- reduced motion sin perder feedback de estado;
- no mostrar un experimento a usuarios con fixture/provider off de modo que confunda capacidades.

No experimentar con una variante que solo es accesible en un idioma o viewport y llamarla ganadora global.

## 9. Flags, canary y rollback

### 9.1. Estados

```text
draft → approved → running → paused/stopped → shipped/reverted
```

`running` exige spec aprobada, flag resuelta, exposure event funcional, guardrails observables y rollback probado en el entorno elegido.

### 9.2. Rollback

El rollback debe ser una acción concreta:

- apagar flag/variante en la resolución efectiva H43;
- detener cohortes nuevas;
- conservar control, datos y decision record;
- invalidar cache/config incompatible si aplica;
- no borrar históricos, tracking, alertas ni eventos;
- verificar `/hoteles`, estados, analytics redacted, cero provider calls no permitidas y browser smoke;
- comunicar impacto y owner;
- abrir postmortem H42 si hubo guardrail P0/P1.

Un cambio de `.env` sin reiniciar procesos o sin comprobar la decisión efectiva no es rollback probado. Mientras no exista resolver dinámico, el experimento solo puede tener canary manual y la evidencia debe decirlo.

### 9.3. Interacciones con H49/H50

- H49: no usar comisión para variant assignment ni dejar que `recommended` personalizado se mezcle con control sin declarar versión/policy.
- H50: no variar disclosure, consentimiento o precio observado para mejorar CTR; la monetización debe permanecer independiente.
- Un experimento de partner requiere registry, allowlist, consent, budget y kill switch; si falta uno, no se lanza.

## 10. Decision record y paquete de evidencia

Cada experimento produce un registro con:

```text
experiment_id/version
spec commit/config revision
owner approvals
population/exclusions
assignment method/ranges
exposure count by variant
eligible denominator by variant
SRM result
primary metric + interval/decision
secondary metrics
novelty/time slices
all guardrail values
privacy/consent state
accessibility/i18n/browser evidence
cost/provider budget
incidents/pauses/rollbacks
final decision: ship | iterate | inconclusive | revert
reason and residual risk
```

El record es inmutable una vez cerrado; una corrección crea una nueva versión enlazada. No incluir PII, URLs completas, tokens, raw provider payload ni screenshots con cuentas reales.

### 10.1. Decisiones válidas

- `ship`: efecto suficientemente respaldado, guardrails dentro de límites y rollback disponible;
- `iterate`: señal prometedora, pero hipótesis o variante necesita ajuste y nueva spec;
- `inconclusive`: muestra, calidad o diferencia insuficiente;
- `revert`: guardrail, regresión o hipótesis refutada;
- `blocked`: no se pudo ejecutar con seguridad o faltó evidencia.

“Ganó porque tuvo más clicks” no es un decision record válido.

## 11. Tests y gates de aceptación

### Unit/contract

- spec incompleta no puede pasar a `approved`;
- hipótesis incluye población, cambio, métrica, dirección y MDE/umbral;
- control y variantes son mutuamente excluyentes;
- asignación determinista devuelve la misma variante para la misma clave/version;
- cambio de experiment/version no reutiliza bucket incompatible;
- exclusiones y consent state se aplican antes de asignar;
- exposición solo ocurre cuando la variante se renderiza/está disponible;
- exposición duplicada por Strict Mode/retry/prefetch se deduplica;
- métricas separan intención, operación confirmada, dominio y conversión;
- denominadores excluyen estados no elegibles y fixtures;
- SRM, muestra insuficiente y novelty se marcan correctamente;
- guardrail cruzado pausa/revierte sin borrar datos;
- flags off producen control/neutral o `not_available`, nunca una variante oculta;
- H49/H50 fields no entran como features comerciales o sensibles;
- telemetry redacts private/sensitive fields.

### Integration/browser

1. abrir `/hoteles` en control sin experimento y verificar baseline;
2. asignar una allowlist manual en una fixture y comprobar stickiness;
3. verificar exposición solo tras render efectivo;
4. ejecutar búsqueda, detalle, favorito/tracking o alerta según la hipótesis;
5. comprobar numerador/denominador y dedupe con refresh, back/forward y retry;
6. simular stale, partial, provider off, demo, auth_required y error;
7. probar ES/EN, dark/light, mobile, teclado, lector de pantalla, zoom y reduced motion;
8. disparar cada guardrail y verificar pause/rollback;
9. cambiar cuenta/logout y comprobar aislamiento;
10. activar H50/partner solo en una fixture consentida y verificar disclosure/allowlist;
11. cerrar decision record con evidencia redacted;
12. repetir smoke H45 post-rollback.

### Gate H51

H51 podrá considerarse implementada cuando:

1. cada experimento tiene spec, hipótesis falsable, owners y decisión previa;
2. control/variantes, asignación, exclusiones y stickiness son reproducibles;
3. exposición efectiva se registra con schema, dedupe y redaction;
4. métrica primaria tiene denominador, ventana, MDE, stopping y análisis definidos;
5. guardrails de veracidad, privacidad, consentimiento, ownership, a11y, i18n, rendimiento, coste y partner están instrumentados;
6. SRM, novelty, muestra insuficiente y estados inconclusos se detectan;
7. variantes mantienen la semántica de precio, estado, disclosure y accesibilidad;
8. flags/canary/kill switch/rollback funcionan en el entorno real o el resultado queda `manual_canary/blocked`;
9. decisión final es reproducible en un record inmutable y no contiene PII;
10. H04/H35/H40/H43/H45 revisan la evidencia antes de promover;
11. H49 no pierde explicabilidad ni reset, y H50 no usa el experimento para esconder afiliación o confianza;
12. H52 recibe feedback clasificado y riesgos residuales, no solo un porcentaje de conversión.

**Resultado contractual:** H51 queda definida como disciplina de aprendizaje segura para `/hoteles`. El repositorio tiene flags por entorno, helpers de analytics, contratos de métricas y runbooks de canary, pero todavía no demuestra un motor A/B, asignación sticky, exposición experimental, tripwires automáticos ni decision records implementados. La ejecución debe comenzar con fixtures/canary manual de bajo riesgo y permanecer `blocked` para rollout general hasta cerrar los gates.
