# H38 — Ownership, secretos, SSRF y abuso hotelero

**Estado:** EN QA; ownership, geocoder SSRF, redaction y deeplinks tienen remediación server-side y regresiones negativas; los hard bounds de abuso están verificados, pero rate limiting distribuido, gateway externo y gates de rollout/operación siguen pendientes
**Fecha:** 2026-08-05  
**Área:** backend / seguridad / privacidad / frontend / providers / QA  
**Fuente de verdad:** sí para el alcance, riesgos, prioridades y gates de seguridad de H38  
**No es:** una certificación de seguridad, un pentest externo ni una afirmación de ausencia de vulnerabilidades

**Depende de:** H10 modelo de estancia/oferta, H11 migración, H22 semántica favorito/tracking, H23 creación de tracking, H27 inbox/deeplinks, H29 lifecycle, H35 legal/privacy/deeplinks, H37 límites/coste  
**Relacionado con:** H06 provider-neutral, H08 onboarding, H09 sweeps, H12 geocoder, H15 resultados, H21 estados, H33 a11y, H36 rendimiento, H39 tests, H41 observabilidad, H43 flags/kill switch.

> H38 protege dos fronteras diferentes: el catálogo hotelero que puede consultarse para descubrir una propiedad y los recursos privados que pertenecen a una cuenta. Un `hotel_id` puede identificar una propiedad pública; no demuestra ownership de un tracking, una regla, un snapshot o un evento.

---

## 1. Objetivo y frontera

H38 debe permitir demostrar que:

1. una cuenta no puede leer, modificar, borrar o inferir recursos privados de otra;
2. las relaciones entre `user_id`, `tracked_offer_id`, `hotel_id`, `rule_id`, snapshot y evento se validan, no solo sus IDs individuales;
3. ningún ID privado, token, email o payload sensible aparece en URL, deeplink, log, error o telemetría innecesaria;
4. las requests salientes del servidor no pueden convertirse en SSRF mediante configuración o input controlado por usuario;
5. los redirects externos solo usan destinos validados y con disclosure H35;
6. API keys y secretos permanecen server-side, no se imprimen en URLs ni logs de transporte;
7. búsqueda, autocomplete, geocoder, provider y endpoints privados tienen límites antiabuso y backpressure;
8. la eliminación, exportación y retención mantienen ownership y cascadas correctos;
9. los controles están probados con dos usuarios, provider malicioso, URLs privadas, errores y carga adversarial.

H38 cubre:

- autenticación y autorización por recurso y relación;
- BOLA/IDOR, enumeración y respuestas `403`/`404` prudentes;
- IDs públicos frente a IDs privados y estado en URL;
- deeplinks, redirects, `href`, `window.open`, `noopener` y `Referrer-Policy`;
- SSRF, DNS/rebinding, IPs privadas, redirects encadenados y allowlists;
- API keys, JWT, cookies, errores y redaction de logs;
- límites de payload, query, fan-out, rate limits y abuso;
- account deletion, exportación, retención y aislamiento de snapshots/eventos;
- pruebas de seguridad y gates de rollout.

H38 no decide:

- la política legal final o la base jurídica (H35/Legal);
- qué provider se contrata (H07/H08);
- la compra de WAF, rate limiter, SIEM o servicio externo;
- la implementación completa de tracking o migraciones (H10/H11/H23/H29);
- que una ruta sea pública por el mero hecho de devolver datos de catálogo.

---

## 2. Estado real V1

### 2.1. Controles que sí existen

