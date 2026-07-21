# Live flight tracking a partir de Watchlist - plan de implementacion

> Convertir una Watch guardada en un punto de acceso fiable al estado operacional real del vuelo, sin romper el seguimiento de precios ni convertir `/watchlist` en un radar saturado.

**Estado:** Completado
**Creado:** 2026-07-21
**Owner:** Codex
**Decision de arquitectura:** [ADR-005](../../adr/ADR-005-live-operational-flight-tracking.md)
**Skills aplicadas:** `brainstorm`, `architecture`, `writing-plans`, `Viru Air UI`, `oma-backend`, `oma-frontend`, `oma-qa`, `omo:programming`, `omo:visual-qa`, `omo:debugging`, `omo:review-work`, `omo:git-master`

## 1. Objetivo verificable

Desde `/watchlist`, al seleccionar una Watch guardada desde un resultado exacto de Quick Search, el usuario puede ver:

- numero y compania del vuelo;
- estado operacional normalizado;
- salida y llegada programadas, estimadas o reales;
- retraso, terminal y puerta cuando existan;
- posicion, altitud, velocidad y rumbo solo cuando sean datos observados;
- fuente, momento de observacion, frescura y cobertura;
- una explicacion util cuando la identidad, la configuracion o la cobertura no permitan tracking.

La Watchlist de precios debe seguir funcionando completa si esta feature esta desactivada o falla.

## 2. Lectura del sistema actual

### Lo que ya existe

- `FlightWatch` pertenece al usuario y es unica por ruta/fecha.
- `PriceSnapshot` es historico visible y privado por Watch.
- `FlightOfferCacheEntry` ya conserva `flight_instance_fingerprint`, numero, carrier, salida y llegada cuando el proveedor los entrega.
- Quick Search persiste observaciones exactas en Fare Memory.
- `/search/save-result` guarda la ruta, pero su payload actual omite identidad y piernas.
- `/watchlist/{id}` devuelve precio e historico, no datos operacionales.
- El mapa actual representa rutas, no posiciones de aeronaves.
- ADR-004 define el hub de frescura/revalidacion y prohibe caches paralelas de precio.

### Brecha estructural

Una ruta/fecha no identifica un vuelo. Puede haber varias salidas, codeshares o conexiones. El seguimiento operacional solo puede activarse con una identidad exacta o con una eleccion explicita del usuario.

## 3. Alcance y no-alcance

### Incluido en v1

- identidad exacta obtenida al guardar desde Quick Search;
- itinerarios directos y con varias piernas;
- snapshots operacionales compartidos por identidad;
- proveedor Aviationstack opcional y reemplazable;
- endpoint autenticado por Watch;
- cache, TTL, cooldown, errores tipados y observabilidad sin PII;
- polling consciente de visibilidad;
- panel operacional compacto y posicion integrada en el mapa existente;
- dual theme, responsive, i18n ES/EN y accesibilidad;
- pruebas unitarias, integracion, contrato, migracion, frontend, browser y resiliencia.

### Fuera de alcance de v1

- notificaciones push de cambios de puerta o retraso;
- prediccion propia de ETA;
- interpolar o simular movimiento entre posiciones;
- historial indefinido de trayectorias;
- tracking de equipaje;
- seleccion manual compleja entre codeshares;
- comprometer una licencia comercial de proveedor desde el codigo.

Estos puntos quedan preparados por el modelo, pero no aparecen como promesas de UI.

## 4. Enfoques comparados

| Enfoque | Tipo | Ventajas | Costes/riesgos | Decision |
|---|---|---|---|---|
| Llamar al proveedor desde React | tactico | implementacion corta | expone clave, CORS, cuota por pestaña, sin cache compartida | descartado |
| Resolver ruta/fecha en cada request | tactico | no migra Watch | identidad ambigua, resultado inestable, imposible multi-leg | descartado |
| Identidad opcional + snapshot operacional compartido | estructural | correcto, compatible, auditable, multi-leg, proveedor intercambiable | migracion y mas pruebas | elegido |

## 5. Principios de experiencia Viru

