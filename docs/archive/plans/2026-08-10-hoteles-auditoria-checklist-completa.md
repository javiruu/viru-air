# Auditoría manual y checklist completo de `/hoteles` — H00–H56

**Fecha de auditoría:** 2026-08-10
**Documento relacionado:** `docs/plans/2026-08-04-hoteles-master-roadmap.md`
**Propósito:** convertir el roadmap en un estado operativo honesto, separando contrato/documentación de implementación y gate verificado.
**Fuente de evidencia:** código, migraciones, tests, scripts QA, runbooks, fixtures y documentos canónicos del repositorio.

> Esta auditoría no considera una fase totalmente terminada solo porque exista un documento, un modelo, una ruta o un test aislado. Para `COMPLETA TOTAL` deben estar cerrados el alcance de la fase, la implementación que ese alcance exige, la evidencia reproducible y sus riesgos de salida. Cuando el documento canónico declara explícitamente que la implementación o el gate siguen pendientes, se conserva esa deuda.

## 1. Leyenda de estados auditados

- **COMPLETA TOTAL:** alcance propio de la fase cerrado, evidencia reproducible y sin pendiente bloqueante dentro de ese alcance.
- **COMPLETA — CONTRATO/DISEÑO:** la especificación está cerrada, pero no la implementación posterior. No cuenta como fase técnica totalmente terminada.
- **PARCIAL:** hay implementación útil, pero faltan partes del contrato o cobertura/gate.
- **EN QA:** existe una implementación verificable, pero falta cerrar la evidencia o el gate de salida.
- **BLOQUEADA:** no puede cerrarse sin provider, decisión, credencial, entorno o evidencia externa.
- **NO INICIADA:** no se encontró implementación o evidencia suficiente.

## 2. Resumen ejecutivo auditado

### 2.1. Fases completamente terminadas en su propio alcance

- **H00:** baseline reproducible documentado, con limitaciones declaradas.
- **H01:** visión, personas, jobs, no-objetivos y métricas de producto definidos.
- **H02:** benchmark fechado, hechos separados de inferencias y traducción a Viru.
- **H07:** auditoría Makcorps y decisión condicionada documentadas; es un cierre documental de auditoría, no aprobación de Makcorps como provider principal ni canary comercial.
- **H44 — subalcance seed/reset + revalidación Mock + browser E2E local:** manifest, seed Mock idempotente, reset fail-closed, abort, loader declarativo local, los 13 profiles soportados en `fetch_hotel_rates()`/worker, warnings/needs_review por ítem, outcomes/latencia, filtros de freshness, smoke API service-level, matriz declarativa de expected counts/status/error/external calls, dry-run desechable y flujo Playwright/Chromium aislado con User A/B, cleanup y privacy están implementados y validados. H44 como fase total sigue abierta por canary comercial, matriz histórica persistida y cross-browser/QA humano.

### 2.2. Fases que no deben aparecer como `COMPLETA TOTAL`

> En H00–H02, `COMPLETA TOTAL` significa que el entregable documental de esa fase está cerrado y reproducible; no significa que el producto hotelero completo no tenga trabajo derivado. H07 se marca deliberadamente como `COMPLETA — AUDITORÍA DOCUMENTAL`: nunca equivale a aprobación del provider.

- **H03–H06, H08, H10–H25, H27–H36, H42, H46–H56:** el contrato/diseño existe, pero los documentos y/o el código declaran implementación, migración, QA o rollout pendientes; H26 queda cerrado en su alcance local determinista, con límites externos explícitos.
- **H28:** solo bridge `in_app` local en QA; email externo y garantías operativas no están cerrados.
- **H37–H41:** implementación parcial verificada; faltan gates de producción, browser/cross-browser, métricas operativas persistentes, SLO y/o canary.
- **H43–H45:** capacidades locales/Mock y scripts existen, pero canary comercial, promoción y rollback probado siguen abiertos.

### 2.3. Bloqueos globales para declarar “tracker hotelero real listo”

- Provider comercial principal sin canary, presupuesto, cobertura y plan de salida aprobado.
- Modelo canónico H10/H11 todavía no sustituye de forma compatible al V1 ni tiene backfill/rollback completo.
- Búsqueda V2, condiciones comparables, fees y envelope de estados aún no gobiernan todo el flujo.
- Tracking V2 no exige todavía en todas las superficies una oferta plenamente contextualizada.
- Delivery externo real no está habilitado; la existencia de un evento o de una fila `queued` no equivale a entrega.
- Browser QA reproducible completo y cross-browser humano no están cerrados.
- Backup/restore y recovery drill productivo no están ejecutados con evidencia.

## 3. Auditoría fase por fase

Cada fase incluye: estado, evidencia cerrada y checklist restante. Los checks marcados `[x]` son hechos comprobados dentro de la auditoría; `[ ]` son trabajo pendiente según el contrato y la evidencia disponible.

### H00 — Kickoff, inventario y baseline reproducible

**Estado auditado: COMPLETA TOTAL.**

**Evidencia:** `docs/qa/reports/2026-08-04-hoteles-h00-baseline.md`; baseline backend 192 tests, frontend TypeScript/build y 10 tests focalizados; matriz hecho/parcial/no verificado; limitaciones de browser, provider y sweeps documentadas. `COMPLETA TOTAL` aquí se refiere al entregable baseline de H00, no al cierre de las deudas que el baseline enumera.

**Checklist cerrado:**

- [x] Inventario de ruta, frontend, API, modelos, providers, worker, flags y tests.
- [x] Baseline backend y frontend reproducible registrado.
- [x] Diferencia entre código presente, tests pasados y operación levantada documentada.
- [x] Riesgos Makcorps, sweeps, delivery y browser separados.

**Pendiente de mantenimiento, no bloqueante para H00:**

- [ ] Repetir baseline cuando cambien contratos mayores.
- [ ] Mantener el número de tests y rutas actualizado en una nueva revisión de baseline.

### H01 — Visión de producto, personas y jobs

**Estado auditado: COMPLETA TOTAL.**

**Evidencia:** `docs/product/hoteles-product-vision-h01.md`. `COMPLETA TOTAL` aquí se refiere al entregable de visión y su gate de producto; la instrumentación y ejecución de métricas pasan a fases posteriores.

**Checklist cerrado:**

- [x] Usuario principal, personas P1–P5 y momentos de uso.
- [x] Jobs-to-be-done y frustraciones prioritarias.
- [x] Flujo comprometido de búsqueda a retorno.
- [x] No-objetivos: no OTA, no booking engine y no promesas live.
- [x] Embudo, métricas objetivo y guardrails de veracidad, privacidad, a11y, coste y rendimiento.

**Trabajo derivado pendiente en fases posteriores:**

- [ ] Medir el embudo real con eventos idempotentes.
- [ ] Convertir métricas objetivo en baseline por cohorte.
- [ ] Verificar que cada nueva feature conserva el vínculo job → métrica → gate.

### H02 — Benchmark funcional y de confianza

**Estado auditado: COMPLETA TOTAL.**

**Evidencia:** `docs/benchmarks/2026-08-04-travelpricedrops-hotels-h02.md`, observación fechada, hechos separados de inferencias y matriz de traducción H03/H05/H13/H19/H35/H50. `COMPLETA TOTAL` aquí se refiere al benchmark fechado y a su gate, no a la implementación de las fases receptoras.

**Checklist cerrado:**

- [x] Navegación, formulario, tracking, partner, disclosure, localización y responsive observados.
- [x] Inferencias comerciales separadas de hechos visibles.
- [x] Patrones que no deben copiarse documentados.
- [x] Preguntas de provider, fees, freshness, delivery y deeplink transferidas a fases posteriores.

**Pendiente de mantenimiento:**

- [ ] Revisar el benchmark si cambia la referencia externa o se toma una decisión dependiente de capacidades externas.

### H03 — Arquitectura de información y navegación

**Estado auditado: COMPLETA — CONTRATO/DISEÑO.**

