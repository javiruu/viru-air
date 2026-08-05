# H39 — Pirámide de tests y huecos explícitos de `/hoteles`

**Estado:** COMPLETA como estrategia/matriz de cobertura; implementación de huecos, canary y QA browser pendientes  
**Fecha:** 2026-08-05  
**Área:** backend / frontend / providers / seguridad / migraciones / QA  
**Fuente de verdad:** sí para la pirámide, matriz de cobertura, prioridades y criterios de cierre de H39  
**No es:** una certificación de cobertura, una garantía de ausencia de bugs ni un resultado de ejecución completa del suite

**Depende de:** H06 provider-neutral, H10 estancia/oferta, H11 migración, H15 resultados, H22 favorito/tracking, H23 tracking, H26 alertas, H27 inbox/deeplinks, H28 delivery, H29 lifecycle, H33 a11y, H35 legal/security, H37 costes/locks, H38 ownership/SSRF  
**Relacionado con:** H05 freshness/confidence, H09 sweeps, H12 geocoder, H13 formulario, H14 filtros, H16 cards, H18 detalle, H21 estados, H24 histórico, H25 recomendaciones, H30 fechas flexibles, H31 visual, H32 responsive, H34 i18n, H36 performance, H40 browser QA, H41 observabilidad, H43 flags.

> H39 no cuenta archivos: cuenta comportamientos críticos demostrados. Un test de parser con respuesta mock prueba el parser; no prueba el contrato actual del provider. Un test estructural de React prueba wiring; no prueba foco, red, layout o navegación en un navegador.

---

## 1. Objetivo y frontera

H39 debe dejar claro:

1. qué comportamiento hotelero está probado y en qué capa;
2. qué pruebas son deterministas, cuáles dependen de DB y cuáles tocan red/provider;
3. qué riesgos P0/P1/P2 siguen sin cobertura;
4. qué evidencia permite cerrar cada contrato H06-H38;
5. cómo ejecutar suites pequeños antes de un cambio y suites de release después;
6. cómo evitar que un fixture, snapshot o test estructural esconda una regresión real.

H39 cubre:

- backend unitario, integración API/DB, migración y worker;
- provider contract tests y canary separado de tests locales;
- frontend unitario/estructural de hooks, helpers, estados e i18n;
- browser/E2E del flujo hotelero crítico;
- seguridad negativa, ownership, SSRF, deeplink, secrets y abuso;
- performance/perf regression y observabilidad de outcomes;
- fixtures, seed, datos multiusuario, limpieza y repetibilidad;
- matriz de riesgo y gates por fase.

H39 no compra herramientas ni declara un proveedor de CI. Las herramientas deben seguir la configuración existente; cualquier nuevo servicio o dependencia requiere decisión separada.

---

## 2. Inventario real de test tooling

