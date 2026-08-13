# H35 — Legal, privacidad, disclosure y deeplinks hoteleros

**Estado:** COMPLETA como contrato; validación server-side deny-by-default y redaction hotelera implementadas; revisión legal/security, CTA/disclosure y QA de integración pendientes
**Fecha:** 2026-08-05  
**Área:** legal / privacidad / seguridad / backend / frontend / producto  
**Fuente de verdad:** sí para el alcance y los criterios de cierre de H35  
**No es:** asesoramiento jurídico ni aprobación de un proveedor, programa de afiliación o tratamiento de datos concreto

**Relacionado con:** H19 precio total y fees, H22 favorito frente a tracking, H23 creación desde oferta real, H26 reglas de alerta, H27 inbox privado y deep links internos, H28 delivery y consentimiento por canal, H29 lifecycle y borrado, H34 localización, H38 seguridad, H41 observabilidad, H50 afiliación y atribución.

> H35 convierte “hay un enlace al partner” y “hay datos hoteleros” en un contrato verificable de confianza. No declara que Viru sea una OTA, que controle la reserva final, que el precio sea garantizado ni que exista una afiliación activa. Toda aprobación legal efectiva corresponde al responsable legal y a los términos vigentes de cada proveedor.

---

## 1. Objetivo y frontera

H35 debe permitir que una persona entienda, antes de salir de Viru:

1. qué está comparando;
2. qué dato procede de un proveedor externo y cuándo fue observado;
3. qué parte controla Viru y qué parte sucede en el partner;
4. si existe una relación comercial o comisión;
5. qué puede cambiar en precio, disponibilidad, impuestos o condiciones;
6. qué datos privados se guardan para favoritos, tracking, alertas e inbox;
7. qué enlace se abrirá y por qué es un destino permitido.

H35 cubre:

- copy y disclosure de intermediación, precio variable y afiliación;
- minimización de datos enviados a providers, geocoders y servicios de delivery;
- base legal, responsable del tratamiento, derechos de acceso/exportación, rectificación, supresión y revocación, transferencias internacionales y tratamiento de datos de menores, sujetos a revisión Legal;
- ownership y privacidad de búsquedas guardadas, tracking, snapshots, reglas, eventos e inbox;
- consentimiento por canal y separación entre tracking y email/push/analítica;
- retención, exportación, pausa, anonimización y borrado coordinados con H11/H29;
- validación de deeplinks externos y seguridad de navegación/redirect;
- redaction de URLs, credenciales, payloads y logs;
- requisitos de evidencia legal, security, QA y soporte.

H35 no decide por sí sola:

- qué proveedor comercial se integra o qué programa de afiliación se firma (H08/H50);
- el modelo canónico de estancia/oferta (H10/H11);
- el motor de reglas o dedupe (H26);
- el delivery concreto de email/push (H28);
- la retención definitiva exigida por una jurisdicción o contrato, que debe aprobar Legal;
- una certificación de cumplimiento o garantía jurídica.

---

## 2. Estado real V1: evidencia, no promesa

### 2.1. Capacidades observadas

| Superficie | Evidencia V1 | Lectura correcta |
|---|---|---|
| Auth | Los endpoints hoteleros usan `get_current_user` en búsqueda, watchlist, alertas, eventos y tracked offers | Hay una base de autenticación; no sustituye una revisión de ownership por recurso y operación |
| Ownership | El servicio filtra por `user_id` y comprueba `not_allowed` para varios recursos | Debe extenderse a cada evento, snapshot, deeplink y deep link interno |
| `deep_link` | `HotelRateOut`/snapshots transportan `deep_link: string \| null`; las salidas y el límite ORM aplican el validador server-side | Deny-by-default; solo se expone/persiste un HTTPS con host/query allowlisted por configuración; el resto es `null` |
| Inbox/deep links internos | H27 define reautorización, aislamiento y separación frente al partner externo | H27 es contrato; no equivale a que todos los paths estén implementados y verificados |
| Policies | Existe una página índice de políticas (`docs/product/policies-page.md`) | Un índice general no prueba disclosure hotelero visible en el CTA |
| Provider/geocoder | Existen adapters/configuración y contratos que contemplan provider externo | Cada servicio requiere términos, minimización, redaction, límites y aprobación propios |
| Consentimiento | H28 separa delivery, preferencias y canales | Crear tracking no puede implicar opt-in automático a email, push o analítica |
| Derechos y base legal | Pendientes de decisión Legal por jurisdicción y provider | No declarar derechos, transferencias o retenciones concretas no aprobadas |