**Evidencia:** `docs/product/hoteles-information-architecture-h03.md`.

**Checklist cerrado:**

- [x] Jerarquía búsqueda → resultados → detalle → tracking → inbox definida.
- [x] URL state objetivo, retorno, mobile IA y estados límite especificados.
- [x] Diferencia entre panel/detalle y superficies secundarias documentada.

**Falta para cierre técnico:**

- [ ] Implementar URL state canónico en la ruta real.
- [ ] Persistir/recuperar búsqueda con back-forward y refresh sin duplicar requests.
- [ ] Implementar master-detail o ruta URL-driven con retorno determinista.
- [ ] Verificar filtros, ocupación avanzada, temas, teclado y mobile en browser.

### H04 — Métricas, eventos y definición de done

**Estado auditado: PARCIAL — allowlist first-party local verificada; instrumentación completa pendiente.**

**Evidencia:** `docs/product/hoteles-metrics-events-h04.md` y `docs/qa/evidence/hotels-local-closeout-current/`; RUM y seis eventos de producto hotelero versionados pasan validación backend sin PII.

**Checklist cerrado:**

- [x] Taxonomía de eventos, propiedades permitidas, fórmulas y guardrails definidos.
- [x] Reglas de privacidad, dedupe, versionado y retención especificadas.
- [x] Primer evento RUM bucketizado y sin PII implementado.

**Falta para cierre total:**

- [x] Allowlist first-party local para seis eventos de producto hotelero, con metadata versionada y tests negativos.
- [ ] `schema_version`, `event_id` y `search_session_id` opacos donde corresponda.
- [ ] Instrumentar submit, completed, recovered, result, detail, favorite, tracking, alert, inbox y partner.
- [ ] Tests contra Strict Mode, re-render, retry y doble click.
- [ ] Métricas con denominador, ventana, segmento y dashboard reproducible.
- [ ] Retención y borrado de eventos first-party definidos y ejecutados.

### H05 — Freshness, provenance, disponibilidad y confidence

**Estado auditado: COMPLETA — CONTRATO; IMPLEMENTACIÓN PARCIAL.**

**Evidencia:** `docs/reference/backend/hoteles-freshness-provenance-confidence-h05.md`; snapshots, provider runs, estados y parte de redaction ya existen.

**Checklist cerrado:**

- [x] Vocabulario de procedencia, freshness, disponibilidad, completitud y confidence.
- [x] Estados `live/recent/cached/historical/demo/partial/unavailable/stale` definidos.
- [x] TTL, hard caps, copy y prohibición de falso live especificados.
- [x] `provider_run_id` y `collected_at` existen en partes del modelo actual.

**Falta para cierre total:**

- [ ] Aplicar la taxonomía de forma uniforme a cada respuesta de búsqueda, detalle, rate, tracking, histórico, paridad y alerta.
- [ ] Separar formalmente precio observado, precio calculable y precio final del partner.
- [ ] Implementar confidence de histórico y comparabilidad, no solo campos aislados.
- [ ] Mostrar copy ES/EN y warnings de freshness en las superficies reales.
- [ ] Añadir contract tests para cada transición de estado.

### H06 — Contrato provider-neutral V2

**Estado auditado: COMPLETA — CONTRATO; ADOPCIÓN V1/V2 PARCIAL.**

**Evidencia:** `docs/reference/backend/hoteles-provider-neutral-contract-h06.md`; `app/hotels/contracts.py`, Mock y Makcorps adapters, normalización y provider runs.

**Checklist cerrado:**

- [x] Interfaces base de provider y records normalizados.
- [x] Separación conceptual de vacío, fallo, rate limit y timeout.
- [x] Política de deeplink allowlisted documentada y sanitizer existente.
- [x] Matriz V2 y bridge V1 descritos.

**Falta para cierre total:**

- [ ] Envelope V2 único con status, warnings, capabilities, freshness y errores allowlisted.
- [ ] Bridge V1→V2 en todas las operaciones, no solo ingestion explícita.
- [ ] Contract tests intercambiables para Mock y provider comercial.
- [ ] Estados `partial/skipped/rate_limited` persistidos donde exige el contrato.
- [ ] Revalidación parametrizada por estancia y provider.

### H07 — Auditoría Makcorps

**Estado auditado: COMPLETA — AUDITORÍA DOCUMENTAL CONDICIONADA.**

**Evidencia:** `docs/reference/backend/hoteles-makcorps-audit-h07.md`; `makcorps_provider.py`; tests de parsing/errores; decisión explícita de no aprobarlo como provider principal.

**Checklist cerrado:**

- [x] Cobertura y endpoints examinados.
- [x] Riesgo de 429, timeout, payload vacío, IDs y fees documentado.
- [x] Decisión limitada, presupuesto, plan de salida y condiciones de reapertura.
- [x] La auditoría no se presenta como canary comercial pasado.

**Pendiente fuera del alcance cerrado de la auditoría:**

- [ ] Si se reabre Makcorps: ejecutar canary con credenciales, budget, métricas y rollback.
- [ ] No activar tracking/sweep comercial antes de ese canary y H08/H37/H41/H43.

### H08 — Onboarding de providers

**Estado auditado: COMPLETA — EVALUACIÓN DOCUMENTAL; PRODUCCIÓN ABIERTA.**

**Evidencia:** `docs/reference/backend/hoteles-provider-onboarding-h08.md`; matriz y política de onboarding.

**Checklist cerrado:**

- [x] Criterios de cobertura, coste, términos, límites, privacidad, deeplink y salida.
- [x] Mock como fallback de fixtures y Makcorps como experimental.
- [x] Regla de no integrar provider sin sandbox/fixtures, contrato y budget.

**Falta para cierre total:**

- [ ] Elegir provider comercial principal con evidencia actualizada y aprobación.
- [ ] Usar Gravity Index/documentación oficial para la selección concreta.
- [ ] Obtener sandbox/credenciales y registrar términos, SLA, coste y límites.
- [ ] Implementar adapter, contract tests, dedupe y kill switch.
- [ ] Ejecutar canary por mercado y declarar cobertura real.

### H09 — Scheduler, sweeps y garantías de ejecución

**Estado auditado: EN QA / PARCIAL.**

**Evidencia:** `backend/app/worker/hotels_sweep.py`, `app/hotels/jobs/run_hotel_sweep.py`, leases, circuit, budget, runbook `docs/runbooks/hotels-sweeps.md`, manifiestos Kubernetes suspendidos.

**Checklist cerrado:**

- [x] Worker separado del API y modo `--once`/`--loop`.
- [x] Leases, circuit breaker, budget ledger y parte de dedupe/retry implementados.
- [x] Runbook manual y kill switches documentados.
- [x] H44/H41 aportan evidencia Mock local.

**Falta para cierre total:**

- [ ] Activar un despliegue real aprobado; los manifests siguen suspendidos.
- [ ] Verificar leases distribuidos y recuperación con PostgreSQL bajo concurrencia.
- [ ] Completar estados `completed/partial/skipped/failed`, replay y priorización.
- [ ] Alertas operativas por sweep perdido, lease expirado y budget agotado.
- [ ] Canary comercial y rollback medido.
- [ ] SLO de frecuencia y freshness comunicable al usuario.

### H10 — Modelo canónico de estancia/oferta

**Estado auditado: COMPLETA — CONTRATO; IMPLEMENTACIÓN V1.**

**Evidencia:** `docs/reference/backend/hoteles-stay-offer-model-h10.md`, `HotelProperty`, `HotelRateSnapshot`, `HotelTrackedOffer`, `ProviderRateRecord` y esquemas actuales.

**Checklist cerrado:**

- [x] Entidades conceptuales de propiedad, estancia, oferta, rate, snapshot, provider y deeplink.
- [x] Invariantes básicas de fechas, guests, moneda y precio en schemas/provider.
- [x] Separación básica de hotel, snapshot y ownership de tracked offer.

**Falta para cierre total:**