| Superficie | Evidencia actual | Interpretación correcta |
|---|---|---|
| Auth | `get_current_user` valida Bearer JWT, `sub`, firma/algoritmo y existencia del usuario | Hay autenticación de ruta; no sustituye autorización de cada recurso relacionado |
| Catálogo | search, detalle, rates, parity y area search dependen de usuario autenticado | Autenticado no significa que el recurso sea privado de ese usuario; el catálogo hotelero no tiene ownership individual |
| Watchlist | list filtra por `user_id`; delete compara owner | Protección parcial correcta para esas operaciones |
| Comp sets | list filtra por `user_id`; detalle/mutaciones verifican owner antes de acceder | Debe mantenerse en cualquier endpoint nuevo y en helpers internos |
| Tracked offers | list/get/update/delete/snapshots pasan `user_id` al service y verifican owner | Es el patrón canónico para recursos privados |
| Alert rules | list/update/delete filtran o verifican `rule.user_id`; creación valida owner y hotel del tracking enlazado | La relación `tracked_offer_id` se rechaza si pertenece a otra cuenta o a otro hotel |
| Alert events | eventos nuevos llevan `user_id`; históricos con `rule_id` se backfillean y se resuelven por owner de regla; eventos no atribuibles quedan fuera | `/alert-events`, inbox y summary aplican ownership explícito; un `hotel_id` compartido no autoriza acceso |
| Account deletion | `account.py` elimina eventos ligados a reglas propias, reglas, comp sets/members, tracked offers y watchlist del usuario | Existe una cascada explícita parcial; no demuestra exportación, retención, aislamiento de eventos sin `rule_id` ni pruebas de borrado completo |
| Provider secrets | Makcorps API key se obtiene de entorno y no de payload de cliente | No garantiza ausencia en access logs, excepciones, tracing o URLs completas |
| Geocoder | URL base configurable por `NOMINATIM_URL`; query de usuario viaja como parámetro | La URL de destino es una superficie de configuración SSRF; no existe allowlist/validación DNS documentada |
| Deeplink | `deep_link` es nullable en snapshots/schemas; H35 exige allowlist futura | El campo puede viajar como string; no debe convertirse en CTA/redirect sin validación implementada |
| Flags | provider/geocoder/sweep tienen flags de entorno | `false` debe probarse como “cero requests externas”, no solo como copy de configuración |

### 2.2. Hallazgos prioritarios

#### H38-P0-01 — Regla con `tracked_offer_id` sin comprobación relacional (remediado)

`create_alert_rule()` comprueba que `hotel_id` existe y guarda `user_id`/`tracked_offer_id`, pero no carga el tracking para comprobar:

```text
tracked_offer.user_id == current_user.id
tracked_offer.hotel_id == payload.hotel_id
```

La creación de una regla debe rechazar cualquier combinación cruzada. No basta con que quien llama esté autenticado ni con que ambos IDs existan.

**Riesgo histórico:** una regla de un usuario podía quedar asociada a un tracking de otra cuenta o a otro hotel.

**Cierre aplicado:** `create_alert_rule()` carga el tracking con ownership del usuario y comprueba coincidencia de hotel; hay regresiones API para tracking cruzado y hotel cruzado.

#### H38-P0-02 — Eventos filtrados por `hotel_id`, no por ownership del evento (remediado)

`HotelAlertEvent` tiene ahora `user_id` nullable e indexado. La migración 0042 backfillea eventos históricos con `rule_id` desde `hotel_alert_rule.user_id`; eventos históricos sin owner verificable permanecen fuera de lecturas privadas.

**Riesgo:** dos cuentas que siguen la misma propiedad pueden ver eventos generados para la otra, especialmente eventos de sweep con `rule_id is None`. El código demuestra una condición de aislamiento insuficiente; la explotación concreta depende de los datos y del flujo de creación.

**Cierre aplicado en esta fase:**

- eventos nuevos reciben `user_id` desde la regla o el tracking;
- la migración 0042 añade FK/index y backfill desde reglas;
- `/alert-events`, inbox, summary y mark-read usan ownership explícito o regla histórica propia;
- eventos legacy sin ownership verificable quedan en cuarentena lógica y no se muestran;
- no se usa `hotel_id` compartido como prueba de ownership;
- el `user_id` interno no se expone en `HotelAlertEventOut`.

La política de retención física de eventos no atribuibles sigue pendiente de H29.

#### H38-P0-03 — Geocoder con host configurable y request server-side (remediado)

`geocoder.py` construye `f"{_NOMINATIM_URL}/search"` y ejecuta `requests.get()` con timeout. La consulta del usuario solo es `q`, pero el host puede cambiar por entorno y la librería puede seguir redirects HTTP según defaults.

