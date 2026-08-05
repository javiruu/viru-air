# H13 — Formulario hotelero, URL state y estados de submit

**Estado:** completa como contrato de interacción; implementación frontend y pruebas E2E pendientes  
**Fecha:** 2026-08-04  
**Área:** frontend / backend-contract / navegación / accesibilidad  
**Fuente de verdad:** sí para el comportamiento del formulario principal de `/hoteles` y la recuperación de una búsqueda.

**Depende de:** [H12 — resolución robusta de destino](hoteles-destination-resolution-h12.md), [H10 — modelo canónico de estancia/oferta](hoteles-stay-offer-model-h10.md), [H06 — contrato provider-neutral](hoteles-provider-neutral-contract-h06.md)  
**Relacionado con:** H03 arquitectura de información, H04 métricas/eventos, H14 filtros/orden, H15 resultados/paginación, H17 autocomplete, H35 privacidad, H41 observabilidad y frontend QA.

---

## 1. Propósito y decisión de fase

H13 define un formulario que una persona pueda completar sin conocer la arquitectura interna de Viru. La búsqueda debe ser válida, recuperable y explicable: el usuario sabe qué destino eligió, qué fechas/ocupación se enviarán y qué ocurre al pulsar buscar.

### Decisión H13

**Persistir en la URL únicamente el estado reproducible de la búsqueda; mantener fuera de la URL ownership, credenciales, alertas privadas y datos sensibles.**

- una búsqueda válida actualiza URL y resultados de forma coordinada;
- recargar la página o volver atrás restaura los parámetros reproducibles;
- una selección de destino conserva `destination_id/type/source` si el contrato H12 lo proporciona;
- la URL no convierte coordenadas o labels arbitrarios en una resolución confiable sin revalidación;
- el formulario muestra errores inline y no depende solo de deshabilitar el botón;
- el doble submit no duplica requests ni tracking;
- V1 API sigue siendo consumible mientras H15 define envelopes de resultados.

---

## 2. Estado actual y gaps

| Área | Estado actual | Gap H13 |
|---|---|---|
| modo | `name` o `area` en estado React | no se restaura desde URL |
| destino name | `query`/`city` locales | no hay contrato de URL ni validación explícita de selección |
| destino area | `areaQuery`, sugerencias y `areaResolved` | resolución se pierde al recargar; selección puede quedar stale al editar |
| fechas | defaults de +7/+14 días | `canSearch` comprueba strings, no comunica todos los errores inline |
| ocupación | scalar `guests` 1–6 | roadmap exige rooms/adults/children; bridge temporal debe ser claro |
| radius | select 1/3/5/10/20 | no se conserva en URL |
| provider | checkbox `useProvider` | no debe ser una promesa live; debe conservarse solo si es reproducible y permitido |
| submit | boolean `loading` | no distingue validating/resolving/fetching/success/error |
| error | mensaje único/toast | no hay campo/error code por input ni foco consistente |
| browser history | no contrato específico | back/forward no restaura búsqueda |

H13 no resuelve todavía el modelado completo de rooms/children de H10; define un bridge explícito para el formulario actual y deja la ampliación estructurada preparada.

---

## 3. Modelo de formulario canónico

### 3.1. Estado mínimo V1 compatible

```text
mode: name | area
query: string
city: string
area_query: string
selected_destination: DestinationSelection | null
check_in: YYYY-MM-DD
check_out: YYYY-MM-DD
guests: positive integer legacy bridge
radius_km: approved integer
currency: ISO-4217
use_provider: boolean, subject to provider flag
```

La UI puede mostrar defaults, pero debe hacerlos visibles y editables. Un default no equivale a una preferencia guardada.

### 3.2. Selección de destino

```text
destination_id: opaque string | null
label: string
secondary_label: string | null
type: city | neighborhood | landmark | airport | region | ...
country_code: ISO-3166-1 | null
latitude/longitude: number | null
confidence: high | medium | low | unknown
source: internal_catalog | geocoder_external | user_selected | legacy_centroid
is_ambiguous: boolean
```

Reglas:

- editar `area_query` después de elegir destino limpia `selected_destination`;
- solo una selección explícita puede habilitar area search;
- coordenadas restauradas desde URL necesitan validación de rango y asociación con label/type;
- una URL con `lat/lng` sin `destination_id` se trata como legacy/approximate, no como selección confirmada;
- `low`, `unknown` o `is_ambiguous=true` requieren confirmación o fallback interno;
- no enviar `user_id`, email, tokens, labels privados o thresholds de alertas.

### 3.3. Fechas

Invariantes:

- formato estricto `YYYY-MM-DD`;
- entrada y salida presentes para area search;
- `check_out > check_in`;
- no permitir estancias de cero noches;
- la política de fechas pasadas se decide según búsqueda histórica, pero debe ser explícita;
- si el provider requiere ventana futura, la validación debe mostrar razón y no un error genérico;
- no depender de timezone del navegador para cambiar la fecha enviada.

### 3.4. Ocupación bridge

Mientras el frontend V1 use `guests`:

```text
guests >= 1
default=2
occupancy_source=legacy_form
```