1. **Utilidad antes que telemetria:** estado, hora y retraso pesan mas que una lista de coordenadas.
2. **Honestidad visible:** `En vivo`, `Actualizado`, `Programado`, `Sin cobertura` y `Dato antiguo` no son intercambiables.
3. **Una lectura principal:** el usuario ve primero "que esta pasando" y despues el detalle.
4. **Profundidad progresiva:** una tarjeta compacta por defecto; detalles de cada pierna bajo demanda.
5. **Aviacion calida:** IATA, timeline, pulsos discretos y mapa con intencion; no consola fria ni dashboard generico.
6. **Movimiento con significado:** solo pulsa un indicador cuando llegan datos recientes; no se anima un avion estacionario ni estimado.
7. **Dual theme real:** dark cinematografico y light luminoso comparten semantica, densidad y jerarquia.
8. **El fallo no domina:** si tracking no existe, precios e historico mantienen prioridad y funcionalidad.

## 6. Viajes de usuario

### 6.1 Watch guardada desde Quick Search, vuelo programado

1. El usuario selecciona la Watch.
2. El panel muestra numero, ruta, salida programada y `Programado`.
3. La fuente y la frescura aparecen como metadato secundario.
4. El mapa conserva la ruta; no inventa una posicion.

### 6.2 Vuelo activo con posicion

1. El estado principal pasa a `En vuelo`.
2. Se muestran salida real, llegada estimada y retraso relevante.
3. El mapa anade un marcador de aeronave con rumbo.
4. La UI actualiza mientras la pestana esta visible.

### 6.3 Vuelo activo sin posicion

1. Se muestra `En vuelo` y los hitos disponibles.
2. Se explica `Posicion no disponible en esta actualizacion`.
3. El mapa conserva la ruta sin marcador.

### 6.4 Watch manual o antigua

1. Se muestra `Seguimiento no enlazado`.
2. CTA: `Buscar este vuelo en Quick Search` con ruta/fecha precargadas.
3. No se intenta adivinar una salida entre varias.

### 6.5 Proveedor no configurado o sin cobertura

1. Mensaje compacto, sin error de pagina.
2. Se conserva el ultimo snapshot si existe y se marca antiguo.
3. Precio, historico, alertas y acciones siguen operativos.

### 6.6 Itinerario con conexiones

1. La tarjeta resume la pierna actual o siguiente.
2. Un control `Ver trayecto completo` abre la lista ordenada.
3. Cada pierna conserva su propio estado y frescura.

## 7. Modelo de datos

### 7.1 `WatchTrackedFlightLeg`

| Campo | Tipo | Regla |
|---|---|---|
| `id` | UUID string | PK |
| `watch_id` | FK | indexado, cascade delete |
| `sequence` | int | >= 0, unico por Watch |
| `flight_instance_fingerprint` | string(64) | indexado |
| `carrier_code` | string(16), nullable | normalizado uppercase |
| `flight_number` | string(32), nullable | normalizado uppercase |
| `origin_iata` | string(3) | uppercase |
| `destination_iata` | string(3) | uppercase |
| `departure_date_local` | date, nullable | fecha civil de salida conservada sin asumir UTC |
| `scheduled_departure_at` | datetime, nullable | UTC naive en DB |
| `scheduled_arrival_at` | datetime, nullable | UTC naive en DB |
| `identity_source` | string(24) | `quick_search` en v1 |
| `created_at`, `updated_at` | datetime | auditoria |

Reglas:

- identidad sin numero es valida solo si el fingerprint contiene horarios y ruta;
- una Watch manual tiene cero piernas;
- re-guardar un resultado reemplaza piernas dentro de una transaccion;
- el reemplazo nunca afecta `PriceSnapshot`.

### 7.2 `FlightOperationalSnapshot`

