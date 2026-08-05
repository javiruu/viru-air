# H50 — Monetización, afiliación y atribución hotelera responsable

**Estado:** COMPLETA como contrato de negocio/confianza/operación; partner aprobado, programa de afiliación, implementación de deeplinks, consentimiento, ledger y reconciliación pendientes  
**Fecha:** 2026-08-05  
**Área:** negocio / producto / backend / frontend / legal / privacidad / seguridad / analítica / operación  
**Fuente de verdad:** sí para la política de monetización, afiliación, atribución, disclosure y coste de `/hoteles`  
**Fase del roadmap:** H50  
**Depende de:** [H04 — métricas y eventos](../../product/hoteles-metrics-events-h04.md), [H08 — onboarding de providers](hoteles-provider-onboarding-h08.md), [H19 — precio total, noches y fees](hoteles-price-total-fees-h19.md), [H28 — delivery y preferencias](hoteles-delivery-retries-preferences-h28.md), [H35 — legal, privacidad y deeplinks](hoteles-legal-privacy-disclosure-deeplinks-h35.md), [H37 — límites y costes](hoteles-benchmark-rate-limits-locks-cost-h37.md), [H38 — seguridad y abuso](hoteles-ownership-secrets-ssrf-abuse-h38.md), [H41 — observabilidad end-to-end](hoteles-observability-e2e-h41.md), [H43 — flags, canary y kill switches](hoteles-flags-canary-killswitch-h43.md), [H45 — release y rollback](hoteles-release-canary-smoke-rollback-h45.md), [H49 — personalización prudente](../frontend/hoteles-personalizacion-prudente-h49.md)  
**Handoff:** [H51 — experimentos con hipótesis y guardrails](../../plans/2026-08-04-hoteles-master-roadmap.md#fase-h51--experimentos-de-producto)

> H50 define cómo puede sostenerse económicamente el tracker sin vender la confianza de la persona. Una comisión nunca es una razón oculta para ordenar un hotel arriba, llamar final a un precio observado o presentar un click como una reserva.

## 1. Decisión de arquitectura y negocio

H50 separa seis objetos y decisiones:

| Objeto | Propósito | Puede cambiar el ranking | Ownership |
|---|---|---:|---|
| **Hotel/provider observation** | dato observado, con precio, condiciones y procedencia | solo según H17/H19 | provider/catálogo; sujeto a contrato |
| **PartnerLink** | salida externa validada hacia un partner | no | provider/policy; puede ser público o contextual privado |
| **AttributionIntent** | registrar un click o referencia permitida | no | sesión/click opaco; minimización |
| **ConversionReport** | conversión reportada por partner, si existe contrato | no | partner + Viru; no equivale a verdad absoluta |
| **CommissionLedgerEntry** | importe/estado comercial reconciliable | no | negocio/finanzas; acceso restringido |
| **DisclosurePolicy** | copy, locale, finalidad y relación comercial | no | producto/legal/versionado |

La monetización se consume después de decidir la utilidad del resultado. No se añade `affiliate_bonus`, comisión, EPC, CPA, margen, partner priority o click-through histórico al cálculo de `price`, `distance`, `stars` ni a un `recommended` de H17/H49 sin una política pública, aprobada y separada.

## 2. Baseline real comprobable

### 2.1. Providers y partners

H08 deja Hotelbeds y LiteAPI como candidatos `candidate_pending_canary`, no como integraciones aprobadas. Booking Demand, Amadeus, Expedia y otros requieren acceso, términos, capacidades y canary propios. Makcorps tiene adapter experimental, riesgo de 429, coste/cuota sin verificar y deeplink/afiliación no aprobados por H07.

Mock es válido para desarrollo, fixtures y QA; no es un partner, no genera comisión ni prueba disponibilidad real. No existe evidencia en el repositorio de un programa hotelero afiliado activo, una cuenta comercial aprobada o una integración de booking/redirect lista para producción.

### 2.2. Deeplinks actuales

`HotelRateOut`/snapshots pueden transportar `deep_link: string | null`. H35 documenta que ese string no es automáticamente seguro: todavía deben demostrarse allowlist de host/path/params, sanitización, `noopener/noreferrer`, `Referrer-Policy`, validación de redirects y disclosure.

H04 define `hotel_partner_clicked` como evento de comportamiento, con `source`, `provenance_kind`, `freshness_bucket` y `disclosure_shown`; el contrato de evento no demuestra que esté instrumentado end-to-end ni que exista conversión downstream.

### 2.3. Métricas y atribución actuales

El repositorio tiene contratos de analítica para clicks, tracking y funnel, pero no demuestra:

- un `AttributionIntent` o click ID hotelero implementado;
- cookies, server-side attribution o consent management específico;
- feed de bookings/stays/conversiones de partner;
- `CommissionLedgerEntry` persistido;
- reconciliación con un ledger del partner;
- payout, refund, clawback o fraude reconciliados;
- revenue reconocido en una cuenta comercial.

Un `hotel_partner_clicked` significa únicamente que Viru intentó abrir un enlace. No significa visita confirmada, booking, stay, comisión ni beneficio neto.

### 2.4. Coste y rollout actuales

H37 exige presupuesto conocido, reserva previa, rate limits, retries, breaker y kill switch; mientras el plan/coste del provider no esté verificado, el presupuesto automático de producción es cero. H45 documenta que el workflow canary genérico imprime mensajes y no demuestra traffic split ni rollback real.

H50 conserva estas restricciones: no activar tráfico comercial, tracking afiliado o widgets monetizados solo porque exista un adapter, un URL o un manifest.

## 3. No objetivos y claims prohibidos

H50 no implementa por sí sola:

- una OTA, booking engine, cobro, cancelación, refund o atención de reservas;
- la selección de Hotelbeds, LiteAPI, Booking.com, Amadeus, Expedia, Makcorps u otro provider;
- una garantía de precio, disponibilidad, reserva, habitación o reembolso;
- un programa afiliado sin términos y aprobación legal/comercial;
- cookies o tracking cross-site por defecto;
- un ranking patrocinado escondido dentro de `recommended`;
- una atribución multi-touch completa sin eventos y consentimientos aprobados;
- un ledger financiero que invente conversiones desde clicks;
- la sustitución de precio comparable por una métrica de margen.

Mientras los gates no estén cerrados, no se puede decir:

- “reserva confirmada”, “precio final garantizado”, “disponible ahora” o “mejor precio” solo por abrir un partner;
- “Viru recibe una comisión” para un provider no aprobado;
- “este partner es recomendado” si la razón es comercial y no está declarada;
- “click convertido” sin confirmación contractual del partner;
- “ingresos”, “payout” o “ROI” a partir de un evento de navegación;
- “sin cookies” si existe otro identificador o transmisión de atribución no documentada.

## 4. Política de ranking e independencia editorial

### 4.1. Reglas no negociables

1. `price`, `distance` y `stars` permanecen objetivos, deterministas y libres de datos comerciales.
2. Los filtros explícitos de la persona siempre tienen prioridad sobre monetización.
3. `recommended` de H17/H49 solo usa features de utilidad aprobadas y explicables.
4. Un partner puede aparecer como acción externa o promoción separada, nunca como bonus oculto.
5. Si una colocación es pagada, patrocinada o priorizada comercialmente, debe etiquetarse adyacente al elemento y quedar fuera del ranking orgánico, o usar una política editorial explícita aprobada.
6. Los datos de comisión, payout, EPC, CPA, margen, click-through y partner tier no entran en features de ranking.
7. Cambiar de usuario no cambia el orden objetivo por tener historial de clicks, tracking o valor comercial.
8. Si falta evidencia comparable, se degrada a estado parcial/unknown; no se eleva por disponibilidad de deeplink.

### 4.2. Revisión técnica

El código de ranking debe poder auditarse para demostrar que no recibe:

```text
affiliate_bonus
commission_rate
partner_margin
payout_status
conversion_value
commercial_priority
```

Una revisión de esquema también debe impedir que campos comerciales se cuelen en el envelope de ranking por un spread genérico. Si el backend devuelve `ranking_version`, `features` y `explanation`, las features deben ser allowlisted por H17/H49.

### 4.3. Promoción separada

Si negocio necesita una promoción:

- se renderiza en slot separado del resultado orgánico;
- tiene etiqueta visible, por ejemplo “Patrocinado” o copy aprobado equivalente;
- no altera el sort ni desplaza silenciosamente un resultado elegible;
- puede ocultarse o desactivarse mediante flag;
- conserva disclosure en ES/EN, dark/light y mobile;
- se mide como promoción, no como éxito orgánico.

## 5. Partner registry y contrato de `PartnerLink`

### 5.1. Registro objetivo

Antes de activar un partner debe existir un registro versionado, con datos mínimos:

```text
PartnerRegistryEntry {
  partner_id: opaque-stable-key
  display_name
  provider_id
  status: candidate | approved_limited | approved_production | paused | revoked
  markets_allowlist
  operations_allowlist: search | redirect | revalidate | booking
  hosts_allowlist
  paths_allowlist
  params_allowlist
  attribution_mode: none | opaque_query | server_side | partner_cookie
  consent_requirement
  disclosure_policy_version
  terms_url
  privacy_url
  refund_policy_url nullable
  cost_policy_version
  request_budget_policy
  owner
  approved_at nullable
  expires_at/review_at
  kill_switch
}
```

No se debe modelar un partner como `provider = string` sin status, capabilities, términos, owner y política de salida. Un registro ausente implica `unavailable`, no aprobación implícita.

### 5.2. Link objetivo

```text
PartnerLink {
  partner_id
  link_id: opaque-short-lived-reference
  canonical_url_or_server_reference
  link_kind: public_provider | contextual_private
  hotel_context: public_catalog_id nullable
  stay_fingerprint: opaque nullable
  allowed_params_version
  attribution_intent_id nullable
  disclosure_key
  created_at
  expires_at nullable
  validation_status: pending | allowed | blocked | expired
}
```

Reglas:

- no guardar la URL completa si basta una referencia server-side;
- nunca incluir `user_id`, email, token, `tracked_offer_id`, `rule_id`, target, snapshot ID privado o payload raw;
- un enlace contextual privado exige auth/ownership y no se convierte en href público reutilizable;
- los hosts, paths, puertos, esquemas y params se validan contra el registry;
- `validation_status=blocked|expired|pending` no genera CTA externa activa;
- un link generado con una configuración antigua debe invalidarse si cambia allowlist, términos o policy version;
- el partner no puede elegir el destino mediante un `returnUrl` arbitrario del cliente.

### 5.3. Redirect seguro

Si Viru usa un redirect interno:

1. acepta solo un `link_id` o token opaco de corta duración, nunca una URL arbitraria;
2. autoriza el recurso contextual privado antes de resolverlo;
3. revalida host, scheme, port, path y params server-side;
4. bloquea localhost, loopback, RFC1918, link-local, metadata endpoints, credenciales embebidas y esquemas no aprobados;
5. limita o prohíbe redirects encadenados; revalida cada `Location` si son necesarios;
6. devuelve estados estables (`invalid_link`, `expired`, `not_allowed`, `partner_unavailable`);
7. aplica `Referrer-Policy: no-referrer` o equivalente y `noopener,noreferrer` al abrir ventana externa;
8. no registra URL completa, query de atribución ni secreto.

El frontend valida como defensa adicional; no sustituye validación server-side cuando hay redirect/proxy/fetch del backend.

## 6. Disclosure, consentimiento y experiencia

### 6.1. Disclosure previo al CTA

Cerca del botón, antes de abandonar Viru, se debe explicar:

- Viru compara y redirige; la reserva ocurre fuera de Viru;
- precio y disponibilidad pueden cambiar;
- impuestos, fees, moneda, habitación, cancelación y ocupación pueden alterar el total;
- el partner controla sus condiciones de reserva, cancelación y reembolso;
- si existe comisión o relación comercial, cuál es la naturaleza relevante;
- el enlace no confirma una reserva.

Copy orientativo sujeto a Legal:

> “Ver oferta en el partner. La reserva, las condiciones y el precio final se confirman fuera de Viru y pueden cambiar. Viru podría recibir una comisión si completas la reserva desde este enlace.”

No ocultar el disclosure en una página general, tooltip inaccesible o texto separado del CTA. Debe existir ES/EN y cubrir desktop, mobile, teclado, zoom y dark/light.

### 6.2. Consentimiento y finalidad

Crear un favorito, tracking o búsqueda guardada no implica consentimiento para:

- cookies de afiliación;
- marketing;
- email/push;
- tracking cross-site;
- perfilado de personalización;
- analítica no esencial.

Cada canal/propósito debe tener:

```text
purpose
lawful_basis/consent_state
version
captured_at
locale
revoked_at nullable
retention_policy
```

Si no hay consentimiento requerido, usar un modo privacy-safe aprobado: click agregado sin cookie, server-side reference de TTL corto, o no atribuir. No crear una cookie “silenciosa” como fallback.

La revocación debe detener usos futuros, invalidar referencias que ya no deban funcionar y no borrar artificialmente una obligación legal/financiera aprobada; cualquier excepción requiere Legal. H28 gobierna canales de delivery; H50 gobierna finalidad comercial y atribución.

### 6.3. Estado después de la salida

Viru no debe asumir booking por una navegación exitosa. Si existe retorno:

- mostrar `partner_returned` o `unknown`, nunca `booking_confirmed` sin evidencia contractual;
- no pedir al usuario datos de tarjeta o reserva como si Viru fuera el merchant;
- enlazar a la política de cancelación/refund del partner cuando aplique;
- permitir informar una discrepancia de precio sin prometer resolución;
- conservar el contexto público mínimo sin reinyectar IDs privados en URL.

## 7. Modelo de atribución privacy-safe

### 7.1. AttributionIntent

Un click elegible puede producir un registro mínimo:

```text
AttributionIntent {
  id: opaque-random-id
  partner_id
  link_id
  surface: card | detail | tracking | inbox | saved_search
  source_context: public_query | authenticated_context
  consent_state
  created_at
  expires_at
  dedupe_key
  status: created | emitted | expired | revoked
}
```

El `dedupe_key` no debe ser un email ni un user ID crudo. Puede usar un identificador interno protegido o una referencia de sesión según la política aprobada. No incluir la query completa, fechas sensibles innecesarias, `tracked_offer_id`, target o snapshot privado en la URL externa.

### 7.2. Eventos allowlisted

Separar los eventos de producto de los eventos financieros:

```text
hotel_partner_link_created
hotel_partner_link_blocked
hotel_partner_disclosure_shown
hotel_partner_clicked
hotel_partner_returned
hotel_partner_conversion_reported
hotel_partner_conversion_rejected
hotel_partner_attribution_expired
hotel_partner_attribution_revoked
hotel_partner_reconciliation_variance
hotel_partner_killswitch_activated
```

`hotel_partner_clicked` solo afirma intento de salida. `hotel_partner_conversion_reported` afirma que un partner envió una señal, no que Viru la haya reconciliado. `hotel_partner_conversion_reconciled` solo se emite tras validación contra el feed/ledger aprobado.

Propiedades permitidas:

- `schema_version`, `partner_id` opaco, `surface`, `link_kind`;
- `disclosure_shown`, `consent_state`, `attribution_mode`;
- `provider_mode`, `freshness_bucket`, `provenance_kind`, `price_semantics`;
- `outcome`, `reason_code`, `latency_bucket`, `market_bucket`;
- `policy_version`, `budget_window`, `cost_source`;
- bucket de resultados, no precio/query completa.

No registrar URL completa, click token, API key, cookie, email, user ID crudo, `tracked_offer_id`, `rule_id`, target, children ages o raw provider payload.

## 8. Conversión, comisión y reconciliación

### 8.1. ConversionReport

Solo aceptar conversiones desde un contrato de partner que defina:

- identificador de partner y versión de feed/API;
- evento (`click`, `booking`, `cancelled`, `stayed`, `refunded`, `reversed`);
- moneda, importe bruto/neto y semántica;
- timestamp y timezone;
- booking/reference ID del partner, guardado con acceso restringido y redaction;
- click/attribution reference opaca;
- estado de validación, dedupe y reversión;
- límites de retención y finalidad.

Un report externo puede ser `received`, `validated`, `rejected`, `reversed` o `reconciled`. No se reconoce revenue por un webhook sin autenticación, firma, schema, dedupe e idempotencia.

### 8.2. CommissionLedgerEntry objetivo

```text
CommissionLedgerEntry {
  id: opaque-finance-id
  partner_id
  source_report_id
  attribution_intent_id nullable
  event_type: pending | approved | reversed | refunded | paid
  gross_amount nullable
  commission_amount nullable
  currency
  reported_at
  eligible_at nullable
  paid_at nullable
  policy_version
  reconciliation_status: pending | matched | variance | rejected
  access_scope: finance_only
}
```

Requisitos:

- separar bruto de comisión y comisión de payout;
- no guardar una tasa inventada cuando el partner solo reporta un importe;
- no exponer ledger financiero en `/hoteles`, inbox, cards o analytics público;
- refunds, cancellations, chargebacks y reversals pueden reducir o anular la comisión;
- no contar una reserva cancelada como éxito neto sin política aprobada;
- todos los importes tienen moneda y fuente.

### 8.3. Reconciliación

Si existe volumen comercial, un job periódico debe comparar feed/API/CSV del partner con los eventos internos:

1. importar con autenticación y checksum/control de versión;
2. validar schema, firma, ventana temporal y partner;
3. deduplicar por referencia externa + evento + versión;
4. enlazar solo por AttributionIntent válido y no revocado, cuando corresponda;
5. clasificar `matched`, `missing_internal`, `missing_partner`, `amount_variance`, `duplicate`, `late`, `reversed`;
6. aplicar tolerancia de moneda/redondeo versionada;
7. generar tarea de revisión financiera para variancias materiales;
8. no modificar ranking ni copy de producto por una variancia;
9. conservar evidencia redacted y retención aprobada.

Sin feed o contrato de reconciliación, H50 puede medir clicks y reportes recibidos, pero no puede declarar comisión neta reconciliada.

## 9. Coste, presupuesto y circuit breakers

### 9.1. Dos presupuestos distintos

No mezclar:

| Presupuesto | Protege | Fuente |
|---|---|---|
| Provider/API | requests, revalidaciones, mapping y coste de datos | H08/H37/contrato provider |
| Monetización/atribución | clicks pagados, CPA, integración, ledger y reconciliación | contrato comercial/finance |

Una API que responde `200` puede consumir coste sin producir un click monetizable. Un click puede generar valor comercial sin autorizar otra llamada provider. Cada unidad se mide por separado.

### 9.2. Reglas de activación

Antes de activar tráfico comercial:

- partner y programa aprobados;
- términos, privacidad, atribución, refund y payout documentados;
- budget diario/mensual y owner;
- rate limit y circuit breaker;
- allowlist de links;
- disclosure y consentimiento;
- métricas de errores, latencia, deny, click y reportes;
- kill switch probado;
- fallback sin monetización y sin copy engañoso.

Defaults de seguridad, como contrato para H43/H45:

```text
HOTEL_MONETIZATION_ENABLED=false
HOTEL_AFFILIATE_<PARTNER>_ENABLED=false
HOTEL_AFFILIATE_<PARTNER>_CANARY_ONLY=true
HOTEL_AFFILIATE_<PARTNER>_DAILY_CLICK_BUDGET=0
HOTEL_AFFILIATE_<PARTNER>_MONTHLY_COST_BUDGET=0
HOTEL_AFFILIATE_<PARTNER>_ATTRIBUTION_MODE=none
HOTEL_AFFILIATE_<PARTNER>_DEEPLINK_ENABLED=false
```

Estos nombres son política futura, no evidencia de que las variables existan actualmente.

### 9.3. Kill switch

El kill switch debe poder:

- desactivar un partner concreto;
- desactivar redirect/deeplink sin apagar discovery;
- desactivar atribución/cookies sin ocultar el resultado orgánico;
- detener imports de conversiones/reconciliación sin borrar históricos;
- volver a `fixture-only`/`unavailable` sin presentar Mock como partner real;
- registrar owner, motivo, hora y versión de configuración.

## 10. Operación, seguridad y privacidad

### 10.1. Secretos y redaction

API keys, partner secrets, webhook signatures y cookies nunca aparecen en:

- URL, href, query pública o clipboard;
- logs de request/response, tracing o error;
- payload de frontend;
- screenshots de QA o fixtures;
- eventos de analítica.

Las excepciones deben sanitizarse antes de llegar al logger. H38 exige probar también access logs/proxies y no solo el logger de aplicación.

### 10.2. Fraud/abuso

Antes de reconocer valor financiero se deben considerar:

- clicks duplicados o automatizados;
- self-referral y tráfico interno;
- referencias expiradas o revocadas;
- conversiones imposibles temporalmente;
- partner report duplicado;
- cancelaciones, refunds y chargebacks;
- abuso de endpoints de redirect para enumerar IDs o generar coste.

No crear perfiles invasivos para detectar fraude sin base legal, minimización y owner. Clasificar anomalía y retener solo lo necesario.

### 10.3. Revisión de provider

Cada partner activo tiene revisión periódica de:

- host/path/params y redirects;
- términos, privacidad, comisión, payout y refund;
- mercados/monedas y capacidades;
- coste, latencia, deny/error rate;
- disclosure y traducciones;
- incidentes, variancias y solicitudes de borrado;
- fecha de expiración/reaprobación.

Un contrato caducado o un host cambiado bloquea deeplinks y atribución hasta revisión.

## 11. Tests y evidencia

### Unit/contract

- ranking objetivo es idéntico con y sin datos comerciales;
- `recommended` no recibe commission/margin/partner tier como feature;
- link builder solo genera hosts, paths, schemes y params allowlisted;
- URLs con credentials, tokens, userinfo, localhost, IP privada, `javascript:` o params desconocidos se bloquean;
- link pendiente/expirado/revocado no produce CTA activa;
- contextual private link exige ownership y no filtra IDs;
- disclosure required aparece junto a toda CTA monetizada;
- click no se interpreta como booking/conversion/revenue;
- no se crea cookie o atribución antes del consentimiento requerido;
- AttributionIntent es opaco, TTL, deduplicable y redacted;
- report firmado/schema válido se acepta; replay, duplicado, partner incorrecto o firma inválida se rechaza;
- refunds/reversals reducen estado financiero sin alterar ranking;
- ledger separa gross/commission/currency y es finance-only;
- reconciliación clasifica variancias y es idempotente;
- budget cero no hace requests/click attribution comercial;
- kill switch bloquea partner sin borrar datos de producto;
- logs, traces, errors y analytics no contienen secretos/PII/URLs completas.

### Integration/browser

1. abrir `/hoteles` con Mock/provider off y comprobar que no hay CTA monetizada engañosa;
2. abrir una oferta aprobada en una fixture de partner y verificar disclosure antes de salir;
3. comprobar `noopener,noreferrer`, referrer policy y URL externa minimizada;
4. denegar consentimiento y verificar fallback privacy-safe/no attribution;
5. aceptar consentimiento, abrir enlace y comprobar solo el evento allowlisted;
6. repetir click y back/forward: dedupe sin conversiones duplicadas;
7. simular link expirado, host no permitido, redirect y partner paused;
8. User A/B: no intercambiar links contextuales, tracking IDs ni ledger;
9. recibir report de click/booking/cancel/refund y reconciliar fixture;
10. activar kill switch y verificar que discovery/ranking siguen intactos;
11. repetir ES/EN, dark/light, mobile, keyboard, zoom y screen reader;
12. comprobar provider API budget separado del attribution budget.

### Gate H50

H50 podrá considerarse implementada cuando:

1. exista un partner/programa aprobado o la política permanezca correctamente en `candidate/blocked`;
2. ranking, filtros y `recommended` sean independientes de comisión, margen y payout;
3. cada deeplink activo tenga registry, allowlist, policy version, TTL y disclosure;
4. consentimientos y finalidades de atribución estén separados de favoritos, tracking, alertas y delivery;
5. clicks, conversiones, bookings, stays, refunds y comisiones tengan estados distintos;
6. attribution intent sea privacy-safe, opaco, deduplicable y revocable;
7. ledger y reconciliación sean idempotentes, finance-only y capaces de clasificar variancias;
8. provider/API budget y monetization budget tengan límites y circuit breakers separados;
9. kill switch detenga partner/atribución sin romper discovery ni borrar históricos;
10. URL, logs, traces, analytics y errores no filtren PII, secretos, IDs privados ni payloads;
11. disclosure, precio observado/final, refund y partner ownership estén aprobados y cubiertos en ES/EN/a11y/browser;
12. canary, rollback, coste, latencia, soporte y runbook tengan evidencia reproducible;
13. H49 conserva ranking personalizado explicable sin bonus comercial;
14. H51 puede experimentar solo con hipótesis y guardrails, no optimizar revenue ocultando confianza.

**Resultado contractual:** H50 queda definida como la frontera entre el producto hotelero útil y su sostenibilidad comercial. El repositorio documenta eventos, disclosure, provider candidates, limits y seguridad, pero no demuestra todavía un partner afiliado aprobado, deeplinks hoteleros allowlisted, consentimiento específico, conversion feed, ledger financiero ni reconciliación. La implementación y el lanzamiento permanecen bloqueados hasta cerrar los gates L/S/D/Q/O de H35, H37, H38, H43 y H45.