### 2.2. Gaps que H35 deja explícitos

- La allowlist server-side existe como configuración `HOTEL_DEEPLINK_ALLOWED_HOSTS`/`HOTEL_DEEPLINK_ALLOWED_QUERY_KEYS`, pero la revisión por provider, ruta y afiliación aún debe documentarse antes de activar CTA.
- No debe copiarse una URL arbitraria de provider directamente a `href`, redirect o telemetría.
- Las escrituras ORM y las respuestas API eliminan URLs no aprobadas y parámetros sensibles; la revisión por provider, ruta y afiliación aún debe completarse antes de activar CTA.
- No hay evidencia de validación contra open redirect, SSRF, hosts privados, DNS rebinding o redirects encadenados si se introduce un proxy servidor.
- El disclosure de intermediación, precio variable y afiliación no está cerrado como copy visible ES/EN en la superficie hotelera.
- Retención, exportación, hard-delete y cascadas de búsquedas, tracking, snapshots, eventos y logs siguen pendientes de decisión legal/operativa.
- El ownership legacy basado solo en `hotel_id` no es suficiente para eventos, snapshots, deep links privados o alertas.
- El nombre/dirección/precio recibido del provider no se convierte automáticamente en contenido verificado por Viru.

**Estado de lanzamiento:** H35 no declara “legal listo”, “deeplinks seguros” ni “afiliación aprobada” hasta superar sus gates.

---

## 3. Clasificación de datos y minimización

### 3.1. Inventario mínimo por superficie

| Dato | Ejemplo | Sensibilidad/uso | Regla |
|---|---|---|---|
| Identidad de cuenta | `user_id` interno | dato de ownership | solo backend/autorización; no en URL pública ni copy |
| Intención de búsqueda | destino, fechas, ocupación, filtros | potencialmente personal | enviar solo lo necesario al provider; no mezclar con identidad |
| Fechas de estancia | `check_in`, `check_out` | contexto de viaje | son fechas civiles; no necesitan timezone de usuario para la semántica |
| Ocupación | habitaciones, adultos, niños/edades | contexto de oferta | enviar únicamente si el provider lo necesita; no registrar edades en logs |
| Oferta | habitación, régimen, cancelación, moneda, precio | dato de comparación | guardar con procedencia y condiciones; no presentarlo como garantía |
| Tracking | fingerprint, target opcional, estado | privado por usuario | ownership estricto y lifecycle H29 |
| Snapshot | importe, `observed_at`, provider, estado | histórico potencialmente privado | retención separada; excluir errores no elegibles del precio |
| Regla/evento | threshold, baseline, transición | señal privada | nunca resolver por `hotel_id` solamente |
| Deeplink | URL partner | dato externo potencialmente sensible | validar, sanitizar y no exponer secretos; guardar referencia segura cuando sea posible |
| Telemetría | acción, estado, correlation ID | analítica/operación | sin URL completa, query sensible, email, token o payload bruto |
| Geocoding | consulta de destino/coordenadas | dato de localización contextual | minimización, límites, cache y términos del servicio |

### 3.2. Principios obligatorios

- No enviar email, `user_id`, target price, regla, tracking ID privado, edades de menores ni contenido de inbox al provider de hoteles salvo contrato explícito y necesidad demostrada.
- No enviar coordenadas de precisión innecesaria si un destino normalizado basta para la búsqueda.
- No poner secretos, API keys, tokens, headers, correlation payloads o identificadores privados en URLs del frontend.
- No usar datos de un tracking para enriquecer el resultado de otro usuario.
- La analítica registra la decisión y el estado, no el payload completo de provider.
- Las excepciones requieren owner, motivo, duración, base legal/contractual y evidencia de redaction.

---

## 4. Ownership, privacidad y lifecycle

### 4.1. Regla de autorización

Toda lectura o mutación de una superficie privada debe autorizarse con la identidad de cuenta y el recurso privado relacionado:

```text
current_user
  → tracked_offer / rule / snapshot / event / inbox item
  → hotel + stay + offer context
```

`hotel_id` identifica una propiedad pública; **no identifica ownership**. Un evento, snapshot, tracking o deep link privado no puede resolverse únicamente mediante `hotel_id`.

El backend debe:

- filtrar por `user_id` desde la consulta, no después de traer datos de todas las cuentas;
- devolver un resultado indistinguible entre “no existe” y “no tienes permiso” cuando el endpoint pueda confirmar la existencia de otro usuario;
- reautorizar al abrir un deep link interno, aunque el enlace contenga un ID válido;
- no incluir IDs privados en URLs compartibles, snippets, referers o eventos analíticos;
- probar aislamiento con dos usuarios y con recursos borrados/archivados.