| Grupo | Campos |
|---|---|
| identidad | `flight_instance_fingerprint`, `provider`, `provider_flight_id`, `flight_number`, `callsign`, `icao24` |
| estado | `status`, `status_raw`, `observed_at`, `expires_at`, `data_quality` |
| horario | scheduled/estimated/actual departure y arrival |
| aeropuerto | terminal y gate de salida/llegada |
| disrupcion | `departure_delay_minutes`, `arrival_delay_minutes` |
| posicion | latitude, longitude, altitude_m, speed_mps, heading_deg, on_ground |
| aeronave | registration, aircraft_iata/icao |
| auditoria | `created_at` |

No se guarda el JSON crudo, access keys, datos de pasajero ni URLs firmadas.

Indices:

- `(flight_instance_fingerprint, observed_at DESC)`;
- `(expires_at)` para limpieza;
- `(provider, provider_flight_id)` cuando exista.

Retencion v1: mantener el ultimo conjunto util; la poda historica queda parametrizada y no bloquea lectura.

## 8. Contrato de proveedor

```text
OperationalFlightProvider.fetch(FlightIdentity, now) -> ProviderFetchOutcome

ProviderFetchOutcome =
  | Observed(snapshot)
  | NoCoverage(reason, retry_after)
  | RateLimited(retry_after)
  | ProviderUnavailable(reason)
  | NotConfigured
```

### Aviationstack v1

- clave: `AVIATIONSTACK_API_KEY`;
- base URL configurable: `AVIATIONSTACK_BASE_URL`;
- timeout configurable y acotado;
- filtro primario por numero/fecha, validacion secundaria por ruta y horario;
- nunca se acepta la primera coincidencia sin puntuar identidad;
- status raw se mapea a vocabulario Viru;
- si dos candidatos empatan, el resultado es `ambiguous`, no una eleccion arbitraria;
- logs con proveedor, latencia, outcome y fingerprint truncado; nunca la clave o payload completo.

### Politica de seleccion futura

El registro de proveedores permitira prioridad por capacidad. OpenSky solo podra enriquecer posicion cuando exista una asociacion ICAO24/callsign fiable y una licencia compatible.

## 9. API

### `GET /api/v1/watchlist/{watch_id}/live`

Autenticacion: Bearer existente. El usuario debe ser owner de la Watch.

Query opcional:

- `refresh=true|false`, default `true`;

Respuesta 200 estable incluso sin cobertura:

```json
{
  "watch_id": "uuid",
  "coverage": "live",
  "provider_status": "ok",
  "generated_at": "2026-07-21T10:00:00Z",
  "refresh_after_seconds": 60,
  "legs": [
    {
      "sequence": 0,
      "identity": {
        "flight_number": "FR1234",
        "origin_iata": "MAD",
        "destination_iata": "FCO"
      },
      "operational": {
        "status": "active",
        "observed_at": "2026-07-21T09:59:30Z",
        "freshness": "fresh",
        "departure": {"scheduled_at": "...", "actual_at": "...", "terminal": "1", "gate": "B12"},
        "arrival": {"scheduled_at": "...", "estimated_at": "...", "terminal": "3", "gate": null},
        "position": {"latitude": 41.1, "longitude": 2.1, "altitude_m": 9100, "speed_mps": 220, "heading_deg": 94, "on_ground": false}
      }
    }
  ]
}
```

Valores de `coverage`:

- `live`: al menos una pierna tiene observacion fresca;
- `cached`: solo hay observaciones reutilizadas;
- `identity_missing`: Watch sin piernas exactas;
- `not_configured`: ningun proveedor operacional activo;
- `no_coverage`: proveedor consultado sin coincidencia fiable;
- `temporarily_unavailable`: error o rate limit con posible dato antiguo;
- `completed`: todas las piernas finalizadas.

Errores HTTP reservados:

- 401 token ausente/invalido;
- 404 Watch inexistente o ajena;
- 422 query invalida;
- 500 solo bug interno no representable como outcome.

### Extension `POST /api/v1/search/save-result`

Anade de forma compatible:

- `legs[]` opcional con numero, IATA y timestamps;
- clientes antiguos siguen validando;
- respuesta conserva `watch_id` y `created_or_existing`, y anade `tracking_identity` (`linked`, `missing`, `updated`).

## 10. Frescura, polling y cuota

