# H21 — Matriz de estados de hoteles: empty, loading, error, partial y stale

**Estado:** contrato de estados y recuperación; implementación frontend/backend, envelope V2, i18n y QA E2E pendientes  
**Fecha:** 2026-08-05  
**Área:** frontend / backend / producto / QA / accesibilidad / operación  
**Fuente de verdad:** sí para la semántica de estados visibles y acciones de recuperación de `/hoteles`  
**Fase del roadmap:** H21  
**Depende de:** H05, H12, H13, H14, H15, H16, H17, H18, H19, H20  
**Relacionado con:** H21 estados de búsqueda, H22 favoritos, H23 tracking, H25 freshness, H27 inbox, H31-H34 UX/a11y/i18n, H36 rendimiento, H38 seguridad, H40 QA

> H21 evita que la interfaz convierta cualquier problema en una lista vacía, un spinner infinito o un error técnico. Cada estado debe explicar qué sabe Viru, qué no sabe y cuál es la siguiente acción segura.

## 1. Decisión de alcance

H21 define el contrato transversal para estas superficies:

- formulario y resolución de destino;
- búsqueda por nombre/ciudad y búsqueda por área;
- resultados y paginación futura;
- detalle de hotel;
- rates e histórico;
- paridad de providers;
- hoteles cercanos y comp sets;
- favoritos/watchlist;
- ofertas trackeadas e histórico;
- reglas y eventos de alertas;
- sesión/autenticación y errores de red.

No implementa todavía nuevos reducers, componentes, schemas V2 ni cambios de CSS. Las implementaciones deben adaptar los estados existentes sin romper V1.

Regla principal:

> Un estado vacío significa que la consulta terminó correctamente y no produjo elementos. Un error significa que no podemos afirmar el resultado. Nunca son intercambiables.

## 2. Estado actual comprobable

### 2.1. Búsqueda

`useHotelSearch` ya expone:

- `loading` booleano;
- `results` y `areaResults` como listas;
- `errorMessage`;
- `areaResolving`;
- `areaResolved`;
- `featureDisabled` derivado del mensaje.

La búsqueda conserva resultados anteriores en algunos caminos, pero no tiene todavía una máquina de estados explícita. El componente muestra un empty genérico cuando `results.length === 0` y no está cargando; no diferencia una consulta todavía no ejecutada de una consulta válida sin coincidencias.

La resolución de área captura el error y deja la lista de sugerencias vacía sin exponer un estado diferenciado de geocoder no disponible. Las fechas, ocupación y demás validaciones no tienen todavía una taxonomía común de errores inline.

### 2.2. Detalle, rates y paridad

`useHotelDetail` dispara detalle, rates y paridad con `Promise.allSettled`:

- un fallo de detalle se convierte en `hotelDetail=null`;
- un fallo de rates se convierte en `rates=[]`;
- un fallo de paridad se conserva como `parityError`;
- loading de rates y loading de paridad se gestionan por separado;
- no existe un error explícito de detalle ni de rates;
- un `[]` puede significar “no hay datos” o “la petición falló”.

El panel de paridad sí distingue loading, error, ausencia de señal y señal limitada, pero depende de `rates` y de un assessment V1 que no conoce todos los estados H05/H20.

### 2.3. Watchlist, tracking, alertas y cercanos

- Watchlist tiene `loading`, `error` y `detailUnavailable` por hotel.
- `useTrackedOffers.refreshTrackedOffers` ignora silenciosamente errores porque el panel se considera secundario.
- `HotelTrackedOfferSnapshots` convierte un fallo de snapshots en lista vacía.
- Alertas tienen errores separados para reglas y eventos.
- Comp sets y cercanos tienen mensajes de error, pero la UI puede mostrar cero sugerencias tras fallos y algunos errores de acción solo aparecen como toast.
- La ausencia de coordenadas del ancla se distingue en cercanos, pero no existe un envelope de estado común.