| Capa | Evidencia local | Lectura correcta |
|---|---|---|
| Backend | `pytest>=8.3.3`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`; markers `integration` y `network` en `backend/pyproject.toml` | Hay infraestructura para tests unitarios, API y red marcada; no todos los tests están clasificados por marker |
| Backend DB | tests usan SQLite in-memory en varias unidades y fixtures de sesión | Sirve para lógica y contratos básicos; no simula todos los locks/concurrencia PostgreSQL |
| Frontend | script `tsx --test` y TypeScript; Playwright en devDependencies | Hay tests Node/estructurales y posibilidad de browser; no existe script dedicado al flujo E2E completo de hoteles |
| TestSprite | casos existentes centrados en Quick Search | No demuestra cobertura de `/hoteles` |
| QA docs | baseline/closeout y contratos H33-H38 | Son evidencia y gates; no sustituyen la ejecución automatizada |
| Red externa | tests Makcorps usan `requests.Session` mock | Detectan parsing/error handling local; no detectan drift, cuota, latencia o disponibilidad real |

**Regla:** un test marcado `network` o un canary live debe estar separado del gate local, tener budget y no usar credenciales en logs. Un test que no se puede ejecutar de forma reproducible se etiqueta `non_blocking` o `manual`, no `passed` por existir.

---

## 3. Cobertura existente observada

### 3.1. Backend unitario

| Área | Tests existentes | Cubre | No cubre todavía |
|---|---|---|---|
| Makcorps adapter | `backend/tests/unit/test_hotels_makcorps_provider.py` | enable/disable, parsing `/city` y `/hotel`, importes, moneda en strings, payload vacío/malformado, HTTP 500/429/timeout simulados, mapping, ausencia de clave en caplog | schema drift real, `Retry-After`, attempts/latencia, cuota/coste, redirects, API key en access logs, contrato provider actual |
| Mock provider | `test_hotels_mock_provider.py` | fixture válido, validaciones de hoteles/rates/moneda/fechas | fixtures corruptos a escala, migración de fixture, lifecycle de datos |
| Ingestion/mapping | `test_hotels_ingestion.py`, `test_hotels_mapping.py` | alias, normalización, matching y rates ingestados | matching ambiguo adversarial, provider ID incorrecto en tracking, rollback/backfill H11 |
| Geo | `test_hotels_geo.py` | haversine, comp sets, radius, anchor y ownership en geo | SSRF geocoder, DNS/redirect, rate limit/cooldown, límites de candidatos grandes |
| Parity | `test_hotels_parity.py` | cálculo de señales con rates | comparabilidad H19/H20, stale/partial/error y múltiples ocupaciones |
| Sweep/alerts | `test_hotels_sweep.py`, `test_hotels_phase7_track_offer.py`, `test_hotels_phase8_sweep.py` | reglas de precio/parity, run Mock, snapshots y algunos tracked offers | leases, dos workers, budget, outcomes H37, dedupe de alertas, provider ID externo, partial/429 sin fallback falso |
| Scheduler/worker | `test_hotels_scheduler_contract.py`, `test_hotels_sweep_worker.py` | contrato básico de flags/ejecución | lock cross-process, restart/lease recovery, catch-up, coste y health real |
| Models | `test_hotels_models_constraints.py` | constraints/relaciones seleccionadas | ownership relacional completa, eventos privados, migraciones SQLite/PostgreSQL |

### 3.2. Backend integración/API

`backend/tests/integration/test_hotels_api_flow.py` cubre una superficie amplia: search, validaciones, feature flag, ingestión Mock, watchlist, comp sets, nearby suggestions, ownership de comp sets/tracked offers/snapshots, alert rules/events, parity, área, CRUD de tracking y respuestas 404/409/422.

Limitaciones observadas:

- la cobertura existente no demuestra todos los endpoints bajo User A/User B;
- no hay gate explícito para regla con `tracked_offer_id` de otra cuenta/hotel;
- no hay test de fuga de `HotelAlertEvent` cuando dos usuarios siguen el mismo hotel;
- no hay integración real PostgreSQL para locks/leases/migraciones H11/H37;
- no hay test server-side de SSRF/open redirect/deeplink allowlist;
- no hay test de redaction en access logs, tracing y excepción de requests;
- no hay prueba de exportación/retención completa de datos hoteleros;
- los tests de provider siguen siendo Mock/fixture.

### 3.3. Frontend

| Archivo/superficie | Evidencia | Límite |
|---|---|---|
| `frontend/tests/hotels-f56-audit.test.ts` | estructura de ruta, componentes, modos, provider signal, tracking/watchlist y bloques responsive | no browser real, no network, no foco/teclado/layout/performance |
| `frontend/tests/hotels-signal-assessment.test.ts` | estados de señal insuficiente/limitada/comparable | no wiring de API, i18n completa, stale/error/partial runtime |
| tests de watchlist vuelo | cobertura fuerte de otras superficies | no sustituyen hotel tracking |
| `frontend/src/modules/hotels` | hooks/componentes ejecutables en `tsx --test` si se extraen helpers | falta una suite hotelera de interacción completa |

No se debe contar la existencia de `hoteles-f56-audit.test.ts` como browser QA. H40 es el gate visual/real.

---

## 4. Matriz por workflow

| Workflow crítico | Unit | Integration/API | Contract/provider | Browser/E2E | Estado H39 |
|---|---:|---:|---:|---:|---|
| auth y catálogo | parcial | parcial | n/a | pendiente hotel | P1 |
| destino/autocomplete | parcial | parcial | geocoder pendiente | pendiente | P1 |
| búsqueda área → resultados | parcial | parcial | Mock parcial | pendiente | P0 |
| detalle → rates/parity | parity parcial | parcial | provider parcial | pendiente | P1 |
| favorito simple | service parcial | watchlist sí | n/a | pendiente | P1 |
| tracking desde oferta | parcial | CRUD/snapshot sí | provider no | pendiente | P0 |
| histórico/freshness/confidence | parcial | limitado | provider no | pendiente | P1 |
| alert rule → event → inbox | reglas sí | eventos sí parcial | delivery no | pendiente | P0 |
| comp set/nearby | geo sí | ownership sí parcial | n/a | pendiente | P2 |
| deeplink externo | no suficiente | no suficiente | no aprobado | pendiente | P0 |
| provider 429/timeout/partial | mock del adapter | limitado | no live | pendiente | P0 |
| sweep concurrente | no | no | no | n/a | P0 |
| migración/rollback | no suficiente | no PostgreSQL | n/a | n/a | P0 |
| SSRF/redaction/abuso | no suficiente | no | no | pendiente | P0 |
| i18n/a11y/responsive | helpers parciales | no | n/a | pendiente H40 | P1 |
| rendimiento/Web Vitals | no | no | n/a | pendiente H36/H40 | P1 |

`P0` aquí significa “no cerrar lanzamiento/contrato operativo sin evidencia”, no necesariamente que el código actual esté roto en todos los casos.

---

## 5. Pirámide objetivo

### 5.1. Base — unitarios rápidos

Deben ser numerosos, deterministas y sin red:

- normalización de nombres/ciudades y matching ambiguo;
- `StayQuery`, fingerprints y comparabilidad;
- fechas civiles, ocupación, moneda, fees y total;
- ranking, confidence, freshness y estados;
- reglas, cooldown, dedupe e idempotencia de alertas;
- provider parser y clasificación de errores;
- redaction de logs/URLs;
- allowlist, parseo y rechazo de SSRF/open redirect;
- helpers frontend de filtros, URL state, locale, copy y estados.

Cada unit test debe indicar qué contrato cubre y no fingir red/DB/lock real.

### 5.2. Centro — integración con DB/API

- FastAPI TestClient con dos usuarios y base aislada;
- CRUD de watchlist/tracking/rules/comp sets/snapshots/events;
- validación relacional de `user_id` + child ID + hotel ID;
- errores 401/403/404/409/422 sin enumeración innecesaria;
- API schema frontend/backend y response envelope;
- ingestión y rollback en SQLite;
- migraciones expand-and-contract y backfill dry-run;
- PostgreSQL real para `FOR UPDATE SKIP LOCKED`, leases, constraints y concurrencia;
- account deletion/export/retention y legacy quarantine.

### 5.3. Contract/provider

Por cada provider habilitado:

- success, empty, partial, unsupported;
- 401/403, 429 con/sin `Retry-After`, 5xx, timeout, invalid JSON;
- attempts, latency, request ID, budget y breaker;
- provider/canonical ID mapping;
- rooms/adults/children/currency/fees/cancellation/availability;
- deeplink ausente/rechazado/allowlisted;
- redaction y no persistencia de secretos.

El provider real se prueba en canary separado, con `network`, credencial efímera, budget explícito y datos no privados. Si no hay plan/cuota aprobados, el resultado es `blocked`, no `passed`.

### 5.4. Cima — browser/E2E

Pocos flujos, pero reales y críticos:

1. login → `/hoteles` → resolver destino → fechas → buscar;
2. loading → result/empty/partial/error con provider Mock controlado;
3. seleccionar hotel → detalle/rates/parity → volver preservando intención;
4. guardar favorito sin crear tracking;
5. crear tracking desde oferta válida → ver snapshot/histórico;
6. crear/editar alerta → ejecutar fixture/sweep → inbox/evento contextual;
7. User B no ve ni muta recursos de User A;
8. deeplink bloqueado/allowlisted con disclosure y nueva pestaña segura;
9. mobile estrecho/intermedio/desktop, dark/light, ES/EN, teclado y reduced motion;
10. provider lento/429/offline sin pérdida de foco ni copy falso.

H40 mantiene la revisión visual humana; un E2E verde no prueba la calidad estética completa.

---

## 6. Prioridades de cobertura

### P0 — bloqueantes de integridad/lanzamiento

- regla con tracking cruzado rechazada;
- eventos privados aislados entre dos usuarios;
- snapshots/alerts/tracking ownership completo;
- provider ID mapping y errores no convertidos en empty/sold_out;
- locks/leases/budget con dos workers en PostgreSQL;
- migración/backfill/rollback y datos legacy;
- SSRF, open redirect, deeplink y secret redaction;
- workflow browser search → tracking → alert/inbox;
- flags off y budget cero producen cero requests externas.

### P1 — estabilidad de producto

- autocomplete latest-wins, cancelación y geocoder limits;
- stale/partial/provider unavailable y recovery;
- histórico/confidence/recommendation con fixtures insuficientes;
- i18n ES/EN, fechas/monedas/timezones;
- responsive/a11y y performance budget;
- rate limits de API, payload, fan-out y abuso.

### P2 — escala y calidad avanzada

- visual regression seleccionada;
- fuzzing de parsers/URLs y mutation testing de reglas;
- load tests de 1/10/30/100 resultados y 1/10/100/1.000 trackings;
- provider canary diario si hay contrato aprobado;
- cross-browser ampliado y chaos/restart de worker;
- coverage trend y test selection por diff.

---

## 7. Fixtures y datos de prueba

Cada fixture debe declarar:

```text
fixture_id
source: local_mock | sanitized_canary | provider_contract
created_at
locale/currency/timezone
stay_query fingerprint
provider/status/outcome
sensitive_data: none | sanitized
expected_capabilities
```

Requisitos:

- hoteles con uno, varios y ningún rate;
- fees/total/cancelación/room/meal explícitos o ausentes;
- provider errors separados de empty;
- estados stale/partial/unavailable;
- dos usuarios y mismo hotel para probar ownership;
- tracking con y sin fechas, habitaciones y condiciones;
- eventos con/sin `rule_id` para legacy quarantine;
- alias interno/externo correcto e incorrecto;
- URLs allowlisted, maliciosas y privadas;
- datos deterministas, timezone explícita y limpieza por test;
- nunca copiar API keys, emails reales o raw provider payload sin redaction.

---

## 8. Gates de ejecución

### Gate U — unit

- suite rápida de dominio/provider/helpers verde;
- no red real ni dependencia de orden global;
- casos boundary e invalidos cubiertos;
- tests nombran el contrato y outcome.

### Gate I — integración/API

- endpoints críticos con User A/B;
- DB aislada y migraciones reproducibles;
- 401/403/404/409/422 verificados;
- eventos, tracking, snapshots y cascadas aislados;
- PostgreSQL requerido para lock/lease real.

### Gate C — contract/provider

- envelope H06 y outcomes H37 completos;
- fixtures versionados y drift detectado;
- provider real solo con canary/budget/credenciales seguras;
- `blocked` explícito si falta contrato comercial.

### Gate B — browser

- flujo principal y recuperación en Chromium al menos;
- foco/teclado, estados, navegación y requests verificadas;
- evidencia de viewport/tema/locale;
- consola sin errores no justificados.

### Gate S — seguridad

- negative authz/BOLA, SSRF, open redirect, secrets, redaction y abuse;
- no endpoints privados por `hotel_id` solamente;
- no raw `deep_link` en href;
- flags off/budget 0 sin egress.

### Gate P — performance

- fixture benchmark y trace H36;
- primer resultado, request count, fan-out y bundle con budget;
- provider real separado de render local;
- no afirmar Web Vitals de field sin RUM suficiente.

### Gate R — release

- no P0 abiertos;
- tests afectados por diff y suites hoteleras completas verdes;
- reportes de tests reproducibles con commit/config/dataset;
- fallos clasificados como código, fixture, provider, infraestructura o entorno;
- rollback y comandos documentados.

---

## 9. Huecos explícitos y definición de cierre

| Hueco | Owner | Dependencia | Evidencia de cierre |
|---|---|---|---|
| authz relacional alert/event | Security/Backend | H38 | tests User A/B y query owner-safe |
| locks/leases/budget | Backend/DB | H37 | PostgreSQL multiworker + outcomes |
| provider drift/canary | Provider/Backend | H06-H08,H37 | contract + canary o blocked firmado |
| migration/legacy | DB/Backend | H11,H29 | dry-run, rollback, quarantine |
| deeplink/SSRF | Security/Frontend | H35,H38 | negative URL/egress/browser tests |
| browser happy path | QA/Frontend | H13-H18,H22-H29 | E2E con fixtures y evidencia |
| notification delivery | Infra/Backend | H28 | inbox/delivery/retry tests |
| performance | Frontend/QA | H36 | lab trace y field no concluyente/conforme |
| i18n/a11y/responsive | Frontend/QA | H32-H34,H40 | automated + browser/manual |

H39 se considera implementada solo cuando cada P0 tiene test o bloqueo explícito firmado, los gates U/I/C/B/S/P/R se ejecutan con evidencia y los huecos restantes aparecen con owner, dependencia y motivo.

---

## 10. Claims que H39 no autoriza

Hasta cerrar los gates, no puede afirmarse que `/hoteles`:

- tenga cobertura de tests completa por tener muchos archivos;
- esté cubierto por browser QA porque exista un test estructural frontend;
- sea compatible con el provider real porque el parser fixture pase;
- tenga locks, leases, budget o SSRF protection porque estén documentados;
- aísle eventos privados entre cuentas sin test User A/B;
- tenga migraciones seguras sin rollback sobre PostgreSQL;
- entregue alertas porque el evento se persista;
- cumpla Web Vitals o accesibilidad por pasar typecheck/build;
- esté listo para lanzamiento si los P0 aparecen como “pendientes conocidos”.

H39 sí autoriza una afirmación más limitada: existe una estrategia de pruebas asignable, una base real identificada y un inventario honesto de los huecos que deben cerrarse antes de declarar el tracker hotelero listo.

**Resultado H39:** matriz de test pyramid aprobada; la cobertura actual es parcial y especialmente insuficiente en browser, seguridad relacional, concurrencia, migraciones, provider live y SSRF. H40 debe cerrar la evidencia visual/browser sin sustituir H39.