No presentar `guests=2` como rooms/adults exactos hasta H10/H15. H13 debe reservar la forma de URL estructurada futura:

```text
rooms=1
adults=2
children=0
child_ages=...
```

Los valores no soportados por el backend actual no se envían de forma experimental sin feature flag y validación.

### 3.5. Currency, radius y provider

- `currency` siempre uppercase ISO-4217 y lista permitida;
- `radius_km` solo valores del catálogo UI/backend;
- `use_provider` se restaura solo si la flag y el provider siguen habilitados;
- si el provider no está disponible, la URL puede conservar la intención pero la UI debe mostrar estado `provider_disabled`, sin ejecutar llamada;
- no guardar API keys ni plan/coste en URL.

---

## 4. URL state canónico

### 4.1. Parámetros V1/V1.5

Ruta sugerida: `/hoteles`.

```text
mode=name|area
q=hotel+name
city=Madrid
area=Madrid+Centro
destination_id=opaque-id
destination_type=city
destination_source=internal_catalog
country=ES
lat=40.4168
lng=-3.7038
in=2026-09-10
out=2026-09-13
guests=2
radius=10
currency=EUR
provider=0|1
```

No incluir parámetros vacíos ni defaults si no aportan recuperación. La canonicalización debe ordenar y codificar de forma determinista.

### 4.2. Parámetros futuros H10

```text
rooms=1
adults=2
children=0
child_ages=4,9
```

Solo se activan cuando backend/frontend comparten el contrato estructurado. No mezclar `guests` y `adults/rooms` con valores contradictorios; si llegan ambos, aplicar versión/precedencia documentada y mostrar warning interno.

### 4.3. Seguridad y privacidad

Nunca poner en URL:

- `user_id` o email;
- access tokens/API keys;
- target prices, alert thresholds o canales;
- raw provider responses;
- PII de huéspedes;
- payloads completos de búsqueda.

Las URLs pueden acabar en historial del navegador, analytics, logs/proxies y enlaces compartidos. `destination_id`, fechas y ocupación son datos funcionales, pero se deben minimizar y redacted en telemetry cuando corresponda.

### 4.4. Push, replace y browser history

- `router.replace` mientras el usuario edita, con debounce y sin crear una entrada por tecla;
- `router.push` al submit válido que inicia una búsqueda reproducible;
- no modificar URL si la validación falla;
- back/forward restaura el estado del formulario desde `URLSearchParams`;
- la restauración no debe disparar doble búsqueda: usar fingerprint de URL/submit;
- cambiar solo panel/collapse no toca URL de búsqueda;
- compartir una URL no debe exponer ownership ni ejecutar automáticamente un provider no permitido.

---

## 5. Validación explícita

### Errores por campo

```text
form.destination.required
form.destination.ambiguous
form.destination.not_found
form.destination.low_confidence
form.dates.check_in_required
form.dates.check_out_required
form.dates.invalid_order
form.dates.past_not_allowed
form.occupancy.guests_invalid
form.occupancy.rooms_invalid
form.currency.invalid
form.radius.invalid
form.provider.unavailable
```

Cada error debe incluir:

```text
field
code
message_key
severity
focus_target
```

El backend sigue devolviendo códigos estables; el frontend resuelve copy ES/EN. No mostrar tracebacks ni mensajes crudos de provider/geocoder.

### Validación al editar

- validar sintaxis local inmediatamente cuando sea barato;
- validar rango/relación en blur o submit;
- no borrar un valor válido hasta que el nuevo valor se confirme;
- al cambiar `check_in`, reajustar un default de `check_out` solo si nunca fue editado por el usuario; no sobrescribir una elección explícita;
- mostrar noches calculadas para reducir errores;
- `aria-invalid` y `aria-describedby` apuntan a error concreto.

### Validación al submit

Orden:

1. campos mínimos;
2. destino seleccionado/resuelto;
3. fechas y noches;
4. ocupación/radius/currency;
5. flags/provider permitido;
6. construir fingerprint/URL;
7. ejecutar búsqueda.

Una validación fallida no limpia resultados anteriores automáticamente: mantiene el contexto y marca qué debe corregirse, salvo que el usuario cambie de consulta válida.

---

## 6. Máquina de estados de submit

```text
idle
  → validating
  → resolving_destination
  → fetching_results
  → success
  → empty
  → partial
  → error
  → cancelled
```

Estados auxiliares:

```text
provider_disabled
stale_result
restoring_from_url
```

### Semántica

- `idle`: formulario listo;
- `validating`: bloqueo de submit duplicado y validación síncrona;
- `resolving_destination`: solo si falta resolución y H12 permite resolver;
- `fetching_results`: request activa con abort/correlation ID;
- `success`: respuesta válida con items;
- `empty`: respuesta válida sin resultados;
- `partial`: datos con warning de cobertura/degradación;
- `error`: error accionable, sin afirmar sold out;
- `cancelled`: usuario/navegación canceló request;
- `provider_disabled`: intención válida pero provider no permitido;
- `stale_result`: respuesta tardía que no corresponde al fingerprint actual.

