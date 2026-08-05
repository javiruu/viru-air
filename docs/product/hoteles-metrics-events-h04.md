# H04 — Métricas, eventos y definición de “done” de `/hoteles`

**Estado:** completo como contrato — pendiente de implementación gradual  
**Fecha:** 2026-08-04  
**Área:** producto / analítica / backend / frontend / QA  
**Fuente de verdad:** sí para la taxonomía y los criterios de éxito de hoteles; la implementación de cada evento debe respetar los helpers y contratos técnicos existentes.

## 1. Propósito

H04 define cómo sabremos si `/hoteles` ayuda a encontrar, entender y vigilar una estancia. No basta con medir que la pantalla carga o que una persona hace muchos clicks: debemos distinguir descubrimiento, comprensión, utilidad, retención, confianza, operación y negocio.

La dirección de H04 es incremental:

1. reutilizar `frontend/src/modules/shared/analytics.ts` para eventos de producto distribuidos a los proveedores configurados;
2. reutilizar `frontend/src/lib/uxTracking.ts` y `backend/app/api/v1/ux.py` para eventos persistidos autenticados cuando se necesite análisis interno;
3. ampliar la allowlist backend solo mediante cambios explícitos y testeados;
4. no crear un tercer sistema de tracking hotelero paralelo;
5. empezar con eventos de hitos y estados relevantes, no con cada interacción menor.

## 2. Diagnóstico de la instrumentación existente

| Capacidad | Estado actual | Decisión H04 |
|---|---|---|
| `trackEvent` | Emite eventos primitivos a gtag, Plausible y PostHog si están disponibles | Reutilizar para hitos de producto; no enviar PII |
| `trackUxEvent` | Envía eventos autenticados a `/ux/events` | Reutilizar para eventos hoteleros persistidos y duraciones |
| Allowlist `ALLOWED_EVENTS` | Incluye dashboard, quick search, watchlist y alertas generales | Añadir eventos hoteleros solo con revisión de contrato |
| `UxEvent` | Guarda usuario, nombre, duración y metadata JSON | Mantener payload pequeño y redacted; definir retención antes de escalar volumen |
| Admin product metrics | Agrega eventos existentes | Añadir métricas hoteleras agregadas, nunca exponer payloads crudos |
| Eventos de dominio hotelero | `HotelAlertEvent.event_type` representa cambios de precio/availability | No confundir eventos de dominio con eventos de comportamiento; relacionarlos mediante IDs opacos solo cuando sea necesario |
| Errores de cliente | `ClientErrorEvent` y logging existente | Usarlo para errores técnicos; no sustituir eventos de producto por logs |

### Gap principal

H01 ya define el embudo hotelero, pero hoy la instrumentación hotelera no tiene un contrato completo ni una allowlist específica. H04 resuelve la semántica; H13, H16, H18, H22-H28 y H41 implementarán los eventos en los puntos adecuados.

## 3. Principios de medición

1. **Hito antes que microclick:** medir acciones que cambian el estado del viaje.
2. **Una semántica por evento:** no reutilizar `hotel_search_completed` para una carga de fixture y una respuesta provider live sin indicar el estado.
3. **Propiedades estables:** usar nombres, tipos y unidades que no cambien por locale o copy.
4. **Resultado separado de intención:** `hotel_tracking_started` no equivale a `hotel_tracking_created`.
5. **Fallo explícito:** registrar `status=error/partial/empty` sin convertir todo en éxito.
6. **Confianza medible:** freshness, provenance y warnings deben alimentar métricas de calidad.
7. **No PII por defecto:** no enviar email, nombre, token, URL completa, payload crudo ni coordenadas precisas.
8. **Idempotencia para hitos críticos:** evitar dobles eventos por re-render, Strict Mode, retry o doble click.
9. **Versionado:** cambiar significado o tipo requiere `schema_version` nuevo o evento nuevo.
10. **Proporcionalidad:** si un evento no responde a una pregunta de producto, no se añade.

## 4. Convención de nombres y esquema común

### 4.1. Nombres

Todos los eventos de producto hotelero usan `snake_case`, objeto en singular y acción en pasado:

```text
hotel_page_viewed
hotel_search_started
hotel_search_completed
hotel_result_opened
hotel_tracking_created
```

No se incluyen IDs, destinos ni estados dinámicos en el nombre. Van en propiedades permitidas.

### 4.2. Propiedades comunes permitidas

Estas propiedades pueden acompañar eventos hoteleros cuando sean relevantes:

| Propiedad | Tipo | Significado |
|---|---|---|
| `schema_version` | integer | Versión del contrato del evento |
| `surface` | enum | `hoteles`, `hotel_detail`, `hotel_tracking`, `notifications` |
| `locale` | enum | `es` o `en`, sin texto libre |
| `device_class` | enum | `mobile`, `tablet`, `desktop` |
| `theme` | enum | `light`, `dark`, `system` si está disponible |
| `search_mode` | enum | `name`, `area`, `destination` |
| `search_status` | enum | `success`, `empty`, `partial`, `stale`, `error`, `fixture_only` |
| `result_count` | integer | Número de resultados visible/devuelto |
| `filter_count` | integer | Número de filtros activos |
| `sort` | enum | Orden lógico, nunca copy visible |
| `provider_count` | integer | Providers consultados |
| `freshness_bucket` | enum | `fresh`, `recent`, `stale`, `unknown` |
| `provenance_kind` | enum | `provider`, `cache`, `historical`, `demo`, `unknown` |
| `duration_ms` | integer | Duración acotada y no negativa |
| `error_code` | enum | Código estable de error, sin stack ni mensaje libre |
| `source` | enum | `card`, `detail`, `tracking`, `inbox`, `deep_link` |

### 4.3. Identificadores

- Para análisis externo, no se envían IDs de hotel, usuario, tracked offer, alerta o provider que permitan reconstruir una identidad innecesaria.
- Para métricas internas autenticadas, se puede persistir un ID interno opaco solo si responde a una necesidad de dedupe o trazabilidad y está cubierto por retención/ownership.
- Nunca se envía `user.email`, token, query cruda, deeplink completo, payload provider o `children_ages` a proveedores externos de analítica.
- Un destino puede representarse como categoría/mercado normalizado o hash controlado si producto lo necesita; no como dirección exacta o coordenadas precisas.

## 5. Taxonomía de eventos hoteleros

### 5.1. Adquisición y entrada

| Evento | Cuándo | Propiedades mínimas | Pregunta |
|---|---|---|---|
| `hotel_page_viewed` | Se muestra `/hoteles` una vez por entrada de ruta/sesión relevante | `schema_version`, `surface`, `locale`, `device_class` | ¿Llegan personas a hoteles? |
| `hotel_search_started` | La persona enfoca o modifica el buscador con intención | `search_mode`, `source` | ¿El buscador se entiende? |

No se dispara `hotel_search_started` por cada pulsación. Debe deduplicarse por sesión de búsqueda o por transición de `idle` a formulario activo.

### 5.2. Búsqueda y resultados

| Evento | Cuándo | Propiedades mínimas | Pregunta |
|---|---|---|---|
| `hotel_search_submitted` | Se pulsa Buscar con intención de ejecución | `search_mode`, `source` | ¿Cuántas búsquedas se intentan? |
| `hotel_search_completed` | La respuesta termina y el sistema conoce su estado | `search_status`, `result_count`, `duration_ms`, `freshness_bucket`, `provenance_kind`, `provider_count` | ¿Cuántas búsquedas son útiles y confiables? |
| `hotel_search_recovered` | La persona modifica una búsqueda vacía/error/partial y obtiene respuesta utilizable | `from_status`, `to_status`, `recovery_action` | ¿El producto rescata problemas? |
| `hotel_filter_opened` | Se abre el control de filtros | `filter_count`, `device_class` | ¿Se encuentran los controles? |
| `hotel_filter_applied` | Cambia el conjunto de filtros aplicado | `filter_count`, `search_status`, `device_class` | ¿Ayudan los filtros? |
| `hotel_sort_changed` | Cambia el orden | `sort`, `result_count` | ¿Qué orden resulta útil? |
| `hotel_results_retried` | Se reintenta una búsqueda fallida o stale | `previous_status`, `error_code` | ¿Los errores se recuperan? |

`hotel_search_completed` no se emite si la respuesta fue abortada antes de conocer el estado; en ese caso se puede registrar un error técnico fuera del embudo si es necesario.

### 5.3. Comprensión y decisión