Estas decisiones son funcionales para V1, pero no suficientes para explicar de forma consistente `empty`, `partial`, `stale`, `unavailable`, provider degradado y recuperación.

## 3. Taxonomía canónica

Los estados son semánticos; cada superficie puede tener detalles propios, pero no debe inventar nuevos significados sin documentarlos.

| Estado | Significado | ¿Es error? | ¿Puede conservar datos anteriores? | Acción típica |
|---|---|---:|---:|---|
| `idle` | La consulta todavía no se ha ejecutado o no hay intención válida | no | no aplica | completar formulario |
| `validating` | Se validan campos locales antes de llamar al backend | no | sí | corregir campo si falla |
| `resolving` | Se resuelve destino, coordenadas o identidad | no | sí | esperar/cancelar |
| `loading` | Petición en curso sin resultado final | no | sí | esperar/cancelar |
| `success` | Respuesta válida con datos utilizables | no | reemplaza | continuar |
| `empty` | Respuesta válida, sin elementos para esa consulta | no | sí, si es una nueva consulta no confirmada | ampliar/cambiar/reintentar |
| `partial` | Hay datos válidos, pero falta parte del universo o de las condiciones | no | sí | revisar limitación/reintentar |
| `stale` | Hay datos históricos o viejos fuera del umbral preferido | no | sí | revalidar |
| `stale_while_error` | Hay datos anteriores y el intento nuevo falló | sí, del intento | sí, obligatoriamente | conservar + reintentar más tarde |
| `unavailable` | No hay dato utilizable por falta de provider/capacidad/configuración | no necesariamente | sí | alternativa local/configurar |
| `auth_required` | La sesión no permite completar la operación | sí | sí | reautenticar sin perder contexto |
| `forbidden` | La operación existe, pero el usuario no tiene permiso | sí | sí | volver a superficie permitida |
| `not_found` | La entidad solicitada no existe o dejó de estar disponible | sí | sí | volver a búsqueda |
| `cancelled` | La petición fue cancelada por una nueva intención o navegación | no | sí | no mostrar error |
| `error` | Fallo inesperado sin resultado confiable | sí | sí, si existía contexto | reintentar/soporte |

### 3.1. Reglas globales

- `null`, `[]` o ausencia de un campo no determinan por sí solos el estado.
- `empty` requiere respuesta válida y una razón de ausencia conocida.
- `partial` requiere metadata o warning que describa qué falta.
- `stale` requiere timestamp/política H05; sin timestamp el estado es `unknown`/`unavailable`, no `stale` positivo.
- `stale_while_error` es preferible a limpiar una respuesta anterior útil cuando el nuevo intento falla, pero solo si el dato anterior pertenece al mismo contexto/fingerprint compatible.
- Una respuesta anterior nunca se renderiza bajo una nueva query, estancia, selección o intención solo porque ambas listas tengan el mismo shape; si el contexto no coincide, el estado es `loading`, `empty` o `error` de la nueva intención.
- `provider_error` no se transforma en `empty`, `sold_out` ni `not_found`.
- `auth_required` no debe borrar formulario, URL state, filtros, selección ni cursor.
- `cancelled` no genera toast de error ni métrica de fallo de provider.
- Los estados técnicos no se exponen con nombres internos si existe copy de producto equivalente.

## 4. Envelope V2 objetivo

H15 debe evolucionar hacia un estado explícito en cada superficie. Como mínimo:

```json
{
  "state": "partial",
  "data": [],
  "previous_data_available": true,
  "context": {
    "request_fingerprint": "opaque",
    "query_fingerprint": "opaque",
    "selected_hotel_id": "opaque-id"
  },
  "freshness": {
    "status": "stale",
    "observed_at": "2026-08-05T10:00:00Z",
    "policy_version": "hotel-freshness-v1"
  },
  "capabilities": {
    "retry": true,
    "revalidate": true,
    "open_detail": true,
    "track_price": false
  },
  "warnings": [
    {
      "code": "provider_partial",
      "severity": "info",
      "source": "provider"
    }
  ],
  "error": null,
  "request_id": "redacted-or-short-lived"
}
```