- [ ] Crear entidades/contrato canónico `StayQuery` y fingerprints V2.
- [ ] Modelar habitaciones, niños/edades, régimen, cancelación, fees y semántica de total sin inferencias.
- [ ] Definir identidad inmutable de oferta y versionado para cambios de estancia.
- [ ] Implementar bridge V1, doble lectura/escritura, backfill marcado e idempotencia.
- [ ] Contract tests contra provider, alertas, ranking, parity y delivery.

### H11 — Migraciones, índices y retención

**Estado auditado: PARCIAL.**

**Evidencia:** numerosas migraciones hoteleras 0042–0053, constraints, leases, budgets, circuits, delivery y latency; tests de migraciones/compatibilidad existentes.

**Checklist cerrado:**

- [x] Evolución aditiva reciente y migraciones hoteleras verificables.
- [x] Parte de índices, FKs, ownership, budget, leases y agregados persistentes.
- [x] Roundtrip SQLite de migraciones recientes documentado en H39.

**Falta para cierre total:**

- [ ] Migrar el modelo canónico H10 con expand-and-contract completo.
- [ ] Backfill reanudable, idempotente, dry-run, `needs_review` y métricas de divergencia.
- [ ] Doble lectura/escritura y shadow compare V1/V2.
- [ ] Retención hot/warm/cold y agregados de histórico.
- [ ] Validación PostgreSQL con copia representativa, rollback y FKs huérfanas.

### H12 — Resolución de destino

**Estado auditado: PARCIAL.**

**Evidencia:** `/area-resolve`, `/area-search`, normalización, centroides/geocoder y tests `test_hotels_area_resolve.py`, `test_hotels_area_search.py`.

**Checklist cerrado:**

- [x] Normalización de acentos/ciudades y fallback local.
- [x] Resolución tipada con lat/lon, country, confidence y source en API V1.
- [x] Flag off de geocoder y tests de área.

**Falta para cierre total:**

- [ ] Autocomplete de ciudad/barrio/landmark/aeropuerto/región.
- [ ] Sugerencias tipadas, país/tipo visible y confirmación de ambigüedad.
- [ ] Adapter geocoder con cache, debounce, cancelación y límites.
- [ ] Pruebas de privacidad, rate limit y comportamiento sin red.
- [ ] Contrato V2 compatible con formulario y URL state.

### H13 — Formulario y URL state

**Estado auditado: PARCIAL.**

**Evidencia:** contrato H13; formulario/estado de búsqueda en `frontend/src/modules/hotels/`, tests de URL/search intent y API V1 de área.

**Checklist cerrado:**

- [x] Búsqueda básica por área, fechas, guests, moneda, radio, stars y precio.
- [x] Validaciones V1 de fechas/ocupación en backend.
- [x] Helpers de intención/URL presentes en frontend.

**Falta para cierre total:**

- [ ] UI canónica con destino, habitaciones, adultos, niños y edades.
- [ ] URL state completo y restauración sin duplicados.
- [ ] Estados validating/resolving/fetching/success/empty/partial/error visibles.
- [ ] Prevención de doble submit y cancelación de requests obsoletos.
- [ ] ES/EN, teclado, lector de pantalla y mobile E2E.

### H14 — Filtros y ordenación

**Estado auditado: PARCIAL.**

**Evidencia:** V1 `radius_km`, `min_stars`, `max_price`, `sort=price|distance|stars`; tests de área y backend.

**Checklist cerrado:**

- [x] Filtros V1 de radio, estrellas, precio y orden determinista.
- [x] Validación de rangos y ordenación backend básica.

**Falta para cierre total:**

- [ ] Filtros por cancelación, régimen, habitación, disponibilidad, provider y condiciones.
- [ ] Solo exponer filtros respaldados por capabilities.
- [ ] Contadores, chips activos, clear/apply y drawer mobile.
- [ ] Explicación del orden y de datos faltantes/partial/stale.
- [ ] Contract/E2E tests de combinaciones y recuperación.

### H15 — Resultados y paginación

**Estado auditado: PARCIAL.**

**Evidencia:** `/search` y `/area-search` V1 con listas y `limit/offset`; contrato H15 V2.

**Checklist cerrado:**

- [x] Respuestas V1 funcionales para catálogo/área.
- [x] Limit/offset y validaciones básicas.
- [x] Tests de búsqueda/área e integración API.

**Falta para cierre total:**

- [ ] Envelope versionado con metadata, warnings, capabilities, providers y freshness.
- [ ] Diferenciar success/empty/partial/stale/error total.
- [ ] Cursor o estrategia V2 estable y bridge V1.
- [ ] Cancelación, request identity y dedupe de búsquedas.
- [ ] Evitar N+1 y probar payloads grandes, ownership y rollback.

### H16 — Result cards

**Estado auditado: PARCIAL.**

**Evidencia:** `HotelRadarPage` y módulos de cards; QA estructural/visual histórico y contrato H16.

**Checklist cerrado:**

- [x] Cards de catálogo y área existentes.
- [x] Acciones de selección, watchlist/tracking según contexto.
- [x] Copy honesto de estados limitados trabajado en fases previas.

**Falta para cierre total:**

- [ ] Card canónica de oferta contextualizada con fechas, guests, room, meal, cancelación y fees.
- [ ] Freshness, provenance, unidad y estado de disponibilidad visibles.
- [ ] Una acción primaria sin competir con guardar/seguir/partner.
- [ ] Estados loading/no-price/partial/stale/error y focus/disabled completos.
- [ ] i18n, responsive, comprensión y QA visual vigente.

### H17 — Ranking explicable

**Estado auditado: PARCIAL.**

**Evidencia:** orden V1 por price/distance/stars y servicios de paridad/area.

**Checklist cerrado:**

- [x] Órdenes V1 deterministas y desempate estable.
- [x] Paridad/nearby relegados a señales secundarias.

**Falta para cierre total:**

- [ ] Metadata de motivo de orden en respuesta.
- [ ] Fórmula versionada para `recommended`, sin activar por afiliación.
- [ ] Política de missing/partial/stale y rating source.
- [ ] Fixtures y contract tests con datos faltantes y providers parciales.
- [ ] Copy breve de explicación en UI.

### H18 — Detalle y navegación

**Estado auditado: PARCIAL.**

**Evidencia:** endpoint `/{hotel_id}`, rates, parity y panel lateral en `HotelRadarPage`; contrato H18.

**Checklist cerrado:**

- [x] Detalle backend, rates, paridad y comp sets existentes.
- [x] Selección y panel lateral funcionales en V1.

**Falta para cierre total:**

- [ ] Ruta/panel URL-driven con `hotel_id` y contexto de búsqueda completo.
- [ ] Back/forward, refresh y entrada directa.
- [ ] Rate offer contextualizada y CTA de tracking/alerta/partner.
- [ ] Estados partial/stale/unavailable/not_found independientes.
- [ ] Teclado, mobile, lector de pantalla, deeplink y QA E2E.

### H19 — Precio total, noches y fees

**Estado auditado: PARCIAL.**

**Evidencia:** `amount`, `initial_price`, `current_price`, currency, tax parsing parcial de Makcorps y contratos H19.

**Checklist cerrado:**

- [x] Importe y currency existentes en rates/tracked offers.
- [x] Algunas respuestas de provider suman tax cuando el payload lo ofrece.
- [x] Disclaimers y sanitizer de partner definidos.

**Falta para cierre total:**

- [ ] Modelo explícito de total, noches y precio por noche.
- [ ] Fees/taxes/depósitos/desconocidos como componentes tipados.
- [ ] Moneda observada/solicitada/mostrada y conversión versionada.
- [ ] Comparabilidad estricta antes de ranking, tracking o alerta.
- [ ] Copy/legal/i18n/a11y y fixtures de fees incompatibles.

### H20 — Paridad, providers y hoteles cercanos

**Estado auditado: PARCIAL.**

**Evidencia:** `HotelParityService`, `/parity`, `HotelCompSet`, nearby suggestions y tests de área/comp sets.