### Doble submit y race conditions

- cada submit obtiene `search_request_id` y `form_fingerprint`;
- deshabilitar solo la acción de submit, no bloquear navegación ni corrección;
- abortar request anterior cuando una nueva búsqueda válida la sustituye;
- ignorar respuestas con fingerprint obsoleto;
- no duplicar `router.push`, tracking ni notificaciones;
- retry explícito conserva la misma intención, pero no reintenta ciegamente un 429 sin cooldown.

---

## 7. Restauración y recuperación

### Primera carga

1. leer URL;
2. validar/canonicalizar parámetros;
3. hidratar formulario sin sobrescribir estado ya editado por el usuario;
4. si existe selección completa, mostrarla;
5. si URL es válida y `run=1`/intención equivalente, ejecutar una sola búsqueda;
6. si falta una dimensión, mostrar formulario prellenado pero no ejecutar;
7. si hay parámetros inválidos, limpiar solo los inválidos y mostrar warning no técnico.

No ejecutar automáticamente un provider real solo por abrir un enlace compartido. La recuperación debe respetar flags, budget y política de consentimiento.

### Back/forward

- escuchar cambios de `useSearchParams`;
- comparar fingerprint contra estado actual;
- restaurar selección, fechas, ocupación, radius, currency y modo;
- cancelar request que ya no representa la URL;
- reutilizar cache si es elegible H05/H09;
- no duplicar una búsqueda si el estado ya está representado por resultados actuales;
- anunciar al lector de pantalla que se restauró una búsqueda.

### Error de URL

Si `lat` está sin `lng`, fechas invertidas o destination type inválido:

- no ejecutar búsqueda;
- marcar campo correspondiente;
- conservar valores seguros restantes;
- ofrecer “restablecer búsqueda”;
- no lanzar excepción de render.

---

## 8. Accesibilidad y feedback

- `<form>` semántico con `type="submit"`;
- labels visibles y asociados a inputs;
- errores con `aria-describedby`;
- `aria-invalid=true` solo cuando el campo tiene error;
- región `aria-live="polite"` para estado de búsqueda y resultados;
- región `aria-live="assertive"` solo para errores que bloqueen;
- foco al primer error al fallar validación;
- foco al heading de resultados tras éxito/empty/partial;
- sugerencias H12 navegables con teclado;
- submit y cancel tienen labels explícitos;
- no usar color como único indicador de estado;
- respetar reduced motion;
- touch targets y contraste según contrato frontend del repositorio.

---

## 9. Instrumentación H04/H41

Eventos mínimos:

```text
hotel_search_form_viewed
hotel_search_mode_changed
hotel_search_destination_typed
hotel_search_destination_selected
hotel_search_validation_failed
hotel_search_submit_started
hotel_search_submit_cancelled
hotel_search_submit_succeeded
hotel_search_submit_empty
hotel_search_submit_partial
hotel_search_submit_failed
hotel_search_url_restored
hotel_search_stale_response_ignored
```

No registrar query completa si puede contener datos sensibles; preferir longitud, tipo, país, fingerprint hash y códigos.

Métricas:

```text
hotel_form_validation_error_total{field,code}
hotel_form_submit_total{mode,outcome}
hotel_form_restore_total{outcome}
hotel_form_double_submit_blocked_total
hotel_form_stale_response_total
hotel_form_url_canonicalized_total
```

---

## 10. Tests y criterios de implementación

### Unitarios

- defaults producen fechas válidas;
- check-out anterior/igual a check-in falla;
- query vacía/destino sin selección falla;
- edición de área limpia selección y coordenadas stale;
- currency/radius/guests inválidos fallan;
- URL serializa y parsea de forma determinista;
- parámetros privados nunca se serializan;
- URL parcial prellena sin ejecutar;
- URL completa ejecuta una sola vez cuando procede;
- `push` solo ocurre tras validación;
- `replace` no crea historial por cada tecla;
- stale response no sobrescribe resultados actuales;
- doble submit no duplica request.

### Integración/frontend

- name search mantiene compatibilidad con `/hotels/search` V1;
- area search conserva `/area-resolve` + `/area-search` actuales;
- back/forward restaura formulario y resultado;
- refresh conserva intención reproducible;
- selección ambigua H12 bloquea submit;
- provider off no hace llamada externa;
- error backend/geocoder muestra copy i18n estable;
- foco y `aria-live` se comportan correctamente;
- mobile/desktop conservan inputs y CTA accesibles.

### Gate H13

H13 podrá considerarse implementada cuando:

- una persona completa una búsqueda válida sin explicación externa;
- destino, fechas, ocupación, radius y currency tienen validación inline;
- URL state sobrevive refresh y back/forward;
- selección de destino no queda stale al editar;
- submit tiene estados visibles y previene duplicados/races;
- errores, empty y partial no se confunden;
- no se filtra información privada en URL/telemetry;
- tests backend/frontend/E2E cubren el flujo y accesibilidad.

**Resultado H13:** contrato de formulario aprobado. El frontend actual continúa siendo V1 con estado principalmente efímero hasta implementar URL state, validación explícita y la máquina de submit.