Reglas:

- `data` nunca se interpreta sin `state` y `warnings`;
- `previous_data_available` no significa que los datos anteriores sean actuales;
- `request_fingerprint` y `request_id` no deben contener PII ni secretos;
- `error.code` debe ser allowlisted y traducible; el mensaje técnico queda en logs seguros;
- el cliente V1 puede seguir recibiendo listas desnudas y usar fallback conservador: respuesta válida con lista vacía = `empty`, error HTTP = `error`, sin inventar `partial`;
- una migración V2 debe permitir comparar respuestas V1/V2 y retirar el fallback solo después de contract tests.

## 5. Matriz por superficie

### 5.1. Formulario y resolución de destino

| Estado | Señal visible | Datos que se conservan | Acción |
|---|---|---|---|
| `idle` | formulario listo, sin error | valores escritos | seleccionar destino y fechas |
| `validating` | botón/input ocupado, error asociado al campo | todos los campos | corregir fecha, ocupación o destino |
| `resolving` | sugerencias cargando | query escrita | esperar, seguir escribiendo o cancelar |
| `empty` | “No encontramos esa zona” | query escrita | probar alias/ciudad/país |
| `unavailable` | geocoder externo no disponible | query escrita y destino previamente resuelto | elegir sugerencia local o introducir opción compatible |
| `error` | mensaje humano junto al campo o formulario | query y búsqueda anterior | reintentar sin resetear formulario |
| `cancelled` | ninguna alarma | valores escritos | continuar edición |

No se borra `areaQuery` cuando una resolución falla. Una sugerencia vacía no demuestra que la zona no exista.

### 5.2. Búsqueda por nombre/ciudad

| Estado | Significado | UI y acción |
|---|---|---|
| `idle` | aún no se buscó | estado inicial orientado a comenzar |
| `loading` | catálogo consultándose | skeleton de resultados; no saltos de layout |
| `success` | hay hoteles | lista y selección |
| `empty` | búsqueda válida sin coincidencias | cambiar nombre/ciudad, quitar filtro, cargar demo si procede |
| `error` | catálogo/backend falló | conservar query y resultados previos; reintentar |
| `auth_required` | sesión expirada | reautenticar y reanudar búsqueda |
| `cancelled` | request obsoleto | ignorar respuesta sin toast |

“Sin resultados todavía” solo es correcto para `idle`; para `empty` debe explicar que la consulta terminó sin coincidencias.

### 5.3. Búsqueda por área y provider

| Estado | Condición | UI y acción |
|---|---|---|
| `loading` | resolución completa y area search en curso | skeleton de cards y estado de búsqueda |
| `success` | lista con datos utilizables | cards/resultados |
| `empty` | catálogo respondió sin hoteles en radio/filtros | ampliar radio, fechas o filtros |
| `partial` | catálogo local o provider devolvió solo parte | mostrar resultados y qué provider/capacidad falta |
| `stale` | se sirven snapshots fuera del TTL preferido | mostrar fecha y revalidar |
| `stale_while_error` | refresh/provider falló con resultados anteriores | conservar cards, marcar limitación y reintentar después |
| `unavailable` | provider opcional apagado/no configurado | usar catálogo/cache/demo rotulado; no prometer live |
| `error` | error total sin datos utilizables | retry seguro y conservar parámetros |

La lista de resultados y la señal del provider deben poder tener estados distintos: `success` de catálogo + `partial` de provider es válido. No se reemplaza una lista útil por un error de provider opcional.

### 5.4. Detalle de hotel