**Requisitos antes de habilitarlo fuera de un entorno controlado:**

- allowlist exacta de esquemas/hosts de geocoder por entorno;
- rechazar credenciales, fragmentos y puertos no autorizados;
- resolver y validar IPs antes de conectar;
- bloquear loopback, RFC1918, link-local, metadata endpoints, multicast y rangos reservados;
- proteger contra DNS rebinding y cambios de resolución;
- limitar redirects o validarlos salto a salto;
- timeout total, tamaño máximo de respuesta y content-type esperado;
- no aceptar una URL completa del cliente como destino;
- cache/cooldown/rate limit y redaction H35/H37.

**Cierre aplicado en este bloque:**

- destino limitado a `https` y allowlist exacta de hosts configurados;
- credenciales, puertos, query y fragmentos en `NOMINATIM_URL` rechazados;
- resolución DNS validada contra IPs no globales y conexión fijada a la IP validada, conservando SNI/Host del dominio;
- proxies heredados y redirects desactivados;
- timeout de conexión/lectura acotado por deadline total, límite de bytes y `Content-Type` JSON;
- input `q` limitado, no interpretado como URL y nunca reflejado en logs;
- regresiones negativas para allowlist, DNS privado, redirects, payload, timeout, coordenadas y redaction.

El input `q` no debe interpretarse como URL ni concatenarse en el path.

#### H38-P0-04 — API key en query parameter y redacción incompleta (remediado parcialmente; gateway externo pendiente)

Makcorps fusiona `api_key` en cada URL de request porque ese es el contrato actual del provider. El adapter redacted excepciones/log payloads y persiste `raw_payload` sin claves sensibles; la key nunca se devuelve al frontend. Siguen fuera del control del adapter los access logs/proxies/tracing externos que puedan capturar la URL completa.

**Cierre aplicado:** sanitización de texto antes del logger propio, redaction recursiva de respuestas antes de persistirlas y regresiones que provocan excepciones con query secreta. **Pendiente antes de producción:** confirmar auth por header o configurar egress/access logs para no capturar URLs completas, además de rotación/revocación y evidencia de infraestructura.

---

## 3. Modelo de clasificación de datos y ownership

### 3.1. Clases

| Clase | Ejemplos | URL/log permitido |
|---|---|---|
| catálogo público | `HotelProperty.id`, nombre, ciudad, estrellas, coordenadas públicas | URL de búsqueda o detalle solo si H18/H35 lo aprueban; no es ownership |
| contexto de estancia | fechas, ocupación, moneda, habitación, régimen, cancelación | URL solo si es intención no privada; redaction/limitación en logs |
| recurso privado | `tracked_offer_id`, `rule_id`, snapshot privado, evento privado, comp set | no en URL compartible ni logs; exigir authz/ownership |
| identidad | `user_id`, email, token, cookie, IP | nunca en deeplink externo ni logs de negocio; hash/agregado solo cuando sea necesario |
| secreto | JWT secret, API key, refresh/reset token, Authorization | nunca en respuesta, URL, error o log |
| provider payload | raw response, vendor IDs, query, deep link | server-side minimizado; no persistir/exportar sin H35 |

### 3.2. Reglas relacionales

Cada operación privada debe validar el grafo completo que utiliza:

```text
current_user
  → owned tracked_offer / watchlist / comp_set / alert_rule
  → canonical hotel
  → provider alias / snapshot / event
```

Reglas mínimas:

- no confiar en `user_id` enviado por cliente;
- no autorizar un hijo solo porque el padre exista;
- al crear/actualizar una regla, validar tracking, hotel y owner en la misma transacción;
- al leer snapshots, validar owner del tracking, no solo `tracked_offer_id` sintácticamente válido;
- al leer eventos, diferenciar evento privado de evento de provider y aplicar owner real;
- al borrar un usuario, conservar la cascada explícita existente como baseline, ampliarla/quarantinar legacy cuando proceda y verificar que no quedan hijos privados legibles;
- al exportar, incluir solo datos del usuario y redaction de provider/secretos;
- usar respuestas indistinguibles para IDs inexistentes y no autorizados donde la enumeración sea sensible.