### 4.2. Estados de lifecycle

H35 se apoya en H29 y no inventa una retención paralela. Cada recurso debe declarar:

- activo/visible;
- pausado o silenciado;
- expirado por fecha o provider;
- archivado;
- borrado lógico, si se necesita auditoría;
- borrado duro y cascadas;
- exportación o acceso del usuario cuando aplique.

El borrado de un tracking debe especificar qué sucede con sus reglas, eventos, snapshots derivados, caches privadas y deeplink metadata. Los logs de seguridad/operación pueden tener una retención separada y minimizada, aprobada por Legal/Security; no se conservan como copia del contenido de usuario.

La política final debe identificar responsable del tratamiento, base legal por finalidad, solicitudes de acceso/exportación/rectificación/supresión, revocación, transferencias internacionales y tratamiento de menores. H35 no fija una jurisdicción única ni sustituye la revisión Legal.

### 4.3. Retención como decisión aprobable

| Objeto | Política requerida antes de producción | No permitido mientras esté abierto |
|---|---|---|
| Búsqueda efímera | TTL corto o no persistencia; definición por producto/legal | guardar indefinidamente por defecto |
| Favorito | lifecycle de cuenta y borrado | prometer alertas o histórico sin tracking |
| Tracking | activo hasta pausa/expiración/borrado; límite documentado | tracking “eterno” sin control del usuario |
| Snapshot elegible | histórico H11/H24 + límites hot/warm/cold | conservar PII innecesaria junto al precio |
| Evento/inbox | retención de lectura/no lectura y cascada H27/H29 | mostrar eventos después de perder ownership |
| Logs/telemetría | retención operativa mínima y redaction | URL completa, token o payload bruto |
| Geocoder/provider cache | TTL, base contractual y borrado definido | cache indefinida con coordenadas de precisión |

Los números concretos de días/meses no se fijan en H35 hasta recibir decisión de Legal, contratos de provider y política operativa. H11/H29 deben incorporar esos valores y sus migraciones.

---

## 5. Disclosure y copy de confianza

### 5.1. Disclosure mínimo antes del CTA externo

El CTA que abre un partner debe comunicar, en el idioma activo y cerca de la acción:

- Viru compara y redirige; la reserva se completa fuera de Viru.
- El precio y la disponibilidad final pueden cambiar al abrir el partner.
- Impuestos, fees, moneda, habitación, cancelación y ocupación pueden modificar el total.
- Si existe afiliación o comisión, debe indicarse de forma clara y no escondida en una página genérica.
- El enlace pertenece al partner aprobado y no es una confirmación de reserva.

Copy orientativo, sujeto a revisión Legal:

> “Ver oferta en el partner. La reserva y el precio final se confirman fuera de Viru y pueden cambiar. Viru podría recibir una comisión si completas la reserva desde este enlace.”

No mostrar “mejor precio garantizado”, “disponible ahora”, “reserva segura”, “precio final” o “ahorro garantizado” salvo que el contrato y la evidencia soporten literalmente la afirmación.

### 5.2. Datos externos y claims

Nombres, fotos, direcciones, ratings, políticas y precios del provider deben etiquetarse según su procedencia. Viru no debe afirmar que:

- ha verificado personalmente una dirección o condición que solo recibió del provider;
- el menor precio observado es universal o definitivo;
- una habitación es equivalente si faltan condiciones comparables;
- un hotel acepta una reserva solo porque existe un deeplink;
- un dato stale o fixture es live.

H34 gobierna la traducción del copy de producto. Los datos externos tienen una allowlist de contenido y no se “traducen” inventando condiciones.

---

## 6. Deeplinks: contrato seguro

### 6.1. Separación de conceptos

Un deeplink es una salida de navegación, no una prueba de:

- precio final;
- disponibilidad actual;
- identidad de reserva;
- autorización del usuario;
- afiliación aprobada.

El modelo V2 recomendado separa:

```text
PartnerLink {
  provider
  canonical_url_or_reference
  approved_host
  approved_path_policy
  allowed_params
  expires_at / validity
  disclosure_key
  attribution_metadata_without_secrets
}
```

La implementación V1 puede conservar el string nullable como bridge, pero no debe presentarlo como validado por defecto.

### 6.2. Allowlist obligatoria

Antes de renderizar un CTA o ejecutar una navegación externa:

1. aceptar únicamente `https` salvo excepción revisada;
2. comparar hostname normalizado contra hosts aprobados por provider;
3. validar puerto, path y parámetros permitidos;
4. eliminar fragmentos/query params no necesarios;
5. rechazar `javascript:`, `data:`, `file:`, esquemas personalizados, credenciales embebidas y hosts/IPs no aprobados;
6. no confiar solo en un `startsWith()` del string;
7. clasificar el enlace como **público de provider** o **privado asociado a tracking**; el segundo requiere autorización y nunca se comparte como URL externa reutilizable;
8. seguir cero redirects por defecto; si el contrato permite saltos, revalidar cada `Location` contra la misma allowlist y limitar cantidad, host y esquema;
9. si existe redirect/proxy backend, separar navegación de fetch y bloquear localhost, loopback, rangos privados/link-local, metadata endpoints y DNS rebinding;
10. registrar únicamente provider, decisión allow/deny y motivo redacted;
11. aplicar `Referrer-Policy: no-referrer` o una política equivalente para no filtrar contexto y usar `noopener,noreferrer` al abrir una nueva ventana;
12. mostrar disclosure antes de la salida.

La validación debe ser server-side cuando el servidor construya, redirija o haga fetch del destino, y client-side como defensa adicional para el CTA. Nunca se debe seguir una URL recibida del provider para “comprobarla” sin un contrato de SSRF.

### 6.3. Parámetros y atribución

- La atribución solo puede usar parámetros permitidos por el contrato del partner.
- No incluir `user_id`, email, target price, tracking ID, rule ID, access token o contenido de búsqueda privada en la URL externa.
- Si se necesita medir el click, usar un identificador opaco no reversible, con TTL y redaction, o una métrica server-side sin transportar datos privados.
- API keys y credenciales deben viajar por headers/secret manager según el contrato del provider, nunca en un deeplink público.
- No persistir la URL completa si basta con `provider + reference + policy version`.
- Un enlace público de provider no debe heredar IDs privados del tracking; un enlace privado asociado a tracking debe conservar su autorización y expiración, y no puede degradarse silenciosamente a un href público.

### 6.4. Retorno y errores

El retorno desde un partner no debe asumir que la reserva se completó. Si se ofrece retorno a Viru:

- usar un estado explícito y no un `success` inferido por navegación;
- no aceptar parámetros privados sin validar firma/TTL;
- no revelar el tracking o evento de otra cuenta;
- distinguir `invalid_link`, `partner_unavailable`, `expired`, `not_allowed` y `not_found`;
- no convertir un fallo del partner en “sold out” o “reserva confirmada”.

---

## 7. Providers, geocoder y observabilidad

### 7.1. RUM hotelero opt-in

La primera instrumentación RUM de `/hoteles` es first-party, mínima y apagada por defecto. Solo se activa cuando `viru_hotels_rum_consent=granted` está presente en almacenamiento local; no se infiere consentimiento por crear tracking, iniciar sesión o abrir la página. El payload `hotel_rum_vitals` no contiene URL, query, email, token, user-agent crudo, IDs privados ni valores exactos: usa únicamente claves y buckets allowlisted, y el backend rechaza metadata extra o buckets incompatibles con la métrica. La evidencia lab intercepta el canal y no persiste telemetría de QA.

Este mecanismo no fija por sí solo la base legal definitiva ni sustituye una UI/política de consentimiento aprobada. Antes de activarlo para tráfico real deben definirse owner, finalidad, revocación, retención, segmentación permitida y revisión Legal; hasta entonces el field/RUM se considera no concluyente.

Antes de activar cualquier provider o geocoder externo, el owner debe adjuntar:

- términos de uso, privacidad, retención y atribución;
- regiones y subprocesadores relevantes;
- autenticación, rate limits, coste y política de salida;
- campos enviados y recibidos, con minimización;
- política de URLs y deeplinks;
- pruebas de redaction de request, response, exception y trace;
- kill switch y fallback `unavailable`/`fixture-only` honesto.

La observabilidad debe poder responder qué ocurrió sin almacenar el secreto:

```text
provider + operation + run_id + status + latency + decision + redacted_error
```

Nunca se registran URL completas con query params sensibles, headers de autorización, cookies, email, target price o payload bruto de provider. El `run_id` no debe ser reutilizable como autorización.

---

## 8. Priorización de remediación

### P0 — bloqueantes de seguridad/legal