**Checklist cerrado:**

- [x] Paridad V1 y comp sets/nearby existentes.
- [x] Ownership básico y hotel ancla fuera de resultados mejorados en closeout.
- [x] Señal insuficiente no se presenta automáticamente como paridad válida.

**Falta para cierre total:**

- [ ] Comparabilidad V2 por estancia, habitación, régimen, fees, freshness y disponibilidad.
- [ ] Estados one-provider/partial/stale/invalid/degraded/no-data.
- [ ] Metadata de exclusión y policy version.
- [ ] UI secundaria accionable, i18n, a11y y retorno navegable.
- [ ] No crear tracking/alerta automáticamente desde nearby.

### H21 — Matriz de estados y recuperación

**Estado auditado: PARCIAL.**

**Evidencia:** contrato H21; booleans/estados V1 en frontend y backend; tests de error/empty parciales.

**Checklist cerrado:**

- [x] Estados básicos loading/empty/error en varias superficies.
- [x] Copy honesto para señales insuficientes trabajado.
- [x] Backend distingue varios errores de validación/not found/permission.

**Falta para cierre total:**

- [ ] Taxonomía única idle/loading/success/empty/partial/stale/stale_while_error/unavailable/auth/not_found/cancelled/error.
- [ ] Envelope V2 y acciones de recuperación por estado.
- [ ] Preservar intención durante retry, auth, back-forward y request cancelado.
- [ ] Copy ES/EN, a11y, reduced motion, mobile y telemetría redacted.
- [ ] Matriz E2E de todas las superficies hoteleras.

### H22 — Favorito frente a tracking

**Estado auditado: PARCIAL.**

**Evidencia:** `HotelWatchlistItem`, `HotelTrackedOffer`, UI y contrato H22; closeout histórico demuestra favorite/tracking separados en base V1.

**Checklist cerrado:**

- [x] Entidades y endpoints separados.
- [x] Watchlist simple disponible.
- [x] Tracking requiere más contexto que un favorito en varios caminos.

**Falta para cierre total:**

- [ ] Copy/CTA consistente en resultados, detalle, cuenta e inbox.
- [ ] Conversión explícita favorito → tracking contextualizado.
- [ ] Estado de tracking insuficiente no presentado como active.
- [ ] Lifecycle pausa/expira/archiva/elimina diferenciado.
- [ ] Tests de no confusión y migración V1→V2.

### H23 — Tracking desde oferta real

**Estado auditado: PARCIAL.**

**Evidencia:** CRUD `/tracked-offers`, `HotelTrackedOfferCreateIn`, snapshot inicial en ciertos caminos y tests de tracking/sweep.

**Checklist cerrado:**

- [x] Alta/listado/detalle/update/delete de tracked offer.
- [x] Snapshot y prevención de duplicado en el flujo V1 histórico.
- [x] Ownership y errores de not found/permission básicos.
- [x] V2 exige una oferta canónica con precio total y condiciones completas.
- [x] Estados V2 `pending_context`, `pending_first_observation`, `partial` y `unavailable` no se presentan como `active`.
- [x] Confirmación de una oferta concreta y E2E local reconstruible con Mock/SQLite, sin servicios externos.

**Falta para cierre total:**

- [ ] Fingerprint V2 e idempotency key transaccional para todos los caminos.
- [ ] Identidad inmutable y versionado al cambiar fechas/ocupación/condiciones/provider.
- [ ] Bloquear snapshot elegible ante timeout, 429, fees desconocidas o error.

### H24 — Histórico y curva de precio

**Estado auditado: PARCIAL.**

**Evidencia:** snapshots y endpoint `/tracked-offers/{id}/snapshots`; contrato H24.

**Checklist cerrado:**

- [x] Histórico crudo consultable por tracked offer.
- [x] Snapshots ligados a hotel/tracked offer en el modelo V1.
- [x] Eventos de cambio de precio existen en sweeps.

**Falta para cierre total:**

- [ ] Elegibilidad por estancia/guests/room/meal/cancelación/currency/provider.
- [ ] Mínimo, máximo, mediana, tendencia, delta y gaps agregados.
- [ ] Separar observación válida de stale, sold out, partial e incompatible.
- [ ] Fallback accesible a gráfico y estados corto/sin histórico.
- [ ] Retención/agregados y QA de series temporales.

### H25 — Freshness, confidence y acciones

**Estado auditado: PARCIAL.**

**Evidencia:** contrato H25, campos de provider run/snapshot, métricas de latency y copy de confianza parcial.

**Checklist cerrado:**

- [x] Contrato de recomendaciones prudentes.
- [x] Parte de freshness/provenance y latencia persistida.
- [x] Sanitización y estados limitados en superficies existentes.

**Falta para cierre total:**

- [ ] Cálculo uniforme de confidence de histórico y oferta.
- [ ] Acciones refresh/esperar/ajustar/buscar alternativa con límites y dedupe.
- [ ] No refrescar provider externo automáticamente sin budget/circuit/consentimiento.
- [ ] Copy, i18n, a11y y tests de stale/error.
- [ ] Métricas de acción tomada y resultado.

### H26 — Reglas, baselines y dedupe de alertas

**Estado auditado: COMPLETA TOTAL en alcance local determinista; dependencias H19/H25/H27-H29/H40-H41 permanecen fuera de alcance.**

**Evidencia:** `HotelAlertRule`, `HotelAlertEvent`, evaluator en `hotels_service.py`, cooldown/dedupe e in-app intents; contrato H26.

**Checklist cerrado:**

- [x] Tipos de reglas y umbrales V1.
- [x] Evaluación de tracked alerts en sweeps.
- [x] Ownership, eventos, cooldown/dedupe, rearmado explícito, metadata de baseline, tolerancia a carreras de unicidad y exclusión de observaciones legacy del inbox privado.

**Fuera del alcance local cerrado / handoffs:**

- [ ] Freshness avanzada, fees/total H19 y comparabilidad completa de todas las superficies.
- [ ] Tipos y políticas V2 que requieren H19/H25/H27-H29.
- [x] No alertar por snapshot incompatible, error, stale, fixture no permitido u observación legacy.
- [x] Persistir reason, baseline, policy version, trace, fuente/importe/moneda de baseline y fingerprint.
- [x] Tests de cooldown, duplicate sweep, rearmado, concurrencia de unicidad y ownership A/B en el alcance local.

### H27 — Inbox privado y deeplinks

**Estado auditado: PARCIAL.**

**Evidencia:** `/api/v1/notifications`, `notification_inbox.py`, `HotelAlertEvent` y delivery intents in-app; contrato H27.

**Checklist cerrado:**

- [x] Inbox unificado y lectura/marcado de notificaciones.
- [x] Ownership de eventos hoteleros en endpoints actuales.
- [x] Fuentes de inbox y deep-link conceptual existentes.

**Falta para cierre total:**

- [ ] Deep links contextuales URL-driven a tracking/detalle/histórico.
- [ ] Revalidar ownership también al resolver cada deep link.
- [ ] Estado de alerta/evento/delivery claramente separado.
- [ ] Copys ES/EN, not found/expired/unauthorized y recovery.
- [ ] E2E: alerta A nunca visible/accionable por B.

### H28 — Delivery, canales, reintentos y preferencias

**Estado auditado: EN QA — `in_app` local; canales externos pendientes.**

**Evidencia:** `HotelNotificationDelivery`, `create_hotel_delivery_intent`, `materialize_hotel_delivery_intents`, `notification_service.py`, tests de delivery y migraciones 0050/0051.

**Checklist cerrado:**

- [x] Ledger hotelero separado y con idempotency key.
- [x] Ownership e in-app local con estados y worker verificado.
- [x] Retries básicos y errores clasificados parcialmente.

**Falta para cierre total:**