| Estado | UI | Acción |
|---|---|---|
| `idle` | ningún hotel seleccionado | elegir hotel |
| `loading` | identidad/detalle en carga | skeleton del bloque, conservar búsqueda |
| `success` | detalle válido | mostrar identidad y acciones |
| `partial` | identidad válida, rates/paridad no disponibles | mostrar detalle, explicar qué panel falta |
| `stale` | rates/histórico antiguos | mostrar fecha y revalidar |
| `not_found` | hotel eliminado/desconocido | limpiar selección URL de forma accesible y volver a resultados |
| `auth_required` | sesión inválida | reautenticar conservando URL segura |
| `error` | detalle no cargable | retry y retorno a búsqueda |

Un fallo de rates no debe borrar el nombre/dirección ya disponibles. Un fallo de paridad no debe ocultar precio/histórico válido.

### 5.5. Rates e histórico

| Estado | Significado | Acción |
|---|---|---|
| `idle` | no hay hotel/contexto | seleccionar/completar estancia |
| `loading` | petición de rates | esperar/cancelar |
| `success` | rates válidos | comparar con H19/H20 |
| `empty` | respuesta válida sin rates para contexto | cambiar fechas/ocupación/provider |
| `partial` | rates con condiciones/fees incompletas | revisar condiciones; no declarar total comparable |
| `stale` | rates fuera de freshness | revalidar |
| `stale_while_error` | refresh fallido con histórico anterior | mostrar histórico fechado, no precio actual |
| `unavailable` | no hay provider/capability para la estancia | guardar hotel o volver a buscar; no crear tracking completo |
| `error` | fallo de endpoint | retry y conservar datos anteriores |

`[]` de rates solo significa `empty` si el backend confirmó respuesta válida. Si el hook no puede distinguirlo en V1, debe añadir una bandera de error/estado antes de que UI lo presente como “sin datos”.

### 5.6. Paridad de providers

| Estado H20 | Presentación H21 | Acción |
|---|---|---|
| `no_data` | no hay comparación | buscar/reintentar |
| `one_provider` | solo una fuente | revisar esa observación, no “estable” |
| `partial` | faltan condiciones/provider | ver diferencias/revalidar |
| `stale` | comparación antigua | revalidar |
| `provider_degraded` | falta respuesta de una fuente | esperar/reintentar |
| `invalid` | no comparable | corregir contexto |
| `comparable/stable/tensioned/breach` | señal elegible con policy version | revisar tarifa/condiciones |
| `error` | servicio de paridad falló | conservar rates y reintentar |

El bridge V1 puede seguir mostrando `info/limited`, pero debe evitar confundirlo con `stable` o con una comparación en tiempo real.

### 5.7. Hoteles cercanos y comp sets

| Estado | Condición | Acción |
|---|---|---|
| `idle` | no hay comparativa seleccionada | crear/seleccionar comp set |
| `loading` | detalle o cercanos cargando | esperar |
| `success` | candidatos disponibles | añadir, abrir detalle o guardar |
| `empty` | radio/catálogo sin candidatos | ampliar radio o volver a resultados |
| `partial` | catálogo/coordenadas incompletos | mostrar limitación, no exhaustividad |
| `unavailable` | faltan coordenadas/capability | usar búsqueda manual |
| `forbidden/not_found` | comp set no pertenece o desapareció | eliminar selección local y volver |
| `error` | endpoint falló | retry sin perder hotel ancla |

Añadir un cercano no inicia tracking ni alerta. El hotel ancla y el contexto H18 se conservan al abrir un miembro.

### 5.8. Watchlist y tracking