### 3.3. Identidad interna/externa

- `HotelProperty.id` es identidad canónica interna.
- `HotelProviderAlias.provider_hotel_id` es identidad del provider.
- No pasar el ID interno a un adapter que espera el externo.
- No aceptar `provider_hotel_id` del cliente para saltarse el mapping autorizado.
- No incluir alias privados, request IDs o tokens en deeplinks.

---

## 4. Deeplinks, redirects y navegación externa

### 4.1. Contrato

Un deeplink externo solo puede nacer de un provider aprobado, pasar H35 y cumplir:

```text
scheme = https
host = exacto o allowlist versionada
port = permitido explícitamente
path = ruta permitida por provider
params = allowlist de claves y valores sanitizados
no credentials / no tokens / no user_id / no private IDs
expiry/context = definido si el enlace es contextual
```

`deep_link: string | null` no equivale a URL segura.

### 4.2. Prohibiciones

- `href={rawProviderUrl}` sin validación server/client;
- redirect a `next`, `returnTo` o query absoluta sin allowlist;
- aceptar `javascript:`, `data:`, `file:`, `blob:` o esquemas no previstos;
- permitir userinfo (`https://user:pass@host`), hosts con confusión Unicode o IP decimal/hexadecimal;
- seguir redirects intermedios sin revalidar cada `Location`;
- enviar `user_id`, email, token, API key o tracking private ID al partner;
- abrir ventana externa sin `noopener,noreferrer`;
- permitir que un deeplink de un evento privado funcione sin reautorización.

### 4.3. Navegador y privacidad

- disclosure H35 visible antes del CTA;
- `rel="noopener noreferrer"` para enlaces externos cuando aplique;
- `Referrer-Policy: no-referrer` o política más restrictiva compatible;
- no usar IDs privados en rutas compartibles;
- telemetría del click agregada y sin URL completa/query sensible;
- si el link caduca, mostrar estado recuperable y no construir uno alternativo arbitrario.

---

## 5. SSRF y requests salientes

### 5.1. Superficies actuales

| Cliente | Destino | Input controlable | Riesgo actual |
|---|---|---|---|
| Makcorps | base URL de entorno + endpoint fijo | configuración, ciudad/hotel/fechas como params | API key en query; falta gateway común, límites y redaction completa |
| Nominatim | `_NOMINATIM_URL + /search` | `q` del usuario y URL de entorno | host configurable, redirects/defaults, sin validación DNS/egress documentada |
| futuros providers | adapter H06 | datos de StayQuery y configuración | no permitir cliente directo al provider |

### 5.2. Allowlist y egress

El gateway de red futuro debe:

1. recibir solo destinos internos/provider IDs, no URLs arbitrarias;
2. normalizar URL antes de validar;
3. permitir únicamente esquemas y hosts registrados;
4. resolver DNS y rechazar IP privada/reservada en cada conexión;
5. impedir rebinding entre validación y conexión;
6. limitar puertos, método, tamaño, timeout y número de redirects;
7. registrar destino como provider/host lógico, no URL completa;
8. fallar cerrado cuando el provider no está registrado o la flag está apagada;
9. probar IPv4, IPv6, loopback, metadata, redirects y DNS alternativo;
10. mantener separación entre navegación client-side y fetch/redirect server-side.

Una allowlist de dominio sin bloqueo de IPs privadas no cierra SSRF. Un bloqueo de IP sin allowlist no cierra el uso de un host externo no aprobado.

### 5.3. Respuesta y parser

- exigir `Content-Type` esperado;
- límite de bytes antes de parsear JSON;
- no reflejar raw payload en errores;
- validar campos, rangos, moneda y tamaño de listas;
- rechazar XML/HTML inesperado si el contrato espera JSON;
- no persistir raw payload completo si H35 no lo permite;
- clasificar `timeout`, `rate_limited`, `invalid_response` y `unavailable` sin convertirlos en `empty`.

---

## 6. Secretos, tokens y logs

### Secretos