- [ ] Adapter email/push real elegido, instalado y verificado.
- [ ] Consentimiento y preferencias por canal, quiet hours y opt-out.
- [ ] Leases, jitter, backoff, max attempts, DLQ y replay.
- [ ] Estados terminales y observabilidad de cada canal.
- [ ] No confundir `queued`/persistido con entregado.
- [ ] QA operativo bajo fallo, concurrencia y rate limits.

### H29 — Lifecycle de seguimientos

**Estado auditado: PARCIAL.**

**Evidencia:** update/delete V1, `is_active`, contratos H29, ownership/cascades parciales.

**Checklist cerrado:**

- [x] Pausar/activar básico mediante estado activo en ciertos caminos.
- [x] Delete y ownership V1.

**Falta para cierre total:**

- [ ] Estados pending/active/paused/stale/expired/archived/deleted tipados.
- [ ] Edición segura de contexto con nueva versión cuando cambia identidad.
- [ ] Scheduler de expiración y archivado reanudable.
- [ ] Cascades e inbox/eventos/snapshots definidos y probados.
- [ ] Idempotencia, recuperación y UI E2E.

### H30 — Calendario y fechas flexibles

**Estado auditado: COMPLETA — CONTRATO.**

**Evidencia:** `docs/reference/backend/hoteles-flexible-dates-calendar-h30.md`; no se encontró una implementación V2 completa en el código auditado.

**Checklist cerrado:**

- [x] Capabilities, comparabilidad, coste, rollout y contrato definidos.
- [x] Invariantes de fechas V1 existentes.

**Falta para cierre total:**

- [ ] API de ventanas flexibles y resultados agrupados comparables.
- [ ] Calendario/heatmap con freshness, moneda y unidad honestas.
- [ ] No mezclar ocupaciones/condiciones en mínimos.
- [ ] Budget/cancelación de búsquedas múltiples.
- [ ] UI mobile, a11y, i18n y QA.

### H31 — Dirección visual y estados

**Estado auditado: COMPLETA — CONTRATO VISUAL.**

**Evidencia:** `docs/reference/frontend/hoteles-visual-direction-states-h31.md`; componentes existentes, pero el propio documento deja implementación específica y browser QA pendientes.

**Checklist cerrado:**

- [x] Dirección Warm-Luxe, jerarquía, temas, estados y motion definidos.
- [x] Handoff de principios y tokens documentado.

**Falta para cierre total:**

- [ ] Aplicar dirección a formulario, cards, detalle, tracking, alertas e inbox reales.
- [ ] Estados completos visuales y reduced motion.
- [ ] Responsive final sin overflow.
- [ ] i18n completa y validación de copy.
- [ ] Browser QA vigente y aprobación humana.

### H32 — Responsive, overflow y CTAs accesibles

**Estado auditado: COMPLETA — CONTRATO RESPONSIVE.**

**Evidencia:** `docs/reference/frontend/hoteles-responsive-accessible-ctas-h32.md`; evidencia histórica y scripts parciales, pero faltan tests de viewport/browser del contrato actual.

**Checklist cerrado:**

- [x] Reglas de layout, overflow, zoom, focus y CTA documentadas.
- [x] Parte de adaptación mobile histórica.

**Falta para cierre total:**

- [ ] Tests automatizados de viewport estrecho, zoom 200/400% y teclado.
- [ ] Verificar drawer/sheet, sticky CTA y no pérdida de contexto.
- [ ] Touch targets, focus visible, orden de tab y lector de pantalla.
- [ ] Dark/light y ES/EN en mobile.
- [ ] Evidencia vigente por commit/build.

### H33 — WCAG 2.2 AA

**Estado auditado: COMPLETA — CONTRATO DE AUDITORÍA.**

**Evidencia:** `docs/reference/frontend/hoteles-wcag-accessibility-audit-h33.md`; auditoría y prioridades documentadas.

**Checklist cerrado:**

- [x] Criterios, prioridades P0/P1/P2 y metodología definidos.
- [x] Riesgos de contraste, teclado, roles y nombres identificados.

**Falta para cierre total:**

- [ ] Remediar P0/P1/P2 en componentes reales.
- [ ] Tests automatizados a11y y regresión en CI.
- [ ] Recorrido manual teclado/lector/reduced motion.
- [ ] Evidencia de cada flujo: búsqueda, detalle, tracking, alerta, inbox y deeplink.

### H34 — Localización, fechas, monedas y timezones

**Estado auditado: COMPLETA — CONTRATO DE LOCALIZACIÓN.**

**Evidencia:** `docs/reference/frontend/hoteles-localization-dates-currency-timezones-h34.md`, i18n existente y formatos compartidos.

**Checklist cerrado:**

- [x] Contrato ES/EN, fechas civiles, moneda observada y timezone definido.
- [x] Reglas de pluralización y no conversión implícita documentadas.

**Falta para cierre total:**

- [ ] Cubrir todas las claves de hoteles en ES/EN.
- [ ] Traducir estados partial/stale/fees/delivery/error y copy legal.
- [ ] Tests de DST, medianoche, locale, currency y timezone.
- [ ] Browser QA ES/EN en desktop/mobile/dark/light.

### H35 — Legal, privacidad, disclosure y deeplinks

**Estado auditado: PARCIAL — SEGURIDAD TÉCNICA VERIFICADA.**

**Evidencia:** `partner_links.py`, sanitizer/allowlist deny-by-default, tests de seguridad y contrato H35.

**Checklist cerrado:**

- [x] Sanitización server-side y allowlist técnica.
- [x] Redaction de secretos y advertencia de partner/precio cambiante documentada.
- [x] Ownership y no disponibilidad garantizada reflejados en contrato.

**Falta para cierre total:**

- [ ] Revisión legal aprobada sobre disclosure, afiliación, consentimiento y retención.
- [ ] CTA/disclosure visible en cada superficie de salida.
- [ ] Deep links con contexto permitido y sin PII/secretos.
- [ ] Tests de URLs privadas, query sensible, punycode, redirects y hosts nuevos.
- [ ] Proceso de revisión periódica de partners.

### H36 — Rendimiento frontend y Web Vitals

**Estado auditado: PARCIAL — LAB CERRADO, FIELD ABIERTO.**

**Evidencia:** `docs/reference/frontend/hoteles-performance-web-vitals-h36.md`, `docs/plans/2026-08-08-h36-performance-baseline.md`, `HotelRumTracker`, scripts de perfil.

**Checklist cerrado:**

- [x] Baseline lab autenticado y gates lab declarados.
- [x] Instrumentación RUM opt-in local y bucketizada.
- [x] Presupuestos de carga/request definidos.

**Falta para cierre total:**

- [ ] Field/RUM real con consentimiento y retención aprobados.
- [ ] Optimización de first useful result, JS, imágenes y requests.
- [ ] LCP/INP/CLS/TTFB por viewport/tema/locale.
- [ ] Gate CI reproducible y no regresión.
- [ ] Correlación rendimiento → búsqueda/resultados/tracking sin PII.

### H37 — Backend, concurrencia y costes

**Estado auditado: EN QA — IMPLEMENTACIÓN PARCIAL.**

**Evidencia:** budget ledger, circuit, leases, outcomes, latency, migraciones 0043–0046 y tests unitarios/integración; canary offline Mock.

**Checklist cerrado:**

- [x] Budget/circuit/lease/outcome básicos.
- [x] Runner Mock/canary offline y kill switch local verificados.
- [x] Latencia y errores se pueden persistir en alcance local.

**Falta para cierre total:**

- [ ] Benchmark PostgreSQL con concurrencia y locks reales.
- [ ] Calibrar p50/p95, timeouts, retries y límites por operación.
- [ ] Canary comercial con coste monetario real y budget no cero.
- [ ] Reconciliación de consumo y alertas de cuota.
- [ ] SLO/cost guardrails aprobados y dashboard operativo.

### H38 — Ownership, secretos, SSRF y abuso

**Estado auditado: EN QA — HARDENING FOCALIZADO.**

**Evidencia:** ownership API, sanitizer de deeplinks, redaction Makcorps, bounds de queries y tests focalizados.