| Fase del vuelo | TTL recomendado | Polling UI | Nota |
|---|---:|---:|---|
| > 24 h antes | 6 h | sin polling automatico | horario bajo demanda |
| 2-24 h antes | 30 min | 10 min | puertas pueden cambiar |
| < 2 h antes | 5 min | 2 min | estado pre-salida |
| active | 60 s | 60 s | limitado por proveedor |
| landed/cancelled/diverted | 6 h | detener | estado terminal |
| error/rate limit | retry indicado o backoff | respetar backend | conservar stale |

La UI usa `refresh_after_seconds` del backend; no codifica una cadencia paralela. `document.visibilityState !== "visible"` detiene timers.

## 11. Arquitectura frontend

### Nuevos modulos

- `frontend/src/modules/watchlist/liveFlightTypes.ts`: contrato tipado.
- `frontend/src/modules/watchlist/useWatchLiveFlight.ts`: carga, polling y stale-while-error.
- `frontend/src/modules/watchlist/components/WatchLiveFlightPanel.tsx`: lectura operacional y timeline.
- `frontend/src/modules/watchlist/liveFlightPresentation.ts`: labels, frescura y seleccion de pierna activa.

### Integracion

- `page.tsx` carga live solo para `selectedWatchId`.
- `WatchDetailPanel` recibe el estado live y mantiene precios separados.
- `WatchlistMapDecisionPanel` recibe como maximo una posicion observada de la Watch seleccionada.
- Quick Search envia piernas al guardar.
- i18n se amplia en ES/EN sin strings hardcoded.

### Jerarquia visual

1. Ruta, fecha y estado Watch.
2. Franja operacional: `En vuelo`, `Retrasado 25 min`, `Aterrizado`, etc.
3. Hitos de salida/llegada.
4. Frescura/fuente.
5. Detalle de piernas y telemetria bajo demanda.
6. Precios e historico continúan como bloque de decision economica.

## 12. Catalogo de fallos y respuesta esperada

### Identidad

| Fallo | Riesgo | Comportamiento |
|---|---|---|
| Watch antigua sin piernas | falsa precision | `identity_missing` + CTA Quick Search |
| vuelo sin numero | match debil | usar fingerprint/horario solo si unico; si no, no coverage |
| codeshare | dos numeros, mismo avion | conservar identidad seleccionada; provider id secundario |
| varias salidas misma ruta/dia | vuelo equivocado | nunca resolver solo por ruta/fecha |
| cambio de numero | snapshot no enlaza | no mutar identidad sin evidencia fuerte |
| conexion con pierna faltante | journey incompleto | mostrar cobertura parcial por pierna |
| re-guardar otro resultado | cambio silencioso | reemplazo transaccional y `tracking_identity=updated` |

### Tiempo

| Fallo | Respuesta |
|---|---|
| timezone proveedor ambiguo | parsear timestamps ISO; almacenar UTC; no inferir offset desconocido |
| vuelo cruza medianoche | fecha por salida local y timestamps completos |
| cambio horario DST | confiar en timestamp con zona; si falta, degradar calidad |
| reloj servidor desviado | frescura basada en `observed_at`; monitorizar edades imposibles |
| datos futuros/negativos | rechazar snapshot invalido |

### Proveedor y red

| Fallo | Respuesta |
|---|---|
| clave ausente | `not_configured`, sin stacktrace usuario |
| 401/403 proveedor | error de configuracion observable, no retry agresivo |
| 429 | respetar retry, servir stale |
| 5xx/timeout/DNS | timeout acotado, stale, backoff |
| payload cambia | parser falla cerrado, contrato testado |
| lista vacia | `no_coverage`, no 500 |
| candidato ambiguo | `no_coverage: ambiguous` |
| posicion nula | estado sin marcador |
| coordenadas fuera de rango | descartar posicion, conservar resto |
| latencia alta | cache compartida y presupuesto de timeout |

### Persistencia y concurrencia