- JWT/API keys solo en secret manager o entorno protegido; nunca en repo, fixture, URL frontend o payload de usuario;
- no leer `.env` de forma silenciosa en producción sin un control de despliegue explícito;
- exigir longitud/entropía y algoritmo permitido para JWT;
- rotación/revocación probada para API keys, refresh y reset tokens;
- no aceptar `Authorization` o secretos en query params de endpoints Viru;
- no enviar claves a providers distintos del destinatario configurado;
- no persistir secrets en `raw_payload`, snapshots o eventos.

### Redaction

Redactar antes de cualquier sink:

```text
Authorization
Cookie / Set-Cookie
api_key / token / secret / password
JWT / refresh / reset token
URLs con query secrets
email, user_id e IP cuando no sean necesarios
payloads provider completos
```

El redactor debe cubrir logger de aplicación, `requests`/HTTP client, access logs, excepciones, tracing, métricas de atributos y dumps de debug. No basta con bajar el nivel de `urllib3`.

### Errores

- respuestas externas solo exponen código estable y mensaje accionable;
- no reflejar excepción con URL, headers o payload;
- no distinguir a un atacante entre “ID inexistente” y “ID de otra cuenta” cuando esa diferencia enumera recursos;
- correlation ID opaco sí; token o query completa no.

---

## 7. Abuso y límites

H38 hereda los budgets de H37, pero añade protección de superficie:

| Superficie | Límite requerido |
|---|---|
| login/auth | rate limit por IP/identidad hasheada, backoff y no enumeración |
| `/hoteles/search` | límite de tamaño, offset/limit, coste SQL y rate limit autenticado |
| autocomplete/`area-resolve` | debounce client-side más límite server-side, cache/cooldown y no tormenta por tecla |
| `/area-search` | radio, resultados, fan-out provider y coste por intención |
| provider opt-in | flags, budget, concurrency, breaker y zero calls when off |
| tracked offers | límites por cuenta, payload, frecuencia y número activo; aprobación de producto/H35 |
| alert rules/events | límites por usuario, dedupe y no fan-out no acotado |
| export/delete | idempotencia, autorización, tamaño y auditoría redacted |

Los límites deben devolver estado estable (`429` cuando proceda), `Retry-After` sanitizado y no filtrar cuotas internas, usuarios ni provider secrets. Un límite documentado pero no instrumentado no es un control cerrado.

---

## 8. Prioridades de remediación

### P0 — aislamiento y secreto

- corregir ownership relacional de `tracked_offer_id` al crear reglas;
- corregir aislamiento de `HotelAlertEvent` y clasificar/quarantinar legacy sin owner;
- bloquear provider/geocoder cuando flags están off y evitar URL configurable no allowlisted;
- cerrar SSRF: esquema/host/IP/redirect/egress y tamaño/timeout;
- redaction de API keys, URLs, tokens, headers y excepciones;
- no usar raw `deep_link` como href/redirect;
- verificar ID interno frente a `provider_hotel_id` antes de cualquier llamada.

### P1 — defensa operativa

- autorización central reusable para recursos y relaciones;
- rate limits server-side de search, resolve, area-search y tracking (pendiente como limiter distribuido/429 estable);
- límites de payload/listas/fan-out, radio, coordenadas, ocupación y paginación segura (hard bounds V1 verificados por regresiones HTTP);
- errores tipados sin enumeración y outcomes H37;
- tests de dos usuarios, provider malicioso, DNS/redirect y logs;
- auditoría de cascada, exportación, retención y replay.

### P2 — endurecimiento

- gateway egress común para todos los providers;
- mTLS/secret manager o equivalente si la infraestructura lo exige;
- detección de abuso y alertas agregadas;
- SAST/DAST periódico, dependency audit y fuzzing de parsers/URLs;
- revisión de seguridad por cambio de provider, schema, deeplink o endpoint.

---

## 9. Gates de seguridad

### Gate A — AuthN/AuthZ/BOLA