**Checklist cerrado:**

- [x] Ownership de tracked offers, alertas, comp sets e inbox en rutas existentes.
- [x] Redaction de API keys/tokens en errores/payloads.
- [x] Allowlist de deeplinks y límites de parámetros.

**Falta para cierre total:**

- [ ] Limiter distribuido y abuso por usuario/IP/operación.
- [ ] Auditoría SSRF completa incluyendo DNS/rebinding/redirects.
- [ ] Dependency/secrets/SAST/DAST scans automatizados.
- [ ] Pen-test focalizado y regresiones de cross-user A/B.
- [ ] Rollout y kill switch de mitigaciones.

### H39 — Pirámide de tests y gaps

**Estado auditado: EN QA.**

**Evidencia:** `docs/reference/backend/hoteles-test-pyramid-gaps-h39.md`; suite backend, migraciones SQLite recientes, tests de observabilidad, provider, API y H44.

**Checklist cerrado:**

- [x] Tests unitarios, integración, contratos y migraciones presentes.
- [x] Gaps explícitos en documentación.
- [x] 315 tests de la suite hotelera relacionada pasan en la validación más reciente.

**Falta para cierre total:**

- [ ] PostgreSQL real y concurrencia de sweeps/alertas/delivery.
- [x] Fault profiles ejecutables reproducibles para 429, timeout, empty, invalid JSON, schema drift, rate sin moneda, sold out y deeplink inválido; outcomes y latencia de revalidación persistidos.
- [x] Fault profiles avanzados `hotel_ambiguous`, `stale_history` y `partial_batch` con warnings/needs_review por item; los matches ambiguos no crean alias operativos.
- [ ] Contract tests V2 provider-neutral.
- [ ] Browser E2E completo con ownership A/B.
- [ ] Gate CI por fases y artefactos redacted.

### H40 — QA visual, manual y cross-browser

**Estado auditado: EN QA.**

**Evidencia:** `docs/reference/frontend/hoteles-visual-manual-crossbrowser-qa-h40.md`; smoke Chromium desktop/mobile × dark/light, `docs/qa/evidence/hotels-h40-rerun-audit-current/report.json` y scripts QA.

**Checklist cerrado:**

- [x] Hay runner Chromium y escenarios Mock/local.
- [x] Se han ejecutado rondas desktop/mobile y dark/light en alcance declarado.
- [x] El documento distingue smoke automatizado de cierre visual completo.

**Falta para cierre total:**

- [x] Repetir evidencia contra el código actual y guardar artefactos redacted en `docs/qa/evidence/hotels-h40-rerun-audit-current/` (Chromium 147, 2026-08-10, cuatro perfiles ES; instancia Next fresca).
- [ ] Firefox/WebKit/Safari real o estrategia aprobada de cross-browser.
- [ ] Revisión humana de jerarquía, copy, foco, overflow y estados degradados.
- [x] Screenshots/network evidence redacted con dataset/profile en `docs/qa/evidence/hotels-h40-rerun-audit-current/`.
- [ ] Aprobación final de QA/UX.

### H41 — Observabilidad end-to-end

**Estado auditado: EN QA — IMPLEMENTACIÓN AMPLIA, GATES ABIERTOS.**

**Evidencia:** request context/correlation, provider runs, latency sinks/aggregates, budget/circuit/lease diagnostics, daily metrics, admin health/cabina, alert→inbox y smoke Chromium Mock; `docs/reference/backend/hoteles-observability-e2e-h41.md`.

**Checklist cerrado:**

- [x] Correlación browser/API/provider/DB en varios caminos.
- [x] Redaction y admin-only diagnostics.
- [x] Provider run, outcomes, latency, ledger diario y diagnósticos de lease/budget/circuit.
- [x] Cabina admin y smoke automatizado Mock.

**Falta para cierre total:**

- [ ] Correlación y evidencia en todos los read paths y errores, no solo ingestion/revalidation/area search.
- [ ] Métricas RED y provider persistentes con cardinalidad controlada.
- [ ] Dashboards RED/provider reales, alertas operativas y SLO.
- [ ] Retención, exportación y acceso auditados.
- [ ] Coste monetario por provider/operación.
- [ ] Revisión humana/cross-browser y canary live.

### H42 — Runbooks, soporte y recovery

**Estado auditado: COMPLETA — CONTRATO/RUNBOOK; OPERACIÓN NO SIMULADA.**

**Evidencia:** `docs/runbooks/hoteles-incidentes-recovery-h42.md`; procedimientos de provider, sweep, delivery, DB, redaction y comunicación.

**Checklist cerrado:**

- [x] Severidades, contención, diagnóstico, recovery y comunicación descritos.
- [x] Límites: no provider live, no delivery real, no rollback genérico y no promesa diaria declarados.
- [x] Handoff a H09/H28/H38/H41/H43/H45.

**Falta para cierre total operativo:**

- [ ] Asignar owners/guardia y contactos reales.
- [ ] Simulacro Mock de provider caído, 429, sweep duplicado, delivery fallido y seed/reset corrupto.
- [ ] Evidencia de tiempos de detección, contención, recuperación y comunicación.
- [ ] Postmortem template usado en un ejercicio.
- [ ] Integrar señales H41 y kill switches H43.

### H43 — Flags, canary y kill switches

**Estado auditado: EN QA — LOCAL/MOCK VERIFICADO; LIVE BLOQUEADO.**

**Evidencia:** resolver central, flags, `hotel_mock_canary.py`, tests H43, redaction y cero red local.

**Checklist cerrado:**

- [x] Resolver de activación central y entrypoints protegidos.
- [x] Mock canary offline con kill switch y evidencia redacted.
- [x] Provider live desactivado por defecto y budget comercial cero por defecto.

**Falta para cierre total:**

- [ ] Flags dinámicas/seguras para staging con audit trail.
- [ ] Canary comercial real por mercado y operación.
- [ ] Leases/budget de rollout y promoción automática/manual.
- [ ] Métricas tripwire, rollback y kill switch probado en caliente.
- [ ] Runbook de aprobación y evidencia de no tráfico fuera del scope.

### H44 — Seed, demo y fallos reproducibles

**Estado auditado: EN QA — seed/reset, profiles, canary offline y browser E2E local cerrados; canary comercial, matriz histórica y cross-browser/QA humano pendientes.**

**Evidencia:** `hotel_demo_seed.py`, `hoteles_demo_manifest.json`, `fault_profiles.py`, `hotel_fault_profiles.json`, `test_hotels_fault_profiles.py`, `test_hotels_phase1_smoke.py`; validación del 2026-08-10: suite hotelera relacionada `315 passed`, frontera H44 focal `92 passed`, Ruff/compileall/diff limpios; smoke CLI real seed repetido, reset bloqueado/confirmado y abort.

**Checklist cerrado:**

- [x] Manifest versionado `hoteles-demo-v1` y label `DEMO_NO_LIVE_AVAILABILITY`.
- [x] SQLite absoluta en temp y `APP_ENV` seguro.
- [x] Seed Mock idempotente con User A/B, hoteles, aliases, snapshots, tracking, alertas, delivery e inbox scope.
- [x] Marker exacto, detección de drift, referencias externas y schema Alembic head.
- [x] Reset fail-closed, orden FK seguro, sidecars y abort explícito.
- [x] Guard de red in-process y reporte redacted con `external_calls_observed`.

**Falta para cierre total:**

- [x] Loader declarativo de fault profiles sin editar producción, con selección por `HOTEL_MOCK_FAULT_PROFILE`.
- [x] Manifest versionado y tests locales de los profiles `happy_path`, `empty_provider`, `rate_limited_429`, `provider_timeout`, `invalid_json`, `schema_drift`,
 `rate_without_currency`, `sold_out`, `hotel_ambiguous`, `deeplink_invalid`, `stale_history`, `partial_batch`, `ownership_cross_user`.