| Fallo | Respuesta |
|---|---|
| dos pestañas refrescan | lock/cooldown DB por identidad o reutilizacion del snapshot |
| migracion parcial | revision idempotente y rollback probado |
| snapshot duplicado | dedupe por identidad/provider/observed_at |
| transaccion de piernas falla | rollback completo, Watch intacta |
| Watch eliminada durante fetch | revalidar ownership antes de responder/persistir enlace |
| crecimiento de snapshots | indice, retencion y prueba de query plan |

### Frontend y UX

| Fallo | Respuesta |
|---|---|
| cambio rapido de Watch | AbortController; respuesta antigua no pisa seleccion nueva |
| pestana oculta | polling pausado |
| navegador offline | ultimo dato + estado offline, sin limpiar panel |
| respuesta parcial | render por campos opcionales |
| mapa no carga | tarjeta operacional sigue util |
| reduccion de movimiento | sin pulsos/rotaciones innecesarias |
| lector de pantalla | `aria-live=polite` solo para cambios relevantes |
| movil estrecho | timeline vertical, sin scroll horizontal obligatorio |
| locale | fechas, horas, unidades y decimales localizados |

### Seguridad y privacidad

| Fallo | Respuesta |
|---|---|
| consultar Watch ajena | 404 indistinguible |
| key en query/log | key solo server-side y redaccion |
| raw payload con PII | no persistir raw |
| enumeracion de IDs | auth + owner filter |
| SSRF por base URL | base URL solo config de despliegue, nunca input usuario |
| abuso de refresh | TTL/cooldown compartido y metricas |

## 13. Fases de implementacion

### Fase 0 - Contrato y pruebas rojas

- [x] Congelar vocabulario de estados y cobertura.
- [x] Anadir pruebas de contrato para save-result con `legs` y compatibilidad legacy.
- [x] Anadir pruebas de parser proveedor y seleccion no ambigua.
- [x] Anadir pruebas de endpoint: owner, ajeno, identity missing, not configured, cached y live.

### Fase 1 - Persistencia de identidad

- [x] Crear migracion para piernas y snapshots operacionales.
- [x] Anadir modelos e indices.
- [x] Extender save-result y persistir piernas en una transaccion.
- [x] Verificar upgrade/downgrade y re-upgrade.

### Fase 2 - Dominio y proveedor

- [x] Crear tipos de dominio y outcomes exhaustivos.
- [x] Implementar normalizacion/validacion del payload Aviationstack.
- [x] Implementar matching por numero, ruta, fecha y horario.
- [x] Implementar proveedor no configurado y registro.
- [x] Anadir logs y metricas sin secretos.

### Fase 3 - Servicio y API

- [x] Implementar repositorio de piernas/snapshots.
- [x] Implementar politica de TTL por fase.
- [x] Implementar `GET /watchlist/{id}/live`.
- [x] Probar autorizacion, cache, stale, rate limit y errores.

### Fase 4 - Quick Search

- [x] Enviar legs exactas al guardar.
- [x] Mantener payload legacy y combinaciones ida/vuelta.
- [x] Probar directos, conexiones y datos incompletos.

### Fase 5 - Watchlist UI

- [x] Crear tipos/presentacion/hook.
- [x] Integrar panel compacto con estados completos.
- [x] Anadir detalle progresivo multi-leg.
- [x] Anadir posicion observada al mapa.
- [x] Completar i18n ES/EN y ambos temas.

### Fase 6 - Resiliencia y rendimiento

- [x] Pausar polling oculto y abortar requests obsoletos.
- [x] Validar dedupe/cooldown concurrente.
- [x] Medir query y payload.
- [x] Verificar que Watchlist sin tracking no hace llamadas innecesarias.

### Fase 7 - QA, rollout y operacion

- [x] Unit, integration, contract, migration y frontend tests.
- [x] Browser QA con mocks; smoke real redacted condicionado a disponer de key.
- [x] Accesibilidad, responsive, dual theme y reduced motion.
- [x] Seguridad, performance y regresion Watchlist/Quick Search.
- [x] Runbook de configuracion, cuota, fallos y rollback.
- [x] Actualizar docs, inventory y HISTORY.

## 14. Matriz QA obligatoria

