# `/hoteles` — Plan Maestro para convertirlo en el tracker hotelero preferido

**Estado:** vivo — plan maestro de ejecución  
**Fecha:** 2026-08-04  
**Área:** producto / frontend / backend / datos / QA / operación  
**Fuente de verdad del plan:** este documento  
**Referencia de producto:** [Travel Price Drops Hotels](https://travelpricedrops.com/hotels?lng=es)  
**Código actual:** `frontend/src/modules/hotels/`, `backend/app/api/v1/hotels.py`, `backend/app/services/hotels_service.py`

> Este documento es un roadmap de producto y ejecución. No pretende resolver en detalle cada implementación: cada fase debe investigarse en el código real, respetar los contratos existentes y cerrarse con evidencia. La prioridad es no dejar huecos: producto, datos, proveedores, experiencia, confianza, alertas, operación, seguridad, rendimiento, adquisición y QA forman parte del resultado final.

---

## 0. Resumen ejecutivo

La ruta `/hoteles` ya tiene una base técnica considerable: catálogo de hoteles, búsqueda por nombre/ciudad y por área, snapshots, `HotelTrackedOffer`, watchlist, alertas, paridad, comparativas de zona, proveedor mock, integración Makcorps y worker de sweeps. Sin embargo, esa base todavía se percibe como un radar técnico en construcción, no como el lugar natural al que una persona vuelve para encontrar y seguir una estancia.

El objetivo de este plan es llevar `/hoteles` desde esa base hasta un **comparador y tracker de precios hoteleros confiable, rápido, claro y adictivamente útil**, inspirado en las mejores ideas observables de Travel Price Drops sin copiar su marca ni sus decisiones visuales.

El flujo central que debe ganar siempre es:

```text
Destino → fechas → habitaciones/huéspedes → resultados comparables
→ entender el precio real → guardar o seguir una oferta
→ recibir una alerta útil → volver y decidir/reservar
```

El plan no convierte Viru en una OTA ni en un booking engine. Viru descubre, compara, contextualiza, monitoriza y redirige; la reserva final, el cobro y la atención posterior pertenecen al partner externo.

---

## 1. Resultado final esperado

Cuando el plan esté completado, una persona debe poder:

1. Llegar a `/hoteles` y entender en pocos segundos qué puede hacer.
2. Buscar por ciudad, zona, landmark o coordenadas.
3. Elegir entrada, salida, habitaciones, adultos y niños sin ambigüedad.
4. Aplicar filtros y ordenar resultados sin perder el contexto de la estancia.
5. Comparar hoteles por precio total relevante, precio por noche, distancia, categoría, condiciones y señales de confianza.
6. Distinguir claramente entre dato live, dato reciente, snapshot histórico, dato de proveedor parcial y fixture/demo.
7. Abrir el detalle de un hotel u oferta sin perder la búsqueda.
8. Ver por qué un resultado está arriba y qué significa cada precio.
9. Guardar un hotel como favorito sin confundirlo con el seguimiento de precio.
10. Seguir una oferta concreta: hotel + fechas + ocupación + habitación + régimen + cancelación + proveedor/contexto de precio.
11. Ver el histórico, mínimo, máximo, mediana/tendencia, última comprobación y confianza del histórico.
12. Definir alertas sencillas: baja de precio, porcentaje de bajada, vuelve a estar disponible o alcanza objetivo.
13. Recibir alertas dentro de Viru y, cuando el canal esté habilitado, por email/push.
14. Abrir un deeplink de partner con contexto suficiente y con una advertencia honesta de que el precio puede cambiar.
15. Gestionar seguimientos desde `/hoteles`, notificaciones y cualquier futura superficie de cuenta.
16. Usar la experiencia en español e inglés, dark/light y móvil sin perder funciones.
17. Entender cuándo no hay datos, cuándo los datos están obsoletos y qué puede hacer a continuación.

### No se considera terminado si

- el flujo principal depende de datos mock sin estar rotulado;
- el sistema llama “live” a un snapshot viejo;
- un sweep puede dejar de ejecutarse silenciosamente;
- la alerta aparece en base de datos pero nunca llega a la persona;
- el usuario no sabe qué está comparando exactamente;
- los CTAs principales compiten entre sí;
- la pantalla funciona solo en desktop o solo en un tema;
- se añaden más paneles técnicos sin mejorar la decisión de reservar;
- el provider falla y la UI muestra una falsa sensación de disponibilidad;
- no existe evidencia de QA funcional, visual, accesible y operativa.

---

## 2. Principios no negociables

### 2.1. Verdad antes que espectáculo

Cada precio debe tener procedencia, fecha/hora de captura, moneda, condiciones y estado de disponibilidad. Si falta una pieza, se muestra como falta; no se rellena con lenguaje ambiguo.

### 2.2. El usuario sigue una estancia, no un hotel abstracto

El objeto principal es la **oferta/estancia trackeada**, no solo `HotelProperty`. Una misma propiedad puede tener muchas fechas, ocupaciones, habitaciones y políticas distintas.

### 2.3. Búsqueda y tracking son productos relacionados, no el mismo proceso

- Discovery: encontrar y comparar.
- Decision: entender condiciones y elegir.
- Tracking: observar una estancia concreta a lo largo del tiempo.
- Alerting: actuar cuando cambia algo relevante.

### 2.4. Primero la decisión, después la inteligencia secundaria

Paridad, comp sets, señales avanzadas y hoteles cercanos se conservan cuando ayudan a decidir, pero nunca deben desplazar destino, fechas, precio, condiciones, tracking y CTA de salida.

### 2.5. Un sistema degradado debe seguir siendo honesto y útil

Provider caído, rate limit, ausencia de coordenadas, snapshot antiguo o historial corto son estados de producto. Cada uno necesita mensaje, severidad y siguiente acción.

### 2.6. Mobile y accesibilidad son el flujo principal

No se diseñará desktop y se “encogerá” después. El buscador, filtros, cards, detalle, tracking, alertas y deeplinks deben pensarse desde viewport estrecho, teclado, lector de pantalla y reducción de movimiento.

### 2.7. Personalidad Viru sin copiar a Travel Price Drops

Se tomarán referencias funcionales: búsqueda directa, alertas visibles, contexto de ahorro, transparencia de partners y localización. La identidad seguirá siendo Viru: cálida, aeronautical, cercana, premium y con alma en dark y light.

### 2.8. No elegir proveedores externos por memoria

Toda futura integración de proveedor de hoteles, geocoder, email, push, analítica, mapas o monitorización debe pasar por investigación actualizada y por el proceso de selección del repositorio. Usar `gravity_index` para descubrir y comparar servicios; leer documentación oficial antes de decidir; registrar coste, límites, privacidad, SLA y plan de salida.

---

## 3. Base actual que se conserva y deudas que no se deben ocultar

### 3.1. Piezas existentes relevantes

| Área | Estado actual observado | Tratamiento en este plan |
|---|---|---|
| Ruta | `/hoteles` renderiza `HotelRadarPage` | Conservar ruta; evolucionar composición |
| Frontend | Hooks separados para búsqueda, detalle, watchlist, comp sets, alertas y tracked offers | Reutilizar; simplificar jerarquía y contratos |
| Catálogo | `HotelProperty` con normalización de nombre/ciudad | Endurecer identidad, geodatos y cobertura |
| Rates | `HotelRateSnapshot` por provider/estancia | Convertirlo en contrato de observación confiable |
| Tracking | `HotelTrackedOffer` con snapshots y precio actual | Convertirlo en objeto principal de retención |
| Guardados | `HotelWatchlistItem` | Mantener como favorito simple, diferenciado del tracking |
| Alertas | Reglas y eventos, parte de ellos visibles en inbox | Unificar evaluación, dedupe, delivery y preferencias |
| Sweeps | Worker separado, opcional, no arrancado por API | Hacerlo operativamente garantizado y observable |
| Provider mock | Fixtures locales | Usarlo para desarrollo, demo y tests; jamás como dato live |
| Makcorps | Adapter real con riesgo de 429 y cobertura limitada | Evaluar, endurecer o sustituir con un contrato provider-neutral |
| Área/geocoder | Haversine y geocoding interno/externo según flags | Mejorar precisión, cache, fallback y privacidad |
| Paridad | Servicio backend y panel lateral | Relegar a contexto accionable |
| Comp sets | API y UI secundaria | Mantener como “hoteles cercanos/comparativa de zona” |
| QA | Amplia cobertura de backend y QA visual documentada | Convertir en gates repetibles de release |

### 3.2. Riesgos de producto actuales

1. El copy y la realidad del provider no siempre tienen la misma fuerza.
2. “Trackear precio” puede crear un seguimiento con datos insuficientes o sin una estancia totalmente definida.
3. El worker existe, pero la ejecución periódica no está garantizada por el API.
4. El mock tiene fechas y tarifas estáticas; no representa variación real.
5. Makcorps puede estar limitado por rate limiting y por diferencias entre mapping, city y hotel.
6. El resultado principal todavía puede sentirse más como panel técnico que como comparador de compra.
7. Watchlist simple y tracked offer tienen semánticas distintas y requieren una arquitectura de producto explícita.
8. Las alertas persistidas no equivalen automáticamente a alertas entregadas.
9. El precio “más bajo” sin condiciones comparables puede inducir decisiones incorrectas.
10. El historical confidence necesita más señales que el número bruto de snapshots.

---

## 4. Cómo ejecutar este roadmap

### 4.1. Regla de trabajo por fase

Cada fase debe producir:

- objetivo y alcance cerrado;
- inventario de archivos/contratos afectados;
- decisión explícita sobre lo que queda fuera;
- tests o evidencias antes y después;
- actualización de documentación si cambia un contrato;
- migración reversible si toca datos;
- criterio de salida firmado por QA o por el owner de la fase;
- nota de riesgos residuales.

### 4.2. Regla de ownership para IAs

Una IA puede implementar una fase solo después de:

1. leer este plan y las docs canónicas del área;
2. comprobar el estado real del código, no confiar en nombres históricos;
3. identificar dependencias y cambios previos ya completados;
4. escribir o actualizar pruebas relevantes;
5. ejecutar el gate de fase;
6. no introducir servicios externos sin investigación y aprobación;
7. no ampliar una fase con “mejoras cercanas” no previstas.

### 4.3. Formato recomendado de entrega por fase

```markdown:
```

### 4.4. Estados del roadmap

- `PENDIENTE`: todavía no se ha trabajado.
- `BLOQUEADA`: falta una decisión, credencial, proveedor o evidencia.
- `EN CURSO`: una IA tiene ownership activo.
- `EN QA`: implementación terminada; falta gate.
- `COMPLETA`: gate aprobado y documentación actualizada.
- `ARCHIVADA`: fase sustituida por una decisión posterior; conservar motivo.

## 4.5. Registro maestro de ejecución

Este registro evita que el roadmap se interprete como una colección de ideas. Cada fila es una unidad asignable. El owner indicado es el owner principal; las demás disciplinas participan en el gate. `PENDIENTE` no significa que el código actual esté vacío: significa que la fase todavía no ha sido validada dentro de este programa.

| Fase | Estado inicial | Owner principal | Dependencias | Entregable mínimo / gate |
|---|---|---|---|---|
| H00 | COMPLETA | QA/PM | — | Baseline reproducible y matriz hecho/parcial/roto — `docs/qa/reports/2026-08-04-hoteles-h00-baseline.md` |
| H01 | COMPLETA | PM | H00 | Visión, personas, jobs y métricas de valor — `docs/product/hoteles-product-vision-h01.md` |
| H02 | COMPLETA | PM/UX | H00 | Benchmark fechado y separado de inferencias — `docs/benchmarks/2026-08-04-travelpricedrops-hotels-h02.md` |
| H03 | COMPLETA (diseño) | UX/Frontend | H01-H02 | IA, wireflows desktop/mobile, estado URL objetivo y estados límite — `docs/product/hoteles-information-architecture-h03.md` |
| H04 | COMPLETA (contrato) | PM/Analítica | H01-H03 | Taxonomía de eventos, métricas, privacidad, guardrails y definición de done — `docs/product/hoteles-metrics-events-h04.md` |
| H05 | COMPLETA (contrato) | Backend/Producto | H00-H01 | Contrato de freshness, provenance, disponibilidad, comparabilidad y confidence — `docs/reference/backend/hoteles-freshness-provenance-confidence-h05.md` |
| H06 | COMPLETA (contrato) | Backend/Arquitectura | H05 | Contrato provider-neutral V2, envelope, errores, deeplinks y matriz de contract tests — `docs/reference/backend/hoteles-provider-neutral-contract-h06.md` |
| H07 | COMPLETA (auditoría condicionada) | Backend/Producto | H06 | Auditoría Makcorps, matriz de evidencia, decisión limitada, presupuesto y plan de canary — `docs/reference/backend/hoteles-makcorps-audit-h07.md` |
| H08 | COMPLETA (evaluación; onboarding abierto) | Backend/Producto | H06-H07 | Matriz provider-neutral, política de onboarding, canary y salida — `docs/reference/backend/hoteles-provider-onboarding-h08.md` |
| H09 | COMPLETA (contrato operativo; implementación pendiente) | Infra/Backend | H06-H08 | Gateway/sweep con leases, dedupe, retries, budget, breaker, health y rollback — `docs/reference/backend/hoteles-sweep-gateway-h09.md` |
| H10 | COMPLETA (contrato de dominio; migración pendiente) | Backend/DB | H05-H09 | StayQuery, ocupación, oferta, snapshot, matching, fingerprints y compatibilidad — `docs/reference/backend/hoteles-stay-offer-model-h10.md` |
| H11 | COMPLETA (contrato de migración; implementación pendiente) | DB/Backend | H10 | Expand-and-contract, backfill, doble lectura/escritura, índices, retención y rollback — `docs/reference/backend/hoteles-data-migration-h11.md` |
| H12 | COMPLETA (contrato de destino; implementación pendiente) | Backend/Frontend | H03-H06 | Resolución tipada, confidence, ambigüedad, geocoder limitado y fallback — `docs/reference/backend/hoteles-destination-resolution-h12.md` |
| H13 | COMPLETA (contrato de interacción; implementación pendiente) | Frontend | H03,H10,H12 | Formulario, URL state, validación, submit, recuperación y accesibilidad — `docs/reference/backend/hoteles-search-form-h13.md` |
| H14 | COMPLETA (contrato de filtros; implementación pendiente) | Frontend/Backend | H13,H10-H12 | Filtros y orden con resultados explicables — `docs/reference/backend/hoteles-filters-ranking-h14.md` |
| H15 | COMPLETA (contrato de resultados; implementación pendiente) | Backend | H05,H06,H09-H14 | Contrato versionado de resultados y paginación — `docs/reference/backend/hoteles-results-pagination-h15.md` |
| H16 | COMPLETA (contrato visual; implementación pendiente) | Frontend/UX | H13-H15,H31 | Cards con precio, condiciones, freshness y CTA — `docs/reference/frontend/hoteles-result-cards-h16.md` |
| H17 | COMPLETA (contrato de ranking; implementación pendiente) | Backend/Producto | H14-H16 | Ranking determinista y explicación de orden — `docs/reference/backend/hoteles-ranking-explainability-h17.md` |
| H18 | COMPLETA (contrato de detalle; implementación pendiente) | Frontend | H10,H13,H15-H17 | Detalle navegable con retorno a búsqueda — `docs/reference/frontend/hoteles-detail-navigation-h18.md` |
| H19 | COMPLETA (contrato de precio; implementación pendiente) | Backend/Producto | H05,H06,H10-H11,H15-H18 | Total/noches/fees comparables y transparencia — `docs/reference/backend/hoteles-price-total-fees-h19.md` |
| H20 | COMPLETA (contrato de comparación; implementación pendiente) | Frontend/Backend | H05,H10,H15,H17-H19 | Paridad y cercanos relegados y accionables — `docs/reference/backend/hoteles-provider-comparison-nearby-h20.md` |
| H21 | COMPLETA (contrato de estados; implementación pendiente) | Frontend/QA | H05,H12-H20 | Matriz transversal de idle/loading/success/empty/partial/stale/error y recuperación — `docs/reference/frontend/hoteles-state-matrix-h21.md` |
| H22 | COMPLETA (contrato de semántica; implementación pendiente) | Producto/Backend | H10,H13,H18-H21 | Favorito simple frente a tracking, ownership, lifecycle y migración — `docs/reference/backend/hoteles-favorite-vs-tracking-h22.md` |
| H23 | COMPLETA (contrato de creación; implementación pendiente) | Backend/Frontend | H05,H09-H15,H18-H22 | Tracking desde oferta real, snapshot inicial, estados, idempotencia y reconstrucción — `docs/reference/backend/hoteles-real-offer-tracking-h23.md` |
| H24 | COMPLETA (contrato; implementación pendiente) | Frontend/Backend | H05,H10,H19,H21-H23 | Histórico ligado a oferta/estancia, elegibilidad, agregados, gaps, estados y alternativa accesible al gráfico | docs/reference/backend/hoteles-price-history-curve-h24.md |
| H25 | COMPLETA (contrato; implementación pendiente) | Producto/Backend | H05,H19,H21,H23-H24 | Freshness, provenance, confidence, recomendaciones prudentes y refresh seguro | docs/reference/backend/hoteles-freshness-confidence-actions-h25.md |
| H26 | COMPLETA (contrato; implementación pendiente) | Backend | H19,H21-H25 | Reglas, baselines, elegibilidad, cooldown, dedupe, ownership y eventos deterministas | docs/reference/backend/hoteles-alert-rules-dedupe-h26.md |
| H27 | COMPLETA (contrato; implementación pendiente) | Backend/Frontend | H26 | Inbox privado, ownership estricto, lectura y deep links contextuales correctos | docs/reference/backend/hoteles-private-inbox-deeplinks-h27.md |
| H28 | COMPLETA (contrato; implementación pendiente) | Backend/Infra | H27, decisión de servicio | Delivery hotelero, canales, reintentos, preferencias, quiet hours y observabilidad | docs/reference/backend/hoteles-delivery-retries-preferences-h28.md |
| H29 | COMPLETA (contrato; implementación pendiente) | Frontend/Backend | H23-H28 | Lifecycle seguro: pausa, edición, expiración, archivado, eliminación, ownership, cascadas e idempotencia — docs/reference/backend/hoteles-lifecycle-pause-edit-expire-delete-h29.md |
| H30 | COMPLETA (contrato; implementación pendiente) | Producto/Backend | H10,H13-H15,H17,H19,H24 | Calendario y flexibilidad de fechas, capabilities, comparabilidad, coste y rollout — docs/reference/backend/hoteles-flexible-dates-calendar-h30.md |
| H31 | COMPLETA (contrato; implementación pendiente) | UX/Frontend | H02-H03,H16,H21 | Dirección visual Warm-Luxe hotelera, jerarquía, estados, responsive, motion y handoff — docs/reference/frontend/hoteles-visual-direction-states-h31.md |
| H32 | COMPLETA (contrato; implementación pendiente) | Frontend/QA | H16,H21,H31 | Responsive sin overflow, zoom, teclado y CTAs accesibles — docs/reference/frontend/hoteles-responsive-accessible-ctas-h32.md |
| H33 | COMPLETA (contrato; remediación pendiente) | QA/Frontend | H13,H16,H18,H27,H32 | Auditoría WCAG 2.2 AA, prioridades P0/P1/P2 y gate de evidencia — docs/reference/frontend/hoteles-wcag-accessibility-audit-h33.md |
| H34 | COMPLETA (contrato; remediación pendiente) | Frontend/i18n | H13,H16,H23,H27 | ES/EN, fechas civiles, monedas de origen, pluralización y timezones — docs/reference/frontend/hoteles-localization-dates-currency-timezones-h34.md |
| H35 | COMPLETA (contrato; implementación y revisión legal/security pendientes) | Legal/Security | H19,H27,H28 | Disclosure, consentimiento, retención, ownership, redaction y deeplinks — [contrato H35](../reference/backend/hoteles-legal-privacy-disclosure-deeplinks-h35.md) |
| H36 | COMPLETA (contrato; instrumentación y optimización pendientes) | Frontend | H13-H21,H31-H35 | Presupuesto de rendimiento, Web Vitals, primer resultado, requests, assets y gates móvil — [contrato H36](../reference/frontend/hoteles-performance-web-vitals-h36.md) |
| H37 | COMPLETA (contrato; implementación y benchmark pendientes) | Backend/DB | H09,H11,H15,H23-H28,H35-H36 | Benchmark, rate limits, locks y coste máximo — [contrato H37](../reference/backend/hoteles-benchmark-rate-limits-locks-cost-h37.md) |
| H38 | COMPLETA (auditoría/contrato; remediación pendiente) | Security/Backend | H10-H29,H35-H37 | Ownership, secretos, SSRF y abuso auditados — [contrato H38](../reference/backend/hoteles-ownership-secrets-ssrf-abuse-h38.md) |
| H39 | COMPLETA (estrategia/matriz; implementación de huecos pendiente) | QA | H06,H10-H29,H33-H38 | Pirámide de tests y huecos explícitos — [contrato H39](../reference/backend/hoteles-test-pyramid-gaps-h39.md) |
| H40 | COMPLETA (contrato; rerun browser y aprobación humana pendientes) | QA/Frontend | H21,H31-H39 | Browser QA dark/light/mobile/intermedio — [contrato H40](../reference/frontend/hoteles-visual-manual-crossbrowser-qa-h40.md) |
| H41 | COMPLETA (contrato; instrumentación, dashboards y SLO pendientes) | Observabilidad/Backend | H06,H09,H26-H28,H37-H40 | Correlación E2E, métricas, logs redacted, health, SLO y gates — [contrato H41](../reference/backend/hoteles-observability-e2e-h41.md) |
| H42 | COMPLETA (contrato/runbook; simulacros y owners pendientes) | Infra/Support | H09,H28,H38,H41 | Incidentes hoteleros, diagnóstico, contención, recovery, rollback y comunicación — [runbook H42](../runbooks/hoteles-incidentes-recovery-h42.md) |
| H43 | COMPLETA (contrato; resolver unificado, canary y kill switches pendientes) | Infra/Backend | H09,H35,H41-H42 | Flags, perfiles, canary, rollout gradual y kill switches — [contrato H43](../reference/backend/hoteles-flags-canary-killswitch-h43.md) |
| H44 | COMPLETA (contrato; seed, reset, fault profiles y E2E pendientes) | Backend/QA | H06,H10,H39,H42-H43 | Dataset demo, fixtures de fallos y reproducción local — [contrato H44](../reference/backend/hoteles-seed-demo-fallos-h44.md) |
| H45 | COMPLETA (contrato; smoke E2E, canary real y rollback probado pendientes) | Release/QA | H32-H44 | Release readiness, smoke, canary, promoción y rollback — [contrato H45](../reference/backend/hoteles-release-canary-smoke-rollback-h45.md) |
| H46 | COMPLETA (contrato; implementación del flujo, auth contextual, eventos y QA browser pendientes) | UX/Frontend | H13,H16,H21,H31-H34,H40,H44-H45 | Primera victoria sin tutorial largo — [contrato H46](../reference/frontend/hoteles-primera-victoria-h46.md) |
| H47 | COMPLETA (contrato; agregador, URL state, deep links, ownership V2, lifecycle visual y QA pendientes) | Producto/Frontend | H24-H29,H40,H45-H46 | Resumen “mis hoteles” y retorno útil — [contrato H47](../reference/frontend/hoteles-mis-hoteles-reengagement-h47.md) |
| H48 | COMPLETA (contrato; parser URL hotelero, SavedHotelSearch, share token opcional, restore y QA pendientes) | Frontend/Backend | H10-H15,H22,H27,H29,H34-H35,H40,H47 | Búsqueda guardada/compartible sin fuga privada — [contrato H48](../reference/backend/hoteles-busquedas-guardadas-compartibles-h48.md) |
| H49 | COMPLETA (contrato; perfil hotelero, recommended, controles, integración y QA pendientes) | Producto/Frontend | H17,H34,H38,H47-H48 | Personalización prudente y explicable — [contrato H49](../reference/frontend/hoteles-personalizacion-prudente-h49.md) |
| H50 | COMPLETA (contrato; partner, deeplinks, consentimiento, ledger, reconciliación y QA pendientes) | Producto/Negocio | H04,H08,H19,H28,H35,H37-H38,H41,H43,H45,H49 | Monetización, afiliación y atribución responsable — [contrato H50](../reference/backend/hoteles-monetizacion-afiliacion-atribucion-h50.md) |
| H51 | COMPLETA (contrato; motor de experimentación, asignación, exposición, tripwires y QA pendientes) | PM/Analítica | H04,H21,H35,H40,H43,H45,H49-H50 | Experimentos con hipótesis y guardrails — [contrato H51](../reference/frontend/hoteles-experimentos-hipotesis-guardrails-h51.md) |
| H52 | COMPLETA (contrato; flujo contextual, triage, correcciones, privacidad y QA pendientes) | Producto/Support | H04,H21,H25,H27,H35,H38,H40,H42,H45,H47,H50-H51 | Feedback clasificado y correcciones de confianza — [contrato H52](../reference/frontend/hoteles-feedback-correcciones-confianza-h52.md) |
| H53 | COMPLETA (contrato; shadow matching, cola, merge/split, migración y QA pendientes) | Backend/DB | H07,H10-H12,H38-H39,H41,H44-H45,H52 | Matching y deduplicación auditable con métricas — [contrato H53](../reference/backend/hoteles-catalogo-matching-deduplicacion-h53.md) |
| H54 | COMPLETA (contrato; registro de mercados, capabilities, canary, salida y QA pendientes) | PM/Backend | H07-H08,H12,H34,H37-H38,H41-H45,H53 | Mercados hoteleros con criterios de entrada y salida — [contrato H54](../reference/backend/hoteles-mercados-entrada-salida-h54.md) |
| H55 | COMPLETA (contrato; backup/restore, worker productivo y recovery drill pendientes) | Infra/DB | H11,H28,H38,H41-H45,H54 | Continuidad, restore, reconciliación y recovery drill medido — [contrato H55](../reference/backend/hoteles-continuidad-disaster-recovery-h55.md) |
| H56 | COMPLETA (contrato; revisión anual ejecutada y siguiente roadmap pendientes) | PM/Arquitectura | H04,H07-H08,H37,H41,H43,H45,H49-H55 | Gobernanza anual, decisiones de provider/mercado/coste y siguiente roadmap — [contrato H56](../reference/backend/hoteles-revision-anual-roadmap-h56.md) |

### 4.6. Matriz de tratamiento del trabajo existente

| Superficie actual | Tratamiento inicial | Evidencia que debe pedir la IA antes de tocarla |
|---|---|---|
| `HotelRadarPage` y hooks | Conservar y reordenar | H00 baseline, H03 IA, H31 dirección visual |
| `HotelTrackedOffer` | Extender con compatibilidad | H10 contrato canónico, H11 migración/backfill |
| `HotelWatchlistItem` | Conservar como favorito simple | H22 semántica y tests de no confusión |
| `HotelRateSnapshot` | Conservar y endurecer | H05 provenance, H10/H11 condiciones e índices |
| Makcorps adapter | Auditar antes de prometer | H07 contract tests, 429, cobertura y coste |
| Mock provider | Conservar para tests/demo | H44 fixtures realistas y rotulado no-live |
| Worker de sweeps | Convertir en operación garantizada | H09 scheduler, H41 observabilidad, H42 runbook |
| Alert rules/events/inbox | Extender delivery y dedupe | H26-H28 ownership, cooldown y delivery |
| Paridad/comp sets | Relegar, no borrar | H20 evidencia de utilidad y estados insuficientes |
| CSS/i18n Viru | Respetar tokens y ampliar localmente | H31-H34 contrato UI, temas, locale y a11y |
| Docs de cierre histórico | No invalidar; añadir delta | H00 contraste actual y actualización de fuente de verdad |

### 4.7. Regla de trabajo paralelo frente a bloqueos de release

Una IA puede desarrollar contratos, componentes y flujos con fixtures controlados antes de que exista un provider real, siempre que etiquete el resultado como `fixture-only`, no use copy de disponibilidad live y añada un test de sustitución por provider. Lo que no puede hacer es declarar “tracking real listo”, activar una promesa pública o conectar un canal de delivery sin cerrar los gates bloqueantes.

Las siguientes condiciones bloquean la declaración de “tracker real listo para lanzamiento”, aunque se pueda seguir desarrollando UI en paralelo:

1. H07/H08 no han producido una matriz de capacidades y mercados soportados.
2. H10/H11 no han definido compatibilidad con tracked offers existentes, backfill y rollback.
3. H09 no garantiza sweeps, locks, retries y métricas.
4. H26-H28 no demuestran dedupe y entrega de alertas.
5. H35/H38 no han revisado privacidad, ownership y deeplinks.
6. H40/H45 no han aportado evidencia de browser QA, canary y rollback.

---

## 5. Mapa de dependencias y gates

```text
H00-H04 Fundamentos y baseline
        ↓
H05-H09 Verdad de datos, proveedor y scheduler
        ↓
H10-H15 Contratos de búsqueda y estancia
        ↓
H16-H21 Resultados, detalle y comparación
        ↓
H22-H26 Tracking, histórico y alertas
        ↓
H27-H31 Experiencia visual, accesibilidad y localización
        ↓
H32-H36 Rendimiento, seguridad y operación
        ↓
H37-H41 Activación, crecimiento, monetización y lanzamiento
        ↓
H42-H45 Mejora continua y escala
```

### Gates globales

- **Gate A — Producto definido:** no se implementa UI nueva con semántica ambigua.
- **Gate B — Datos confiables:** no se presenta tracking serio sin provider/status/freshness definidos.
- **Gate C — Búsqueda usable:** el happy path y los estados vacíos/error están cubiertos.
- **Gate D — Tracking real:** una alerta creada puede evaluarse, deduplicarse y entregarse.
- **Gate E — Release UI:** dark/light/mobile/a11y/visual QA pasan.
- **Gate F — Operación:** sweeps, proveedores, costes y fallos tienen runbook y métricas.
- **Gate G — Lanzamiento:** canary, rollback, soporte y métricas de producto están preparados.

---

# BLOQUE A — Dirección, baseline y contrato de producto

## Fase H00 — Kickoff, inventario y baseline reproducible

**Objetivo:** congelar una fotografía real de `/hoteles` antes de cambiarlo.

**Requisitos:**

- Registrar rutas, componentes, hooks, endpoints, modelos, migraciones, workers, flags, fixtures y tests.
- Ejecutar y guardar baseline de tests backend hotelero, typecheck/build frontend y QA visual disponible.
- Medir tiempos de búsqueda, tamaño de payloads, errores de consola y estados visibles.
- Identificar discrepancias entre docs históricas y código actual.
- Crear una tabla de “hecho / parcial / roto / no verificado”.

**Gate:** cualquier IA futura puede saber qué existía antes de su fase y reproducir el baseline.

## Fase H01 — Visión de producto, usuarios y trabajos a resolver

**Objetivo:** convertir “que sea como Travel Price Drops” en necesidades comprobables.

**Requisitos:**

- Definir personas: escapada urbana, vacaciones familiares, viajero sensible a precio, usuario que ya tiene hotel, usuario flexible, usuario recurrente.
- Definir jobs-to-be-done y frustraciones: precio cambiante, fees ocultas, condiciones incomparables, no saber cuándo comprar, miedo a perder la bajada.
- Priorizar el job principal sobre funcionalidades accesorias.
- Definir qué significa “tracker predilecto”: frecuencia de retorno, seguimientos activos, alertas útiles, confianza, conversión de deeplink y retención.

**Gate:** cada funcionalidad posterior debe poder vincularse a un job y a una métrica.

## Fase H02 — Benchmark funcional y de confianza

**Objetivo:** estudiar referencias sin copiar.

**Requisitos:**

- Documentar Travel Price Drops, comparadores conocidos, trackers y patrones relevantes.
- Separar hechos observados de inferencias.
- Comparar: búsqueda, filtros, cards, precio total, alertas, calendario, favoritos, partners, legal, localización, mobile y estados degradados.
- Registrar qué patrones no encajan con Viru o con sus datos disponibles.
- Mantener un pequeño catálogo de screenshots/enlaces/evidencia si el equipo puede conservarlos legalmente.

**Gate:** decisiones de producto basadas en evidencia, no en una imitación literal.

## Fase H03 — Arquitectura de información y navegación

**Estado:** COMPLETA como diseño — contrato documentado en `docs/product/hoteles-information-architecture-h03.md`; la implementación de URL state, filtros y superficies secundarias queda para H13-H18/H22-H23.

**Objetivo:** decidir la jerarquía de la página y de las superficies relacionadas.

**Requisitos:**

- Definir `/hoteles` como búsqueda + resultados + seguimiento, no como dashboard técnico.
- Definir futuro detalle profundo, historial, alertas, favoritos, notificaciones y preferencias.
- Decidir qué estado vive en URL: destino, fechas, ocupación, filtros, orden, página y moneda.
- Decidir qué se preserva al navegar al detalle y volver.
- Definir mobile IA: filtros en sheet/drawer, detalle como panel o ruta, CTA sticky solo si no tapa contenido.
- Cerrar el contrato H03 en `docs/product/hoteles-information-architecture-h03.md`, incluyendo parámetros URL canónicos, wireflows, estados límite, reglas de retorno y handoff.

**Gate:** wireflow aprobado antes de rediseñar componentes.

**Resultado H03:** diseño aprobado. La siguiente IA puede implementar H04/H13/H15/H16/H18/H22 sin reinterpretar la jerarquía. Este cierre no afirma que URL state, filtros, habitaciones/niños o paneles secundarios ya existan; deben implementarse y verificarse en sus fases respectivas, manteniendo `fixture-only` y los bloqueos de provider/tracking definidos en el plan.

## Fase H04 — Métricas de éxito, eventos y definición de “done”

**Estado:** COMPLETA como contrato — `docs/product/hoteles-metrics-events-h04.md`; la instrumentación se implementa por fases posteriores.

**Objetivo:** evitar medir solo “la pantalla carga”.

**Requisitos:**

- Métricas de adquisición: llegada, búsqueda iniciada, búsqueda completada.
- Métricas de utilidad: resultado seleccionado, filtros usados, detalle abierto, precio entendido.
- Métricas de retención: guardado, tracking creado, alertas activadas, retorno por alerta, seguimiento mantenido.
- Métricas de confianza: datos con freshness visible, errores de provider, clicks a partner, discrepancias reportadas.
- Métricas de negocio: deeplink CTR, conversión partner si existe, coste por búsqueda/sweep, margen y coste de notificaciones.
- Definir eventos con privacidad y sin payloads sensibles innecesarios.
- Documentar triggers, propiedades, estados, dedupe, versionado, fórmulas, denominadores y guardrails en `docs/product/hoteles-metrics-events-h04.md`.

**Gate A:** producto, analítica y QA comparten la misma definición de éxito.

**Resultado H04:** contrato aprobado. No implica que los eventos hoteleros estén ya instrumentados; H05/H09/H13/H15/H16/H18/H22-H28/H41 deben implementar y verificar sus partes.

---

# BLOQUE B — Verdad de datos, providers y operación de precios

## Fase H05 — Taxonomía de procedencia, freshness y confianza

**Estado:** COMPLETA como contrato — `docs/reference/backend/hoteles-freshness-provenance-confidence-h05.md`; la implementación queda distribuida entre H06-H11 y las superficies de frontend.

**Objetivo:** que el sistema sepa y comunique qué significa cada dato.

**Requisitos:**

- Definir estados: `live`, `recent`, `cached`, `historical`, `demo`, `partial`, `unavailable`, `stale`.
- Definir TTL por tipo de observación y contexto.
- Guardar `observed_at`, `provider_run_id`, provider, condiciones, moneda, zona horaria y estado.
- Definir cálculo de confianza separado de ranking: no confundir “barato” con “confiable”.
- Definir copy visible y metadata técnica para cada estado.
- Prohibir lenguaje “disponible ahora” si no existe confirmación equivalente.
- Cerrar vocabulario separado de procedencia, freshness, disponibilidad, completitud y confidence, con TTL base, hard caps, migración compatible y tests requeridos en `docs/reference/backend/hoteles-freshness-provenance-confidence-h05.md`.

**Gate:** contrato de freshness aprobado por producto, backend, frontend y QA.

**Resultado H05:** contrato aprobado. No implica que los nuevos bloques de API/UI o el cálculo de confidence ya existan; H06-H11 y las fases de resultados/tracking deben implementarlos y verificarlos.

## Fase H06 — Contrato provider-neutral de hoteles

**Estado:** COMPLETA como contrato — `docs/reference/backend/hoteles-provider-neutral-contract-h06.md`; la adopción V2 queda pendiente de H07-H11 y no sustituye todavía al adapter V1.

**Objetivo:** que ningún provider dicte la arquitectura de negocio.

**Requisitos:**

- Formalizar interfaces V2 de catálogo, búsqueda por área, tarifas, revalidación y deeplink.
- Definir `ProviderResult`, capacidades declarativas, warnings estructurados, errores, rate limit, timeout, retry y partial result.
- Definir normalización de nombres, IDs, moneda, importe, condiciones y estados de disponibilidad.
- Separar “provider responde vacío” de “provider falló”, sin convertir 429/timeout en `sold_out`.
- Definir deeplinks como URLs externas validadas por allowlist, separados de precio y disponibilidad.
- Crear contract tests reutilizables para cualquier provider nuevo y un bridge V1→V2 explícito.
- Documentar las limitaciones actuales: listas desnudas, firmas divergentes, `HotelProviderRun` sin `partial/skipped` y `deep_link` sin allowlist hotelera.

**Gate:** existe un contrato reemplazable y una matriz de tests que permite sustituir Makcorps o añadir otro provider sin reescribir el dominio de usuario. Esto es un cierre de diseño/contrato, no una afirmación de implementación V2 en producción.

**Resultado H06:** contrato aprobado en `docs/reference/backend/hoteles-provider-neutral-contract-h06.md`, con handoff a H07/H08/H09/H10/H11/H15/H35/H41.

## Fase H07 — Auditoría Makcorps y decisión de continuidad

**Estado:** COMPLETA como auditoría condicionada — `docs/reference/backend/hoteles-makcorps-audit-h07.md`; Makcorps queda limitado/experimental y no aprobado como provider principal.

**Objetivo:** decidir con datos si Makcorps sirve para discovery, tracking, ambos o ninguno.

**Requisitos:**

- Medir cobertura real de `/mapping`, `/city`, `/hotel`, fechas, ocupación, precios, fees y deeplinks.
- Reproducir 429, timeouts, payloads vacíos y hoteles sin rates.
- Medir coste, cuotas, latencia, estabilidad y límites por usuario/sweep.
- Verificar que los IDs de catálogo interno se pueden vincular de forma segura.
- Decidir: mantener, limitar a discovery, limitar a refresh dirigido, complementar o retirar.
- Documentar decisión y plan de salida; nunca esconder una limitación en copy.
- Mantener el tracking dirigido y el sweep periódico bloqueados hasta corregir el mismatch de IDs, clasificar errores V2, controlar cuota/coste y validar condiciones.

**Gate:** decisión provider real aprobada con evidencia y presupuesto.

**Resultado H07:** auditoría aprobada. Makcorps no es provider principal; solo puede reabrirse como experimento controlado cuando se cumplan los criterios del documento H07.

## Fase H08 — Evaluación y onboarding de providers adicionales

**Estado:** COMPLETA como evaluación documental; onboarding de producción abierto — [contrato H08](../reference/backend/hoteles-provider-onboarding-h08.md).

**Objetivo:** ampliar cobertura sin crear deuda ni dependencia ciega.

**Requisitos:**

- Elaborar matriz de candidatos: cobertura geográfica, precio total, ocupación, cancelación, fees, deeplinks, API terms, coste, rate limits, privacidad y afiliación.
- Usar `gravity_index` para descubrir opciones de servicios y documentación oficial para verificar capacidades.
- No integrar un provider sin sandbox/fixtures, contrato, límite de coste y plan de desactivación.
- Implementar adapters aislados y contract tests.
- Definir estrategia de deduplicación y orden entre providers.
- Mantener Mock como fallback honesto de fixtures y Makcorps como adapter experimental según H07.
- No aprobar Hotelbeds, LiteAPI, Booking.com, Amadeus ni Expedia sin cuenta/plan, canary, budget y revisión H35/H37/H41.

**Decisión:** abrir onboarding condicionado; no aprobar todavía un provider comercial como principal de producción. Hotelbeds y LiteAPI quedan como candidatos prioritarios para canary, no como integraciones activas.

**Gate:** al menos un provider usable para el caso de uso priorizado y un fallback honesto. El gate queda abierto hasta cerrar la evidencia de canary y seguridad.

## Fase H09 — Scheduler, sweeps y garantías de ejecución

**Estado:** COMPLETA como contrato operativo; implementación y canary pendientes — [contrato H09](../reference/backend/hoteles-sweep-gateway-h09.md).

**Objetivo:** que “tracking diario” deje de ser una promesa manual, pero solo después de demostrar una ejecución coordinada y reversible.

**Requisitos:**

- Elegir despliegue operativo real: worker/cron/job/container según infraestructura vigente.
- Garantizar ejecución idempotente por `StayQuery`, leases distribuidos, locks, backoff, reintentos y límite de concurrencia.
- Reservar budget antes de cada llamada y coordinar circuit breaker por provider/operación.
- Priorizar tracked offers activos, próximos check-in y usuarios con alertas críticas sin prometer frecuencia que el budget no cubra.
- Registrar `completed`, `partial`, `skipped`, `failed`, duración, outcomes, ofertas procesadas y snapshots creados.
- Definir qué ocurre si un sweep se salta una ventana y permitir replay seguro.
- Añadir runbook, health check sin requests implícitos, alertas operativas, redaction y kill switch.
- Mantener los providers externos automáticos desactivados hasta superar H08/H35/H37/H41/H43.

**Decisión:** contrato operativo aprobado; el worker V1 sigue siendo manual/Mock y no se declara tracking diario estable.

**Gate B:** un tracking activo tiene una política de comprobación garantizada y visible, demostrada con canary, budget, lease recovery y rollback.

---

# BLOQUE C — Modelo de estancia, búsqueda y resultados

## Fase H10 — Modelo canónico de estancia/oferta

**Estado:** COMPLETA como contrato de dominio; implementación y migración pendientes — [contrato H10](../reference/backend/hoteles-stay-offer-model-h10.md).

**Objetivo:** representar correctamente lo que el usuario cree que está siguiendo.

**Requisitos:**

- Definir entidades y relaciones: propiedad, estancia, oferta, tarifa, snapshot, provider, habitación, régimen, cancelación y deeplink.
- Separar identidad estable del hotel de la identidad variable de la estancia y del ownership de usuario.
- Normalizar número de habitaciones, adultos, niños, edades, moneda y fechas.
- Definir `StayQuery`, fingerprints de consulta/oferta/snapshot y matching interno/externo.
- Definir invariantes: salida posterior a entrada, ocupación válida, moneda válida, precio no negativo, fee semantics y condiciones comparables.
- Mantener compatibilidad V1 con bridge, doble lectura/escritura y backfill marcado como inferido.
- Evitar que parity, ranking o alertas mezclen habitaciones, regímenes, cancelaciones o ocupaciones distintas.

**Decisión:** contrato canónico aprobado; el modelo actual permanece V1 hasta completar H11/H12/H19/H20.

**Gate:** existe un contrato común para UI, API, DB, alertas y provider, con migración reversible.

## Fase H11 — Migraciones, índices y retención de datos hoteleros

**Estado:** COMPLETA como contrato de migración; implementación, Alembic y backfill pendientes — [contrato H11](../reference/backend/hoteles-data-migration-h11.md).

**Objetivo:** sostener histórico y búsquedas sin degradar la base.

**Requisitos:**

- Aplicar estrategia expand-and-contract sin borrar ni reinterpretar datos V1.
- Crear estructuras canónicas nuevas de forma aditiva y conservar `HotelTrackedOffer`/snapshots legacy durante la transición.
- Añadir índices para búsquedas por hotel, zona, fechas, ocupación, provider, fingerprints, tracked offer y timestamp.
- Ejecutar backfill dry-run y por lotes, reanudable e idempotente, con `needs_review` para ambigüedades.
- Definir doble lectura/escritura, shadow compare, divergencias y flags de rollback.
- Definir dedupe de snapshots por observación, sin borrar histórico válido por accidente.
- Definir retención hot/warm/cold y agregados diarios/semanales.
- Definir cascadas, ownership, integridad referencial y aislamiento de datos de usuario.
- Verificar migraciones en SQLite y PostgreSQL, incluyendo rollback y copia representativa.

**Decisión:** contrato de migración aprobado; el esquema actual permanece V1 hasta cerrar los gates de implementación.

**Gate:** migración revisada por DB/QA y probada con copia representativa, sin FKs huérfanas ni pérdida de históricos.

## Fase H12 — Búsqueda de destino robusta

**Estado:** COMPLETA como contrato de destino; implementación de autocomplete y hardening pendientes — [contrato H12](../reference/backend/hoteles-destination-resolution-h12.md).

**Objetivo:** que “Madrid”, “Madrid Centro”, un aeropuerto, landmark o zona razonable produzcan una búsqueda útil sin ocultar ambigüedad.

**Requisitos:**

- Autocomplete con resultados diferenciados por tipo: ciudad, barrio, landmark, aeropuerto, región.
- Normalización de acentos, alias, idiomas y variantes.
- Geocoder externo solo detrás de adapter, cache, debounce, cancelación y límites; nunca enviar más datos de los necesarios.
- Mostrar país y tipo para evitar ambigüedad.
- Resolver fallback si no hay geocoder o catálogo.
- Registrar confidence/source sin enseñar jerga técnica innecesaria.
- Mantener V1 `/area-resolve` compatible y preparar sugerencias aditivas para H13/H15.

**Decisión:** contrato aprobado; la implementación actual sigue siendo catálogo interno/centroides más fallback Nominatim y no se declara autocomplete completo de producción.

**Gate:** consultas ambiguas piden confirmación; consultas válidas no fallan por acentos; flag off no produce requests externos.

## Fase H13 — Formulario de búsqueda principal

**Estado:** COMPLETA como contrato de interacción; implementación frontend y E2E pendientes — [contrato H13](../reference/backend/hoteles-search-form-h13.md).

**Objetivo:** reemplazar el formulario técnico por un flujo de búsqueda evidente y recuperable.

**Requisitos:**

- Destino, entrada, salida, habitaciones, adultos, niños y moneda cuando corresponda; mantener bridge V1 de `guests` hasta H10/H15.
- Defaults razonables sin ocultar valores.
- Validación inline: fechas, ocupación, destino y estancias imposibles.
- Presets útiles sin encerrar al usuario: fin de semana, fechas flexibles si se implementan.
- Submit con feedback inmediato, estados `validating/resolving/fetching/success/empty/partial/error` y prevención de doble envío.
- Persistencia del estado reproducible en URL y recuperación de búsqueda al volver/back-forward.
- No incluir ownership, credenciales ni thresholds privados en URL/telemetry.
- Copy ES/EN consistente con el glosario Viru y feedback accesible.

**Decisión:** contrato de formulario aprobado; la implementación actual sigue siendo principalmente efímera y V1.

**Gate C:** un usuario nuevo completa una búsqueda válida sin necesitar explicación externa, y una URL válida restaura la intención sin duplicar requests.

## Fase H14 — Filtros y ordenación accionables

**Estado:** COMPLETA como contrato de filtros y ordenación; implementación frontend/backend pendiente — [contrato H14](../reference/backend/hoteles-filters-ranking-h14.md).

**Objetivo:** ayudar a elegir sin convertir la búsqueda en un panel abrumador.

**Requisitos:**

- Precio total/precio por noche, estrellas/categoría, distancia, cancelación, régimen, habitaciones, disponibilidad y proveedor cuando haya datos.
- Filtros compatibles con el contexto de estancia.
- Orden por recomendado, precio, distancia, rating/señal y ahorro cuando exista evidencia.
- Contadores de resultados y filtros activos visibles.
- Aplicar/borrar filtros de forma clara en desktop y mobile.
- No mostrar filtros que el provider no puede respaldar.
- Mantener separado lo soportado hoy por V1 de los filtros futuros definidos por H10/H15.
- Explicar precio nulo, provider parcial, freshness y motivo de ordenación sin inferir estados desde una lista vacía.

**Decisión:** contrato aprobado; V1 conserva `radius_km`, `min_stars`, `max_price` y `sort=price|distance|stars`, mientras `recommended`, `signal`, `savings` y filtros de condiciones quedan condicionados a evidencia y capabilities.

**Gate:** cada filtro modifica resultados de forma explicable y testeable; los controles no respaldados no se prometen al usuario.

## Fase H15 — Contrato de resultados y paginación

**Estado:** COMPLETA como contrato de API y consumo; implementación V2, adaptadores y contract tests pendientes — [contrato H15](../reference/backend/hoteles-results-pagination-h15.md).

**Objetivo:** que frontend y backend compartan un resultado rico, estable y eficiente.

**Requisitos:**

- Contrato versionado con resultados, metadata de búsqueda, freshness, warnings, providers consultados y paginación.
- Diferenciar lista parcial, lista vacía, error total y resultado cacheado.
- Cursor/paginación o estrategia adecuada a la fuente.
- Evitar N+1 para precio, detalle, tracking y estado de favorito.
- Soportar cancelación de requests y búsquedas repetidas.
- Mantener V1 estable y migrar mediante adaptador/feature flag.
- Tests de compatibilidad, ownership, payloads grandes y rollback.

**Decisión:** contrato V2 aditivo aprobado; V1 conserva listas desnudas y `limit/offset`, mientras V2 usará envelope, metadata, warnings, capabilities y cursor opaco o bridge etiquetado.

**Gate:** la UI no necesita adivinar el estado del backend por ausencia de campos.

---

# BLOQUE D — Resultados, detalle y decisión

## Fase H16 — Rediseño de result cards

**Estado:** COMPLETA como contrato visual y funcional; implementación frontend, CSS, i18n y QA visual pendientes — [contrato H16](../reference/frontend/hoteles-result-cards-h16.md).

**Objetivo:** hacer que cada card responda “qué es, cuánto cuesta, bajo qué condiciones y qué puedo hacer”.

**Requisitos:**

- Nombre, ubicación, categoría, imagen si existe con licencia/procedencia, precio comparable y precio por noche solo cuando la unidad esté respaldada.
- Fechas/ocupación resumidas para evitar comparar estancias distintas.
- Política de cancelación, régimen, habitación y fees cuando estén disponibles y asociadas a la misma oferta.
- Señal de última comprobación y provider con lenguaje humano, sin llamar live a un snapshot.
- Una acción primaria por card; guardar hotel, seguir precio, detalle y partner como acciones secundarias diferenciadas.
- Estados de hover/focus/selected/disabled/loading/no-price/partial/stale/error.
- Evitar card dentro de card, botones anidados y acciones ambiguas.
- Mantener separadas la card de catálogo sin oferta y la card de oferta comparable.

**Decisión:** contrato aprobado; la implementación actual sigue mostrando una card de catálogo y una card de área con capacidades distintas. No se inventan condiciones, freshness, fees, disponibilidad ni deeplinks ausentes.

**Gate:** pruebas de comprensión y QA visual confirman que el precio, su contexto y el CTA dominan correctamente.

## Fase H17 — Ranking explicable y señales de recomendación

**Estado:** COMPLETA como contrato de ranking; implementación backend, metadata V2, fixtures y contract tests pendientes — [contrato H17](../reference/backend/hoteles-ranking-explainability-h17.md).

**Objetivo:** ordenar resultados de forma útil sin fabricar “mejor opción”.

**Requisitos:**

- Separar ranking por precio, relevancia de destino, distancia, confianza de datos y preferencias.
- Mantener `price`, `distance` y `stars` deterministas, con `hotel_id` como desempate final.
- Activar `recommended` solo con features comparables, fórmula versionada y explicación respaldada.
- Mostrar explicación breve cuando el orden no sea precio puro.
- No usar rating sin fuente ni mezclar escalas incompatibles.
- Definir política explícita para missing data, provider parcial, stale, paridad, personalización y afiliación.
- Tests de ranking con missing data y providers parciales.
- Preparar espacio para personalización futura sin bloquear MVP ni alterar órdenes objetivos.

**Decisión:** contrato aprobado; V1 conserva sus tres órdenes actuales y `recommended` queda sin activar hasta cerrar H15/H19/H20 y la evidencia de ranking.

**Gate:** un resultado no aparece arriba por una señal invisible o imposible de auditar.

## Fase H18 — Página/panel de detalle de hotel

**Estado:** COMPLETA como contrato de navegación y superficie; implementación frontend, URL state y QA E2E pendientes — [contrato H18](../reference/frontend/hoteles-detail-navigation-h18.md).

**Objetivo:** permitir decidir sin saturar la lista.

**Requisitos:**

- Identidad, ubicación/mapa si aplica, categoría, descripción, condiciones y rates comparables.
- Historial o contexto de precio cuando exista.
- Proveedores y deeplinks con transparencia de afiliación y allowlist.
- Acciones de guardar hotel, seguir precio, crear alerta y compartir si se decide incluir.
- Preservar query original, filtros, sort, cursor/contexto y volver a resultados sin perder selección válida.
- Detalle URL-driven con `hotel_id`, back/forward, refresh y entrada directa segura.
- Estados independientes de loading, partial, stale, provider unavailable, error y propiedad no encontrada.
- Ownership estricto y sin datos privados en URLs compartibles.

**Decisión:** contrato aprobado; la implementación actual mantiene el panel lateral con selección efímera y debe evolucionar a master-detail URL-driven antes de declarar H18 cerrada.

**Gate:** detalle usable en desktop, mobile, teclado y lector de pantalla, con retorno determinista a la búsqueda.

## Fase H19 — Precio total, noches y transparencia de fees

**Estado:** COMPLETA como contrato de precio; implementación backend/frontend, migración V2, i18n, legal y QA pendientes — [contrato H19](../reference/backend/hoteles-price-total-fees-h19.md).

**Objetivo:** evitar que el precio barato sea una trampa de contexto.

**Requisitos:**

- Definir total de estancia, noches y precio equivalente por noche sin doble suma.
- Separar precio observado, precio total calculable y precio final del partner.
- Modelar impuestos, resort fees, limpieza, servicio, tasas locales, depósitos y cargos desconocidos.
- Diferenciar moneda solicitada, observada y mostrada; no convertir sin tasa/versionado válido.
- Comparar solo ofertas con estancia, ocupación, condiciones y semántica de fees compatibles.
- Mantener `amount`/`current_price` V1 sin reinterpretarlos como total garantizado.
- Impedir que snapshots incompatibles, fixtures o errores de provider actualicen tracking o disparen falsas bajadas.
- Exigir disclosure, deeplink validado, copy ES/EN, accesibilidad y siguiente acción segura.
- Handoff explícito a H22-H29 para favoritos, tracking, histórico, alertas, inbox, delivery y lifecycle.

**Gate:** backend, frontend, producto, legal y QA validan escenarios con fees incluidos, parciales, desconocidos, monedas distintas, providers degradados y comparaciones incompatibles.

**Resultado H19:** contrato aprobado; la implementación y el gate de producto siguen pendientes.

## Fase H20 — Comparación de proveedores y hoteles cercanos

**Estado:** COMPLETA como contrato de comparación; implementación V2, comparabilidad completa, frontend y QA pendientes — [contrato H20](../reference/backend/hoteles-provider-comparison-nearby-h20.md).

**Objetivo:** reutilizar paridad y comp sets como ayuda secundaria, separando comparación de tarifas del mismo hotel y exploración de propiedades cercanas.

**Requisitos:**

- Comparar providers solo con estancia, ocupación, habitación, régimen, cancelación, moneda, fees, freshness y disponibilidad compatibles.
- Exponer estados distintos para comparable, one-provider, partial, stale, invalid, provider-degraded y no-data.
- Presentar proveedor más barato solo como menor precio observado cuando las condiciones sean comparables y el disclosure sea visible.
- Explicar diferencia de importe, condiciones, procedencia y freshness.
- Relegar comp sets a “Hoteles cercanos” o “Comparativa de zona”, sin confundirlos con paridad.
- Mantener hotel ancla, ownership, orden determinista por distancia y retorno al detalle/búsqueda.
- Permitir añadir un cercano al flujo principal sin crear tracking, alerta ni experiencia B2B automática.
- Mantener V1 compatible y preparar metadata V2 de elegibilidad, exclusiones y policy version.
- No puntuar paridad con muestras inválidas, fees desconocidas incompatibles, fixtures o providers fallidos.

**Gate:** backend, frontend, producto, legal y QA validan paridad estricta, estados insuficientes, cercanos accionables, ownership, i18n, accesibilidad y retorno navegable.

**Resultado H20:** contrato aprobado; la implementación y el gate visual/funcional siguen pendientes.

## Fase H21 — Matriz transversal de estados y recuperación

**Estado:** COMPLETA como contrato — `docs/reference/frontend/hoteles-state-matrix-h21.md`; implementación de estados explícitos, envelope V2, i18n, accesibilidad y QA E2E pendientes.

**Objetivo:** que la ausencia de resultados no sea un callejón sin salida y que ningún error de provider, sesión, red o dato stale se presente como una respuesta vacía válida.

**Alcance contractual:** búsqueda, resolución de destino, resultados, detalle, rates, paridad, cercanos/comp sets, watchlist, tracking, snapshots, alertas e inbox comparten taxonomía, preservación de contexto y acciones de recuperación.

**Requisitos:**

- Sin resultados: sugerir ampliar fechas, zona, radio, filtros o volver a intentar.
- Provider parcial: mostrar resultados disponibles y explicar qué falta.
- Provider caído: usar snapshot/caché solo con freshness visible.
- Geocoder no disponible: permitir destino conocido o entrada manual compatible.
- Error de sesión/auth: acción de reautenticación sin perder búsqueda.
- Error inesperado: mensaje humano, request ID/log interno y reintento seguro.
- Distinguir explícitamente `idle`, `loading`, `success`, `empty`, `partial`, `stale`, `stale_while_error`, `unavailable`, `auth_required`, `not_found`, `cancelled` y `error`.
- Conservar formulario, URL state, selección y datos previos útiles durante reintentos, reautenticación y degradación.
- No convertir `[]`, `null`, timeout, 401/403, 404 o fallo de provider en el mismo copy; el envelope V2 deberá transportar estado, warnings, freshness, capabilities y error allowlisted.
- Cubrir copy ES/EN, teclado, lectores de pantalla, reduced motion, móvil, telemetría sin PII y requests obsoletos/cancelados.

**Gate:** todos los estados tienen una acción siguiente y no muestran resultados engañosos. La implementación no se declara completa por la existencia de booleans V1: requiere evidencia de transiciones en código, UI real y QA.

---

# BLOQUE E — Tracking, histórico, alertas y retorno

## Fase H22 — Unificación semántica de favoritos y seguimientos

**Estado:** COMPLETA como contrato — `docs/reference/backend/hoteles-favorite-vs-tracking-h22.md`; implementación frontend/backend, migración V2, i18n, inbox y QA pendientes.

**Objetivo:** que el usuario entienda la diferencia entre guardar una propiedad y vigilar una estancia/oferta concreta, sin prometer refresh ni alertas para un favorito simple.

**Alcance contractual:** identidad separada, CTA y copy, conversión explícita, duplicados, lifecycle, ownership, inbox, privacidad, migración V1→V2 y pruebas de no confusión.

**Requisitos:**

- “Guardar hotel” = favorito simple, sin fechas, precio, provider, refresh ni promesa de alerta.
- “Seguir oferta/precio” = suscripción privada a hotel + estancia + ocupación + condiciones + provider/scope de precio.
- Permitir convertir un favorito en tracking solo después de elegir y confirmar el contexto de la estancia.
- No mostrar como activo un tracking con fechas/precio/condiciones insuficientes o sin policy de revalidación.
- Mostrar estado independiente de favorito y tracking en resultados, detalle, cuenta e inbox.
- Separar pausa, expiración, archivado y eliminación; no prometer recuperación tras un borrado duro.
- Impedir que eventos de sweep sin ownership inequívoco se compartan entre usuarios que siguen el mismo hotel.
- Migrar nomenclatura visible de “seguimiento” solo donde corresponda y conservar V1 con bridge reversible.

**Gate:** no existe una pantalla donde dos acciones con el mismo nombre tengan comportamientos distintos; favorito y tracking se distinguen en código, API, copy y UI real.

## Fase H23 — Crear tracking desde una oferta real

**Estado:** COMPLETA como contrato — `docs/reference/backend/hoteles-real-offer-tracking-h23.md`; implementación estricta de alta, snapshot/fingerprint V2, idempotencia, migración, UI de confirmación y QA E2E pendientes.

**Objetivo:** eliminar tracked offers incompletos o ambiguos y hacer que cada suscripción pueda reconstruirse sin depender de la búsqueda que la originó.

**Alcance contractual:** contexto canónico de estancia, identidad de oferta, observación inicial, confirmación, estados `active/pending/partial/stale/unavailable`, dedupe, idempotencia, ownership, inmutabilidad de identidad y bridge V1→V2.

**Requisitos:**

- Crear tracking desde una oferta/rate contextualizada, no desde un hotel ID y una cifra aislada.
- Capturar hotel, entrada, salida, noches, ocupación y fuente del bridge, habitación, régimen, cancelación, moneda, provider/scope y precio observado.
- Crear o enlazar un snapshot inicial inmutable con procedencia, timestamp, freshness y semántica de importe cuando estén disponibles.
- Permitir target price opcional sin incluirlo en la identidad compartida de la oferta.
- Confirmar qué se va a vigilar antes de guardar, mostrando condiciones, warnings y última observación.
- Prevenir duplicados con fingerprint de estancia/oferta, constraint transaccional e idempotency key.
- No mostrar como `active` una fila sin contexto, snapshot elegible o policy de revalidación; devolver `pending_context`, `pending_first_observation`, `partial`, `stale` o `unavailable` cuando corresponda.
- Mantener core identity inmutable: cambiar fechas, ocupación, habitación, régimen, cancelación o provider crea nueva versión/suscripción.
- Permitir reconstruir el tracking desde su propia respuesta y snapshots, sin leer el estado efímero de la búsqueda.
- Impedir que provider error, timeout, rate limit o fees desconocidas creen snapshot elegible o actualicen `current_price`.

**Gate D parcial:** un tracking creado puede reconstruirse sin leer el estado de la búsqueda original, y la evidencia de creación distingue oferta real, legacy incompleto, duplicado y error.

## Fase H24 — Histórico y curva de precio

**Estado:** COMPLETA como contrato; implementación backend/frontend y QA pendientes.

**Objetivo:** convertir snapshots en una herramienta de decisión, no en una lista de fechas.

**Requisitos:**

- Histórico ligado a una oferta/estancia comparable, no a un hotel abstracto.
- Elegibilidad explícita: importe, moneda, semántica de precio, freshness, provider y condiciones.
- Timeline con precio, provider, condiciones, disponibilidad, estados y razones de exclusión.
- Mínimo, máximo, mediana/promedio y variaciones frente a inicial, anterior y mínimo cuando la muestra lo permita.
- Agregación diaria que conserve cantidad total/elegible, providers, cambios y gaps.
- Provider error, sold out, ausencia de observación y datos incompatibles sin convertirlos en cero ni interpolarlos.
- Empty state, historial corto, partial, stale, gapped, expired y provider cambiado.
- Curva accesible con tabla/resumen equivalente, teclado, i18n y reduced motion.
- Ownership y caché privada preservados para históricos de seguimientos.

**Gate:** una persona puede responder “¿está barato para esta estancia?” sin interpretar datos técnicos y sin que la UI convierta ausencia de datos en una falsa tendencia.

## Fase H25 — Confianza, freshness y recomendaciones de acción

**Estado:** COMPLETA como contrato; implementación backend/frontend, refresh seguro, i18n y QA pendientes.

**Objetivo:** explicar si conviene esperar, seguir o revisar ahora sin convertir la señal en una predicción absoluta.

**Requisitos:**

- Freshness contextual basada en timestamp, TTL y provider; sin confundirla con disponibilidad.
- Provenance, confidence, comparabilidad y parity separadas.
- Recomendaciones estructuradas y prudentes: revisar, seguir observando, esperar señal o insuficiencia de datos.
- No usar `book_now`, compra garantizada ni promesas de bajada futura sin contrato aprobado.
- Refresh seguro con ownership, cooldown, coste, estado, retry y fallback no engañoso.
- Provider error, fixture, cache, histórico y datos parciales con procedencia visible.
- Estados stale, expired, partial, unknown, throttled y error con recuperación segura.
- Copy ES/EN, accesibilidad, reduced motion, telemetría y tests con muestras 0/1/2/3+.

**Gate:** las recomendaciones no exceden la evidencia disponible y ningún error se presenta como precio actual, sold out o confianza alta.

## Fase H26 — Motor de reglas de alerta y deduplicación

**Estado:** COMPLETA como contrato; implementación backend/frontend, migración de eventos, cooldown y QA pendientes.

**Objetivo:** generar alertas útiles, privadas y deterministas, no ruido.

**Requisitos:**

- Tipos iniciales: precio bajo/alto, bajada/subida porcentual, cambio de provider, disponibilidad recuperada y paridad.
- Reglas separadas entre alcance legacy por hotel y tracking/oferta privada.
- Baselines elegibles: snapshot anterior, inicial y target con semántica explícita.
- Provider error, stale, fixture, fees desconocidas o condiciones incompatibles no disparan falsos positivos.
- Cooldown y dedupe por owner, tracking/regla, fingerprint, transición y ventana.
- Evitar alertas repetidas en cada sweep sin cambio; soportar rearme tras volver a `clear`.
- Registrar baseline/current snapshots, razón, comparabilidad, provider run y estado de supresión.
- No resolver eventos privados por `hotel_id` solamente; ownership inequívoco antes de H27.
- Tests de bordes, moneda, redondeo, timezone, concurrencia, replay y datos faltantes.

**Gate:** un mismo cambio produce un único evento determinista, privado y trazable, no una tormenta.

## Fase H27 — Inbox privado hotelero, ownership y deep links

**Objetivo:** cerrar el ciclo desde evento hotelero autorizado hasta la persona correcta, sin filtrar señales entre usuarios y sin perder el contexto al abrirlas.

**Contrato:** [H27 — Inbox privado hotelero, ownership y deep links correctos](../reference/backend/hoteles-private-inbox-deeplinks-h27.md).

**Requisitos:**

- Inbox persistente integrado con las fuentes hoteleras y estado `read/unread` privado por usuario.
- Ownership verificable por regla, tracking, suscripción y snapshot; nunca por `hotel_id` solamente.
- Eventos legacy sin relación determinista fuera del inbox privado o migrados con evidencia auditable.
- Deep links internos hacia hotel, regla, tracking, evento o snapshot correcto, con reautorización al abrir.
- Estados partial, stale, provider degraded, auth y not-found sin convertir fallos en empty engañoso.
- Compatibilidad con el centro de notificaciones actual y con categorías/fuentes ya soportadas por backend y frontend.
- Límites, summary, paginación, cache privada, i18n, accesibilidad, telemetría y aislamiento entre dos usuarios.

**Gate:** desde una notificación autorizada se llega a la decisión correcta, con el contexto mínimo necesario, sin revelar ni confirmar datos de otra cuenta.

**Frontera:** H26 decide qué evento existe y si se deduplica; H27 decide quién puede verlo y a dónde navegar; H28 cubre delivery y preferencias; H29 cubre lifecycle.

## Fase H28 — Delivery hotelero, canales, reintentos y preferencias

**Estado:** COMPLETA como contrato; adapters externos, consentimiento por canal, endurecimiento del pipeline hotelero y QA operativo pendientes — [contrato H28](../reference/backend/hoteles-delivery-retries-preferences-h28.md).

**Objetivo:** que “avisarme” tenga un significado operativo, verificable y honesto para una señal hotelera autorizada.

**Requisitos:**

- Mantener `in_app` como canal privado base y no declarar email/push activos sin adapter, consentimiento, sandbox, límites y canary.
- Elegir cualquier provider externo mediante investigación de servicio, coste, privacidad, límites y salida, no por memoria.
- Separar evento hotelero H26, ownership H27, intención/outbox, cola, adapter de canal y estado final.
- Usar delivery at-least-once con idempotency key, retries clasificados, backoff, lease, dead-letter/replay y observabilidad redacted.
- Aplicar preferencias por canal, consentimiento, quiet hours, digest y fallback honesto a inbox.
- Mantener el stub email como fixture/sandbox; no interpretarlo como correo real.
- Respetar opt-in, unsubscribe, preferencias, lifecycle y privacidad.
- Usar plantillas ES/EN, copy de señal stale/provider-degraded y deeplink seguro de H27.
- No filtrar información de usuario en logs, colas, templates ni métricas.
- Probar adapter real o sandbox, fallo temporal/permanente, replay y fallback in-app.

**Gate:** pruebas end-to-end y operativas evidencian delivery hotelero autorizado por H27 y, por canal habilitado, `queued → sent/delivered` o fallo clasificado con recuperación; además prueban consentimiento/quiet hours, idempotencia, aislamiento entre dos usuarios, dead-letter/replay, redaction, rollback a inbox-only y que el stub no hace red. La existencia de `delivery_status` en la base no basta.

## Fase H29 — Lifecycle seguro de seguimientos

**Estado:** COMPLETA como contrato; implementación V2, migración, scheduler de expiración, archivado y QA E2E pendientes — [contrato H29](../reference/backend/hoteles-lifecycle-pause-edit-expire-delete-h29.md).

**Objetivo:** que pausar, reanudar, editar, expirar y eliminar un seguimiento sea explícito, reversible solo cuando exista soporte real y seguro frente a sweeps, alertas, delivery y retención.

**Requisitos:**

- Separar `is_active` legacy de estados persistidos `active`, `paused`, `expired`, `archived` y `deleted`.
- Pausar debe detener sweeps, reglas y delivery futuro, conservando histórico según la policy.
- Editar target, canales y preferencias sin cambiar identidad; cambiar estancia, ocupación, habitación, régimen, cancelación o provider debe crear versión/suscripción nueva o rechazarse.
- Expirar por checkout/policy con timezone definida, reconciliación, leases/locks, idempotencia y métricas.
- No llamar archivado a un booleano ni prometer undo mientras V1 mantenga DELETE duro.
- Definir cascadas de snapshots, reglas, eventos, delivery intents y favoritos sin borrar catálogo/cache global.
- Probar ownership, dos usuarios, IDOR, carreras sweep/lifecycle, retries y borrado de cuenta.
- Migrar sin inventar timestamps, sin mezclar series históricas y con rollback reversible.

**Gate:** la evidencia demuestra que ningún tracking pausado, expirado o eliminado genera trabajo nuevo; el histórico queda conservado o purgado según policy; las carreras y retries son idempotentes; y el sistema detecta huérfanos y activos vencidos. La existencia de `is_active` no basta.

## Fase H30 — Calendario y flexibilidad de fechas

**Estado:** COMPLETA como contrato; implementación de ventanas, calendario, capabilities, migración V2, canary y QA pendientes — [contrato H30](../reference/backend/hoteles-flexible-dates-calendar-h30.md).

**Objetivo:** permitir explorar fechas alternativas sin romper la búsqueda exacta ni convertir estancias incompatibles en una falsa oportunidad.

**Requisitos:**

- Mantener búsqueda exacta como baseline estable y normalizarla como `TemporalIntent=exact`.
- Definir modos separados: exacto, desplazamiento manteniendo noches, mes flexible, fines de semana y duración variable.
- Devolver siempre fechas efectivas, noches, ocupación, precio, moneda, condiciones y freshness por candidato.
- Declarar capabilities por provider; `unknown` o `unsupported` nunca se tratan como soportados.
- Limitar candidatos, fan-out, timeout, concurrencia, rate limit, cache y coste por búsqueda.
- Separar ranking total, precio/noche y proximidad temporal; no comparar duraciones o condiciones incompatibles.
- Persistir intención flexible en URL solo con parámetros reproducibles, sin ownership ni reglas privadas.
- Mostrar calendario/matriz únicamente con evidencia de datos suficiente y estados `partial/limited/unsupported/provider_error` honestos.
- Crear tracking solo después de elegir una estancia exacta; una ventana guardada pertenece a H48, no a `HotelTrackedOffer` por defecto.
- Activar progresivamente detrás de flags, canary y rollback a exact-date.

**Gate:** la evidencia demuestra compatibilidad exacta, capabilities verificadas, presupuesto respetado, candidatos trazables, comparabilidad/ranking explicables, privacidad, accesibilidad y rollback. La existencia de un date picker no basta.

---

# BLOQUE F — Diseño, accesibilidad y localización

## Fase H31 — Dirección visual específica de hoteles

**Estado:** COMPLETA como contrato; implementación específica, responsive final, i18n completa y browser QA pendientes — [contrato H31](../reference/frontend/hoteles-visual-direction-states-h31.md).

**Objetivo:** dar personalidad al módulo sin romper el sistema Viru y orientar toda la superficie a buscar, comparar, guardar y seguir una estancia.

**Requisitos:**

- Mantener Aviation Warm-Luxe dual, Playfair/IBM Plex, tokens y patrones canónicos.
- Hacer protagonista el buscador; ordenar resultados como secuencia identidad → precio → contexto → confianza → acciones.
- Tratar detalle como ancla de contexto y relegar paridad, alertas y comp set a instrumentos secundarios.
- Aprobar estados idle/loading/success/empty/partial/stale/unavailable/auth/not-found/cancelled/error con copy y acción.
- Separar visualmente catálogo sin oferta, oferta comparable, favorito y tracking.
- Definir responsive 360/390/414/768/1024 px, touch targets, foco y navegación sin hover.
- Usar motion breve para carga, selección, cambios y confirmaciones, respetando reduced motion.
- Mantener estructura y semántica equivalentes en dark/light sin crear paleta hotelera paralela.
- No sugerir capacidades de provider, precio, tracking o delivery que H10-H30 no respalden.
- Validar componentes y excepciones contra `DESIGN.md`, `docs/ui/*`, H16 y H21 antes de codificar.

**Gate:** propuesta visual y evidencia browser cubren estados felices y no felices, dark/light, responsive, teclado, foco, i18n y reduced motion; no basta una captura de resultados.

## Fase H32 — Responsive, overflow y CTAs accesibles

**Estado:** COMPLETA como contrato responsive; implementación frontend, hardening de CSS, tests de viewport y browser QA pendientes — [contrato H32](../reference/frontend/hoteles-responsive-accessible-ctas-h32.md).

**Objetivo:** que buscar, comparar y seguir una estancia sea cómodo y accionable en móvil, tablet, desktop, teclado y zoom ampliado.

**Requisitos:**

- Definir layout y orden de lectura para 360, 390/414, 600, 768, 820, 1024 y desktop.
- Eliminar overflow horizontal inesperado, clipping, min-content traps y saltos de layout en buscador, cards, detalle y paneles.
- Fijar targets táctiles de 48 × 48 px mínimo para CTAs, inputs, toggles, summaries y controles de recuperación.
- Mantener una acción primaria por panel/card y distinguir favorito, tracking, retry y acciones destructivas.
- Garantizar navegación por teclado, `focus-visible`, `aria-expanded`/`aria-controls`, retorno de foco y Escape en drawers/sheets cuando existan.
- Probar zoom/text scaling 100/150/200%, nombres largos, copy ES/EN, monedas, fechas y warnings multilínea.
- Preservar la taxonomía H21: empty no es error, provider error no es sold out y stale no es live.
- Mantener contexto durante loading/error/empty/stale/partial/auth/not-found/cancelled y evitar CTAs ocultos bajo teclado, safe areas o sticky UI.
- Respetar dark/light, reduced motion y alternativa textual para cualquier gráfico o timeline.
- Guardar evidencia browser con viewport, tema, locale, zoom, interacción, consola, scroll width y foco antes/después.

**Gate:** `/hoteles` funciona sin overflow inesperado y con CTAs operables por touch/teclado/zoom en la matriz completa, sin declarar por ello cerrado H33 WCAG, H34 i18n ni H40 browser QA de release.

**Resultado H32:** contrato aprobado en `docs/reference/frontend/hoteles-responsive-accessible-ctas-h32.md`; la implementación actual es una base parcial y conserva al menos un control de 44 px que debe corregirse antes del cierre.

**Gate E parcial:** evidencia de mobile dark/light y sin overflow horizontal.

## Fase H33 — Accesibilidad WCAG 2.2 AA

**Estado:** COMPLETA como contrato de auditoría; remediación frontend, tests a11y y recorrido manual pendientes — [contrato H33](../reference/frontend/hoteles-wcag-accessibility-audit-h33.md).

**Objetivo:** hacer el flujo usable para teclado, lector de pantalla, zoom y usuarios con necesidades diversas, sin confundir una auditoría estática con conformidad real.

**Requisitos:**

- Auditar landmarks, headings, labels, descriptions, errores asociados, roles, estados y orden de lectura.
- Completar el patrón combobox/listbox del autocomplete con teclado, `aria-activedescendant`, Escape, Enter y foco verificables.
- Relacionar controles plegables con `aria-expanded`/`aria-controls`/IDs y devolver foco al trigger.
- Corregir `role=status` usado en errores accionables y separar `alert` de progreso informativo.
- Añadir `aria-invalid`/`aria-describedby`, live regions estables y nombres contextuales para acciones repetidas.
- Auditar cards seleccionadas, favorito/tracking, snapshots, alertas, paridad, cercanos y estados H21 sin depender de color.
- Verificar contraste dark/light, reflow/zoom 200%, targets H32, reduced motion y alternativas textuales de históricos/gráficos.
- Cubrir automatización a11y y recorrido manual de teclado/lector de pantalla en búsqueda, resultados, tracking y alertas.
- Priorizar P0 antes de cualquier declaración de accesibilidad; cerrar o aceptar explícitamente P1 con owner antes de release.

**Gate:** no quedan bloqueantes P0; existe evidencia automatizada y manual en dark/light y ES/EN; la puntuación de axe/Lighthouse no se usa como única prueba. El cierre H33 no declara completadas H34 i18n ni H40 browser QA.

**Resultado H33:** contrato aprobado en `docs/reference/frontend/hoteles-wcag-accessibility-audit-h33.md`; la implementación actual conserva fundamentos parciales, pero la remediación y el gate real siguen pendientes.

## Fase H34 — Internacionalización, monedas y zonas horarias

**Estado:** COMPLETA como contrato de localización; remediación frontend, cobertura de claves y QA ES/EN pendientes — [contrato H34](../reference/frontend/hoteles-localization-dates-currency-timezones-h34.md).

**Objetivo:** que ES/EN no sean una traducción superficial y que las fechas, importes, unidades y timestamps no induzcan a error.

**Requisitos:**

- Completar y comparar claves ES/EN para hoteles, errores, filtros, fees, alertas, estados, aria/live copy y mensajes dinámicos.
- Mantener placeholders equivalentes y orden gramatical correcto; no concatenar frases traducibles.
- Pluralizar huéspedes, noches, hoteles, proveedores y resultados para 0/1/2+.
- Separar fechas civiles `YYYY-MM-DD` de timestamps ISO y documentar timezone de usuario, propiedad y provider.
- Usar locale activo para moneda de origen, números, porcentajes y distancias; eliminar `es-ES` hardcodeado del área.
- Mantener visible la moneda observada y no introducir FX ni selector de moneda sin contrato de H19/servicio aprobado.
- Externalizar copy incrustado como `No disponible`, errores y live regions; conservar nombres/direcciones provider como datos propios.
- Verificar `document.documentElement.lang`, `<time>`, aria-copy, dark/light, zoom y estados H21/H33 en ambos idiomas.
- Priorizar P0 antes de declarar cierre y cerrar/aceptar P1 con owner antes del release.

**Gate:** ES y EN pasan comparación de claves/placeholders, formatos, timezones, estados y recorrido browser sin claves faltantes, fallback visible, mezcla de idiomas ni desplazamiento de fechas; no se declara soporte global ni conversión de divisas.

**Resultado H34:** contrato aprobado en `docs/reference/frontend/hoteles-localization-dates-currency-timezones-h34.md`; la base actual ES/EN es parcial y conserva gaps de locale hardcodeado, pluralización, timezone/copy incrustado.

## Fase H35 — Legal, afiliación, privacidad y consentimiento

**Estado:** COMPLETA como contrato; implementación, revisión legal/security y QA de integración pendientes — [contrato H35](../reference/backend/hoteles-legal-privacy-disclosure-deeplinks-h35.md).

**Objetivo:** construir confianza y reducir riesgo sin declarar aprobación legal, afiliación activa ni deeplinks seguros antes de tener evidencia.

**Requisitos:**

- Explicar que Viru compara/redirige y no controla la reserva final.
- Disclosure visible ES/EN de afiliación cuando exista, precio observado frente a precio final y variación posible.
- Separar crear tracking de consentimiento para email, push y analítica.
- Definir ownership por recurso, minimización de payloads y redaction de URLs/credenciales/logs.
- Definir retención, exportación, pausa, expiración, borrado y cascadas junto a H11/H28/H29.
- Validar deeplinks mediante allowlist de esquema/host/path/parámetros; bloquear open redirects y SSRF si existe proxy o fetch.
- Probar aislamiento entre usuarios y prohibir resolver eventos privados por `hotel_id` solamente.
- Revisar providers/geocoder, términos, atribución, límites, coste y kill switch antes de activarlos.

**Gate:** Legal/Producto aprueban copy y tratamiento; Security/Backend pasan allowlist, redaction, SSRF/redirect e IDOR; Datos/QA prueban retención, borrado, disclosure y navegación en ES/EN, dark/light, móvil y teclado.

**Resultado H35:** contrato aprobado. No implica que la implementación legal/security o los deeplinks externos estén habilitados; el gate queda bloqueado hasta cerrar evidencia L/S/D/Q/O y cero P0.


---

# BLOQUE G — Rendimiento, seguridad y calidad técnica

## Fase H36 — Rendimiento frontend y percepción de velocidad

**Estado:** COMPLETA como contrato; instrumentación, optimización y QA de rendimiento pendientes — [contrato H36](../reference/frontend/hoteles-performance-web-vitals-h36.md).

**Objetivo:** que la búsqueda parezca rápida incluso cuando un provider tarda, sin ocultar la latencia ni declarar cumplimiento sin medición.

**Requisitos:**

- Medir shell, buscador interactivo, primer resultado útil, carga completa, LCP, INP, CLS y TTFB.
- Separar la carga principal de refreshes secundarios de watchlist, alertas, tracked offers, parity, comp sets e histórico.
- Skeletons con estructura real, reserva de espacio y estados loading/empty/partial/stale/error estables.
- Cancelación/lates-wins de requests obsoletas y debounce razonable del autocomplete.
- Cache solo con TTL, claves, invalidación, límites y aislamiento privado explícitos.
- Proteger el fan-out de watchlist/details y mantener el límite V1 de resultados; añadir paginación/virtualización si el catálogo crece.
- Auditar bundle route-specific, CSS, fuentes, imágenes, mapas y terceros fuera de la ruta crítica.
- Probar móvil, CPU representativa, Fast 3G, dark/light, ES/EN, teclado, zoom y reduced motion.
- Diferenciar lab de field/RUM; no llamar “instantáneo” ni “cumple Web Vitals” sin evidencia p75 suficiente.

**Gate:** presupuesto aprobado y recorrido definido; los budgets lab pasan en hardware móvil representativo, existe field evidence suficiente o se marca no concluyente, y no quedan P0 de carga principal, cancelación o estabilidad visual.

**Resultado H36:** contrato aprobado. No implica que la instrumentación, el presupuesto o las optimizaciones ya estén implementados.


## Fase H37 — Rendimiento backend, concurrencia y costes

**Estado:** COMPLETA como contrato — [benchmark, rate limits, locks y coste máximo H37](../reference/backend/hoteles-benchmark-rate-limits-locks-cost-h37.md); implementación, benchmark de canary y revisión del plan comercial pendientes.

**Objetivo:** escalar búsquedas y sweeps sin multiplicar costes ni producir snapshots falsos.

**Requisitos:**

- Separar fixture, canary y field benchmark; registrar p50/p95/p99, query count, pool, worker y outcomes.
- Resolver `provider_hotel_id` antes de llamadas dirigidas; no usar el ID interno como sustituto.
- Rate limit por provider/operación/ventana y, cuando corresponda, usuario/IP con H35.
- Ledger de presupuesto antes de salir a red; si la cuota/precio es desconocida, requests automáticos de producción = 0.
- Singleflight, fingerprints, locks distribuidos, leases y recovery cross-process.
- Retry único con `Retry-After`, jitter, backoff y circuit breaker sin duplicación entre capas.
- Estados explícitos `partial`, `skipped`, `rate_limited`, `timeout`, `unavailable` y `invalid_response`.
- Backpressure, límites de batch/fan-out y degradación controlada sin convertir errores en `empty`/`sold_out`.
- Kill switch, replay presupuestado, redaction y rollback verificable.

**Gate:** no quedan P0 de coste o integridad; dos workers no duplican una `StayQuery`; flags/budget cero no realizan llamadas; existe canary con plan/cuota/coste verificables o se marca no concluyente; H35/H41/H43 revisan privacidad, observabilidad y rollout.

**Resultado H37:** contrato aprobado. La implementación actual sigue siendo V1/manual/Mock y no se declara escalable ni económicamente aprobada para providers comerciales.

## Fase H38 — Seguridad de dominio hotelero

**Estado:** COMPLETA como auditoría/contrato — [ownership, secretos, SSRF y abuso H38](../reference/backend/hoteles-ownership-secrets-ssrf-abuse-h38.md); remediación, pruebas de seguridad y revisión de rollout pendientes.

**Objetivo:** proteger cuentas, datos y operaciones sin confundir autenticación con ownership.

**Requisitos:**

- Ownership relacional en favoritos, tracking, alertas, snapshots, eventos, inbox y notificaciones.
- Validación de `user_id`, `tracked_offer_id`, `hotel_id`, `rule_id` y `provider_hotel_id` como grafo autorizado.
- Sanitización/redaction de copy, payloads, URLs, headers, tokens y secretos de provider.
- SSRF, DNS rebinding, open redirect y deeplink review con allowlist, egress y revalidación.
- API keys fuera de frontend, query/logs intermediarios y respuestas de error.
- Rate limits, límites de payload/fan-out y abuso de autocomplete, búsqueda, geocoder y tracking.
- Auditoría de migraciones, borrado, exportación, legacy events y retención de datos.
- Tests negativos con dos usuarios, provider malicioso, URLs internas, redirects y logs.

**Gate:** cero P0 de aislamiento/secreto/SSRF; matriz AuthN/AuthZ aprobada; redaction y requests externas verificadas; abuso acotado; H35/H37/H39/H41/H43 revisan el cierre.

**Resultado H38:** contrato aprobado. El código actual conserva JWT y ownership parcial, pero no se declara seguro para lanzamiento hasta remediar los P0 y ejecutar los gates.

## Fase H39 — Test pyramid específica de hoteles

**Estado:** COMPLETA como estrategia/matriz — [contrato H39](../reference/backend/hoteles-test-pyramid-gaps-h39.md); implementación de huecos, canary y QA browser pendientes.

**Objetivo:** que cada fase futura pueda cambiar sin romper el dominio y que ningún hueco crítico quede oculto detrás de fixtures o tests estructurales.

**Requisitos:**

- Unit: normalización, matching, money, dates, ranking, confidence, alert rules, dedupe, redaction y URL validation.
- Contract: provider adapters, schemas H06, outcomes H37 y fixtures versionados.
- Integration: API, ownership relacional, migraciones, PostgreSQL locks/leases, worker, notification inbox y account deletion/export.
- Frontend: hooks, reducer/state, i18n, structural tests y components.
- E2E: búsqueda → resultado → detalle → tracking → alerta → notificación → deeplink en navegador real.
- Security: User A/B, BOLA, SSRF/open redirect, secrets, logs y abuso.
- Performance: request count, fan-out, primer resultado y trazas H36.
- Fixtures deterministas y tests de provider `empty/partial/429/timeout/invalid_response`.
- No convertir tests estructurales, build o typecheck en sustituto de browser QA, canary o security tests.

**Gate:** matriz U/I/C/B/S/P/R con áreas críticas, P0 explícitos, owner de hueco y evidencia reproducible.

**Resultado H39:** estrategia aprobada. La cobertura actual es parcial y no se declara tracker hotelero listo hasta cerrar los P0.

## Fase H40 — QA visual, manual y cross-browser

**Estado:** COMPLETA como contrato — [QA visual, manual y cross-browser H40](../reference/frontend/hoteles-visual-manual-crossbrowser-qa-h40.md); rerun browser, evidencia visual vigente y aprobación humana pendientes.

**Objetivo:** demostrar que la ruta funciona en la UI real sin convertir un test estructural o un cierre histórico en pase permanente.

**Requisitos:**

- Matriz desktop/móvil/intermedio, dark/light, ES/EN, zoom y reduced motion.
- Flujos F1–F5: búsqueda, autocomplete, detalle, favorito/tracking, alertas/comp set y degradación.
- Happy path, empty, loading, error, partial, stale, provider-off/slow/429, long names y many items.
- Teclado, foco, touch, lector de pantalla complementario y targets de 48 px.
- Consola limpia, requests esperados, sin overflow, deformación ni click targets bloqueados.
- Screenshots full/results/sidebar, traces, report JSON y entorno versionado.
- Chromium más navegador adicional acordado; limitaciones declaradas si no se ejecutan.
- Revisar copy, jerarquía, densidad y tono con criterio humano, no solo pixel diff.
- Recuperar artefactos históricos de fase 57 o repetir el runner con el código vigente.

**Gate E:** F1–F5 pasan, no quedan P0, la evidencia vigente está guardada y QA visual/funcional es aprobado por una persona además de automatización.

**Resultado H40:** contrato aprobado. El cierre histórico de junio no se reutiliza como pase actual sin rerun o artefacto recuperado.

---

# BLOQUE H — Operación, observabilidad y lanzamiento

## Fase H41 — Observabilidad end-to-end

**Estado:** COMPLETA como contrato — `docs/reference/backend/hoteles-observability-e2e-h41.md`; instrumentación hotelera, métricas persistentes, dashboards, SLO y alertas operativas pendientes.

**Objetivo:** saber por qué falla una búsqueda, un sweep, una revalidación, una alerta o su entrega, desde la UI hasta el provider y de vuelta al inbox.

**Requisitos:**

- Correlation/request/execution ID desde UI/API/provider/worker/notification, sin usar IDs privados como labels.
- Outcomes separados por provider y operación: success, empty, partial, timeout, 429/rate-limited, unavailable, invalid response y failed.
- Métricas de tracking/sweeps: due, scanned, leases, snapshots, stale, skipped, failed, alert triggered y budget.
- Métricas de delivery: queued, sent, failed, retry, suppressed y opened solo si H04/H28 lo autorizan.
- Logs estructurados con redacción verificable de PII, secretos, URLs firmadas y payloads externos.
- Health sin side effects, dashboards consultables y alertas SLO con owner, cooldown y runbook H42.
- Cardinalidad, sampling, retención y coste de observabilidad explícitos.
- Fixture E2E que correlacione búsqueda → provider → snapshot/tracking → regla → inbox/UI y pruebe degradaciones.

**Gate F parcial:** un incidente puede localizarse por código, provider, worker, DB o delivery; H41 no declara que ese gate operativo ya esté implementado.

## Fase H42 — Runbooks, soporte y recuperación

**Estado:** COMPLETA como contrato/runbook — `docs/runbooks/hoteles-incidentes-recovery-h42.md`; simulacros, owners de guardia y controles H09/H41/H43 pendientes.

**Objetivo:** operar `/hoteles` sin depender de la IA que lo construyó.

**Requisitos:**

- Runbook de provider caído, rate limited, timeout, respuesta inválida y coste inesperado.
- Runbook de worker detenido, duplicado, bloqueado o con ventana perdida.
- Runbook de backlog de notificaciones, ownership cruzado, dedupe y deep links.
- Runbook de snapshots corruptos/duplicados, tracking inconsistente y migración/retención.
- Procedimiento de desactivar provider/sweep y conservar lecturas históricas con freshness visible.
- Rollback de releases, migraciones y flags; sin asumir que todos los kill switches H43 existen todavía.
- Incidentes SEV-0 de secreto, SSRF, BOLA/IDOR y PII con contención y rotación.
- Mensajes para soporte: precio cambiado, datos stale, deeplink roto, alerta no recibida y hotel duplicado.
- Simulacros reproducibles con Mock/fixtures y paquete de evidencia.

**Gate F parcial:** otra persona puede seguir los playbooks para incidentes comunes; la operación productiva solo se declara cerrada tras simulacros y gates H09/H41/H43/H45.

## Fase H43 — Feature flags, canary y rollout gradual

**Estado:** COMPLETA como contrato — `docs/reference/backend/hoteles-flags-canary-killswitch-h43.md`; resolver central, protección de todos los entrypoints, canary real y pruebas de cero llamadas externas pendientes.

**Objetivo:** activar hoteles de forma gradual y reversible, con defaults fail-closed, perfiles explícitos, kill switches verificables y rollback sin pérdida de datos.

**Requisitos:**

- Definir perfiles `local_demo`, `local_fixture`, `staging_canary`, `prod_off` y `prod_gradual`.
- Mantener `HOTEL_FEATURE_ENABLED`, `HOTEL_SWEEP_ENABLED`, `HOTEL_PROVIDER` y `HOTEL_GEOCODER_ENABLED` como baseline V1, documentando sus límites reales.
- Cubrir también `/area-resolve` y `/area-search?use_provider=true`; el master switch no puede dejar caminos externos de lectura fuera del resolver.
- Crear una decisión efectiva única para API, worker y job directo; ningún entrypoint puede saltarse el kill switch.
- Hacer que ausencia de configuración sea `off` para providers comerciales; eliminar el fallback local implícito de `ingestion.py` o restringirlo a test explícito.
- Garantizar “off means zero external calls” con tests de transporte bloqueado y evidencia de ausencia de requests.
- Separar kill switch global, sweep, provider, operación, seguridad y coste; apagar no borra históricos.
- Ejecutar canary en fixture/DB aislada antes de cualquier provider comercial, con budget, rate limit, retries, concurrencia, ventana, owner y rollback.
- No confundir el canary genérico de release con cohortes hoteleras reales todavía inexistentes.
- Registrar `reason_code`, revisión de configuración, provider, ventana, owner y evidencia sin secretos.
- Integrar H09/H37 para scheduler, leases, budget y breaker; H41 para métricas/redaction; H42 para incidentes y recuperación.

**Gate:** cualquier feature hotelera de riesgo puede desactivarse desde todos sus entrypoints, se demuestra cero tráfico externo cuando está off, y la recuperación conserva datos. No se declara `staging_canary` o `prod_gradual` activa hasta cerrar los gaps P0/P1 del contrato H43.

**Decisión V1:** mantener `prod_off` como perfil seguro; `HOTEL_FEATURE_ENABLED=false`, `HOTEL_SWEEP_ENABLED=false` y `HOTEL_GEOCODER_ENABLED=false` deben fijarse explícitamente en ese perfil. Los defaults de plantilla no sustituyen un resolver unificado.


**Objetivo:** lanzar por partes y poder apagar lo peligroso.

**Requisitos:**

- Flags separadas para discovery, provider, search mode, tracking, alerts, delivery, calendar y recommendations.
- Defaults seguros y semántica documentada.
- Rollout por entorno, usuario interno, porcentaje o región si existe infraestructura.
- Kill switch para provider caro/inestable.
- Compatibilidad de API mientras se migran clientes.
- Checklist de preflight/postdeploy.

**Gate:** cualquier feature de riesgo puede desactivarse sin perder datos existentes.

## Fase H44 — Seed, demo y entorno de desarrollo realista

**Estado:** COMPLETA como contrato — `docs/reference/backend/hoteles-seed-demo-fallos-h44.md`; seed hotelero integral, reset seguro, fault profiles y E2E reproducible pendientes.

**Objetivo:** que las IAs y el equipo puedan investigar sin depender de producción.

**Requisitos:**

- Versionar un manifest y dataset sintético con varias ciudades, fechas, ocupaciones, providers, fees, cancelaciones, gaps y cambios de precio.
- Cubrir hoteles con y sin rates, coordenadas incompletas, matching ambiguo, tracking, histórico, alertas, inbox y User A/B.
- Crear fixtures de fallos tipadas: 429, timeout, vacío, invalid JSON/schema drift, rate sin currency, sold out, hotel ambiguo, stale, partial y deeplink inválido.
- Entregar comandos seguros y claramente diferenciados para seed, reset y sweep local; los módulos objetivo y `AISOLATED_DB_URL` deben etiquetarse como futuros hasta existir, y el worker actual debe ejecutarse solo con una guardia de DB aislada y flags explícitas.
- Aislar DB/entorno, hacer seeds idempotentes y prohibir datos reales, secretos o copy que parezca disponibilidad live.
- Reutilizar los escenarios por tests backend, frontend, Playwright/TestSprite y browser QA, con dataset/profile en la evidencia.

**Gate:** un flujo completo se puede reproducir localmente desde cero, con cero red externa por defecto y sin tocar datos fuera del entorno demo.

## Fase H45 — Lanzamiento, canary y rollback

**Estado:** COMPLETA como contrato — `docs/reference/backend/hoteles-release-canary-smoke-rollback-h45.md`; smoke E2E hotelero, canary real, métricas de promoción y rollback probado pendientes.

**Objetivo:** ponerlo delante de usuarios sin convertirles en testers involuntarios.

**Requisitos:**

- Separar release canary genérico, smoke hotelero y provider canary comercial.
- Ejecutar checklist de migración, compatibilidad y backup/restore sin asumir rollback universal.
- Cubrir smoke de ruta, auth, búsqueda, detalle, rates/parity, favorito, tracking, snapshots, alertas, inbox, ownership y deeplink.
- Usar dataset/provider controlado de H44 y distinguir `passed`, `partial`, `blocked` y `failed`.
- Comparar errores, latencia, coste, resultados vacíos/partial/stale, duplicados, soporte y baseline H00/H41.
- Aclarar que `/health` y `/ready` solo prueban API; el worker Kubernetes actual es placeholder.
- Definir criterios explícitos de continuar, pausar o bloquear; apagar flags conserva datos.
- Producir paquete redacted de evidencia y comunicación/changelog cuando el cambio sea visible.

**Gate G:** no promover a usuarios reales hasta que quality, smoke, canary, rollback y evidence estén aprobados con evidencia reproducible.

---

# BLOQUE I — Retención, crecimiento y diferenciación

## Fase H46 — Onboarding y primera victoria

**Estado:** COMPLETA como contrato de experiencia — `docs/reference/frontend/hoteles-primera-victoria-h46.md`; implementación del flujo guiado, auth contextual, eventos y QA browser pendientes.

**Objetivo:** que una persona nueva entienda el valor de `/hoteles` y consiga una primera utilidad sin tutorial largo ni claims de disponibilidad que el sistema no pueda respaldar.

**Requisitos:**

- Promesa breve y buscador protagonista; distinguir `idle`, `empty`, `demo`, `partial`, `stale`, `auth_required` y `error`.
- Empty state que explique el siguiente paso con una o dos acciones, sin convertirlo en tutorial.
- Ejemplo/fixture de búsqueda explícitamente rotulado como demo y `DEMO_NO_LIVE_AVAILABILITY`.
- Primera acción guiada de `Guardar hotel` frente a `Seguir precio`, con copy, confirmaciones y estados distintos.
- Bloquear o completar tracking cuando falten hotel, estancia, ocupación, precio, procedencia o policy elegibles; nunca crear defaults silenciosos.
- Pedir login/registro solo en la mutación privada necesaria y volver conservando la intención de búsqueda de forma idempotente.
- Explicar qué ocurre después de activar una alerta, diferenciando regla persistida de evaluación y delivery.
- Cubrir ES/EN, dark/light, teclado, móvil, zoom, touch targets y recuperación según H21/H32-H34/H40.
- Instrumentar activación con eventos allowlisted, dedupe, redaction y exclusión de fixtures/QA.

**Gate:** una persona nueva puede buscar y completar una victoria de guardado o tracking sin tutorial largo, sin perder contexto y sin recibir una promesa no respaldada. El contrato se considera cerrado en H46; la implementación y la evidencia browser siguen siendo trabajo pendiente.

## Fase H47 — Re-engagement y superficie de “mis hoteles”

**Estado:** COMPLETA como contrato de producto/navegación — `docs/reference/frontend/hoteles-mis-hoteles-reengagement-h47.md`; agregador, URL state, deep links contextuales, ownership V2, lifecycle visual, eventos y QA browser pendientes.

**Objetivo:** crear un retorno útil a `/hoteles` sin crear otro dashboard ni duplicar la fuente de verdad.

**Requisitos:**

- Superficie `Mis hoteles` dentro de `/hoteles`, compatible con los paneles/hook actuales.
- Prioridad explícita: seguimientos activos/próximos → señales accionables → pendientes/stale → hoteles guardados → pasados/expirados.
- Cards de retorno con hotel, contexto, estado, freshness y una siguiente acción segura.
- URL state objetivo para `panel=mis-hoteles`, sección y detalle contextual, sin afirmar que la ruta actual ya lo lea.
- Inbox → `/hoteles` con deep links internos, contexto autorizado, retorno seguro y fallback para eliminado/stale/not-found.
- Retirar o poner en cuarentena el fallback de ownership por `hotel_id` antes de declarar re-engagement privado listo.
- Lifecycle visible para `active`, `pending`, `partial`, `stale`, `unavailable`, `expired`, `archived` y `error`; `is_active` queda como bridge V1.
- Empty states accionables, progressive disclosure, auth/cache privados, ES/EN, dark/light, mobile y a11y según H21/H32-H34/H40.
- Recordatorios solo con consentimiento/canal/policy cerrados por H28; evitar spam y no convertir eventos en booking.
- Instrumentación allowlisted de retorno, deep links, fallbacks y ownership, con redaction y exclusión de QA/demo.

**Gate:** una persona con hoteles guardados o seguimientos puede decidir en segundos qué revisar; ninguna señal privada cruza cuentas y los estados de retorno no se confunden con empty, live o disponibilidad garantizada.

## Fase H48 — Guardar y compartir búsquedas

**Estado:** COMPLETA como contrato de dominio/navegación — `docs/reference/backend/hoteles-busquedas-guardadas-compartibles-h48.md`; parser URL hotelero, persistencia SavedHotelSearch, share token opcional, restore, lifecycle y QA pendientes.

**Objetivo:** reducir fricción para búsquedas recurrentes sin mezclar una intención pública con una suscripción privada.

**Requisitos:**

- Definir `StayQuery` versionada y canonicalización determinista para `/hoteles`.
- URL compartible anónima sin PII, ownership, tracking, alertas, snapshots ni tokens privados.
- Guardar búsqueda exacta o flexible con semántica distinta, ownership, CRUD, expiración, pausa y borrado.
- Restaurar destino, fechas, ocupación, filtros, orden y modo sin perder contexto ni duplicar requests.
- Definir auth/re-auth para guardar y editar, con reanudación idempotente y sin payload privado en URL.
- No ejecutar provider live automáticamente al abrir, restaurar o guardar una búsqueda; la comprobación live requiere acción explícita.
- Mantener cache pública de query separada de cache privada de cuenta y redaction de URL/token/telemetría.
- No confundir búsqueda guardada con favorito, tracking, alerta o delivery.
- Reutilizar patrones de `useRouteState` sin copiar parámetros IATA como si fueran estado hotelero.
- Cubrir ES/EN, dark/light, mobile, teclado, zoom, stale, unsupported version, not-found y provider off.

**Gate:** volver a una búsqueda es reproducible, privacy-safe y no genera requests inesperados; la búsqueda guardada privada no puede cruzar cuentas.

## Fase H49 — Personalización prudente

**Estado:** COMPLETA como contrato — `docs/reference/frontend/hoteles-personalizacion-prudente-h49.md`; implementación del perfil hotelero, `recommended`, controles, integración y QA pendientes.

**Objetivo:** mejorar resultados sin crear una caja negra.

**Requisitos:**

- Separar preferencias declaradas, contexto de sesión e inferencias; las declaradas tienen precedencia.
- Mantener `price`, `distance` y `stars` objetivos y deterministas; personalizar solo `recommended` cuando H17 lo habilite.
- Explicar cada influencia con códigos, fuente, evidencia, versión y fallback estricto.
- No inferir ni usar atributos sensibles, proxies económicos, comisión, afiliación o tracking como bonus oculto.
- Ofrecer cold start neutral, activación opcional, ajuste, desactivación, reset y borrado idempotente.
- Aislar perfil, cache, ownership, exportación, borrado y analítica redacted de H38/H48.
- Cubrir stale, partial, provider off, demo, ES/EN, accesibilidad, responsive, flags y rollback.
- Ejecutar tests de ranking con/sin preferencias, dos usuarios, cache, fallback y telemetría.

**Gate:** la persona entiende por qué ve una recomendación, puede cambiar el criterio y puede volver inmediatamente a un orden neutral sin perder su búsqueda.

## Fase H50 — Monetización y afiliación responsable

**Estado:** COMPLETA como contrato — `docs/reference/backend/hoteles-monetizacion-afiliacion-atribucion-h50.md`; partner aprobado, deeplinks allowlisted, consentimiento, ledger, reconciliación y QA pendientes.

**Objetivo:** hacer sostenible el tracker sin degradar confianza.

**Requisitos:**

- Definir registry de partner, capacidades, términos, deeplink, atribución, disclosure y política de salida.
- Separar ranking editorial de comisión, margen, payout y partner priority; no esconder `affiliate_bonus`.
- Distinguir click, conversión reportada, booking, stay, cancelación, refund, comisión y payout.
- Medir click-through y conversión sin almacenar más datos de los necesarios ni activar cookies sin consentimiento.
- No destacar una oferta peor por ingresos sin etiqueta, política visible y revisión aprobada.
- Mostrar disclosure claro sobre intermediación, precio observado frente a final, condiciones, refund y relación comercial.
- Modelar por separado coste de provider/API y presupuesto de monetización/atribución.
- Implementar allowlist, consentimiento, ledger/reconciliación, kill switch, canary, rollback y QA antes de activar partners.

**Gate:** negocio, producto, legal, seguridad y finanzas aceptan la política de monetización con evidencia reproducible antes de optimizar conversión.

## Fase H51 — Experimentos de producto

**Estado:** COMPLETA como contrato — `docs/reference/frontend/hoteles-experimentos-hipotesis-guardrails-h51.md`; motor de experimentación, asignación sticky, exposición, tripwires y QA automatizado pendientes.

**Objetivo:** aprender sin fragmentar el contrato.

**Requisitos:**

- Priorizar experimentos sobre CTA de tracking, copy de alertas, resumen de precio, filtros y onboarding.
- Definir hipótesis falsables, población, control/variantes, métrica primaria, denominador, MDE, ventana, stopping y decision record.
- Mantener asignación reproducible, exposición efectiva, dedupe, privacidad, consentimiento y stickiness cuando exista soporte real.
- Instrumentar guardrails de veracidad, freshness, comparabilidad, ownership, a11y, i18n, rendimiento, coste y partner.
- No experimentar con veracidad, consentimiento, legal, seguridad o accesibilidad; las variantes conservan la misma semántica.
- Mantener variantes localizadas, accesibles, reversibles y compatibles con H43/H45.
- Registrar novelty, SRM, muestra insuficiente, resultados inconclusos y decisión mantener/iterar/revertir.

**Gate:** cada experimento tiene hipótesis falsable, exposición medible, guardrails observables y rollback probado; si el motor no existe, la evidencia queda limitada a `manual_canary` o `blocked`.

---

# BLOQUE J — Mejora continua y escala

## Fase H52 — Feedback de usuarios y correcciones de confianza

**Estado:** COMPLETA como contrato — [contrato H52](../reference/frontend/hoteles-feedback-correcciones-confianza-h52.md); implementación del flujo contextual, triage, correcciones, inbox y QA pendientes.

**Objetivo:** aprender dónde no coincide la promesa con la experiencia y convertir la señal en una corrección trazable, reversible y con owner.

**Requisitos:**

- Feedback contextual de precio, fees, condiciones, identidad, freshness/provenance, alertas, UX, privacidad y seguridad.
- Taxonomía allowlisted, evidencia mínima redacted, ownership, severidad, dedupe e idempotencia.
- Separar provider, normalización Viru, catálogo/matching, tracking/alertas, delivery/inbox, frontend y partner externo.
- Lifecycle de `received` a `acknowledged`, `triaged`, `investigating`, `contained`, `corrected`, `verified` y `closed`, con estados de duplicado, abuso, no reproducible y explicación sin cambio.
- Preservar la observación original; hacer correcciones versionadas, reversibles y limitadas al scope probado.
- No modificar ranking por volumen de quejas, comisión, clicks o conversión; P0/P1 de confianza, privacidad y ownership prevalecen sobre H50/H51.
- Integrar acknowledgment privado con H27 solo mediante ownership y deeplink seguro; no prometer SLA, compensación ni cambio automático de provider.
- Medir TTA/TTT/TTFA/TTR, recurrencia y guardrails con denominadores, sin exponer texto libre o PII.
- Pasar smoke, browser QA, canary, rollback y runbook H42 antes de declarar implementación completa.

**Gate:** existe una ruta contextual y general compatible; cada caso tiene identidad idempotente, ownership, severidad, owner y estado; las correcciones preservan evidencia y tienen regresión; H51 recibe riesgos de confianza; H53 recibe casos de identidad/matching sin fusionarlos automáticamente.

## Fase H53 — Calidad de catálogo, matching y deduplicación avanzada

**Estado:** COMPLETA como contrato — [contrato H53](../reference/backend/hoteles-catalogo-matching-deduplicacion-h53.md); implementación de shadow matching, cola de revisión, merge/split, migración y QA pendientes.

**Objetivo:** que el mismo hotel no aparezca como cuatro propiedades distintas sin fusionar hoteles diferentes por similitud superficial.

**Requisitos:**

- Separar `provider_hotel_id`, `HotelProviderAlias`, `HotelProperty`, oferta y tracking privado.
- Reutilizar normalización y geodatos existentes, añadiendo candidate generation con límites, procedencia y policy version.
- Matching determinista o scored con señales explicables, hard negatives y umbrales high/review/low.
- Cola de casos ambiguos con owner, permisos, score breakdown redacted, decisión y audit trail.
- Gold set por mercado/provider para medir precision, recall, falsos merges, falsos splits y conflictos de alias.
- Propuestas de merge/split en dry-run, ledger append-only, migración idempotente y rollback.
- Reconciliar favoritos, tracking, snapshots, alertas, inbox y feedback sin reescribir evidencia ni cruzar ownership.
- Métricas de duplicados, aliases conflictivos, hoteles sin geodata, backlog, coste y latencia.
- No fusionar propiedades solo por similitud textual, coordenadas cercanas o una única señal de provider.

**Gate:** la policy de matching está versionada, el catálogo tiene evidencia gold-set o equivalente, los casos ambiguos no se ocultan y una operación de corrección puede auditarse y revertirse por mercado prioritario.

## Fase H54 — Escala geográfica y cobertura de mercados

**Estado:** COMPLETA como contrato — [contrato H54](../reference/backend/hoteles-mercados-entrada-salida-h54.md); implementación de registro de mercados, matriz de capabilities, canary, kill switch, salida y QA pendientes.

**Objetivo:** crecer por mercados donde la experiencia sea realmente buena, con un alcance probado y una retirada segura.

**Requisitos:**

- Definir `MarketSpec` versionado: territorio, ciudades/zonas, locale, moneda, timezone, provider scope, owner y estado.
- Mantener una matriz mercado/provider/capability con evidencia, fecha, exclusiones y policy version.
- Validar identidad H53, cobertura por ciudad/temporada, geodata y calidad de resolución H12 antes de ampliar scope.
- Probar estancia, ocupación, habitación, régimen, cancelación, fees, moneda, disponibilidad y freshness para el caso exacto declarado.
- Pasar gates de locale/legal/security H34/H35/H38, coste/rate limits H37, observabilidad H41 y flags/kill switch H43.
- Ejecutar fixtures, contract tests, smoke, canary y rollback H44/H45 antes de `limited_live` o `approved_live`.
- Definir budget, denominadores, thresholds, owner, soporte y decision record; no inventar cifras por provider.
- No abrir un país solo porque el geocoder lo reconoce, hay un `country_code`, un fixture o una respuesta HTTP 200.
- Pausar/retirar sin borrar snapshots, aliases, feedback ni históricos; retirar CTAs y deeplinks que ya no estén respaldados.

**Gate:** cada mercado tiene scope, capabilities, evidencia y criterios de entrada/salida versionados; ningún mercado se declara `approved_live` sin canary, rollback y decisión firmada.

## Fase H55 — Hardening de continuidad y disaster recovery

**Estado:** COMPLETA como contrato; implementación de backup/restore, recuperación de workers, reconciliación y recovery drill medido pendientes — [contrato H55](../reference/backend/hoteles-continuidad-disaster-recovery-h55.md).

**Objetivo:** proteger el histórico y la confianza acumulada, recuperando `/hoteles` sin inventar disponibilidad, perder ownership ni duplicar snapshots/alertas.

**Requisitos:**

- Inventariar datos P0/P1, reconstruibilidad, privacidad, owner y prioridad de recuperación.
- Proporcionar backup/export con `backup_id`, alcance, schema/config revision, integridad, retención y restore probado en entorno aislado.
- Medir RPO/RTO por dataset y superficie; no declarar objetivos antes de aprobarlos ni confundir `/health` con recuperación funcional.
- Mantener compatibilidad de código/schema, Alembic audit, backfills reanudables y rollback no destructivo según H11.
- Recuperar workers, leases, locks, cursores, runs en vuelo y delivery sin doble snapshot, alerta o envío.
- Reconciliar ventanas perdidas, provider outage, mercado pausado, datos ambiguos y snapshots corruptos sin convertirlos en `empty`, `sold_out` o live.
- Preservar ownership H27/H38, estados H28, identidad H53, flags `prod_off` H43 y release rollback H45.
- Ejecutar drills aislados con fixtures H44, evidencia redacted, decision log, stop conditions, postmortem y acciones correctivas.

**Gate:** backup restaurable, restore íntegro, recuperación idempotente y recovery drill medido con resultado `passed`, `partial`, `blocked` o `failed`; H55 solo puede marcar implementación completa cuando los objetivos aprobados y las capas críticas estén verificadas.

## Fase H56 — Revisión anual de producto, providers y costes

**Estado:** COMPLETA como contrato; revisión anual ejecutada, instrumentación completa, provider aprobado, reconciliación financiera y siguiente roadmap pendientes — [contrato H56](../reference/backend/hoteles-revision-anual-roadmap-h56.md).

**Objetivo:** evitar que el plan quede obsoleto y convertir cada ciclo en decisiones fechadas sobre valor, confianza, providers, mercados, costes y deuda.

**Requisitos:**

- Crear un paquete `HotelAnnualReview` con periodo, scope, fuentes, owners, expiración, versión de métricas y estado de evidencia.
- Revisar funnel, retorno, feedback, confianza, freshness, SLO candidatos, operación, costes API/infra/monetización y conversiones solo cuando estén realmente medidas.
- Revalidar providers, mercados y capabilities con cobertura, cuotas, latencia, coste, términos, privacidad, incidents, kill switch y decisión `renew/promote`, `remediate/throttle`, `pause/contain`, `sunset/deprecate` o `reject/keep_fixture`.
- Auditar experimentos, personalización y monetización sin confundir flags manuales con A/B, clicks con bookings ni contratos con implementación.
- Auditar flags, adapters, dependencias, migraciones, fixtures, código muerto candidato y documentación drift sin eliminar kill switches ni compatibilidad legacy.
- Registrar decision records con evidencia, owner, approver, fecha efectiva, expiración, riesgo y rollback/exit path.
- Publicar un siguiente roadmap versionado con jobs/evidencia, capacidad, dependencias, presupuesto, gates y decisiones explícitas de no hacer.
- Mantener revisión mensual/trimestral de coste, cuota, terms, seguridad y cambios materiales; no esperar al cierre anual para contener un riesgo.

**Artefactos iniciales:** [plantilla de revisión anual](../qa/hoteles-h56-annual-review-template.md) · [plantilla de DecisionRecord](../qa/hoteles-h56-decision-record-template.md) · [primer baseline local](../qa/hoteles-h56-annual-review-2026-08-05.md) · [DecisionRecord inicial](../qa/hoteles-h56-decision-record-2026-08-05.md). El baseline queda en `evidence_incomplete`: prueba Mock/fixtures y rutas seguras, pero no ejecuta provider comercial ni aprueba producción.

**Gate:** primer `HotelAnnualReview` real aprobado y fechado, decisiones trazables por provider/mercado/capability/flag relevante y siguiente roadmap aprobado con al menos una decisión de aplazamiento o no hacer.

---

## 5.1. Paquete mínimo de ejecución por fase

Aunque este documento no dicta la implementación línea por línea, cada IA debe completar este paquete antes de marcar una fase como `EN QA`:

1. **Contexto:** leer las docs canónicas del área y el código bajo estos roots probables: `frontend/src/modules/hotels/**`, `frontend/src/app/(private)/hoteles/**`, `frontend/src/i18n/domains/hotels.ts`, `frontend/src/styles/screens.css`, `backend/app/api/v1/hotels.py`, `backend/app/services/hotels_service.py`, `backend/app/hotels/**`, `backend/app/worker/hotels_sweep.py`, `backend/app/infrastructure/db/models.py`, `backend/alembic/**`, `backend/tests/**` y `frontend/tests/**`.
2. **Contrato:** indicar qué schemas, endpoints, modelos, eventos o copy cambia y qué compatibilidad se mantiene.
3. **Verificación:** ejecutar el test dirigido de la fase; añadir integración/browser QA cuando la fase cruce una frontera real; no sustituir runtime QA por un grep estructural.
4. **Evidencia:** guardar comando, resultado, fixtures/datos usados y limitación restante en la doc de QA o plan correspondiente.
5. **Handoff:** indicar qué fase puede empezar y qué deuda queda bloqueada; si el trabajo usa fixtures, marcarlo `fixture-only`.
6. **Review:** cambios significativos pasan por revisión de código y, si son UI, por verificación en navegador en los temas/viewport definidos.

Comandos base a adaptar al estado real del repo:

```bash
cd backend && python -m pytest tests/unit/test_hotels_*.py tests/integration/test_hotels_*.py -q
cd frontend && npx tsc --noEmit && npm run build
cd frontend && node --import tsx --test tests/hotels-f56-audit.test.ts tests/hotels-signal-assessment.test.ts
```

No todos los comandos aplican a todas las fases; la IA debe justificar el subconjunto ejecutado y no inventar scripts que no existan.

---

## 6. Contratos transversales que deben existir al completar el programa

### 6.1. Contrato de búsqueda

Debe incluir, como mínimo:

- `destination` normalizado y tipo;
- `check_in`, `check_out`;
- `rooms`, `adults`, `children` y edades si aplican;
- `currency` y locale;
- filtros y orden;
- estado de resolución geográfica;
- providers consultados y capacidades;
- results, pagination y warnings;
- freshness y source por resultado/precio.

### 6.2. Contrato de oferta trackeada

Debe reconstruir sin la búsqueda original:

- hotel/property ID y nombre visible;
- destino/coordinates si se usaron;
- fechas, habitaciones y ocupación;
- habitación, régimen y cancelación;
- provider y provider offer ID si existe;
- initial/current/target price;
- currency;
- estado activo/pausado/expirado;
- created/updated/last checked/next check;
- confidence y provenance.

### 6.3. Contrato de snapshot

Debe guardar:

- identidad de estancia/oferta;
- provider y run;
- timestamp UTC y timezone visible;
- importe, moneda, total/nightly si existen;
- taxes/fees included/unknown;
- availability status;
- room/meal/cancellation;
- deeplink seguro;
- raw payload solo donde esté justificado y protegido.

### 6.4. Contrato de alerta

Debe incluir:

- owner y tracking/oferta;
- tipo y threshold;
- baseline (`previous`, `initial`, `target`);
- evento que la disparó;
- dedupe/cooldown;
- canales y preferencias;
- delivery status;
- deep link;
- audit timestamps.

---

## 7. Matriz mínima de QA final

| Dimensión | Casos mínimos |
|---|---|
| Funcional | búsqueda por destino, fechas, ocupación, filtros, detalle, favorito, tracking, pausa, alerta, inbox, deeplink |
| Datos | provider live, cache, stale, demo, partial, vacío, 429, timeout, malformed payload |
| Fechas | mismo día, salida anterior, cambio de mes/año, timezone, check-in próximo, estancia expirada |
| Precio | moneda, fees, impuestos, nightly/total, bajada, subida, sin precio, precio inválido |
| Catálogo | acentos, alias, destinos ambiguos, hotel duplicado, sin coordenadas |
| Propiedad | dos usuarios, IDs ajenos, notificaciones ajenas, URLs manipuladas |
| Responsive | móvil estrecho, móvil ancho, tablet/intermedio, desktop |
| Temas | dark y light con misma semántica y contraste |
| Accesibilidad | teclado, focus, labels, combobox, errores, lector, reduced motion |
| Rendimiento | cold start, cache hit, provider lento, muchos resultados, muchos trackings |
| Operación | worker parado, retry, lock, replay, provider desactivado, rollback |
| Localización | ES/EN, plural, moneda, fecha, mensajes de error y email |
| Legal | disclosure, consentimientos, unsubscribe, deeplink, retención/borrado |

---

## 8. Métricas de lanzamiento recomendadas

### Salud técnica

- éxito de búsqueda por provider;
- p50/p95 de primera respuesta y primer resultado útil;
- tasa de timeout/429/partial;
- snapshots creados frente a snapshots esperados;
- edad de snapshot por tracking;
- alertas duplicadas por usuario;
- delivery success/failure;
- errores JS y Core Web Vitals;
- coste por búsqueda y por tracking activo.

### Salud de producto

- búsqueda iniciada → búsqueda completada;
- búsqueda completada → detalle abierto;
- detalle → guardar;
- resultado/detalle → tracking creado;
- tracking → alerta activada;
- alertas útiles/descartadas;
- retorno después de alerta;
- seguimientos activos a 7/30 días;
- click a partner y conversión cuando haya datos;
- ratio de feedback de precio incorrecto.

### Guardrails

No optimizar conversión a costa de:

- más falsos “live”;
- más alertas sin cambio relevante;
- más errores de precio final;
- menor accesibilidad;
- mayor coste no controlado;
- menos transparencia de afiliación.

---

## 9. Decisiones que deben quedar explícitas antes de implementarlas

Estas decisiones no se deben esconder dentro de una PR:

1. ¿Qué provider o combinación de providers soportará el primer lanzamiento real?
2. ¿Qué mercados/ciudades tendrán cobertura garantizada?
3. ¿Qué significa “diario”: cada 24h, una ventana local o una frecuencia dinámica?
4. ¿Qué canales de alerta estarán disponibles en cada entorno?
5. ¿Qué datos se consideran precio comparable?
6. ¿Se permite mostrar precio cacheado y durante cuánto tiempo?
7. ¿Qué ocurre con un tracking sin provider capaz de refrescarlo?
8. ¿Se mantiene `HotelWatchlistItem` indefinidamente como favorito o se migra a una entidad común?
9. ¿Qué funcionalidades quedan fuera del primer release: calendario flexible, mapa avanzado, reviews, personalización, share?
10. ¿Cuál es el modelo de afiliación y cómo se informa?
11. ¿Qué presupuesto máximo de provider/geocoder/email existe?
12. ¿Qué SLO mínimo es aceptable para búsqueda, sweep y alertas?

---

## 10. Orden recomendado de ejecución inmediata

Si varias IAs van a trabajar en paralelo, empezar así:

### Ola 1 — No bloquearse entre sí

- H00 baseline.
- H01/H02/H03 producto e IA.
- H05 freshness/provenance.
- H06 contrato provider-neutral.
- H39 matriz de tests.
- H31 dirección visual.

### Ola 2 — Dependiente de Ola 1

- H07 Makcorps audit.
- H10 modelo de estancia.
- H12 destino/geocoder.
- H13 formulario.
- H15 contrato de resultados.
- H41 observabilidad mínima.

### Ola 3 — Flujo visible principal

- H14 filtros/orden.
- H16 cards.
- H18 detalle.
- H19 fees/precio.
- H21 estados.
- H32 responsive/H33 a11y.

### Ola 4 — Valor diferencial

- H22 semántica favorito/tracking.
- H23 crear tracking.
- H24 histórico.
- H25 confidence.
- H26 reglas/dedupe.
- H27 inbox/H28 delivery.

### Ola 5 — Release real

- H09 scheduler.
- H36/H37 rendimiento.
- H38 seguridad.
- H40 QA visual.
- H42 runbooks.
- H43 flags.
- H45 canary/rollback.

### Ola 6 — Después de una primera versión útil

- H30 flexibilidad de fechas.
- H46 onboarding.
- H47 re-engagement.
- H48 búsquedas guardadas.
- H49 personalización.
- H50 monetización.
- H51 experimentos.
- H52-H56 mejora continua.

---

## 11. Skills y agentes recomendados por tipo de fase

Usar los skills existentes y respetar sus límites:

| Tipo de trabajo | Skill/agente recomendado | Resultado esperado |
|---|---|---|
| Descubrimiento y diseño | `brainstorming`, `oma-brainstorm`, `oma-pm` | decisión, alcance, tareas y dependencias |
| Arquitectura | `oma-architecture` | límites, trade-offs, ADR si aplica |
| Backend/API | `oma-backend` | contratos, servicios, endpoints, tests |
| Frontend/UI | `oma-frontend`, `frontend-design`, `design-taste-frontend`, `make-interfaces-feel-better` | experiencia fiel al contrato Viru |
| Diseño de sistema | `oma-design`, `ui-design`, `high-end-visual-design` | dirección visual y tokens sin generic SaaS |
| Datos/migraciones | `oma-db` | modelo, índices, integridad, retención, rollback |
| Proveedores externos | `gravity_index`, `researcher-docs`, `researcher-web` | selección contrastada, coste y límites |
| QA | `oma-qa`, `review`, `web-design-guidelines` | pruebas, accesibilidad, seguridad y rendimiento |
| Observabilidad | `oma-observability` | métricas, trazas, logs, SLO y privacidad |
| Documentación | `oma-docs`, `writing-plans` | docs enlazadas y sin drift |
| Navegador | `browser-use` | evidencia real de ruta e interacciones |
| Revisión | `code-reviewer-luna` | feedback crítico tras cambios significativos |

### Regla para IAs

No invocar un skill de implementación para saltarse el diseño de una fase. Primero leer contexto, después decidir, luego editar, finalmente revisar y verificar.

---

## 12. Checklist de cierre total del programa

- [x] H00 baseline archivado y reproducible — `docs/qa/reports/2026-08-04-hoteles-h00-baseline.md`.
- [x] Visión, personas, IA y métricas aprobadas — `docs/product/hoteles-product-vision-h01.md`.
- [ ] Contrato provider-neutral y decisión de provider real documentados.
- [ ] Freshness/provenance/confidence implementados y visibles.
- [ ] Scheduler ejecutándose con locks, retries, presupuesto y alertas.
- [ ] Modelo de estancia/oferta completo y migrado.
- [ ] Búsqueda de destino, fechas y ocupación funcional.
- [ ] Filtros, orden y ranking explicables.
- [ ] Cards y detalle orientados a decisión.
- [ ] Precio total, noche, fees y partner transparentes.
- [ ] Favorito y tracking claramente diferenciados.
- [ ] Histórico útil y accesible.
- [ ] Alertas deduplicadas, entregadas y trazables.
- [ ] Inbox/deeplinks correctos.
- [ ] ES/EN, monedas, fechas y timezones revisados.
- [ ] Dark/light/mobile/tablet verificados.
- [ ] WCAG 2.2 AA sin bloqueantes críticos.
- [ ] Rendimiento y coste dentro de presupuesto.
- [ ] Ownership, secretos, rate limits y deeplinks auditados.
- [ ] Fixtures realistas y entorno reproducible.
- [ ] Observabilidad, runbooks y rollback listos.
- [ ] Canary y smoke tests aprobados.
- [ ] Métricas de producto y guardrails instrumentados.
- [ ] Feedback, soporte y revisión post-lanzamiento preparados.

---

## 13. Fuentes consolidadas

- `docs/specs/hotels-product-direction.md`
- `docs/specs/hotels-intelligence-mvp.md`
- `docs/plans/2026-06-04-hoteles-correcciones-post-cierre.md`
- `docs/qa/hotels-pending-closeout.md`
- `docs/qa/hotels-visual-qa.md`
- `docs/runbooks/hotels-sweeps.md`
- `frontend/src/modules/hotels/HotelRadarPage.tsx`
- `frontend/src/modules/hotels/components/HotelSearchPanel.tsx`
- `frontend/src/modules/hotels/api.ts`
- `backend/app/api/v1/hotels.py`
- `backend/app/services/hotels_service.py`
- `backend/app/hotels/makcorps_provider.py`
- `backend/app/worker/hotels_sweep.py`
- Referencia externa: `https://travelpricedrops.com/hotels?lng=es` (observación de producto realizada el 2026-08-04; validar de nuevo si una decisión depende de comportamiento que pueda cambiar)

> Las fuentes históricas pueden decir “completado” aunque el producto necesite una evolución mayor. Este plan distingue cierre técnico de madurez de producto y exige evidencia actual para cada gate. La referencia externa se usa para patrones de producto y confianza, no para copiar branding, contenido o implementación.