- [x] Profiles ejecutables seleccionables por `HOTEL_MOCK_FAULT_PROFILE` en el worker real; `HotelProviderRun` conserva outcomes y los agregados de latencia de revalidación para 429/timeout/invalid response.
- [x] Deeplink inválido se neutraliza antes de persistir; `sold_out` queda como observación `unavailable` sin sobreescribir precio ni entrar en ranking/parity.
- [x] Expected outcome/status/counts/external_calls completos por los 13 profiles en la matriz offline del canary; cada ejecución reporta redaction y cleanup verificado. [ ] Matriz histórica persistida entre ejecuciones sigue fuera de alcance.
- [x] Smoke API service-level reproducible búsqueda → detalle → tracking → alerta → inbox con User A/B, incluyendo disjoint `source_id` de eventos hoteleros; no se presenta como browser/worker E2E.
- [x] Browser E2E Playwright/Chromium reutilizable sobre dataset H44 `hoteles-demo-v1`, con aislamiento A/B, cleanup y privacy redacted; la evidencia vigente está en `docs/qa/evidence/hotels-h44-browser-current/report.json`.
- [x] Integrar profiles ejecutables con `fetch_hotel_rates()`/worker y outcomes persistidos; la frontera cubre `empty_provider`, `rate_limited_429`, `provider_timeout`, `invalid_json`, `schema_drift`, `rate_without_currency`, `sold_out` y `deeplink_invalid`.
- [x] Completar `hotel_ambiguous`, `stale_history` y `partial_batch` con outcomes por item, warnings y `needs_review` en el alcance service-level/canary. [ ] Separación formal freshness/disponibilidad en todas las superficies sigue pendiente.
- [x] `hotel_mock_canary.py --dry-run` levanta una SQLite efímera por profile sin aceptar DB del caller, compara expectativas y deja `temporary_databases_remaining=0`.
- [x] El workflow backend de CI queda configurado para ejecutar `python scripts/hotel_mock_canary.py --dry-run` como gate offline Mock redacted; la ejecución local del mismo comando pasa y la ejecución remota sigue sin observarse.

### H45 — Release, smoke, canary y rollback

**Estado auditado: EN QA — contrato, smoke local y E2E H44 aislado cerrados; canary/promoción/rollback reales pendientes.**

**Evidencia:** `hoteles-release-canary-smoke-rollback-h45.md`, scripts `qa_hotels_gate_*.mjs`, `qa_hotels_phase57.mjs`, healthchecks y documentación de release.

**Checklist cerrado:**

- [x] Readiness checklist y separación Mock/live documentadas.
- [x] Smoke Chromium/local y health checks parciales.
- [x] Condiciones de promoción, rollback y kill switch descritas.

**Falta para cierre total:**

- [x] Smoke E2E local sobre seed H44 con evidencia redacted, cleanup y privacy; evidencia: `docs/qa/evidence/hotels-h44-browser-current/report.json`.
- [ ] Canary comercial real con métricas de éxito/fallo y presupuesto.
- [ ] Promoción gradual por mercado/flag.
- [ ] Rollback real de imagen/config/migración ensayado y medido.
- [ ] Incidente y comunicación asociados a un ejercicio H42.
- [ ] Firma de release owner/QA/infra.

### H46 — Primera victoria

**Estado auditado: PARCIAL.**

**Evidencia:** contrato H46, implementación parcial del Camino A: copy honesto guardar/seguir, idle/empty y bloqueo de tracking sin contexto; tests frontend existentes.

**Checklist cerrado:**

- [x] Copy de primera búsqueda y empty/idle trabajado.
- [x] Bloqueo honesto de tracking sin contexto.

**Falta para cierre total:**

- [ ] Flujo guiado completo hasta favorito/tracking/confirmación.
- [ ] Auth contextual sin perder intención.
- [ ] Eventos H04 de primera victoria.
- [ ] Mobile, a11y, ES/EN y browser E2E.
- [ ] Métrica de conversión y guardrails.

### H47 — Re-engagement y “Mis hoteles”

**Estado auditado: COMPLETA — CONTRATO/NAVEGACIÓN; IMPLEMENTACIÓN PARCIAL.**

**Evidencia:** contrato H47, módulos actuales, inbox/notificaciones y superficies de tracked offers.

**Checklist cerrado:**

- [x] Contrato de retorno y agregador definido.
- [x] Piezas separadas de watchlist/tracking/inbox existentes.

**Falta para cierre total:**

- [ ] Agregador `/mis-hoteles` o superficie equivalente.
- [ ] URL/deep links contextuales y ownership V2.
- [ ] Lifecycle visual, estados de alertas y snapshots.
- [ ] Eventos de retorno y métricas D1/D7/D30.
- [ ] QA browser mobile/desktop.

### H48 — Búsquedas guardadas y compartibles

**Estado auditado: COMPLETA — CONTRATO; IMPLEMENTACIÓN NO INICIADA SUFICIENTEMENTE.**

**Evidencia:** contrato H48, `hotelSearchUrlState` parcial y tests URL; no se encontró `SavedHotelSearch` completo.

**Checklist cerrado:**

- [x] Parser/contrato URL y reglas de privacidad documentados.
- [x] Parte de serialización/restauración local.

**Falta para cierre total:**

- [ ] Modelo/API de `SavedHotelSearch` y lifecycle.
- [ ] Guardado autenticado, naming, edición, pausa y eliminación.
- [ ] Share token opaco opcional, expiración y revocación.
- [ ] Redacción de PII/geo precisa y ownership.
- [ ] Restore/back-forward y QA E2E.

### H49 — Personalización prudente

**Estado auditado: COMPLETA — CONTRATO; IMPLEMENTACIÓN NO CERRADA.**

**Evidencia:** contrato H49, `searchIntent`/señales frontend parciales y documentación de explicabilidad.

**Checklist cerrado:**

- [x] Principios de opt-in, explicabilidad, límites y no uso de datos sensibles.
- [x] Intento de búsqueda y señales base existentes.

**Falta para cierre total:**

- [ ] Perfil/preferencias hoteleras explícitas y consentimiento.
- [ ] `recommended` versionado con explicación.
- [ ] Controles “por qué veo esto” y desactivar personalización.
- [ ] No alterar ranking objetivo sin evidencia/capabilities.
- [ ] Tests, métricas y QA mobile.

### H50 — Monetización, afiliación y atribución

**Estado auditado: COMPLETA — CONTRATO; IMPLEMENTACIÓN PENDIENTE.**

**Evidencia:** contrato H50, `partner_links.py`, allowlist y sanitizer; no ledger/reconciliación de afiliación hotelera completa.

**Checklist cerrado:**

- [x] Partner/disclosure y límites de atribución definidos.
- [x] Deeplink técnico seguro en alcance actual.

**Falta para cierre total:**

- [ ] Elegir partner/programa y documentar términos.
- [ ] Parámetros de atribución firmados/allowlisted sin secretos.
- [ ] Consentimiento y preferencias.
- [ ] Ledger de clicks, atribución, dedupe y reconciliación.
- [ ] QA de disclosure, redirect, expiración y partner unavailable.

### H51 — Experimentos de producto

**Estado auditado: COMPLETA — CONTRATO; MOTOR PENDIENTE.**

**Evidencia:** contrato H51, flags y métricas disponibles parcialmente.

**Checklist cerrado:**

- [x] Hipótesis, guardrails, tripwires, privacidad y criterios de parada definidos.

**Falta para cierre total:**

- [ ] Asignación sticky y exposición idempotente.
- [ ] Versionado de variante, elegibilidad y exclusiones.
- [ ] Métricas con denominador y no contaminación entre cohorts.
- [ ] Kill switch automático/manual por guardrail.
- [ ] QA y documentación de un experimento real.

### H52 — Feedback y correcciones de confianza

**Estado auditado: COMPLETA — CONTRATO; FLUJO PENDIENTE.**

**Evidencia:** contrato H52 y manejo genérico de errores/API; no se encontró flujo hotelero contextual completo.

**Checklist cerrado:**