| Superficie | Estado | Acción |
|---|---|---|
| watchlist | `loading` | esperar; no mostrar empty prematuro |
| watchlist | `success_empty` | guardar hotel desde resultados |
| watchlist | `success_partial` | mostrar guardados aunque falte detalle de alguno |
| watchlist | `error` | retry; no borrar guardados locales/servidor |
| watchlist | `detail_unavailable` | conservar favorito por ID y permitir quitarlo |
| tracked offers | `loading` | esperar |
| tracked offers | `success_empty` | iniciar desde oferta válida |
| tracked offers | `success_partial` | mostrar ofertas válidas y cuáles requieren revisión |
| tracked offers | `stale` | mostrar última comprobación, no prometer diario |
| tracked offers | `error` | mostrar error recuperable; no ignorarlo silenciosamente |
| snapshots | `empty` | tracking existe, aún sin historial |
| snapshots | `error` | diferenciar fallo de endpoint de historial vacío |

El tracking creado sin fechas/precio no se presenta como seguimiento operativo completo; debe tener estado `pending_context`/`unavailable` definido por H23.

### 5.9. Alertas e inbox

| Estado | Significado | Acción |
|---|---|---|
| `loading` | reglas/eventos cargando | esperar |
| `success_empty` | no hay reglas/eventos | crear regla o volver a detalle |
| `success` | datos disponibles | activar, pausar, abrir señal |
| `partial` | reglas cargan, eventos fallan o viceversa | conservar la mitad válida y explicar |
| `stale` | lectura no reciente cuando el producto lo indique | actualizar |
| `auth_required` | sesión expirada | reautenticar y volver a la vista |
| `forbidden/not_found` | entidad no pertenece/desapareció | limpiar selección segura |
| `error` | endpoint no disponible | retry; no afirmar que no existen alertas |

Un toast confirma una acción inmediata, pero no sustituye al estado persistente de la superficie. Un evento generado no equivale a delivery externo exitoso.

## 6. Preservación de contexto y concurrencia

### 6.1. Qué se conserva

Ante error, reintento o reautenticación se conservan, cuando sean válidos:

- destino y tipo/confidence;
- fechas, noches y ocupación bridge;
- radio, filtros, orden y moneda;
- query y formulario sin enviar;
- cursor/snapshot token del mismo contexto H15;
- `hotel_id` seleccionado si sigue permitido;
- hotel ancla/comp set privado solo en sesión autenticada;
- datos anteriores con etiqueta de freshness/stale y fingerprint/contexto compatible.

Los envelopes que incluyan selección, comp set, `has_tracking`, reglas, notas o cualquier otro dato privado no pueden entrar en cachés compartidas, respuestas SSR reutilizables entre usuarios ni almacenamiento público. Deben estar ligados a la sesión/ownership correcta y llevar una política explícita de `private`/no-store cuando corresponda.

Nunca se conservan en URL o telemetry:

- tokens, emails, `user_id` o secrets;
- thresholds, labels y notas privadas;
- payload raw de provider;
- redirect arbitrario;
- IDs privados en una URL compartible sin contrato H27/H35.

### 6.2. Requests obsoletos

- cada request debe tener identidad/fingerprint de intención;
- una respuesta cancelada o vieja no puede sobrescribir la selección nueva;
- cambiar de hotel cancela o invalida respuestas de detalle anteriores;
- cambiar de búsqueda invalida cursor, rates y paridad incompatibles;
- cambiar query, fechas, ocupación, moneda o hotel invalida cualquier dato anterior que no comparta fingerprint compatible;
- un refresh fallido no reemplaza automáticamente datos previos válidos;
- los errores de requests cancelados no aparecen como toasts de fallo.

### 6.3. Stale-while-error

Cuando exista dato previo:

1. conservarlo;
2. marcar `stale_while_error`;
3. mostrar qué intento falló y cuándo fue la última observación;
4. ofrecer retry/backoff seguro;
5. no actualizar `current_price`, spread o disponibilidad con el error;
6. no convertir el dato anterior en live.

## 7. Acciones, copy y severidad

Cada estado debe tener una acción siguiente o explicar por qué no existe:

| Severidad | Uso | Ejemplo de acción |
|---|---|---|
| `info` | limitación no bloqueante | ver detalles, ampliar radio |
| `warning` | dato parcial/stale | revalidar, revisar condiciones |
| `error` | operación fallida recuperable | reintentar |
| `critical` | seguridad/auth/corrupción | reautenticar, soporte |

Copy mínimo:

- no decir “No hay hoteles” cuando el provider falló;
- no decir “agotado” cuando hay `provider_error`;
- no decir “sin historial” si el endpoint de snapshots falló;
- no decir “seguimiento activo” si falta contexto o no existe scheduler garantizado;
- no decir “comparación estable” con un solo provider;
- no decir “no existe” cuando solo se agotó un radio/catálogo;
- incluir el momento de última observación cuando se sirve stale;
- request ID solo como referencia de soporte, nunca como explicación principal.

Todos los códigos y copys deben tener ES/EN, pluralización, fechas/monedas locale-aware y lenguaje no técnico para producto.

## 8. Accesibilidad y comportamiento visual

- cada estado tiene texto, no solo color, icono o spinner;
- `role="status"` para cambios informativos y `role="alert"` para errores accionables sin abusar de anuncios;
- los errores inline se asocian a su campo mediante `aria-describedby`;
- loading anuncia una vez y no produce loops de live region;
- botones de retry tienen nombre específico: “Reintentar tarifas”, no solo “Reintentar”;
- stale conserva lectura de datos y añade una nota asociada;
- empty ofrece acción enfocada y no deja el teclado en un control eliminado;
- skeletons respetan reduced motion y no sustituyen el contenido en un error permanente;
- focus vuelve al origen después de retry/cierre de detalle cuando corresponda;
- móvil no oculta el CTA de recuperación bajo un panel o teclado virtual;
- estados largos, nombres de provider y mensajes de error no rompen layout.

## 9. Telemetría y observabilidad

Registrar eventos versionados sin PII innecesaria:

```text
hotel_state_viewed
hotel_state_action_clicked
hotel_search_started
hotel_search_completed
hotel_search_empty
hotel_search_partial
hotel_search_stale_served
hotel_search_error
hotel_destination_resolve_empty
hotel_destination_resolve_error
hotel_detail_partial
hotel_rates_empty
hotel_rates_error
hotel_parity_limited
hotel_provider_degraded
hotel_nearby_empty
hotel_nearby_error
hotel_watchlist_detail_unavailable
hotel_tracking_load_error
hotel_retry_clicked
hotel_auth_recovery_started
hotel_request_cancelled
```

Cada evento puede incluir:

- `surface` y `state`;
- `state_version`;
- `reason_code` allowlisted;
- `request_fingerprint` opaco;
- provider/capability no sensible;
- `has_previous_data`;
- duración y resultado de retry.

No incluir query completa, email, URL externa, thresholds ni payloads raw.

Métricas mínimas:

- tasa de empty real frente a error;
- tasa de partial/stale por provider;
- retry success rate;
- tiempo hasta primer resultado útil;
- auth recovery success;
- requests canceladas y respuestas obsoletas descartadas;
- errores silenciosos eliminados en tracking/snapshots.

## 10. Tests y evidencias

### Unitarios

- reducer/mapper de cada código HTTP y estado provider;
- `[]` válido no confundido con excepción;
- error con previous data produce `stale_while_error`;
- cancelación no genera error visible;
- auth conserva contexto;
- partial conserva datos válidos;
- stale no se presenta como fresh/live;
- provider error no se presenta como empty/sold_out;
- request viejo no sobrescribe selección nueva;
- i18n no deja claves faltantes.

### Integración

- búsqueda sin coincidencias devuelve `empty`;
- provider parcial devuelve datos + warnings;
- provider caído conserva snapshot/stale si existe;
- geocoder fallido conserva query y permite fallback;
- detalle con rates fallidos conserva identidad;
- paridad fallida conserva rates;
- watchlist con un detalle inexistente conserva el favorito;
- tracked offers y snapshots distinguen error de empty;
- comp set sin coordenadas devuelve estado accionable;
- 401/403/404 no filtran datos ni destruyen URL state;
- request IDs no exponen secretos.