| Evento | Cuándo | Propiedades mínimas | Pregunta |
|---|---|---|---|
| `hotel_result_opened` | Se abre detalle desde un resultado | `source`, `result_count`, `search_status`, `freshness_bucket` | ¿Qué resultados merecen atención? |
| `hotel_detail_viewed` | El detalle termina de cargarse o alcanza estado visible | `detail_status`, `rate_count`, `freshness_bucket`, `provenance_kind` | ¿Se puede entender la opción? |
| `hotel_price_context_opened` | Se expande la explicación de total/noches/fees/freshness | `context_kind`, `provenance_kind` | ¿Hace falta más explicación? |
| `hotel_partner_clicked` | Se intenta abrir deeplink | `source`, `provenance_kind`, `freshness_bucket`, `disclosure_shown` | ¿La decisión produce una acción externa? |
| `hotel_feedback_submitted` | Se reporta precio/condición incorrecta o problema | `feedback_kind`, `surface` | ¿Dónde falla la confianza? |

No se mide un partner click como conversión de reserva: Viru solo sabe que abrió el enlace, salvo que exista una integración contractual posterior.

### 5.4. Guardado y retención

| Evento | Cuándo | Propiedades mínimas | Pregunta |
|---|---|---|---|
| `hotel_favorite_created` | Se guarda una propiedad | `source`, `search_status` | ¿Qué opciones se quieren recuperar? |
| `hotel_favorite_removed` | Se elimina un favorito | `source` | ¿Hay valor o ruido en favoritos? |
| `hotel_tracking_started` | Se abre el flujo de seguir precio | `source`, `tracking_eligibility` | ¿La propuesta se entiende? |
| `hotel_tracking_created` | El backend confirma el tracking | `source`, `tracking_status`, `provenance_kind`, `freshness_bucket` | ¿Se crea retención real? |
| `hotel_tracking_creation_failed` | El backend rechaza o falla la creación | `error_code`, `tracking_eligibility` | ¿Qué bloquea el seguimiento? |
| `hotel_tracking_viewed` | Se abre la superficie de seguimiento/histórico | `active_tracking_count`, `source` | ¿Se vuelve al producto? |
| `hotel_tracking_paused` | Se pausa un tracking | `source` | ¿Se puede controlar el ruido? |
| `hotel_tracking_resumed` | Se reactiva | `source` | ¿La pausa es reversible? |
| `hotel_tracking_deleted` | Se elimina | `source` | ¿Se entiende la gestión? |

La creación de favorito y tracking no se fusiona en un único evento.

### 5.5. Alertas y retorno

| Evento | Cuándo | Propiedades mínimas | Pregunta |
|---|---|---|---|
| `hotel_alert_created` | Se confirma una regla de alerta | `rule_type`, `source`, `tracking_status` | ¿Se activa el retorno? |
| `hotel_alert_creation_failed` | Error al crear regla | `rule_type`, `error_code` | ¿Qué fricción existe? |
| `hotel_alert_opened` | Se abre una alerta desde inbox/deep link | `source`, `alert_kind` | ¿Las alertas son accionables? |
| `hotel_alert_action_taken` | Desde la alerta se abre partner, tracking, edición o pausa | `action`, `source` | ¿Qué hace la persona al volver? |
| `hotel_alert_dismissed` | Se descarta sin acción principal | `source`, `alert_kind` | ¿Hay ruido? |
| `hotel_inbox_viewed` | Se abre inbox con señales hoteleras | `unread_count_bucket` | ¿Se consulta el centro de retorno? |

Los eventos de comportamiento se relacionan conceptualmente con `HotelAlertEvent.event_type`, pero no se sustituyen entre sí: uno describe un cambio de dominio y el otro una acción de la persona.

## 6. Métricas derivadas

### 6.1. Embudo principal

Ventana base propuesta: por sesión de búsqueda; H41 podrá definir ventanas operativas definitivas.

```text
hotel_page_viewed
  → hotel_search_submitted
  → hotel_search_completed(status=success|partial)
  → hotel_result_opened
  → hotel_detail_viewed
  → hotel_favorite_created OR hotel_tracking_created
  → hotel_partner_clicked
```

Métricas:

- **Search completion rate:** `hotel_search_completed / hotel_search_submitted`.
- **Useful result rate:** búsquedas `success|partial` con `result_count > 0` / búsquedas completadas.
- **Result open rate:** resultados abiertos / búsquedas con resultados.
- **Detail comprehension proxy:** apertura de contexto de precio o acción de guardado/seguimiento / detalles vistos.
- **Save rate:** favoritos creados / resultados abiertos.
- **Tracking creation rate:** trackings creados / flujos de tracking iniciados.
- **Partner click rate:** clicks partner / detalles vistos con deeplink válido.

No se presenta ninguna de estas métricas sin su denominador, ventana temporal y segmento.

### 6.2. Retención