- matriz de rutas hoteleras con authn, recurso, owner y respuesta no autorizada;
- User A no puede leer/modificar/borrar recursos de User B;
- regla con tracking cruzado es rechazada;
- evento privado de User B no aparece si User A sigue el mismo hotel;
- snapshots, comp sets, watchlist, alerts e inbox tienen tests relacionales;
- IDs inexistentes/no autorizados no permiten enumeración sensible;
- account deletion/export no deja hijos privados legibles.

### Gate S — SSRF/open redirect/deeplink

- pruebas contra `localhost`, `127.0.0.1`, IPv6 loopback, RFC1918, link-local y metadata IP;
- hosts no allowlisted, puertos no permitidos, userinfo, Unicode confusable y esquemas no HTTPS rechazados;
- redirects encadenados revalidados o bloqueados;
- `next`/`returnTo` absoluto malicioso rechazado;
- provider deeplink sin validación nunca llega a `href`/redirect;
- `noopener,noreferrer`, `Referrer-Policy` y disclosure verificados;
- API key/user ID/token ausentes de URLs y referrer.

### Gate K — secretos y redaction

- secret scan en código, docs operativas, fixtures y logs;
- tests de logger con URL query, Authorization, Cookie, API key, JWT y excepción de HTTP;
- no hay secretos en respuestas 4xx/5xx, traces, métricas ni dumps;
- rotación/revocación y startup fail-closed verificables;
- provider key nunca se serializa al frontend.

### Gate R — abuso y egress

- **Parcial verificado:** search/resolve/area-search rechazan inputs sobredimensionados o fuera de rango antes del servicio, con regresión `test_hotels_search_and_area_inputs_have_server_side_hard_bounds`;
- **Pendiente:** burst de search/resolve/area-search/tracking debe producir backpressure estable;
- **Pendiente:** `429` y `Retry-After` no deben revelar información privada;
- flags off y budget cero producen cero requests externas;
- tamaño, timeout, bytes y redirects externos están acotados;
- dos workers/requests concurrentes no duplican una operación sensible fuera de H37;
- no hay acceso SSRF desde el servidor a servicios internos.

### Gate Q — regresión

- unit/integration/security/browser tests relevantes;
- fixtures de dos usuarios y provider malicioso;
- `git diff --check`, lint/typecheck/tests afectados;
- revisión H35/H37/H39/H41/H43 antes de activar provider o deeplink.

**Criterio final:** cero P0 abiertos; matriz de ownership aprobada; SSRF/open redirect/deeplink probado; redaction demostrado en todos los sinks relevantes; abuso acotado; migración/legacy y rollback documentados; y cualquier incertidumbre marcada como bloqueante, no como “segura por defecto”.

---

## 10. Claims que H38 no autoriza

Hasta cerrar los gates, no puede afirmarse que `/hoteles`:

- tenga aislamiento completo de eventos privados por usuario;
- sea inmune a BOLA/IDOR;
- acepte únicamente deeplinks seguros;
- esté protegido contra SSRF o DNS rebinding;
- tenga rate limiting distribuido para todas sus rutas;
- redacted todos los access logs, traces y errores de provider;
- permita compartir URLs hoteleras sin riesgo de fuga;
- use una API key fuera de query params o fuera de logs intermediarios;
- convierta `hotel_id` en prueba de ownership;
- tenga sus cascadas/exportaciones de datos hoteleros completamente auditadas; existe una cascada explícita parcial en account deletion, pero quedan pruebas de completitud, retención y exportación.

H38 sí autoriza el contrato de que toda nueva ruta, provider, URL externa, migración o superficie de usuario debe aportar owner, clasificación de datos, modelo de abuso, redaction y pruebas negativas antes de habilitarse.

---

## 11. Referencias de seguridad

- [OWASP Top 10 — A01 Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/)
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Unvalidated Redirects and Forwards](https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- H35 — legal, privacidad, disclosure y deeplinks
- H37 — benchmark, rate limits, locks y coste máximo

**Resultado H38:** auditoría y contrato de seguridad aprobados; las regresiones focalizadas de ownership, SSRF, deeplink, redaction y hard bounds pasan, pero H38 queda en `EN QA` hasta demostrar limiter distribuido/backpressure, sinks externos de logs, exportación/retención y los gates de rollout.
