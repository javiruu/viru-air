# H52 — Feedback de usuarios y correcciones de confianza

**Estado:** COMPLETA como contrato de producto/soporte/calidad; implementación del flujo hotelero contextual, triage, correcciones, inbox y QA pendientes  
**Fecha:** 2026-08-05  
**Área:** producto / soporte / frontend / backend / datos / seguridad / QA  
**Fuente de verdad:** sí para recoger, clasificar, priorizar, resolver y cerrar feedback relacionado con `/hoteles`  
**Fase del roadmap:** H52  
**Depende de:** H04, H21, H25, H27, H35, H38, H40, H42, H45, H47, H50, H51  
**Relacionado con:** H05 freshness/provenance/confidence, H10 oferta/estancia, H19 precio y fees, H23 tracking desde oferta real, H26 alertas, H28 delivery, H41 observabilidad, H43 flags/kill switches, H53 matching y deduplicación

**Handoff:** [H53 — calidad de catálogo, matching y deduplicación avanzada](../../plans/2026-08-04-hoteles-master-roadmap.md#fase-h53--calidad-de-catálogo-matching-y-deduplicación-avanzada)

> H52 convierte una señal de una persona en una investigación trazable y, cuando procede, en una corrección reversible. No convierte automáticamente una reclamación en un hecho, no modifica ranking por popularidad de quejas y no promete que enviar feedback cambie el precio, el provider o el histórico al instante.

---

## 1. Propósito y decisión de alcance

La confianza de `/hoteles` se rompe cuando la interfaz parece afirmar más de lo que la evidencia permite:

- un precio observado parece ser el precio final, pero no incluye fees o condiciones;
- una habitación, régimen o política de cancelación cambia al abrir el partner;
- un hotel aparece duplicado o unido a otra propiedad;
- una alerta llega tarde, se repite o no explica qué cambió;
- un dato stale, partial o de provider se presenta como live;
- un favorito o tracking pertenece a otra persona o conserva un contexto equivocado;
- un error técnico se presenta como “sin hoteles” o “sin historial”.

H52 define el circuito de confianza:

```text
señal contextual → confirmación mínima → clasificación → triage
→ investigación con evidencia redacted → decisión/contención
→ corrección o explicación → comunicación → cierre auditable
→ aprendizaje agregado y backlog con owner
```

### 1.1. Dentro de H52

- Reportes contextualizados desde resultado, detalle, histórico, tracking, alerta e inbox.
- Feedback de precio, fees, condiciones, identidad, freshness/provenance, disponibilidad, alertas, UX, privacidad y seguridad.
- Separación entre dato incorrecto del provider, normalización de Viru, copy/UI, operación de sweeps/delivery y reporte abusivo.
- Severidad, deduplicación, ownership, estado de caso y decisión de cierre.
- Evidencia mínima, redaction, retención, rate limit y protección contra abuso.
- Acknowledgment al usuario sin prometer resolución o SLA no aprobado.
- Correcciones reversibles, invalidación de snapshots/ofertas afectadas y comunicación de estados.
- Métricas agregadas de tiempo de reconocimiento, triage, resolución, recurrencia y confianza.
- Handoff a catálogo/matching H53, release H45, observabilidad H41, flags H43 y experimentos H51.

### 1.2. Fuera de H52

- No es un sistema de soporte general que sustituya al contrato vigente de `/support/feedback`.
- No es una herramienta de reservas ni una disputa contractual con un partner.
- No decide unilateralmente que un precio del partner sea vinculante.
- No modifica el ranking por volumen de reportes, opiniones o conversiones.
- No transforma feedback libre en entrenamiento, perfilado o personalización automática.
- No expone una consola administrativa ni un endpoint público nuevo hasta definir ownership, auth, auditoría y retención.
- No activa automáticamente un provider alternativo, afiliación, refund o compensación.
- No inventa SLA de soporte: los tiempos se registran y se publican solo cuando producto/support los aprueben.

---

## 2. Baseline real y frontera de lo que no se debe afirmar

### 2.1. Capacidades observables hoy

El repositorio ya contiene piezas reutilizables:

- `backend/app/api/v1/support.py` expone `POST /support/feedback` y persiste `SupportFeedback` con `feedback_type`, `message` y `attachment_url`.
- `frontend/src/app/(private)/soporte/feedback/SoporteFeedbackClient.tsx` permite tipos generales `bug`, `idea` y `general`, texto, URL opcional y confirmación mediante notificación.
- `SoporteContactoClient.tsx` añade validación de longitud, URL y copy de contacto; sigue enviando el mismo feedback general.
- H04 ya define `hotel_feedback_submitted`, eventos de estado, privacidad, dedupe y métricas de confianza como contrato de medición.
- H21 ya exige diferenciar `empty`, `partial`, `stale`, `provider_error`, `error`, `auth_required` y `not_found`, sin convertir estados degradados en ausencia válida.
- H25 ya separa freshness, provenance, confidence, comparabilidad y recomendaciones prudentes.
- H27 ya define inbox privado, ownership estricto, lectura, deep links, estados y eventos de cuarentena.
- H35/H38 ya exigen redaction, allowlists, no fuga de URLs/tokens/payloads, aislamiento por usuario y protección contra abuso.
- H40/H45 ya definen evidencia visual, smoke, canary, rollback y aprobación de release.

### 2.2. Lo que todavía no se demuestra

No existe evidencia suficiente de que el sistema actual tenga:

- formulario contextual específico para una oferta/estancia hotelera;
- taxonomía persistida de incidencias hoteleras más allá de `bug/idea/general`;
- `case_id`, fingerprint de dedupe, severidad, owner, estado o audit trail de resolución;
- enlace seguro y privado entre feedback, hotel, oferta, snapshot, tracking o alerta;
- consola de triage con separación provider/producto/soporte/seguridad;
- acknowledgment persistente en inbox o seguimiento de estado para la persona;
- corrección automática de precio, condición, matching, snapshot, alerta o ranking;
- SLA contractual, on-call, cola operativa o reconciliación de casos;
- métrica verificada de TTA/TTT/TTR, recurrencia o tasa de corrección;
- redaction específica de adjuntos, URL externa y texto libre antes de persistir/mostrar;
- integración de feedback con experimentos H51 sin contaminar el análisis.

Por tanto, `POST /support/feedback` no se presenta como circuito H52 completo. La implementación futura debe evolucionar de forma aditiva y compatible, o crear un contrato separado después de revisión H35/H38.

---

## 3. Taxonomía canónica de feedback

El cliente debe ofrecer categorías comprensibles; el backend debe almacenar códigos estables y allowlisted. El texto libre complementa la categoría, pero no la sustituye.

| Código | Copia de producto | Qué investiga | Evidencia contextual preferida |
|---|---|---|---|
| `price_total_wrong` | El precio total no coincide | suma, noches, moneda o fees | oferta, estancia, currency, price semantics, observed_at |
| `price_unit_wrong` | El precio por noche/total no se entiende o calcula mal | unidad, noches, redondeo | importe observado y cálculo versionado |
| `fees_missing_or_changed` | Faltan cargos o han cambiado las condiciones | tasas, resort fee, limpieza, impuestos, depósito | fee status y condiciones, nunca payload raw |
| `room_or_board_changed` | Habitación o régimen no coincide | room type, board, ocupación | fingerprint de oferta y copy visible |
| `cancellation_changed` | La cancelación no coincide | cancelación, deadline, refundable | código de política y timestamp |
| `availability_changed` | Ya no hay disponibilidad | provider result, observed_at | estado provider, no afirmar causa si no se conoce |
| `hotel_identity_wrong` | El hotel no es el que parece | nombre, dirección, coordenadas, provider ID | identidad normalizada y fuente |
| `duplicate_hotel` | El mismo hotel aparece repetido | matching y aliases | IDs opacos y señales de matching |
| `location_or_map_wrong` | La ubicación o distancia no parece correcta | geodata, radio, landmark | bucket geográfico, no coordenada exacta en analytics |
| `stale_or_provenance_wrong` | La fecha o fuente del dato no es clara | freshness, provider, cache/demo | status, observed_at, provenance |
| `alert_wrong_or_unhelpful` | La alerta no fue útil o llegó mal | regla, baseline, cooldown, delivery | alert event, tracking y razón allowlisted |
| `tracking_context_wrong` | Estoy siguiendo otra estancia/oferta | ownership, fingerprint, versión | tracked offer opaco, no query libre |
| `inbox_or_link_wrong` | El aviso o enlace no lleva al contexto correcto | deep link, lectura, ownership | item opaco, source y estado |
| `accessibility_or_localization` | No puedo entender o usar esta parte | foco, teclado, idioma, fecha, moneda | superficie, locale, device class |
| `privacy_or_security` | Veo datos que no debería ver o un enlace inseguro | ownership, SSRF, redaction, secreto | no pedir secretos; escalar con prioridad |
| `technical_failure` | Algo no funciona | HTTP, frontend, request cancelado, provider | error code/request reference redacted |
| `idea_or_general` | Sugerencia o comentario general | mejora no correctiva | texto mínimo y superficie |

### 3.1. Reglas de clasificación

- La persona puede elegir una categoría visible; el backend valida el código.
- Una incidencia puede tener `primary_kind` y `secondary_kind`, pero el primer release no debe permitir combinaciones libres sin necesidad.
- `privacy_or_security` nunca se mezcla con feedback público, experimento ni analytics de terceros.
- `price_total_wrong` y `fees_missing_or_changed` no prueban por sí solos un error de Viru: el caso debe distinguir precio observado, cálculo propio y precio final externo.
- `availability_changed` no significa `sold_out` si solo falló un provider.
- `duplicate_hotel` y `hotel_identity_wrong` alimentan H53, pero no fusionan registros automáticamente.
- El texto puede contener información sensible; debe limitarse, redacted y excluirse de dashboards y proveedores analíticos.

---

## 4. Contexto y evidencia mínima

### 4.1. Contexto capturable sin PII innecesaria

Un reporte contextual puede incluir, solo cuando la persona lo autorice y el dato exista:

- `surface`: `search`, `result`, `detail`, `history`, `tracking`, `alert`, `inbox`, `support`;
- `locale`, `device_class`, `theme` y `schema_version`;
- código de categoría y severidad sugerida;
- `hotel_ref` opaco, `offer_ref` opaco, `tracking_ref` opaco o `alert_ref` opaco, con ownership validado;
- fingerprint opaco de estancia/oferta, nunca query completa en analytics externo;
- `provider_kind` y `provenance_kind` allowlisted;
- `freshness_bucket`, `observed_at` y estado (`success`, `partial`, `stale`, `error`, etc.);
- `error_code` estable y request reference corto, no stack trace;
- versión de precio/condiciones/copy si está disponible;
- `user_description` acotada y con advertencia de no incluir datos personales.

### 4.2. Prohibido por defecto

- email, nombre, token, contraseña, cookie, IP, authorization header o secreto;
- URL completa de partner, parámetros de atribución, sesión o redirect;
- payload raw de provider, HTML, stack trace o headers;
- coordenadas exactas, dirección privada o edades de menores;
- datos de pago, reserva, documento o conversación externa;
- texto libre enviado a proveedores de analytics, experimentación o afiliación;
- adjuntos sin allowlist, límite, escaneo y política de retención.

### 4.3. Captura de evidencia

1. Mostrar al usuario qué contexto se adjuntará y permitir enviarlo sin ese contexto cuando sea posible.
2. Generar referencias internas opacas y de vida limitada.
3. Tomar un snapshot redacted del estado visible, no de toda la respuesta del provider.
4. Guardar `observed_at` y estado; no reescribir una observación histórica como si fuera actual.
5. Si el contexto ya no pertenece al usuario, devolver `404` genérico o `403` según H27/H38, sin confirmar existencia ajena.
6. Si la incidencia afecta seguridad/privacy, minimizar la evidencia y escalar sin solicitar más datos sensibles.

---

## 5. Ownership: provider, producto, operación o usuario

Una corrección fiable necesita asignar la responsabilidad correcta sin trasladar automáticamente la culpa.

| `responsibility` | Criterio | Owner de investigación | Acción inicial |
|---|---|---|---|
| `provider_observation` | provider devuelve precio/condición/availability distinta | Provider/Backend | congelar claim, marcar observación y revisar contrato |
| `viru_normalization` | adapter, fees, moneda, redondeo o mapping transforma mal | Backend/Producto | contener salida y abrir corrección versionada |
| `catalog_identity` | nombre/ID/geodata/matching incorrectos | Backend/DB | derivar a H53, no fusionar por similitud simple |
| `tracking_or_alert` | fingerprint, baseline, cooldown o evaluación incorrecta | Backend/Producto | suspender alerta afectada y revisar snapshots |
| `delivery_or_inbox` | evento existe pero no se muestra/entrega correctamente | Infra/Support | revisar H27/H28/H41, no duplicar alertas |
| `frontend_copy_or_state` | UI confunde empty/error/stale/fees/CTA | Frontend/UX/QA | abrir bug reproducible y aplicar flag/rollback si procede |
| `privacy_or_security` | ownership, redaction, SSRF o exposición indebida | Security | prioridad crítica, contención y runbook H42 |
| `user_context_or_external_partner` | cambio real después de abrir partner o contexto incompleto | Support/Partner | explicar precio observado vs final, sin prometer compensación |
| `unknown` | evidencia insuficiente | Owner de triage | conservar estado `needs_evidence`, no inventar causa |

### 5.1. Independencias obligatorias

- Feedback no altera el ranking por defecto.
- Un reporte no invalida masivamente snapshots sin una regla aprobada y evidencia reproducible.
- Un partner no puede editar directamente el histórico interno sin contrato y auditoría.
- El owner del caso no puede aprobar su propia corrección crítica sin revisión secundaria.
- Una corrección de catálogo no debe modificar retrospectivamente la evidencia original; debe crear una versión o relación de corrección.
- Un incidente de seguridad prevalece sobre métricas de conversión, experimentos H51 o monetización H50.

---

## 6. Lifecycle idempotente del caso

### 6.1. Estados

```text
received → acknowledged → triaged → investigating
  ├─ needs_evidence → investigating
  ├─ contained → investigating/resolved
  ├─ duplicate → closed
  ├─ invalid_or_abuse → closed
  ├─ not_reproducible → closed
  ├─ provider_pending → investigating
  ├─ corrected → verified → closed
  └─ explained_no_change → closed
```

Significado:

- `received`: aceptado por el endpoint; no implica que sea cierto.
- `acknowledged`: se confirmó recepción con una referencia segura.
- `triaged`: categoría, severidad y owner asignados.
- `investigating`: evidencia suficiente para reproducir o pedir contexto mínimo.
- `needs_evidence`: falta un dato no sensible; no pedir secretos o capturas indiscriminadas.
- `contained`: se limitó el impacto mediante flag, suppressión, quarantine, rollback o pausa.
- `provider_pending`: depende de una fuente externa; no presentar como resolución.
- `corrected`: se aplicó cambio versionado y reversible.
- `verified`: QA/owner confirmó que la corrección no rompe estados vecinos.
- `explained_no_change`: no se modifica el dato porque la evidencia muestra una diferencia legítima o externa.
- `duplicate`: vinculado a un caso canónico sin perder la señal individual.
- `invalid_or_abuse`: spam, manipulación o contenido no válido; no usarlo para silenciar una crítica legítima.
- `closed`: cierre con razón, actor, timestamp y evidencia redacted.

### 6.2. Idempotencia y dedupe

- El submit debe aceptar una idempotency key efímera por operación y usuario autenticado.
- Reintentar la misma operación no crea casos duplicados ni envía múltiples acknowledgments.
- El fingerprint de dedupe puede combinar categoría, contexto opaco, ventana temporal y hash redacted del mensaje; nunca email o URL completa.
- Deduplicar no debe ocultar conteo de personas afectadas: mantener `reported_count` agregado y referencias individuales con ownership.
- Una alerta/price issue repetida después de una nueva observación no es automáticamente duplicada: comparar `observed_at`, versión de oferta y estado.
- Las transiciones de estado deben ser monotónicas salvo reapertura explícita y auditada.

### 6.3. Comunicación al usuario

- Acknowledgment: “Hemos recibido el aviso” + referencia corta + qué se revisará.
- Mientras se investiga: explicar que el precio/condición puede cambiar; no afirmar que el caso está confirmado.
- Corrección: indicar qué superficie y versión se corrigieron, sin revelar datos internos ni otro usuario.
- No reproducible/externo: explicar la diferencia entre precio observado y precio del partner con copy H19/H35.
- Seguridad/privacy: comunicación mínima; no incluir detalles que ayuden a explotar el fallo.
- No enviar email/push automáticamente hasta que H28 y preferencias lo permitan; inbox privado H27 puede ser el canal first-party si está habilitado.

Los textos deben tener ES/EN, pluralización y fechas/monedas locale-aware. Las notificaciones transitorias no sustituyen un estado persistente cuando el caso tenga seguimiento.

---

## 7. Severidad, triage y contención

La severidad describe impacto y riesgo, no enfado ni volumen.

| Severidad | Criterio | Primera respuesta operativa |
|---|---|---|
| `P0` | exposición de datos, takeover, SSRF, secreto, ownership roto o claim público peligrosamente falso | contener/kill switch/rollback y Security; no esperar volumen |
| `P1` | precio/condición masivamente incorrectos, tracking cruzado, alertas duplicadas a gran escala o provider etiquetado como live sin evidencia | pausar superficie/claim afectado, abrir incidente H42/H45 |
| `P2` | error reproducible que afecta una cohorte/mercado, matching duplicado, historial o alerta no fiable | owner de producto/engineering y backlog priorizado |
| `P3` | problema localizado de copy, UX, accesibilidad, i18n o sugerencia sin riesgo material | backlog con owner y versión objetivo |
| `P4` | idea, preferencia o feedback no accionable | agrupar para investigación, sin prometer trabajo |

### 7.1. Reglas de contención

- P0/P1 no se resuelven solo con una respuesta de soporte.
- Si no se puede garantizar la veracidad de un precio/condición, se degrada a `unknown`, `partial`, `stale` o `unavailable` según H21/H25.
- Una alerta afectada puede pausarse sin borrar tracking ni histórico.
- Un hotel/matching dudoso se puede poner en cuarentena para nuevas asociaciones; no borrar la evidencia fuente.
- Un experimento H51 se pausa si el guardrail de confianza o privacidad falla, aunque mejore conversión.
- La contención debe registrar actor, motivo, scope, flag/versión y plan de salida.

---

## 8. Correcciones de confianza

### 8.1. Tipos de corrección

| Corrección | Ejemplo | Reversible | Requiere evidencia |
|---|---|---:|---:|
| `copy_or_disclosure` | aclarar precio observado o fee desconocida | sí | screenshot/estado y revisión H35 |
| `state_mapping` | no mostrar error como empty | sí | reproducción y test |
| `provider_adapter` | mapear moneda/fee/room correctamente | sí | fixture/contract test |
| `catalog_mapping` | corregir alias/ID/geodata | sí | señales múltiples y H53 |
| `snapshot_quarantine` | excluir observación incompatible del cálculo futuro | sí | motivo, versión, ownership |
| `tracking_repair` | corregir contexto sin mutar identidad histórica | sí | fingerprint y migración |
| `alert_suppression` | detener regla/duplicado mientras se investiga | sí | evento/threshold y rollback |
| `inbox_deeplink` | reparar contexto o retirar link inseguro | sí | test ownership y H27/H35 |
| `release_rollback` | volver a versión segura | sí | gate H45/H43 |

### 8.2. Principios de corrección

1. Conservar el hecho original y añadir la decisión de corrección; no reescribir historia silenciosamente.
2. Versionar reglas, mappings, copy y policy que cambien interpretación.
3. Invalidar solo el scope probado: oferta, provider, mercado, versión o superficie.
4. Recalcular agregados de forma idempotente y marcar la versión usada.
5. No enviar una bajada o subida artificial como alerta al corregir datos.
6. Revalidar tracking y alertas vinculados antes de reactivarlos.
7. Añadir regresión para el caso y un caso vecino sano.
8. Hacer dry-run cuando la corrección afecte más de un usuario, mercado o proveedor.
9. Documentar si la corrección cambia solo copy, la lectura futura o también agregados derivados.
10. Mantener una vía de rollback y un owner explícito.

### 8.3. Relación con H53

`duplicate_hotel`, `hotel_identity_wrong`, aliases, provider IDs y geodata pasan a H53 con:

- referencias opacas y señales redacted;
- propuesta de merge/split separada de la decisión final;
- score/regla de matching versionado;
- impacto estimado en favoritos, tracking, snapshots, alertas e inbox;
- rollback y casos de falsos merges;
- prohibición de fusionar únicamente por similitud textual.

---

## 9. Privacidad, seguridad y abuso

### 9.1. Protección de datos

- Auth y ownership se validan por la entidad contextual, no por `hotel_id` aislado.
- Las respuestas de caso usan referencias opacas; `404` genérico no confirma objetos ajenos.
- El texto libre se cifra/retiene según la política vigente antes de ampliar el modelo; no se copia a logs.
- Adjuntos y URLs opcionales requieren allowlist, tamaño máximo, validación de protocolo, redaction y decisión de almacenamiento.
- Analytics solo recibe categoría, superficie, estado y buckets; nunca el mensaje, URL completa o payload.
- Los exports de soporte son redacted, con acceso mínimo, motivo y audit log.
- Los casos de seguridad no entran en experimentos, afiliación, personalización ni datasets de entrenamiento por defecto.
- Borrado/retención debe separar el caso necesario para auditoría de la información no necesaria para resolverlo.

### 9.2. Abuso y calidad de señal

- Rate limits por usuario/sesión/IP según política vigente, sin usar IP como identidad de producto.
- Idempotency key y cooldown para evitar doble submit.
- Límites de longitud, categorías y adjuntos; rechazo seguro de esquemas no permitidos.
- Detección de spam/simulación masiva sin descartar automáticamente categorías P0/P1.
- Un usuario puede reportar repetidamente una nueva observación; el sistema debe agrupar sin silenciar.
- No permitir que un reporte cree directamente un redirect, consulta externa, cambio de precio o flag global.
- Las decisiones de `invalid_or_abuse` quedan auditadas y revisables.

### 9.3. Seguridad operativa

- P0/P1 activa runbook H42 y, si procede, flags/kill switches H43.
- No incluir secretos en request IDs, mensajes, screenshots o evidencias.
- SSRF/deeplink/partner se valida antes de persistir o abrir.
- Un caso no puede cambiar su propio owner/severidad/cierre sin permiso adecuado.
- Las acciones administrativas son auditables y requieren autorización separada de la lectura del caso.

---

## 10. Métricas y backlog

### 10.1. Métricas de feedback

Cada métrica debe tener ventana, denominador, segmento y versión de taxonomía.

- **Feedback rate:** casos enviados / sesiones o superficies elegibles; no interpretar como calidad sin exposición.
- **Context attachment rate:** casos con contexto válido / casos recibidos.
- **Acknowledgment success:** acknowledgments persistidos / submits aceptados.
- **Triage coverage:** casos con categoría, severidad y owner / casos recibidos.
- **Time to acknowledge (TTA):** recepción → acknowledgment.
- **Time to triage (TTT):** recepción → triage.
- **Time to first action (TTFA):** triage → contención, investigación o solicitud mínima de evidencia.
- **Time to resolution (TTR):** triage → corrected/verified/explained/closed; publicar solo con definición aprobada.
- **Correction rate:** casos verificados con corrección / casos investigados, separado por responsabilidad.
- **Reopen rate:** casos reabiertos / casos cerrados.
- **Recurrence rate:** mismo fingerprint o causa reaparece después de corrección.
- **Affected-surface rate:** casos por búsqueda, detalle, tracking, alerta e inbox.
- **Trust guardrail:** feedback de precio/condición, stale mal etiquetado, alertas no útiles y exposición de datos por cohorte.

No hay que inventar objetivos, SLA o umbrales antes de que Producto/Support/Engineering los aprueben. Hasta entonces, las métricas sirven como baseline y señal de regresión.

### 10.2. Backlog accionable

Cada caso confirmado o agrupación debe producir un item con:

- `case_cluster_id` o referencia canónica;
- problema y evidencia redacted;
- responsabilidad probable y owner nominal;
- severidad, alcance y usuarios/superficies afectadas en buckets;
- hipótesis de causa y confianza de la hipótesis;
- acción: investigar, contener, corregir, documentar o no cambiar;
- dependencia H04/H21/H25/H27/H35/H38/H41/H43/H45/H51/H53;
- aceptación y regresión requerida;
- versión/flag de rollout, fecha objetivo si está aprobada y riesgo residual;
- decisión de cierre y enlace a evidencia persistente.

El backlog no debe ordenar únicamente por número de clicks, conversiones, comisión o ingresos. P0/P1, privacidad, veracidad y ownership prevalecen sobre optimización comercial H50/H51.

---

## 11. Integración con inbox, experimentos y monetización

### 11.1. Inbox H27

- Un caso de feedback y una alerta de dominio son objetos distintos.
- Un acknowledgment puede mostrarse en inbox solo si existe ownership, estado persistente y deep link seguro.
- Marcar leído no cierra el caso ni demuestra resolución.
- Un deep link mantiene hotel/estancia/filtros compatibles y no incluye secretos.
- Casos legacy, sin owner o con contexto inválido quedan en cuarentena y no se abren por una ruta privada ambigua.

### 11.2. Experimentos H51

- H52 recibe comentarios clasificados, riesgos residuales y evidencia de confianza, no texto raw ni solo conversión.
- No se cambia una variante porque una persona reportó un problema aislado sin investigar; tampoco se ignora un P0/P1 por significancia estadística.
- Una hipótesis experimental debe declarar cómo recogerá y segmentará feedback sin introducir sesgo de exposición.
- Si una variante aumenta `price_total_wrong`, `stale_or_provenance_wrong`, `privacy_or_security` o `alert_wrong_or_unhelpful`, se evalúa como guardrail; puede bloquear promoción/activar rollback.
- El caso y la decisión experimental deben enlazarse por `experiment_id`/`variant_id` allowlisted, sin texto libre o identidad del usuario.

### 11.3. Monetización H50

- Un partner click no es evidencia de conversión ni de precio correcto.
- Feedback de partner/fees no se usa para mejorar ranking a favor de la comisión.
- Un problema de atribución o deeplink se separa de una incidencia de precio observado.
- Si monetización y confianza entran en conflicto, gana la veracidad, privacidad y seguridad.
- No se activa un partner por recibir feedback positivo ni se desactiva por un caso sin triage; usar evidencia y gates H35/H37/H41/H43/H45.

---

## 12. Tests y evidencia de cierre

### 12.1. Backend y contrato

- categorías desconocidas se rechazan;
- texto vacío, demasiado largo y URL no permitida reciben error seguro;
- submit repetido con idempotency key no duplica caso ni acknowledgment;
- contexto que no pertenece al usuario devuelve respuesta genérica y no filtra existencia;
- `hotel_id` sin oferta/tracking/alerta autorizada no basta para adjuntar contexto privado;
- estados y transiciones inválidas se rechazan;
- dedupe conserva el número agregado de reportes afectados;
- casos P0/P1 no pueden cerrarse sin owner/revisión exigida;
- evidencia y logs no incluyen email, token, URL completa, stack ni payload raw;
- corrección conserva observación original y es reversible;
- snapshot/quarantine no actualiza ranking, tracking o alertas sin policy explícita;
- H53 merge/split es auditable y no se activa por similitud textual única.

### 12.2. Frontend y accesibilidad

- reportar desde resultado/detalle/tracking/alerta/inbox adjunta el contexto correcto y visible;
- enviar sin contexto opcional sigue siendo posible cuando no sea necesario;
- la categoría es etiquetada, traducida y usable con teclado/lector;
- `aria-describedby`, `aria-invalid`, `role=status` y `role=alert` se usan sin duplicar anuncios;
- feedback no bloquea la tarea principal ni borra búsqueda, selección o tracking;
- éxito, error, offline, rate limit y caso duplicado tienen copy ES/EN;
- el estado acknowledged/closed se puede consultar sin confundir leído con resuelto;
- dark/light, móvil, zoom, reduced motion y foco pasan H33/H40;
- ninguna URL de partner o referencia privada aparece en clipboard, analytics o error visible.

### 12.3. Operación y release

- smoke de submit, dedupe, triage, acknowledgment, corrección, rollback y cierre;
- canary con fixture-only y datos redacted antes de provider/live;
- dashboards agregados para TTA/TTT/TTFA/TTR, recurrencia y P0/P1;
- runbook H42 con owner, contención, comunicación y recuperación;
- flags/kill switches H43 probados sin reinicio si el contrato lo exige;
- paquete H45 con logs redacted, trazas, screenshots, decisión y rollback;
- prueba de que fallar feedback/analytics no rompe búsqueda, tracking, alertas ni deeplinks.

### 12.4. Gate H52

H52 puede declararse implementada solo cuando:

1. existe una ruta contextual y una ruta general compatible, con categorías allowlisted;
2. cada caso tiene identidad idempotente, ownership, estado, severidad y owner;
3. el circuito diferencia provider, producto, catálogo, operación, seguridad y contexto externo;
4. existe acknowledgment verificable sin prometer SLA inexistente;
5. las correcciones preservan evidencia original, son reversibles y tienen regresión;
6. privacidad, abuso, redaction y deep links pasan H35/H38/H27;
7. las métricas tienen denominadores y no se usan para ocultar errores;
8. H51 recibe guardrails de confianza y H50 no puede sesgar ranking o cierre;
9. H40/H45 aportan evidencia browser/release y H42 tiene runbook para P0/P1;
10. H53 recibe los casos de identidad/matching con una propuesta auditable y no una fusión automática.

**Estado de cierre documental:** contrato aprobado; la implementación futura debe marcar cada capacidad como `planned`, `implemented` o `verified` y no cambiar este baseline sin nueva evidencia.