- **D1/D7/D30 hotel return:** usuarios o sesiones que vuelven a `/hoteles` después de crear favorito/tracking.
- **Tracking survival:** trackings activos a 7 y 30 días, excluyendo expiración legítima.
- **Alert return rate:** aperturas de `/hoteles` o tracking tras `hotel_alert_opened`.
- **Actionable alert rate:** alertas abiertas que producen partner click, edición, pausa o revisión de histórico.
- **Alert noise rate:** alertas descartadas o repetidas sin acción / alertas entregadas.

Las cohortes deben usar identificadores internos controlados; no se exportan emails.

### 6.3. Confianza y calidad

- `% resultados con freshness visible`.
- `% resultados con provenance conocida`.
- `% búsquedas `fixture_only` en entorno no demo` — objetivo de producción: cero.
- `partial rate` y `stale rate` por provider/mercado.
- `provider error rate`, timeout y 429 rate.
- `% precios con condiciones comparables`.
- `feedback incorrect price rate`.
- `% trackings con snapshot inicial válido`.
- `% alertas vinculadas a snapshot trazable`.

Estas métricas no se optimizan ocultando estados degradados.

### 6.4. Operación y coste

- Latencia p50/p95 de búsqueda.
- Duración p50/p95 de refresh dirigido.
- Sweeps iniciados/completados/partial/fallidos.
- Ofertas procesadas por sweep.
- Coste estimado por búsqueda y tracking activo.
- Eventos descartados por allowlist, tamaño o rate limit.
- Tasa de duplicados por evento crítico.
- Delivery success/failure cuando H28 lo habilite.

## 7. Guardrails

Un experimento o cambio no se considera positivo si mejora clicks pero empeora materialmente cualquiera de estos límites:

| Guardrail | Señal de bloqueo |
|---|---|
| Veracidad | sube `fixture_only` o se etiqueta live sin evidencia |
| Frescura | aumenta stale/unknown sin copy o warning |
| Comparabilidad | aumentan feedbacks de precio/condición incompatible |
| Alertas | sube ruido, duplicación o alertas sin snapshot trazable |
| Privacidad | aparece PII, query cruda, token o payload provider |
| Accesibilidad | falla teclado, foco, contraste o reduced motion |
| Rendimiento | p95 o error rate supera el presupuesto acordado |
| Coste | coste por búsqueda/sweep supera el límite sin aprobación |
| Ownership | un usuario puede consultar o accionar datos ajenos |

## 8. Privacidad y seguridad

### Estado técnico al cerrar H04

El contrato está definido, pero la infraestructura actual todavía no lo implementa completo:

- `trackEvent` normaliza propiedades primitivas, pero no aplica una allowlist hotelera ni añade automáticamente `schema_version`.
- `trackUxEvent` compacta metadata, pero aún no genera `event_id`, `search_session_id` ni una clave de dedupe.
- `/ux/events` valida el nombre contra `ALLOWED_EVENTS`, pero no valida todavía una allowlist de propiedades hoteleras ni límites específicos de metadata más allá del esquema general.
- Las métricas de funnel no deben publicarse como exactas hasta que H13/H15 introduzcan una identidad de búsqueda/sesión y tests contra retry, Strict Mode y re-render.

Estas carencias son requisitos de implementación para H13/H15/H41, no una razón para cambiar la semántica de este documento.

### Permitido

- Categorías de búsqueda, no texto libre completo.
- Bucket de resultados, freshness y duración.
- Locale, dispositivo y tema si la política vigente lo permite.
- IDs internos opacos en almacenamiento first-party para dedupe/trazabilidad estricta.
- Código estable de error, sin stack ni mensaje del provider.

### No permitido por defecto

- Email, nombre, token, IP o secretos.
- Hotel ID o tracked offer ID en proveedores externos si no es imprescindible.
- Coordenadas exactas, dirección, landmark preciso o edades de niños.
- Fechas y ocupación completas en herramientas externas si no existe base legal/necesidad.
- URL completa de partner con parámetros de atribución o sesión.
- `raw_payload`, deeplink crudo, headers o credenciales.

### Redacción obligatoria

- El helper debe reducir valores a primitivas y aplicar una allowlist por evento antes de enviar propiedades a terceros.
- Backend valida nombres, `schema_version`, propiedades permitidas y límites de tamaño antes de persistir eventos hoteleros.
- Logs nunca imprimen metadata JSON cruda ni tokens.
- Hasta que esa validación exista, solo se pueden instrumentar eventos hoteleros en almacenamiento first-party controlado o con propiedades explícitamente auditadas.
- Los cambios deben añadir tests de redacción para email, token, URL completa, coordenadas, edades y payload provider.

