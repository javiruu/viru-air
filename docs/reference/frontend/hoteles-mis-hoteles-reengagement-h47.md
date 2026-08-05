# H47 — Re-engagement y superficie “Mis hoteles”

**Estado:** COMPLETA como contrato de producto/navegación; agregador hotelero, URL state, deep links contextuales, ownership V2, lifecycle visual, eventos y QA browser pendientes  
**Fecha:** 2026-08-05  
**Área:** producto / frontend / backend / inbox / privacidad / i18n / QA  
**Fuente de verdad:** sí para el retorno útil a hoteles guardados, seguimientos y señales accionables  
**Fase del roadmap:** H47  
**Depende de:** [H22 — favorito frente a tracking](../backend/hoteles-favorite-vs-tracking-h22.md), [H23 — tracking desde oferta real](../backend/hoteles-real-offer-tracking-h23.md), [H24 — histórico](../backend/hoteles-price-history-curve-h24.md), [H25 — freshness y acciones](../backend/hoteles-freshness-confidence-actions-h25.md), [H26 — reglas y dedupe](../backend/hoteles-alert-rules-dedupe-h26.md), [H27 — inbox y deep links](../backend/hoteles-private-inbox-deeplinks-h27.md), [H28 — delivery](../backend/hoteles-delivery-retries-preferences-h28.md), [H29 — lifecycle](../backend/hoteles-lifecycle-pause-edit-expire-delete-h29.md), [H40 — browser QA](hoteles-visual-manual-crossbrowser-qa-h40.md), [H45 — release readiness](../backend/hoteles-release-canary-smoke-rollback-h45.md), [H46 — primera victoria](hoteles-primera-victoria-h46.md)  
**Handoff:** [H48 — búsquedas guardadas/compartibles](../../plans/2026-08-04-hoteles-master-roadmap.md#fase-h48--guardar-y-compartir-búsquedas)

> H47 no crea otro dashboard técnico. Convierte el resultado de H46 en un lugar al que la persona pueda volver: primero para actuar sobre seguimientos y señales, después para recuperar hoteles guardados y continuar la búsqueda sin perder contexto.

## 1. Decisión de arquitectura

La superficie canónica de “Mis hoteles” vive dentro de `/hoteles`, no en una ruta paralela obligatoria:

```text
/hoteles
├── búsqueda y resultados
├── estado/filtro de retorno: mis-hoteles
│   ├── seguimientos activos y próximos
│   ├── alertas/señales accionables
│   ├── hoteles guardados
│   └── pasados, stale, expirados o incompletos bajo disclosure
└── detalle contextual / histórico

/notifications
├── bandeja privada de señales
└── reglas de alertas
```

El enlace de navegación de “Mis hoteles” puede llegar en una fase posterior, pero no debe crear una segunda fuente de verdad. `/notifications` sigue siendo el inbox de eventos; `/hoteles` es la superficie de decisión, retorno y gestión contextual.

### 1.1. Qué no se hará en H47

- no se crea una nueva base de datos agregada que duplique watchlist, tracking o alertas;
- no se copia el dashboard de vuelos como si los hoteles tuvieran el mismo modelo;
- no se autoriza una señal privada por `hotel_id` solamente;
- no se presenta un favorito como tracking ni un tracking como disponibilidad garantizada;
- no se interpreta `is_active=true` como sweep diario operativo sin evidencia H09/H45;
- no se convierten eventos de inbox en booking, reserva o precio garantizado;
- no se añaden filtros o personalización opacos antes de H48/H49;
- no se declara una integración de provider nueva.

## 2. Baseline actual comprobable

### 2.1. En `/hoteles`

`frontend/src/app/(private)/hoteles/page.tsx` renderiza `HotelRadarPage`. La página ya carga y muestra, mediante hooks separados:

- `HotelWatchlistPanel` con hoteles guardados, detalle hidratado, error y acción de quitar;
- `HotelTrackedOffersPanel` con seguimientos, precio inicial/actual/objetivo, fechas, histórico expandible y detener;
- `HotelAlertsPanel` con reglas y eventos para el hotel seleccionado;
- selección de hotel, timeline, paridad, hoteles cercanos y comp sets;
- overview counts de resultados, tracking activo y watchlist;
- estado efímero de paneles colapsables en `collapsedPanels`.

`useHotelWatchlist` lista `/hotels/watchlist`, hidrata detalles con `GET /hotels/{id}` y conserva unavailable IDs cuando un detalle falla. `useTrackedOffers` lista `/hotels/tracked-offers`, pero ignora silenciosamente el error de carga porque lo considera secundario. `useHotelAlerts` lista reglas globales y eventos por `hotel_id` seleccionado; no existe todavía una vista global de alertas hoteleras dentro de `/hoteles`.

El resultado es útil para una sesión que ya está en el radar, pero no constituye todavía una superficie de retorno:

| Área | Estado actual | Gap H47 |
|---|---|---|
| agregación | tres paneles independientes | falta una jerarquía común y un estado `mis-hoteles` |
| prioridad | orden de composición favorece resultados y secundarios laterales | debe priorizar tracking activo/señal accionable antes de guardados |
| retorno | selección y paneles viven en React | falta URL state hotelero estable para volver/reanudar |
| freshness | tracking muestra precios y fechas; detalle muestra última captura | falta clasificación visible stale/expired/pending/unavailable por item |
| guardados | listados y se pueden quitar | falta CTA de retorno a búsqueda/detalle y empty state de re-engagement |
| tracking | se puede ver histórico y detener | falta lifecycle visual completo: pausar, reactivar, expirado, archivado |
| alertas | reglas/eventos ligados al hotel seleccionado | falta resumen global y enlace contextual desde una señal |
| ownership | endpoints privados exigen usuario | el inbox hotelero V1 aún tiene fallback por `hotel_id` que H27 bloquea |
| notificaciones | `/notifications` carga inbox común y marca leído | `action_href` hotelero básico no conserva oferta/regla/snapshot explícitos |
| navegación | `/alerts` redirige a `/notifications?view=rules` | falta puente documentado inbox → `/hoteles` → retorno a inbox |
| auth | `/hoteles` está bajo `(private)` | no existe en H47 una política implementada de sesión expirada y reanudación |
| medición | contratos H04/H41/H46/H27 definen eventos posibles | no hay evidencia de instrumentación H47 completa |

### 2.2. Inbox y navegación existentes

La ruta `/notifications` renderiza `SignalsInbox` o `AlertRulesWorkspace` según `view=rules`. La API `/api/v1/notifications` devuelve items autenticados con `source_type`, `source_id`, categoría, estado de lectura y `action_href`. El frontend marca leído individualmente o en bloque.

H27 documenta dos límites que H47 no puede ocultar:

1. la lectura hotelera legacy puede resolver ownership por cualquier `HotelTrackedOffer` del mismo hotel;
2. `hotel_alert_item()` genera `/hoteles?hotel_id=<hotel_id>` sin `tracked_offer_id`, `rule_id`, `snapshot_id` o evento explícito.

H47 adopta H27: la superficie puede prepararse con fixtures y enlaces seguros, pero no se declara privada/contextual completa hasta que el backend revalide ownership por cadena explícita y el frontend consuma el contexto autorizado.

### 2.3. Rutas y modelos que se conservan

- `/hoteles`: búsqueda, detalle contextual y “mis hoteles” objetivo;
- `/notifications`: inbox y reglas;
- `/alerts`: alias compatible hacia reglas;
- `HotelWatchlistItem`: favorito simple;
- `HotelTrackedOffer`: seguimiento privado de estancia/oferta;
- `HotelAlertRule`/`HotelAlertEvent`: reglas y señales, sujetas a H26/H27;
- `action_href`: enlace interno provisional, no autorización;
- `is_active`: bridge técnico, no lifecycle V2 completo.

## 3. Jerarquía de re-engagement

La vista “mis hoteles” no debe mostrar un mosaico de paneles equivalentes. El orden de decisión es:

1. **Seguimientos activos y próximos:** requieren atención, muestran estancia, estado, última observación y acción segura.
2. **Señales/alertas accionables:** cambios autorizados que justifican volver a revisar; mostrar razón, fecha y freshness.
3. **Seguimientos pendientes, parciales o stale:** requieren completar/revalidar antes de presentarse como activos.
4. **Hoteles guardados:** colección de interés, sin promesa de refresh ni alerta.
5. **Pasados, expirados, archivados o sin datos:** bajo sección secundaria con explicación y retención conforme a H29/H35.

Esta prioridad no cambia la semántica de las entidades ni mezcla una alerta con un tracking. Solo decide qué se presenta primero para reactivar una intención útil.

### 3.1. Card resumida de retorno

Cada item visible debe responder en una lectura:

- hotel y ubicación;
- tipo: guardado, seguimiento, alerta o evento;
- fechas/huéspedes si es tracking;
- estado: activo, pendiente, parcial, stale, expirado, no disponible o guardado;
- última observación/captura y provider/procedencia cuando exista;
- una acción primaria contextual;
- acción secundaria de detalle, histórico, editar, pausar, quitar o volver a buscar.

La card no debe mostrar IDs internos ni datos de otra entidad para rellenar huecos.

### 3.2. Acciones primarias

| Estado/superficie | CTA principal | CTA alternativa |
|---|---|---|
| tracking activo y elegible | Revisar seguimiento | Ver histórico / pausar |
| tracking stale | Revisar datos | Revalidar si capability lo permite |
| tracking pendiente | Completar estancia/contexto | Guardar hotel |
| tracking expirado | Ver histórico | Crear nuevo seguimiento |
| alerta autorizada | Revisar cambio | Marcar leída |
| hotel guardado | Ver hotel/buscar fechas | Quitar de guardados |
| detalle no disponible | Volver a resultados | Reintentar solo si está soportado |
| entidad no autorizada/no encontrada | Volver a Mis hoteles | ninguna acción que revele existencia |

“Revisar seguimiento” no equivale a reservar ni a confirmar disponibilidad. El CTA de partner pertenece a H18/H35 y solo aparece con deeplink validado.

## 4. URL state y retorno

### 4.1. Convención objetivo

H47 adopta la convención de H03/H18/H27, sin afirmar que la ruta actual la lea todavía:

```text
/hoteles?panel=mis-hoteles
/hoteles?panel=mis-hoteles&section=tracking
/hoteles?panel=mis-hoteles&section=alerts
/hoteles?panel=mis-hoteles&section=saved
/hoteles?hotel_id=H&panel=detail&source=notifications
/hoteles?hotel_id=H&tracked_offer_id=T&snapshot_id=S&event_id=E&panel=detail&source=notifications
/notifications?view=rules&hotel_id=H&rule_id=R
```

Los IDs privados son referencias de contexto, nunca una autorización. El backend debe revalidar ownership y el frontend debe degradar a `not_found/not_allowed` sin filtrar información.

### 4.2. Reglas de navegación

- entrar en “Mis hoteles” no borra una búsqueda válida; puede usar `router.push` si el usuario espera volver o `replace` para normalizar estado sin crear historial por cada cambio de panel;
- abrir un item desde inbox selecciona el hotel correcto y expande solo el bloque necesario;
- back devuelve al inbox o a la búsqueda original según el origen preservado, sin un `returnUrl` arbitrario;
- refresh de un deep link repite la autorización, no confía en el estado React previo;
- si el hotel existe pero el tracking fue eliminado, abrir detalle permitido del hotel con warning contextual, nunca un panel vacío que parezca un tracking activo;
- si el hotel no existe, el target expiró o no hay ownership, mostrar estado genérico y volver a la superficie segura;
- no serializar targets, thresholds, emails, tokens, respuestas raw de provider ni `user_id`.

## 5. Estados, freshness y lifecycle

H47 consume H21/H25/H29. La lista no puede usar `is_active` como única explicación:

| Estado | Significado | Presentación | Acción |
|---|---|---|---|
| `loading` | se carga el retorno | skeleton estable | esperar |
| `success` | entidad autorizada y usable | card normal | revisar |
| `success_empty` | no hay guardados/seguimientos visibles | empty accionable | explorar hoteles |
| `partial` | solo parte del contexto o fuentes está disponible | warning localizado | revisar/completar |
| `pending_context` | faltan fechas, ocupación u oferta | no activo | completar o guardar |
| `pending_first_observation` | tracking creado pero snapshot inicial pendiente | pendiente explícito | esperar/revisar |
| `active` | elegible según policy real | estado destacado | revisar/pausar |
| `stale` | observación fuera de TTL | atenuado con timestamp | revalidar/revisar |
| `unavailable` | provider/capability no disponible | no afirmar precio actual | volver/reintentar |
| `expired` | checkout/policy terminó | sección pasada | histórico/nuevo tracking |
| `archived` | fuera de activos pero retenido | sección secundaria | restaurar solo si existe |
| `error` | consulta fallida | no convertir en empty | reintentar |
| `auth_required` | sesión ausente/expirada | conservar intención segura | autenticar |
| `not_found/not_allowed` | entidad inexistente/ajena | copy genérico | volver |

Freshness debe ser contextual a la oferta/observación. “Última captura” no prueba que el precio siga disponible. Una alerta histórica puede seguir visible como evento, pero no debe presentarse como precio actual.

## 6. Empty states y progressive disclosure

### Sin guardados ni seguimientos

Mostrar una explicación breve y dos entradas posibles:

- `Explorar hoteles` → `/hoteles` en modo búsqueda;
- `Cargar datos de prueba` solo en entorno/demo y con etiqueta explícita.

### Solo guardados

Explicar que guardar no activa seguimiento y ofrecer completar una búsqueda/estancia desde el hotel seleccionado.

### Solo tracking

Priorizar el seguimiento activo y ocultar detalles secundarios bajo histórico/alertas cuando no sean necesarios para la siguiente decisión.

### Sin alertas

No mostrar “no hay alertas” si la API falló. Si la respuesta es válida y vacía, explicar que se pueden crear desde un tracking elegible o desde el detalle.

### Progressive disclosure

- resumen primero: hotel, tipo, estado, fecha, última señal, CTA;
- condiciones, snapshots, reglas y metadata después de expandir;
- una sola región live para cambios de estado;
- no usar hover como única vía;
- paneles colapsables con `aria-expanded`, `aria-controls`, IDs estables y retorno de foco;
- mobile conserva la prioridad tracking → alertas → guardados sin crear una cuadrícula estrecha.

## 7. Auth, ownership y privacidad

La ruta actual es privada y los endpoints requieren `get_current_user`. H47 no inventa un modo local persistente. Antes de implementar un estado guest/account hay que decidirlo explícitamente:

- si “Mis hoteles” es de cuenta, mostrar que está sincronizado y pedir auth cuando la sesión sea necesaria;
- si existiera un borrador local, etiquetarlo como local y definir migración/limpieza; no mezclarlo silenciosamente con datos de cuenta;
- un logout o expiración debe limpiar o aislar cache privada y conservar únicamente intención de búsqueda no sensible;
- cualquier acción sobre tracking, alertas, histórico o favoritos comprueba ownership server-side;
- un `hotel_id` compartido no autoriza una alerta, snapshot, target o evento privado;
- `action_href`, `hotel_id`, `tracked_offer_id`, `rule_id` y `snapshot_id` no conceden acceso por sí mismos;
- caches, SSR y prefetch deben estar particionados por usuario/no-store para entidades privadas;
- usuario A no puede contar, listar, abrir, marcar leído o borrar datos de usuario B aunque comparta hotel.

H27 identifica que la lectura hotelera legacy tiene un fallback por `hotel_id`; H47 bloquea declarar el re-engagement privado terminado hasta retirarlo o ponerlo en cuarentena con evidencia.

## 8. Inbox/deep links y fallback

### Entrada desde `/notifications`

Una señal hotelera autorizada debe transportar, cuando H27 lo permita:

- clase de deep link;
- hotel;
- tracking/regla/snapshot/evento autorizado;
- estado de freshness y warnings;
- origen `notifications`.

El cliente abre `/hoteles` en la sección mínima necesaria. No debe abrir cinco paneles ni llevar a la persona a repetir la búsqueda si el contexto autorizado ya existe.

### Fallback seguro

| Fallo | Resultado |
|---|---|
| hotel autorizado, tracking válido | detalle + tracking/histórico enfocado |
| hotel autorizado, tracking eliminado | detalle hotelero permitido + warning |
| evento stale | item visible + aviso de fecha; no precio actual |
| provider degradado | histórico/contexto + reintento si soportado |
| ID ajeno | `not_found/not_allowed` genérico |
| entidad no encontrada | Mis hoteles/inbox seguro |
| href externo/no allowlisted | rechazar y registrar reason code |
| sesión expirada | auth y retorno seguro, sin payload privado en URL |

El backend debe autorizar antes de serializar contexto privado y volver a autorizar al abrir. `source=notifications` sirve para UX/telemetría, nunca para seguridad.

## 9. Instrumentación y observabilidad

Los eventos siguientes son un contrato futuro; no existe evidencia de que H47 esté instrumentada hoy:

```text
hotel_my_surface_viewed
hotel_my_surface_loaded
hotel_my_surface_empty
hotel_my_item_opened
hotel_my_tracking_reviewed
hotel_my_alert_reviewed
hotel_my_saved_hotel_opened
hotel_my_item_paused
hotel_my_item_resumed
hotel_my_item_removed
hotel_my_item_revalidated
hotel_my_stale_seen
hotel_my_deeplink_opened
hotel_my_deeplink_fallback
hotel_my_deeplink_rejected
hotel_my_auth_required
hotel_my_return_completed
```

Propiedades permitidas:

- `section`, `item_type`, `state`, `outcome`, `reason_code`;
- `has_tracking`, `has_alert`, `has_snapshot`, `freshness_state`;
- origen `hoteles|notifications`, locale, tema y viewport bucket;
- duración, versión de contrato y fingerprints opacos si están aprobados.

No registrar nombres completos innecesarios, email, user ID crudo, targets, thresholds, tokens, raw provider payloads ni URLs externas completas.

Métricas mínimas antes de usar H47 para crecimiento:

- retorno a `/hoteles` desde inbox;
- tiempo desde apertura hasta primera acción útil;
- proporción de items activos/stale/expired/error;
- apertura de tracking frente a guardado;
- fallback de deep links;
- ownership rechazado y eventos huérfanos;
- errores de carga que no deben contarse como empty;
- reactivación o creación de nuevo tracking después de una estancia expirada.

## 10. Tests y evidencia

### Backend/integración

- lista global no mezcla watchlist, tracking y alertas de usuarios distintos;
- un hotel compartido no cruza snapshots, targets, reglas ni eventos;
- `read`, `read-all`, summary y deep link respetan ownership explícito;
- evento sin owner o solo con `hotel_id` queda fuera del inbox privado;
- entidad eliminada/expirada devuelve fallback seguro;
- `action_href` interno se valida y no permite open redirect;
- respuesta paginada/limitada declara su ventana;
- caches privadas no se reutilizan entre usuarios;
- logout/expiración no deja datos privados en cliente.

### Frontend/contract

- `/hoteles?panel=mis-hoteles` abre la superficie correcta sin borrar búsqueda válida;
- tracking activo aparece antes que guardados;
- alertas accionables aparecen antes de la colección pasiva;
- estados stale/expired/pending/unavailable no aparecen como activos;
- empty states tienen CTA de exploración y no llaman error empty;
- deep link de inbox enfoca el item correcto y vuelve al origen;
- contexto ausente/ajeno degrada genéricamente;
- `community`/`community_trending` no rompe normalización del inbox, siguiendo H27;
- `aria-expanded`/`aria-controls`, foco, teclado, dark/light y ES/EN funcionan.

### Browser QA

- usuario A y B con el mismo `hotel_id` no ven señales cruzadas;
- abrir desde inbox, volver a `/notifications` y refrescar conserva autorización;
- tracking activo, stale, expirado, guardado y error tienen copy distinto;
- mobile 360/390/414/768 y desktop mantienen prioridad y CTAs;
- zoom 200%, teclado, lector de pantalla y reduced motion;
- consola limpia, sin requests duplicadas ni open redirects.

## 11. Gates H47

H47 podrá considerarse implementada cuando:

1. existe una superficie “Mis hoteles” dentro de `/hoteles` sin duplicar la fuente de verdad;
2. tracking activo/próximo, señales accionables y guardados tienen una jerarquía comprensible;
3. cada item muestra estado, freshness, contexto y siguiente acción sin claims engañosos;
4. stale, expired, pending, unavailable, auth y error no se convierten en una lista vacía o tracking activo falso;
5. favoritos, tracking, alertas, histórico y delivery conservan semánticas separadas;
6. inbox → `/hoteles` abre un deep link contextual autorizado y tiene fallback seguro;
7. no existe autorización hotelera por `hotel_id` únicamente en list, summary, read, read-all o deep link;
8. sesión, cache y SSR no cruzan datos entre cuentas;
9. mobile, dark/light, ES/EN, teclado, foco, zoom y reduced motion pasan H32-H34/H40;
10. existen tests de dos usuarios, lifecycle, estados, deep links, retorno y errores;
11. la instrumentación H47 tiene redaction, dedupe, ventanas y exclusión de QA/demo;
12. el owner acepta evidencia residual y H48 recibe una superficie de retorno estable.

**Resultado contractual:** H47 queda definida como retorno útil y privado alrededor de `/hoteles`. El código actual ya tiene piezas reutilizables, pero no existe todavía un agregador “Mis hoteles”, URL state hotelero completo, deep link contextual autorizado ni cierre de ownership V2; la fase de implementación y QA permanece pendiente.