### Backend unitario

- normalizacion de status;
- validacion de coordenadas/unidades;
- matching exacto y ambiguo;
- TTL por fase;
- mapeo de errores 401/403/429/5xx/timeout;
- seleccion de stale util;
- redaccion de claves.

### Backend integracion

- migration upgrade/downgrade/re-upgrade;
- save-result legacy y nuevo;
- reemplazo transaccional de legs;
- endpoint owner/otro usuario;
- identity missing/not configured/no coverage/live/cached/stale;
- multi-leg parcial;
- dos requests concurrentes no duplican llamada/persistencia.

### Contrato

- OpenAPI y Pydantic admiten clientes antiguos;
- campos nuevos opcionales;
- enums documentados;
- timestamps serializados en ISO 8601;
- ninguna respuesta contiene key/raw payload.

### Frontend unitario

- presentacion de cada estado;
- pierna actual/siguiente;
- formato de retrasos y unidades;
- payload Quick Search con legs;
- polling y visibility;
- stale-while-error;
- ausencia de posicion no crea marcador.

### Browser/E2E

- ruta `/watchlist` autenticada con mocks;
- seleccionar Watch directa programada;
- transicion programado -> active -> landed;
- multi-leg y expansion;
- Watch manual con CTA;
- 429/timeout manteniendo stale;
- cambio rapido entre Watches;
- mapa con/sin posicion;
- pausa de polling al ocultar pestaña;
- consola sin errores y red sin loops.

### Visual

- 1440x900, 768x1024, 375x812 y 320 px;
- light/dark;
- loading, empty, no coverage, stale, active, landed, cancelled;
- contenido largo ES/EN;
- zoom 200%;
- `prefers-reduced-motion`;
- contraste WCAG 2.2 AA y foco visible.

### Rendimiento

- no fetch live sin Watch seleccionada;
- un timer por pantalla;
- respuesta cacheada sin llamada externa;
- payload acotado;
- indices usados en lookup principal;
- build production y auditoria browser sin regresion material.

### Seguridad

- IDOR;
- secreto en logs/respuestas;
- validacion de proveedor;
- limites de longitud/numero/rangos;
- base URL no controlable por usuario;
- dependencia y audit basico;
- errores no revelan configuracion sensible.

### Operacion

- feature funciona desactivada;
- key invalida;
- cuota agotada;
- proveedor caido;
- rollback de migracion;
- metricas permiten distinguir no-config, no-coverage, rate-limit y fallo;
- runbook permite verificar sin datos privados.

## 15. Comandos de verificacion previstos

```bash
cd backend
python -m pytest tests/unit/test_aviationstack_operational_provider.py -q
python -m pytest tests/unit/test_live_flight_snapshot_retention.py -q
python -m pytest tests/integration/test_watchlist_live_tracking.py -q
python -m pytest -q
python -m alembic upgrade head
python -m alembic downgrade -1
python -m alembic upgrade head
python -m ruff check app tests

cd ../frontend
npm test
npm exec tsc -- --noEmit --pretty false
npm run build
```

Browser QA reutiliza `localStorage.viru_token` y mocks `page.route('**/api/v1/**', ...)`, con requests contadas para demostrar la cadencia.

## 16. Definition of Done

- [x] Una Watch guardada desde Quick Search conserva cada pierna exacta.
- [x] Una Watch manual no se enlaza a un vuelo por adivinacion.
- [x] El backend devuelve estados honestos con o sin proveedor.
- [x] Cache, TTL y errores evitan consumo duplicado.
- [x] La UI muestra estado/hitos/frescura sin desplazar precios ni historico.
- [x] El mapa solo muestra posiciones observadas validas.
- [x] Multi-leg, legacy, no-config y stale estan cubiertos.
- [x] Auth/IDOR, secretos y payloads crudos estan auditados.
- [x] Tests objetivo, suites completas, typecheck, lint y build pasan.
- [x] QA browser y visual cubren temas y breakpoints.
- [x] Migracion y rollback estan verificados.
- [x] Docs/runbook/inventory/HISTORY estan sincronizados.
- [x] Revisión multidisciplinar completada y cambios preparados para publicación en `main`.