- [x] Tipos de feedback, triage, privacidad y respuesta conceptual definidos.

**Falta para cierre total:**

- [ ] CTA contextual de reportar precio/condición/estado/deeplink.
- [ ] Modelo, endpoint, ownership y redaction.
- [ ] Cola/admin triage con prioridad y estado.
- [ ] Vincular feedback a provider/run/snapshot sin PII.
- [ ] Cerrar loop con corrección, respuesta y métrica.

### H53 — Matching y deduplicación de catálogo

**Estado auditado: COMPLETA — CONTRATO; IMPLEMENTACIÓN AVANZADA PENDIENTE.**

**Evidencia:** normalización/ingestion/geocoder y contrato H53; no se encontró cola completa shadow matching/merge/split.

**Checklist cerrado:**

- [x] Normalización básica, aliases y matching inicial.
- [x] Ambigüedad básica registrada en ingestion.

**Falta para cierre total:**

- [ ] Shadow matching auditable con score/version/policy.
- [ ] Cola `needs_review` y resolución humana/admin.
- [ ] Merge/split reversible, aliases e historial preservados.
- [ ] Métricas precision/recall y drift por provider/mercado.
- [ ] Migración y QA multilingüe, incluidos nombres no latinos.

### H54 — Mercados y cobertura geográfica

**Estado auditado: COMPLETA — CONTRATO; REGISTRO/CANARY PENDIENTES.**

**Evidencia:** contrato H54 y budget/provider services; no registro operativo completo de mercados/capabilities.

**Checklist cerrado:**

- [x] Criterios de entrada/salida y capabilities definidos.
- [x] Budget y seguridad como prerequisitos.

**Falta para cierre total:**

- [ ] Registro versionado de mercados, providers y capabilities.
- [ ] Matriz de cobertura, freshness, coste y legal por mercado.
- [ ] Canary, kill switch, rollout y rollback por mercado.
- [ ] Alertas de presupuesto y salud.
- [ ] Decisión documentada de mercado inicial y límites visibles al usuario.

### H55 — Continuidad, backup/restore y disaster recovery

**Estado auditado: PARCIAL — contrato + drill local SQLite/Mock verificados; producción pendiente.**

**Evidencia:** `docs/reference/backend/hoteles-continuidad-disaster-recovery-h55.md` y `docs/qa/evidence/hotels-local-closeout-current/recovery-drill.json`.

**Checklist cerrado:**

- [x] RPO/RTO, backup/restore, reconciliación y recuperación conceptual definidos.
- [x] Riesgos de workers, delivery, provider y migración descritos.

**Falta para cierre total:**

- [ ] Backup automático cifrado con retención/restore testable.
- [x] Restore en SQLite aislada y verificación de schema head, counts, ownership/scope, sentinel y cleanup.
- [ ] Recovery de worker/sweep/delivery y reanudación idempotente.
- [x] Recovery drill local medido con tiempos observados y limitación explícita de RPO same-process.
- [ ] Evidencia firmada y rollback/reconciliation posterior.

### H56 — Revisión anual y siguiente roadmap

**Estado auditado: PARCIAL — EVIDENCIA INCOMPLETA.**

**Evidencia:** `docs/reference/backend/hoteles-revision-anual-roadmap-h56.md`, annual review y DecisionRecord con estado `evidence_incomplete`; baseline y closeout históricos.

**Checklist cerrado:**

- [x] Paquete anual, DecisionRecord, baseline y preguntas de provider/coste/gobernanza creados.
- [x] Gaps H37/H41/H43/H45/H49–H55 identificados.

**Falta para cierre total:**

- [ ] Completar evidencia de cada decisión y owner.
- [ ] Aprobar DecisionRecord por producto/arquitectura/operación.
- [ ] Actualizar el roadmap maestro con el estado auditado actual.
- [ ] Congelar siguiente roadmap H57+ con dependencias y fechas.
- [ ] Cerrar discrepancias entre docs históricas, código actual y gates reales.

## 4. Checklist transversal de cierre

### Contratos y datos

- [ ] `StayQuery`/offer/snapshot/alert V2 implementados y versionados.
- [ ] V1→V2 bridge, doble lectura/escritura, backfill y rollback.
- [ ] Fees, total/noches, moneda y comparabilidad tipados.
- [ ] Freshness/provenance/confidence aplicados a todas las superficies.
- [ ] Retención y agregados de histórico definidos y ejecutados.

### Provider y operación

- [ ] Provider principal aprobado con sandbox/canary, coste, términos y salida.
- [ ] Provider-neutral envelope y contract tests.
- [ ] Scheduler real con leases, retries, replay, budget, circuit y SLO.
- [ ] Market registry y coverage matrix.
- [ ] Provider live bloqueado por defecto fuera de canary.

### Producto y frontend

- [ ] Formulario H13 completo y URL-driven.
- [ ] Resultados V2, cards contextualizadas y ranking explicable.
- [ ] Detalle URL-driven y retorno.
- [ ] Favorito/tracking con copy y lifecycle sin confusión.
- [ ] Histórico/alertas/inbox con estados honestos.
- [ ] Mis hoteles, búsquedas guardadas y primera victoria.
- [ ] Personalización y experimentación con opt-in/guardrails.

### Calidad, seguridad y compliance

- [ ] WCAG P0/P1/P2 remediado y recorrido manual.
- [ ] ES/EN y timezone/currency/DST verificados.
- [ ] Web Vitals lab + field con gates.
- [ ] SSRF, secrets, abuse y limiter distribuido auditados.
- [ ] PostgreSQL/concurrencia y migraciones probados.
- [ ] Browser E2E y cross-browser vigentes.
- [ ] Legal/disclosure/consentimiento aprobados.

### Alertas, feedback y monetización

- [ ] Alert evaluator/baseline/cooldown/dedupe con tests concurrentes.
- [ ] Delivery in-app, email/push, preferencias, quiet hours, DLQ/replay.
- [ ] Feedback contextual, triage y loop de corrección.
- [ ] Partner/deeplink/affiliate ledger y reconciliación.

### Release y continuidad

- [ ] H44 fault profiles + API/browser E2E.
- [ ] H45 smoke/canary/promotion/rollback real.
- [ ] H42 simulacros y owners de guardia.
- [ ] H55 backup/restore/recovery drill.
- [ ] H56 DecisionRecord aprobado y H57+ congelado.

## 5. Criterio de cierre total del programa

El programa no se marcará como terminado hasta que:

- [ ] todas las fases técnicas indiquen `COMPLETA TOTAL` o tengan una excepción aprobada;
- [ ] los gates A–G tengan evidencia reproducible;
- [ ] no exista provider live o fixture presentado con copy engañoso;
- [ ] una persona pueda ejecutar búsqueda → detalle → tracking → alerta → inbox → partner;
- [ ] User B no pueda ver ni accionar recursos de User A;
- [ ] los estados empty/partial/stale/error tengan recovery útil;
- [ ] el sistema tenga delivery real o comunique claramente que solo existe inbox/in_app;
- [ ] browser, a11y, rendimiento, seguridad, legal, coste, operación y continuidad tengan aprobación y artefactos;
- [ ] el DecisionRecord H56 deje constancia de la decisión de lanzamiento y del siguiente roadmap.

## 6. Regla de actualización futura

La presencia de un archivo, ruta, modelo o test se registra como **evidencia de existencia**. Solo un comando/evidencia fechado que cubra el gate completo se registra como **gate ejecutado**. Si ambas cosas no coinciden, prevalece el estado conservador: `PARCIAL` o `EN QA`.

Cada nuevo cierre debe actualizar simultáneamente:

1. este checklist por fase;
2. el registro auditado del roadmap maestro;
3. el documento canónico de la fase;
4. tests/evidencias con fecha y commit/build;
5. los bloqueos globales de release.

Nunca cambiar `PARCIAL`, `EN QA` o `BLOQUEADA` a `COMPLETA TOTAL` solo porque se haya creado un archivo o pasado un test aislado.