- Los errores de analítica no bloquean búsqueda, guardado, tracking o alertas.
- El contrato de retención y borrado se cierra con H41/H42 antes de ampliar volumen.

## 9. Dedupe, identidad y versionado

### Dedupe

- Añadir una clave de evento solo para hitos donde un doble disparo altere la métrica: submit, tracking creado, alerta creada, partner click.
- La clave no debe incluir PII; puede ser una combinación de acción, sesión efímera y operación interna.
- Un re-render o Strict Mode no debe duplicar `hotel_page_viewed` ni `hotel_detail_viewed`.
- Un retry de API no debe producir dos `hotel_tracking_created` si el backend solo creó uno.
- H13/H15/H41 deben aportar un `event_id` o equivalente idempotente y una `search_session_id` efímera/opaque para unir submit → respuesta → resultado sin usar email, query cruda o identidad externa.
- Hasta que exista esa identidad, las métricas de funnel deben etiquetarse como aproximadas y no usarse para decisiones de rollout finas.


### Identidad

- Separar sesión/usuario en las herramientas autorizadas.
- No usar email como identificador analítico.
- Las métricas first-party pueden agrupar por usuario interno sujeto a controles de acceso y retención.
- Eventos anónimos no deben intentar reconstruir identidad mediante campos de búsqueda sensibles.

### Versionado

Todos los eventos nuevos nacen con `schema_version=1`. Si cambia el significado o tipo de una propiedad:

1. actualizar contrato y tests;
2. considerar coexistencia temporal;
3. migrar dashboards;
4. retirar el evento/propiedad antigua con fecha y motivo.

## 10. Definición de “done” para H04 y fases posteriores

### H04 está completa cuando

- existe una taxonomía hotelera sin nombres ambiguos;
- cada evento tiene trigger, propiedades, pregunta y estado de error;
- se distingue intención, éxito, fallo y evento de dominio;
- métricas tienen fórmula, denominador, ventana y segmento;
- guardrails de confianza, privacidad, accesibilidad, coste y rendimiento están definidos;
- se documentan dedupe, identidad, retención y versionado;
- el roadmap y los índices apuntan a este contrato;
- la siguiente IA puede implementar eventos sin crear otro helper paralelo.

### Una fase técnica hotelera no está completa si

- solo registra clicks, pero no el resultado real de la operación;
- no tiene test de evento o validación de payload;
- no indica qué ocurre en empty/partial/stale/error;
- no puede calcular su métrica con denominador definido;
- envía PII o payloads crudos;
- duplica eventos por render/retry;
- carece de evidencia de QA y guardrails;
- confunde una alerta de dominio con una alerta entregada o abierta.

### Plantilla mínima de cierre por fase

```markdown
## Métricas y evidencia
- Evento(s):
- Trigger exacto:
- Propiedades y schema_version:
- Estados cubiertos:
- Dedupe/idempotencia:
- Métrica derivada y denominador:
- Guardrails revisados:
- Tests/evidencia:
- Riesgo residual:
```

## 11. Plan de implementación posterior

| Fase | Trabajo de medición |
|---|---|
| H05 | Exponer freshness/provenance/confidence como propiedades y estados coherentes |
| H09 | Medir sweeps, locks, retries, coste y fallos operativos |
| H13 | Instrumentar entrada, submit, validación, recuperación y URL state |
| H15 | Emitir estado de búsqueda, paginación, partial, stale y warnings |
| H16/H18 | Medir card, detalle, contexto de precio y partner |
| H22/H23 | Separar favorito, tracking iniciado y tracking creado |
| H26-H28 | Medir creación, apertura, acción, dedupe y delivery de alertas |
| H33/H36/H37 | Añadir guardrails de a11y, rendimiento y coste |
| H38 | Revisar PII, ownership y superficies de abuso |
| H41 | Implementar dashboards, retención, alertas operativas y SLO |
| H45 | Incluir smoke de eventos y decisión canary/rollback |

## 12. Gate de H04

**Aprobado como contrato de medición.** H04 no afirma que todos los eventos ya estén instrumentados. Declara la semántica que deben implementar las fases posteriores y evita que `/hoteles` se optimice solo para clicks o volumen.

H04 puede pasar a H05/H06 y a la implementación de H13 en paralelo, siempre que cada fase marque sus eventos como `planned`, `implemented` o `verified` y aporte evidencia.