## 17. Revision ciega de riesgos

| Lente | Critica independiente | Resolucion |
|---|---|---|
| usuario | un mapa bonito puede ocultar que se rastreo el vuelo equivocado | identidad exacta o estado no enlazado |
| backend | cada polling podria consumir cuota | TTL y snapshot compartido |
| datos | ruta/fecha no soporta conexiones | piernas ordenadas |
| seguridad | proveedor directo expone key | adapter server-side |
| operaciones | key ausente podria romper Watchlist | outcome `not_configured` no fatal |
| frontend | demasiada telemetria sobrecarga | resumen principal + disclosure |
| accesibilidad | actualizaciones frecuentes crean ruido | aria-live selectivo y polling moderado |
| QA | mocks felices no prueban degradacion | matriz de error, stale y ambiguedad |

Tier 1 resuelto antes de codigo: identidad ambigua, cuota duplicada, fallo global por proveedor y mezcla precio/operacion.

## 18. Decision log

| Fecha | Decision | Motivo |
|---|---|---|
| 2026-07-21 | interpretar `live` como tracking operacional real | separa claramente precio de estado de vuelo |
| 2026-07-21 | conservar `FlightWatch` ruta/fecha | compatibilidad y semantica actual |
| 2026-07-21 | modelar piernas exactas | directos, conexiones y ausencia de adivinacion |
| 2026-07-21 | snapshots operacionales compartidos | cuota, coherencia y privacidad |
| 2026-07-21 | Aviationstack como primer adapter opcional | cubre status, horarios, gates y posicion |
| 2026-07-21 | no usar OpenSky como fuente primaria | contrato incompleto y restricciones de uso |

## 19. Progress notes

- [2026-07-21] Inventario de Watchlist, Fare Memory, Quick Search, mapa, tests y docs completado.
- [2026-07-21] Brainstorming, comparacion de enfoques, ADR y revision ciega completados.
- [2026-07-21] Plan creado; comienza Fase 0 con TDD.
- [2026-07-21] Backend: 977 tests superados, 2 omitidos; Ruff, mypy aislado de la feature, migracion reversible y query plan verificados.
- [2026-07-21] Frontend: 434 tests superados, 17 omitidos; typecheck, ESLint y build de produccion correctos.
- [2026-07-21] Browser QA: 31 aserciones, 14 capturas, cero errores de consola o HTTP inesperados; marcador observado con rumbo real, dentro del canvas y sin popup automático, dark/light, desktop/tablet/375 px/320 px, zoom 200% y reduced motion.
- [2026-07-21] El primer review multidisciplinar detectó riesgos reales de cuota, secreto en logs, UTC, fecha civil, multi-leg parcial y deriva documental; todos fueron corregidos antes de la revisión final.
- [2026-07-21] Auditoria npm identifica deuda previa en Next.js/PostCSS; no se amplia el alcance con un upgrade forzado sin migracion dedicada.
- [2026-07-21] Cierre: cinco revisiones tecnicas y dos visuales independientes concluyen PASS sin bloqueos; la evidencia final contiene 31 aserciones y 14 capturas.

## 20. Auditoria runtime de hipotesis

| Hipotesis de fallo | Evidencia ejecutada | Resultado |
|---|---|---|
| Dos refrescos secuenciales tras `no_match`, 429 o 503 vuelven a consumir cuota | Integracion parametrizada contra el endpoint real: dos GET por caso y contador del adapter | refutada: una sola llamada externa; el segundo GET reutiliza el cooldown persistente |
| Una pestana oculta mantiene activo el polling | Playwright cambia `visibilityState` y compara el contador de requests antes/despues | refutada: el contador no aumenta oculto y vuelve a aumentar al recuperar visibilidad |
| Una respuesta lenta de la Watch anterior pisa la seleccion nueva | Playwright retrasa la primera respuesta, cambia de Watch y comprueba el panel final | refutada: `AbortController` y la guarda de seleccion conservan la Watch activa |