- Allowlist verificable de deeplinks y rechazo de esquemas/hosts no permitidos.
- Pruebas de open redirect y SSRF si existe redirect, proxy o fetch server-side.
- Redaction de API keys, tokens, cookies, URLs completas y payloads sensibles.
- Ownership estricto de tracking, reglas, snapshots, eventos e inbox; cero resolución privada por `hotel_id` solamente.
- Disclosure visible ES/EN antes del CTA externo, revisado por Legal/Producto.
- Consentimiento por canal separado de crear tracking; no email/push implícito.
- Cada opt-in debe tener default opt-out por canal, finalidad, versión/fecha, prueba auditable, revocación efectiva y comportamiento verificable tras revocar.
- Retención y borrado aprobados antes de persistir datos nuevos en producción.

### P1 — cierre de confianza y privacidad

- Modelo `PartnerLink` o bridge validado con provider/path/params/policy version.
- Pruebas de dos usuarios, IDOR, deep link interno, recurso borrado y expirado.
- Inventario de campos enviado a Makcorps/geocoder/otros providers.
- Política de atribución, comisión y copy de precio variable.
- Eliminación de IDs privados de URL, referer y telemetría.
- Estados de enlace inválido, provider degradado, stale y not-found con copy no engañoso.

### P2 — endurecimiento y operación

- Dashboard de decisiones allow/deny y métricas redacted.
- Revisión periódica de hosts, rutas, términos y expiración.
- Exportación/soporte de solicitudes de privacidad según política aprobada.
- Simulacros de revocación, borrado y rotación de credenciales.
- Documentación de subprocesadores y cambios de provider.

---

## 9. Evidencia y gates de cierre

H35 solo puede pasar de “contrato” a “implementada” cuando exista evidencia versionada de todos estos gates:

### Gate L — Legal/producto

- Copy ES/EN de disclosure aprobado.
- Atribución/afiliación y claims de precio aprobados para cada provider activo.
- Política de privacidad, consentimiento y retención enlazada desde la superficie adecuada.
- Términos del provider y geocoder archivados con fecha/revisión.

### Gate S — Security/backend

- Tests de allowlist para hosts, esquemas, puertos, paths, parámetros, credenciales embebidas y redirects, incluyendo revalidación de cada salto `Location` cuando exista.
- Tests SSRF si el backend resuelve, proxyfica o sigue URLs.
- Tests de redaction en logs, traces, errores y métricas.
- Tests de aislamiento con dos usuarios para watchlist, tracking, rule, snapshot, event e inbox.
- Revisión de URL state y telemetría sin identificadores privados.

### Gate D — Datos/lifecycle

- Matriz de campos enviados a cada provider/geocoder.
- Retención y cascadas de H11/H29/H28 implementadas o bloqueadas con razón explícita.
- Borrado/pausa/expiración y cache privada verificados.
- Datos legacy y eventos sin ownership determinista aislados, migrados o excluidos.

### Gate Q — Frontend/browser

- Disclosure visible antes de abrir partner en dark/light, ES/EN, móvil y teclado.
- CTA externo con estado de enlace no aprobado/expirado/no disponible.
- No existen parámetros privados en la URL externa ni en el referrer de la navegación; la salida usa `Referrer-Policy` y `noopener,noreferrer` cuando corresponde.
- Navegación a partner no se presenta como reserva completada.
- Errores de enlace mantienen contexto de búsqueda y no filtran datos.

### Gate O — Operación

- Kill switch de provider/deeplink.
- Rotación de credenciales sin tocar URLs públicas.
- Alertas para aumento de deny, redaction failure, redirect inesperado y errores de provider.
- Runbook de incidente, revocación y comunicación al usuario.

**Criterio final:** cero bloqueantes P0, todos los gates L/S/D/Q/O con evidencia, revisión legal explícita y no quedan claims públicos que excedan los datos o términos aprobados.

---

## 10. Claims que H35 no autoriza

Mientras H35 no tenga los gates cerrados, no se puede afirmar que:

- los deeplinks hoteleros son seguros o allowlisted;
- el precio mostrado es final o garantizado;
- la disponibilidad está confirmada por Viru;
- existe afiliación, comisión o atribución activa para un provider no aprobado;
- el tracking implica una reserva o disponibilidad;
- los datos se borran en un plazo concreto no aprobado;
- Viru ofrece cumplimiento legal global;
- los errores de provider son equivalentes a falta de habitaciones.

H35 sí autoriza como contrato la dirección de remediación: comparar con transparencia, minimizar datos, aislar ownership, validar salidas externas y obtener evidencia antes de habilitar la promesa pública.