### Frontend/E2E

- idle → búsqueda → loading → success;
- búsqueda válida → empty → cambio de filtros → success;
- loading → error con retry;
- success → refresh error → stale_while_error;
- área escribiendo → resolving → empty/error → fallback;
- seleccionar hotel → detail partial/rates error/parity success;
- comp set → nearby empty/error → retry;
- tracking empty/error/success y snapshots empty/error;
- auth recovery desde formulario, detalle e inbox;
- teclado, lector de pantalla, dark/light, móvil y reduced motion;
- consola sin errores inesperados y sin loops de requests.

### QA de producto

- cada estado tiene copy, severidad y siguiente acción;
- no hay “sin resultados” cuando la causa es provider/error/auth;
- no se pierden filtros, formulario ni selección al recuperarse;
- stale muestra fecha y limitación;
- acciones deshabilitadas explican por qué;
- estados secundarios no bloquean la decisión principal.

## 11. Gate H21

H21 podrá marcarse completa cuando:

- exista taxonomía compartida para idle/loading/success/empty/partial/stale/unavailable/auth/error/cancelled;
- cada superficie tenga una matriz de entrada, copy, datos conservados y acción;
- empty, provider error, auth error, not-found y unavailable no se confundan;
- stale-while-error conserve contexto útil sin afirmar frescura;
- detalle, rates, paridad, watchlist, tracking, snapshots y cercanos dejen de convertir fallos silenciosos en listas vacías;
- V1 siga funcionando con fallback conservador y V2 exponga state/warnings/capabilities;
- requests obsoletos y cancelados no sobrescriban datos ni generen toasts falsos;
- ES/EN, accesibilidad, responsive y reduced motion cubran todos los estados;
- eventos y métricas permitan separar ausencia real de fallo técnico;
- QA E2E valide recuperación, auth, stale, partial y contexto preservado.

**Resultado contractual:** H21 queda definido como matriz de estados. La implementación de la máquina de estados, los envelopes V2 y el QA visual/E2E permanecen pendientes; no se declara la fase implementada por tener algunos booleans existentes.

La frontera con H22/H23 es obligatoria: `HotelWatchlistItem`/“guardar hotel” puede ser un favorito simple sin fechas ni promesa de refresh; “seguir oferta/precio” requiere la estancia y el contexto de oferta definidos por H23. Un estado `empty`, `error`, `unavailable` o contexto incompleto no bloquea necesariamente guardar el hotel, pero sí impide presentar un tracking operativo como activo sin confirmación explícita y evidencia válida.

## 12. Handoff

| Fase | Handoff H21 |
|---|---|
| H22-H23 | permitir “guardar hotel” como favorito simple aunque falten fechas; bloquear o marcar como `pending_context` el “guardar oferta/seguir precio” cuando el contexto sea `empty`, `error`, `unavailable` o incompleto, sin presentarlo como tracking activo |
| H24-H25 | etiquetar históricos `stale`, `partial` y `unknown` sin mezclarlos con actual |
| H26-H28 | no generar ni entregar alertas desde estados no evaluables; mantener reason codes |
| H29 | pausar/expirar tracking cuando no haya revalidación válida, sin borrar histórico |
| H31-H34 | jerarquía visual, copy ES/EN, responsive y accesibilidad de estados |
| H36 | skeleton, cancelación y presupuesto de percepción de velocidad |
| H38 | auth/ownership, errores seguros y no filtrado de request context |
| H39-H40 | matriz de tests y browser QA de todas las transiciones |
| H41 | métricas de estados, retries, provider degradation y silent failures |
| H43 | flags y kill switches para degradar a cache/demo sin copy live |

**No se declara H21 implementada hasta que la evidencia confirme cada transición en código y en UI real.**