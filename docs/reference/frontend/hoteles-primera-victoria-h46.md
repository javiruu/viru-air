# H46 — Primera victoria sin tutorial largo en `/hoteles`

**Estado:** COMPLETA como contrato de experiencia; implementación del flujo guiado, persistencia URL, auth contextual, eventos y QA browser pendientes  
**Fecha:** 2026-08-05  
**Área:** producto / UX / frontend / i18n / QA  
**Fuente de verdad:** sí para la primera victoria, la jerarquía de entrada y el onboarding implícito de `/hoteles`  
**Fase del roadmap:** H46  
**Depende de:** [H03 — arquitectura de información](../../product/hoteles-information-architecture-h03.md), [H13 — formulario y recuperación](../backend/hoteles-search-form-h13.md), [H16 — result cards](hoteles-result-cards-h16.md), [H21 — estados y recuperación](hoteles-state-matrix-h21.md), [H31 — dirección visual](hoteles-visual-direction-states-h31.md), [H32 — responsive y CTAs](hoteles-responsive-accessible-ctas-h32.md), [H33 — WCAG](hoteles-wcag-accessibility-audit-h33.md), [H34 — i18n](hoteles-localization-dates-currency-timezones-h34.md), [H40 — browser QA](hoteles-visual-manual-crossbrowser-qa-h40.md), [H44 — seed y fallos reproducibles](../backend/hoteles-seed-demo-fallos-h44.md), [H45 — release readiness](../backend/hoteles-release-canary-smoke-rollback-h45.md)  
**Handoff:** [H47 — re-engagement y superficie de “mis hoteles”](../../plans/2026-08-04-hoteles-master-roadmap.md#fase-h47--re-engagement-y-superficie-de-mis-hoteles)

> H46 no añade un tutorial que explique toda la plataforma. Define cómo una persona nueva entiende el valor de Viru y consigue una primera utilidad observable con la mínima fricción posible.

## 1. Decisión de producto

La primera victoria de `/hoteles` es:

> **Encontrar un hotel o zona, entender qué señal se está viendo y dejar una intención recuperable —guardar el hotel o seguir una estancia suficientemente definida— sin perder el contexto ni recibir una promesa de disponibilidad live.**

La pantalla debe enseñar el producto mientras la persona lo usa:

```text
promesa breve → búsqueda válida → resultado comprensible
→ acción de guardar o seguir → confirmación honesta → siguiente paso claro
```

No se exige que una persona configure alertas, comprenda paridad, cree un comp set o lea el histórico para completar H46. Esas capacidades aparecen después, como progressive disclosure contextual.

### 1.1. Qué queda fuera

H46 no cierra por sí sola:

- el modelo V2 de estancia/oferta de H10/H23;
- URL state completo de H13;
- result cards V2 de H16;
- entrega real de alertas de H26-H28;
- `/hoteles` como booking engine u OTA;
- confirmación de disponibilidad, precio garantizado o reserva dentro de Viru;
- un provider comercial nuevo;
- un tutorial, tour de bienvenida o modal obligatorio;
- una métrica de activación sin definición de denominador y privacidad.

Si una capacidad no está respaldada por el backend o el provider, H46 debe degradar el copy y la acción, no simularla.

## 2. Baseline real comprobable

La ruta actual `frontend/src/app/(private)/hoteles/page.tsx` renderiza `HotelRadarPage`. La composición ya contiene:

- cabecera con `hotels.title` y `hotels.subtitle`;
- overview de hoteles encontrados, seguimientos activos y hoteles en lista;
- `HotelSearchPanel` con modo por nombre o zona;
- fechas y huéspedes por defecto en modo zona, radio y checkbox opcional de provider;
- acción primaria `Buscar hoteles` y acción secundaria `Cargar datos de prueba`;
- resultados y estado vacío `Sin resultados todavía`;
- selección contextual de hotel;
- `HotelTrackedOffersPanel`, `HotelWatchlistPanel`, timeline, paridad, alertas y comp sets;
- acciones de card para tracking y watchlist;
- mensajes de éxito/error mediante el centro de notificaciones.

La base permite construir H46, pero no demuestra todavía una primera victoria coherente:

| Área | Actual verificable | Gap H46 |
|---|---|---|
| Promesa | título/subtítulo breves | no explican en una frase qué se puede guardar, seguir y revisar |
| Entrada | dos modos de búsqueda y campos visibles | el modo por nombre no pide fechas/ocupación; el modo zona exige resolver área antes de buscar |
| Demo | botón explícito de datos de prueba | es útil para QA, pero no debe parecer una fuente equivalente a una búsqueda real |
| Resultados | cards seleccionables y acciones | la decisión, el precio y su contexto no tienen todavía la jerarquía V2 de H16 |
| Favorito | backend/UI de watchlist existente | copy actual `Añadir a seguimiento` puede confundirse con tracking de precio |
| Tracking | CTA y panel de seguimientos existentes | `useTrackedOffers` puede crear usando defaults/bridge cuando falta una oferta completa; H23 exige confirmación contextual |
| Alertas | formulario en panel lateral | aparece demasiado pronto para una persona nueva y no explica el ciclo posterior en un paso breve |
| Auth | la ruta es privada en la estructura actual | no existe aún una política H46 explícita de preservar búsqueda al pedir login/registro |
| Estados | loading, empty y errores parciales por panel | no hay un camino único de recuperación ni una distinción completa idle/empty/error según H21 |
| Evidencia | tests estructurales H56/H57/H59-H61 y tests de señal | no existe todavía un test de primera victoria completo ni aprobación browser de H40 |

### 2.1. Regla de claims

- `Modo demo`, fixture, snapshot o señal parcial nunca se presenta como disponibilidad confirmada.
- `Cargar datos de prueba` es una herramienta de desarrollo/QA y debe conservar rotulación explícita.
- `Trackear precio` no puede confirmar tracking activo si faltan hotel, fechas, huéspedes, condiciones, precio/procedencia o policy de revalidación elegibles.
- Un favorito simple no implica refresh, histórico ni alerta.
- “Viru revisará la señal disponible cada día” solo puede mostrarse cuando H09/H23/H45 hayan demostrado esa política para el entorno y el tracking concreto; mientras tanto el copy debe ser condicional y honesto.

## 3. Definición operativa de primera victoria

H46 se considera conseguida cuando una persona nueva, sin leer documentación externa, puede completar uno de estos caminos:

### Camino A — Descubrimiento y guardado

1. Entiende que `/hoteles` sirve para comparar señales y conservar hoteles de interés.
2. Completa una búsqueda válida o carga una fixture claramente etiquetada en entorno de demo.
3. Identifica al menos un hotel y entiende su ciudad/categoría y el contexto disponible.
4. Pulsa `Guardar hotel`.
5. Ve una confirmación localizada que dice qué se guardó y qué **no** se ha activado.
6. Encuentra el hotel en `Hoteles guardados` sin perder los resultados.

### Camino B — Seguimiento de una estancia

1. Ejecuta una búsqueda con hotel, entrada, salida y huéspedes suficientes para el contexto V1 admitido.
2. Selecciona un resultado y entiende qué precio/señal se está mostrando.
3. Pulsa `Seguir precio` solo si la oferta es elegible; si no, recibe una razón y una alternativa segura.
4. Revisa una confirmación con hotel, fechas, huéspedes, moneda, precio observado, procedencia/freshness y alcance del seguimiento.
5. Ve el seguimiento en `Seguimientos activos`.
6. Entiende qué ocurrirá después: próxima comprobación solo si está realmente habilitada; de lo contrario, estado `pendiente`, `demo`, `señal parcial` o `sin validación live`.

No es necesario completar ambos caminos. Guardar hotel y seguir precio son victorias distintas y no se deben combinar silenciosamente.

### 3.1. Tiempo y fricción objetivo

H46 no fija una promesa universal de segundos. El gate debe medir, con fixture determinista y usuario sin historial:

- pasos visibles hasta la primera búsqueda válida;
- errores de validación y abandonos;
- tiempo hasta comprender el primer resultado;
- tiempo hasta guardar o confirmar tracking;
- pérdida de contexto al pedir auth o recuperarse de un error;
- comprensión de la diferencia entre guardar y seguir.

El owner debe establecer baselines y umbrales antes de declarar la implementación completa. No se aceptan umbrales inventados después de observar solo el happy path.

## 4. Onboarding implícito y jerarquía de pantalla

### 4.1. Primera vista: una promesa, una acción

La primera vista debe responder, sin párrafo tutorial:

- qué hace Viru;
- qué necesita la persona para empezar;
- cuál es la acción primaria.

Copy de referencia, sujeto al glosario i18n vigente:

```text
H1: Encuentra y sigue hoteles sin perder la pista del precio
Apoyo: Compara la señal disponible, guarda tus favoritos y sigue una estancia cuando el contexto esté completo.
CTA: Buscar hoteles
```

El texto final debe respetar ES/EN, dark/light, espacio disponible y H34. No debe afirmar “precio garantizado”, “disponibilidad live” ni ahorro futuro.

### 4.2. Orden de exposición

```text
1. Promesa + buscador protagonista
2. Resultado y contexto de búsqueda
3. Una acción principal por resultado
4. Confirmación de guardar/seguir
5. Seguimientos y guardados recientes
6. Alertas e histórico como siguiente paso
7. Paridad, cercanos y comp sets como inteligencia secundaria
```

La UI actual tiene muchos paneles montados en una sola ruta. H46 no exige borrarlos, pero sí que una persona nueva no necesite comprenderlos todos para avanzar. Paneles secundarios pueden estar plegados, resumidos o desplazados tras la primera decisión, respetando H31/H32.

### 4.3. Empty state

El estado inicial debe distinguir `idle` de `empty`:

- `idle`: aún no se ha ejecutado una búsqueda; explica en una frase qué introducir y ofrece `Buscar hoteles`.
- `empty`: la consulta terminó correctamente sin resultados; conserva campos y ofrece modificar destino/fechas/radio o reintentar.
- `demo`: la persona pidió explícitamente fixture; etiqueta dataset, fecha/contexto y ausencia de disponibilidad live.
- `error`: explica que la consulta no pudo completarse; no dice “no hay hoteles”.

El empty state no debe ser una lista de instrucciones larga. Debe tener como máximo una explicación breve y una o dos acciones siguientes.

## 5. Flujo guiado de búsqueda

### 5.1. Modo recomendado para primera visita

El modo primario debe reducir decisiones innecesarias:

1. destino/zona;
2. fechas;
3. huéspedes;
4. buscar.

Si la implementación V1 mantiene nombre/ciudad como alternativa, esa variante debe conservarse como fallback explícito, no competir visualmente con el flujo de estancia cuando el objetivo sea seguir precio.

### 5.2. Preservación de intención

Al cambiar de modo, resolver destino, buscar, seleccionar, guardar, pedir auth o abrir un panel:

- conservar los campos ya introducidos;
- conservar el resultado y la selección cuando el contexto siga siendo válido;
- no duplicar requests por restauración o re-render;
- preparar la serialización H13 aunque la implementación aún sea efímera;
- no poner ownership, tokens, targets ni thresholds privados en URL.

Si una operación requiere autenticación, el formulario y la búsqueda deben sobrevivir al retorno. Si no pueden sobrevivir todavía, la fase no pasa el gate.

### 5.3. Resultado que enseña sin tutorial

El primer resultado debe hacer visible, en el orden que H16 define:

1. nombre y ubicación;
2. precio o estado honesto de precio ausente;
3. fechas/huéspedes si respaldan el dato;
4. provider/freshness/limitación traducidos a lenguaje humano;
5. acción principal de detalle/selección;
6. `Guardar hotel` y `Seguir precio` con semántica separada.

No se debe usar un tooltip o modal para esconder información esencial de la primera decisión.

## 6. Conversión explícita: guardar frente a seguir

H46 adopta H22/H23 como regla de copy y comportamiento:

| Acción | Significa | Confirmación mínima | No promete |
|---|---|---|---|
| `Guardar hotel` | interés en la propiedad | nombre, ubicación, estado guardado | refresh, precio, histórico o alerta |
| `Seguir precio` | vigilar una estancia/oferta concreta | hotel, fechas, huéspedes, moneda, precio observado, procedencia y policy disponible | precio final, disponibilidad garantizada o alertas entregadas si H26-H28 no están cerradas |
| `Crear alerta` | regla sobre un tracking/elegibilidad concreta | condición, baseline, estado y alcance | que el evento se entregue por un canal no habilitado |

La nomenclatura actual `Añadir a seguimiento` para watchlist no cumple este contrato: H46 debe migrar a `Guardar hotel`/`Guardado` en ES y `Save hotel`/`Saved` en EN, con un bridge de API si es necesario. `Trackear precio`/`Ya en seguimiento` debe evolucionar a `Seguir precio`/`Siguiendo precio` o equivalente aprobado por el glosario.

### 6.1. Tracking incompleto

Cuando no exista una oferta elegible:

- no crear tracking silenciosamente con `hotel_id` y defaults que parezcan completos;
- explicar qué falta: fechas, ocupación, precio, condiciones, snapshot o provider permitido;
- ofrecer completar la estancia, guardar el hotel o volver a buscar;
- conservar la búsqueda;
- no usar `aria-pressed` como si el tracking estuviera activo.

## 7. Auth contextual sin perder la búsqueda

H46 no decide el proveedor de autenticación. La ruta actual vive en `frontend/src/app/(private)/hoteles/page.tsx`, por lo que no se debe presentar el acceso anónimo como capacidad existente: la búsqueda sin registro es un objetivo condicionado a la política de sesión vigente y queda como gap de implementación.

El contrato de UX futuro es:

1. pedir auth justo antes de una mutación privada que lo necesite: guardar, seguir, crear alerta o abrir una superficie privada;
2. explicar por qué se solicita: conservar el hotel/seguimiento y mostrarlo después;
3. retornar a `/hoteles` con query, selección, modo, fechas, huéspedes, estado y acción pendiente;
4. reanudar solo una vez y de forma idempotente;
5. si la sesión expira, no borrar campos ni mostrar una lista vacía;
6. si el usuario cancela auth, volver al mismo punto con una acción segura alternativa.

Actualmente no existe evidencia en H46 de un mecanismo de intención pendiente, retorno o reanudación idempotente. Ese mecanismo debe definirse en el contrato de auth existente antes de declarar este gate cerrado. No se permite guardar un payload privado completo en la URL: usar un intento efímero, referencia opaca o mecanismo de sesión aprobado, con expiración y ownership.

## 8. Confirmaciones y siguiente paso

Una confirmación de primera victoria debe ser local, breve y accionable:

### Guardado

- qué hotel se guardó;
- enlace o foco a `Hoteles guardados`;
- copy explícito: “Esto guarda el hotel; no activa seguimiento de precio”.

### Tracking

- qué estancia se sigue;
- snapshot/precio observado y freshness/procedencia;
- estado: `activo`, `pendiente de primera observación`, `señal parcial`, `demo` o `no disponible` según evidencia;
- qué hará el sistema después, solo si H09/H23/H45 lo permiten;
- enlace a seguimiento/histórico cuando exista;
- acción para editar, pausar o detener según lifecycle.

### Alerta

Después de crear una alerta, no basta con “Alerta creada”:

- mostrar la condición en lenguaje humano;
- indicar el tracking/estancia al que pertenece;
- explicar que se generará un evento cuando la condición sea evaluada y qué canal está habilitado;
- diferenciar regla persistida de entrega realizada;
- enlazar a gestión de alertas/inbox cuando exista.

Los toasts no sustituyen el estado persistente ni deben ser la única evidencia para lector de pantalla.

## 9. Estados y recuperación de H21 aplicados a la primera victoria

| Momento | Estado | Mensaje/acción mínima |
|---|---|---|
| primera entrada | `idle` | completar búsqueda; CTA visible |
| autocomplete | `resolving` | resolver zona; teclado y Escape funcionan |
| búsqueda | `loading` | contexto conservado; no duplicar submit |
| resultados | `success` | resultado comprensible y acción siguiente |
| sin coincidencias | `empty` | modificar destino/fechas/radio o cargar fixture explícita |
| provider parcial | `partial` | señal disponible + qué falta + reintento seguro |
| dato anterior | `stale`/`stale_while_error` | fecha de captura, limitación y revisar/reintentar |
| provider/config off | `unavailable` | alternativa local/demo honesta; no “agotado” |
| auth | `auth_required` | login/registro y retorno preservando intención |
| entidad perdida | `not_found` | volver a resultados sin borrar búsqueda |
| fallo | `error` | error accionable, no empty; reintentar superficie concreta |
| mutación | `pending`/`success`/`failed` | feedback local, idempotencia y recuperación |

Los paneles secundarios no pueden convertir un fallo de snapshots, rates, alertas o tracking en una lista vacía silenciosa, en contra de H21/H33.

## 10. Accesibilidad, responsive e i18n

La primera victoria debe funcionar sin tutorial visual ni dependencia de color:

- headings y landmarks siguen H31/H32;
- labels visibles, combobox de área y errores siguen H13/H33;
- foco se mueve al resultado o confirmación solo cuando la transición lo requiere y vuelve al trigger al cerrar un panel;
- `role=status` comunica progreso/éxito informativo; `role=alert` comunica errores accionables;
- `aria-describedby`/`aria-invalid` relacionan validación y campos;
- `aria-pressed` representa un toggle real, no un botón disabled sin transición;
- targets táctiles son de 48×48 px mínimos según H32;
- la jerarquía se conserva en 360/390/414/768/1024 px y con zoom 200%;
- dark/light conservan el mismo significado y CTA;
- ES/EN traducen también placeholders, labels, aria, estados y confirmaciones;
- fechas de estancia son civiles; timestamps de captura siguen la política H34;
- moneda observada y unidad de precio permanecen visibles; no hay conversión implícita;
- la fixture demo se rotula en ambos idiomas.

## 11. Instrumentación y privacidad

Los eventos de esta sección son un contrato futuro; la auditoría actual no demuestra que exista instrumentación hotelera verificable. H46 debe instrumentar el embudo sin registrar PII ni payloads crudos:

```text
hotel_first_visit_viewed
hotel_first_search_started
hotel_first_search_succeeded
hotel_first_search_empty
hotel_first_search_failed
hotel_first_result_understood
hotel_first_save_started
hotel_first_save_succeeded
hotel_first_save_failed
hotel_first_track_started
hotel_first_track_blocked
hotel_first_track_succeeded
hotel_first_auth_requested
hotel_first_auth_cancelled
hotel_first_auth_resumed
hotel_first_alert_created
hotel_first_victory_reached
```

Propiedades permitidas:

- modo de búsqueda;
- outcome/state estable;
- número de resultados en bucket;
- si el origen era fixture/demo, sin confundirlo con producción;
- razón allowlisted de bloqueo;
- locale, tema y viewport bucket;
- versión de contrato/experimento;
- fingerprints opacos o hashes aprobados.

No registrar query completa, nombres de hotel si no son necesarios, emails, user IDs crudos, tokens, targets, thresholds, payloads de provider ni deeplinks privados.

La métrica `hotel_first_victory_reached` debe tener definición de denominador, ventana temporal, exclusiones de QA/demo y deduplicación antes de usarse para decisiones de producto.

## 12. Pruebas y evidencia

### 12.1. Unitarias/estructurales

- idle no se presenta como empty;
- empty ofrece recuperación y conserva campos;
- demo está etiquetado como `DEMO_NO_LIVE_AVAILABILITY` o equivalente aprobado;
- copy de favorito y tracking es distinto en ES/EN;
- tracking se bloquea o pide completar contexto cuando faltan invariantes;
- confirmación de tracking incluye hotel, estancia, huéspedes, moneda, precio/procedencia y estado;
- auth request conserva intención y no duplica la mutación al volver;
- provider error no se transforma en empty/sold out;
- alert creation explica condición y alcance sin afirmar delivery;
- todos los eventos H46 tienen nombre/versionado y no contienen campos privados.

### 12.2. Integración/browser

Con fixtures H44 y estados H21:

1. abrir `/hoteles` sin historial;
2. comprobar promesa y foco inicial;
3. ejecutar búsqueda por nombre y por zona;
4. probar idle, loading, éxito, empty, partial, stale y error;
5. seleccionar un resultado;
6. guardar hotel y comprobar confirmación/lista;
7. intentar tracking sin contexto y verificar bloqueo/alternativa;
8. crear tracking con contexto elegible y revisar confirmación;
9. provocar auth_required, cancelar y reanudar conservando búsqueda;
10. abrir/cerrar alertas sin perder selección;
11. repetir en 360×800, 390×844, 414×896, 768×1024, 1024×768 y desktop;
12. repetir dark/light y ES/EN;
13. recorrer el camino principal solo con teclado;
14. comprobar consola, requests duplicadas, focus, live regions y scroll horizontal.

La evidencia debe indicar route, viewport, locale, tema, fixture/profile, pasos, resultado observado y limitaciones. H40 exige aprobación humana para cerrar browser QA; los tests estructurales no sustituyen esa revisión.

## 13. Gate de salida H46

H46 podrá marcarse implementada cuando:

1. una persona nueva entiende la promesa y encuentra la acción primaria sin tutorial largo;
2. idle, empty, demo, partial, stale, auth y error son distinguibles y recuperables;
3. puede completar una búsqueda válida sin perder contexto;
4. puede guardar un hotel con copy y confirmación que no prometen tracking;
5. puede iniciar tracking solo con contexto elegible o recibe un bloqueo accionable;
6. la confirmación de tracking explica qué se seguirá y qué ocurrirá después, sin claims no respaldados;
7. auth, si aparece, conserva intención y reanuda de forma idempotente;
8. alertas explican condición, alcance y estado de evaluación/delivery;
9. ES/EN, dark/light, teclado, móvil, zoom y touch targets pasan H32-H34/H40;
10. existen tests del camino de primera victoria y evidencia browser manual aprobada;
11. eventos H46 tienen definición, redaction, dedupe y exclusión de fixtures/QA;
12. no quedan blockers P0 de H33 en el camino principal.

**Resultado contractual:** H46 queda definida como activación por producto útil, no como tutorial ni como promesa de booking. La implementación actual aporta piezas reutilizables, pero la primera victoria completa sigue pendiente hasta superar este gate.
