# H03 — Arquitectura de información y wireflows de `/hoteles`

**Estado:** completo como diseño — contrato de navegación para implementación posterior  
**Fecha:** 2026-08-04  
**Área:** producto / UX / frontend  
**Fuente de verdad:** sí para la arquitectura de información de hoteles; los contratos técnicos de API y datos siguen en `docs/specs/` y en el código.

## 1. Propósito

H03 convierte la visión de H01 y los patrones observados en H02 en una estructura navegable y comprobable. El objetivo no es implementar todavía los componentes, sino decidir qué debe ser protagonista, qué debe quedar contextual y cómo una persona conserva su búsqueda al explorar, guardar o seguir una estancia.

La dirección aprobada es **workspace progresivo**:

- una ruta principal `/hoteles` concentra búsqueda y resultados;
- el detalle aparece de forma contextual sin borrar la búsqueda;
- tracking, favoritos, alertas y señales avanzadas siguen disponibles, pero no compiten con la primera decisión;
- la URL conserva el contexto reproducible;
- mobile no es una versión comprimida del dashboard actual, sino el mismo flujo con capas progresivas.

## 2. Decisión de arquitectura

### Opción elegida: workspace progresivo

```text
/hoteles
├── Promesa breve y buscador protagonista
├── Resumen de búsqueda ejecutada
├── Filtros y orden
├── Resultados comparables
├── Detalle contextual del hotel/oferta
├── Guardar o seguir precio
└── Accesos secundarios a mis hoteles, alertas e histórico
```

### Por qué no se eligen rutas completamente separadas ahora

Separar desde el inicio búsqueda, resultados, detalle y tracking produciría una arquitectura más limpia en abstracto, pero introduce más estados compartidos, más transiciones y más puntos donde se puede perder destino, fechas, ocupación o filtros. La fase actual necesita mejorar la decisión principal sin romper las capacidades ya existentes.

### Evolución permitida

El workspace no bloquea una futura ruta profunda como `/hoteles/seguimientos` o `/hoteles/[hotel_id]`. H03 deja identificadores y estados compatibles para extraer esas superficies cuando el volumen de uso lo justifique.

## 3. Objetivos y no-objetivos de H03

### Incluido

- Jerarquía de la pantalla principal.
- Sitemap funcional del dominio hoteles.
- Wireflows de primera búsqueda, resultados, detalle, tracking y retorno.
- Estado mínimo que vive en URL.
- Reglas de selección, cierre y vuelta.
- Prioridad desktop/mobile.
- Estados funcionales que cada superficie debe representar.
- Handoff explícito a H04, H05, H10, H13, H15, H16, H18 y H22.

### Fuera de alcance

- Implementar componentes o cambiar estilos.
- Elegir o integrar providers.
- Migrar tablas o contratos de base de datos.
- Definir el algoritmo final de ranking.
- Integrar email, push u otros canales externos.
- Cerrar la dirección visual final de H31.
- Crear una OTA, reserva, pago o soporte de booking.

## 4. Jerarquía de `/hoteles`

### 4.1. Primer nivel: búsqueda

La primera pantalla debe responder en pocos segundos:

1. qué puede hacer Viru;
2. dónde y cuándo quiere viajar la persona;
3. cómo definir habitaciones y huéspedes;
4. qué acción ejecuta la búsqueda.

Estructura conceptual:

```text
Encabezado
  ├── H1 orientado a beneficio
  └── Subtítulo corto, sin jerga de provider

Buscador protagonista
  ├── Destino
  ├── Entrada
  ├── Salida
  ├── Habitaciones / adultos / niños
  ├── Opciones avanzadas cuando estén soportadas
  └── Buscar

Estado de búsqueda
  ├── idle
  ├── validación
  ├── loading
  └── error/partial con siguiente acción
```

La ingesta mock queda fuera del flujo principal visible para usuarios finales. Si se conserva para desarrollo o QA, debe rotularse como fixture/demo y no aparecer como alternativa equivalente a buscar.

### 4.2. Segundo nivel: resultados

Una vez ejecutada una búsqueda, el buscador se compacta y el resultado se convierte en protagonista:

```text
Resumen de estancia
  ├── destino
  ├── fechas
  ├── ocupación
  └── Editar búsqueda

Toolbar de resultados
  ├── número de resultados
  ├── freshness / procedencia resumida
  ├── Filtros
  └── Orden

Lista de resultados
  ├── Card comparable
  ├── Card comparable
  └── estados vacío/parcial/stale/error
```

El resultado debe hacer visible la estancia comparada. No se permite una lista de hoteles sin fechas, ocupación o contexto de precio cuando esos datos sean necesarios para entender la oferta.

### 4.3. Tercer nivel: detalle contextual

El detalle se abre sobre el workspace o en una sección contextual de la misma ruta, conservando la búsqueda:

```text
Detalle contextual
  ├── Identidad del hotel
  ├── Ubicación y categoría
  ├── Oferta/estancia seleccionada
  ├── Precio y condiciones
  ├── Freshness y procedencia
  ├── Historial si existe
  ├── Guardar hotel
  ├── Seguir precio
  ├── Abrir partner
  ├── Paridad/cercanos como secundarios
  └── Cerrar / volver a resultados
```

El CTA primario del detalle depende del estado de la oferta:

- `Seguir precio` si la estancia es suficientemente concreta y el dato permite tracking.
- `Completar estancia` si faltan datos necesarios.
- `Guardar hotel` si se puede guardar la propiedad pero no prometer vigilancia.
- `Abrir partner` solo con disclosure y contexto de precio.

### 4.4. Superficies secundarias

| Superficie | Papel | Regla de exposición |
|---|---|---|
| Mis hoteles/favoritos | Recuperar propiedades guardadas | Acceso secundario, nunca desplaza la búsqueda inicial |
| Seguimientos | Retención y retorno | Visible tras guardar/seguir y desde navegación de cuenta |
| Alertas | Actuar sobre cambios | Ligadas a una estancia; la gestión global puede vivir en inbox |
| Histórico | Entender evolución | Se muestra en detalle o tracking, no como dashboard inicial |
| Paridad | Comparar providers | Solo si las condiciones son comparables |
| Hoteles cercanos | Ampliar exploración | Bloque contextual y plegable |
| Comp sets | Inteligencia avanzada | No protagonista del flujo consumidor |

## 5. Sitemap funcional

```text
/hoteles
  ├── /hoteles?{search-state}
  │     ├── resultados
  │     ├── filtros
  │     ├── orden
  │     └── detalle contextual
  ├── /hoteles?{search-state}&hotel_id={id}&panel=detail
  ├── /hoteles?panel=tracked
  ├── /hoteles?panel=watchlist
  └── /notifications?hotel_id={id}&tracked_offer_id={id}
```

`panel=tracked` y `panel=watchlist` son estados de transición compatibles con la implementación actual; una futura extracción a rutas propias debe conservar deep links antiguos mediante redirección o lectura equivalente.

No se añade todavía `/hoteles/[hotel_id]` como ruta obligatoria. El identificador de hotel sí queda definido para permitir esa evolución sin rehacer los contratos de selección.

## 6. Estado de búsqueda en URL

> **Importante:** esta sección define el contrato objetivo, no afirma que todos los parámetros estén implementados hoy. H03 queda completa como arquitectura; H13/H15/H22 deben introducir y probar la serialización por etapas. La implementación actual conserva estado de hoteles principalmente en React y todavía no sincroniza toda esta superficie con la URL.

### 6.1. Parámetros canónicos propuestos

```text
/hoteles?
  destination=madrid
  &destination_type=city
  &country=ES
  &check_in=2026-09-12
  &check_out=2026-09-15
  &rooms=1
  &adults=2
  &children=0
  &children_ages=
  &currency=EUR
  &sort=recommended
  &price_min=
  &price_max=
  &stars=
  &distance_km=
  &cancellation=
  &meal_plan=
  &provider=
  &page=1
  &hotel_id=
  &panel=
```

### 6.2. Estado de soporte

| Parámetro/superficie | Estado al cerrar H03 | Fase que lo implementa |
|---|---|---|
| `query`, `city` | Disponible en la búsqueda actual, aún no persistido en URL | H13 |
| `area`, `check_in`, `check_out`, `guests`, `radius` | Disponible en el flujo de área actual, aún no persistido en URL | H10/H13 |
| `rooms`, `children`, `children_ages`, condiciones de estancia | Contrato objetivo; no completo en la UI/API actual | H10/H13 |
| `sort`, filtros y `page` | Contrato objetivo; filtros/orden aún no forman parte del resultado hotelero principal | H14/H15 |
| `hotel_id`, `panel=detail` | Convención objetivo para selección contextual; no implementada aún | H18 |
| `panel=tracked`, `panel=watchlist` | Convención futura para superficies secundarias; `HotelRadarPage` aún no la lee | H22/H23 |

### 6.3. Reglas

1. Solo se serializan valores necesarios para reconstruir la búsqueda.
2. Fechas se expresan en ISO `YYYY-MM-DD`.
3. `destination` debe ir acompañado por `destination_type` cuando haya ambigüedad.
4. Habitaciones, adultos, niños y edades no se sustituyen por un único campo `guests` cuando el backend ya pueda distinguirlos.
5. Filtros ausentes no generan parámetros vacíos innecesarios.
6. Orden, página y filtros se pueden compartir y recuperar.
7. `hotel_id` identifica la selección; `panel=detail` explicita que el detalle está abierto.
8. Las acciones de edición de formulario pueden usar `router.replace` con debounce.
9. Las transiciones deliberadas a detalle, partner o tracking usan `router.push` cuando el usuario espera volver con el botón atrás.
10. Nunca se escriben tokens, emails, payloads crudos de provider ni datos privados no necesarios.

### 6.4. Compatibilidad y normalización

- H03 define nombres canónicos; H13 debe comprobar qué campos existen hoy y crear un adaptador si la API actual usa otros.
- Valores inválidos se ignoran o se normalizan a defaults seguros; no deben romper el render.
- Si solo hay búsqueda por nombre/ciudad disponible, se mantiene una variante mínima con `query` y `city` hasta que H10/H13 completen el contrato de estancia.
- La migración debe aceptar deep links históricos que solo contengan `hotel_id`.

## 7. Wireflows principales

### WF-01 — Primera visita y búsqueda

```text
Usuario entra en /hoteles
  ↓
Ve promesa + buscador
  ↓
Escribe destino
  ↓
Selecciona sugerencia inequívoca
  ↓
Elige entrada, salida y ocupación
  ↓
Pulsa Buscar
  ↓
URL se actualiza con estado válido
  ↓
Se muestra loading con contexto
  ↓
Resultados o estado degradado
```

**Éxito:** existe una query reproducible y el primer resultado útil explica qué estancia representa.

**Errores:** destino ambiguo, fechas inválidas, ocupación incompleta, provider caído, resultado parcial o ausencia de resultados. Cada error conserva los campos ya introducidos y ofrece una acción de recuperación.

### WF-02 — Resultados, filtros y orden

```text
Resultados visibles
  ↓
Usuario ve resumen de estancia y freshness
  ↓
Abre Filtros
  ↓
Aplica uno o varios filtros
  ↓
URL conserva filtros + page se reinicia a 1
  ↓
Lista se actualiza
  ↓
Usuario cambia orden
  ↓
Lista se actualiza sin perder destino/fechas/ocupación
```

**Regla:** filtros inexistentes para el provider o sin datos suficientes no se presentan como si fueran aplicables.

### WF-03 — Abrir y cerrar detalle

```text
Card seleccionada
  ↓
/hoteles?{search-state}&hotel_id=id&panel=detail
  ↓
Detalle contextual abre con loading local
  ↓
Se cargan identidad, rates, condiciones y señales
  ↓
Usuario cierra detalle o pulsa volver
  ↓
Resultados conservan query, filtros, orden y posición razonable
```

Si el detalle falla, la lista sigue siendo utilizable y muestra un error localizado con reintento. No se borra la búsqueda completa por un fallo de detalle.

### WF-04 — Guardar propiedad

```text
Resultado o detalle
  ↓
Guardar hotel
  ↓
Se crea/actualiza favorito simple
  ↓
Confirmación: “Guardado”
  ↓
La acción no crea tracking ni promete alertas
```

El copy debe diferenciar claramente `Guardar hotel` de `Seguir precio`.

### WF-05 — Crear tracking

```text
Resultado o detalle
  ↓
Seguir precio
  ↓
Revisión de estancia:
 hotel + destino + fechas + habitaciones + ocupación
 + habitación/régimen/cancelación/provider si existen
  ↓
Si falta contexto: pedir completar o degradar a Guardar hotel
  ↓
Crear tracking
  ↓
Confirmar snapshot inicial, freshness y política de comprobación
  ↓
Mostrar enlace a seguimiento/histórico
```

No se puede mostrar una confirmación de tracking real si el provider solo aporta fixture, datos stale o una oferta no reconstruible. En esos casos el estado debe indicar `fixture-only`, `stale` o `pending provider validation` según el contrato de H05/H06.

### WF-06 — Abrir partner

```text
Detalle/oferta
  ↓
Usuario pulsa Abrir partner
  ↓
Se muestra contexto breve:
 precio observado + fecha/hora + condiciones + posible variación
  ↓
Deeplink seguro y atribuible
  ↓
Partner externo
```

Viru no presenta el precio observado como garantía del precio final del partner.

### WF-07 — Retorno desde alerta

```text
Inbox/email/push
  ↓
Deep link con hotel_id + tracked_offer_id + contexto permitido
  ↓
/hoteles abre panel de seguimiento o detalle
  ↓
Se muestra delta, snapshots y razón de la alerta
  ↓
Usuario decide: abrir partner, editar, pausar o eliminar
```

El deep link debe respetar ownership. Un identificador ajeno no debe revelar detalle ni histórico.

## 8. Estados funcionales obligatorios

| Superficie | Estados mínimos | Acción siguiente |
|---|---|---|
| Buscador | `idle`, validación, `loading`, error | corregir, reintentar o editar |
| Autocomplete | vacío, cargando, sugerencias, ambiguo, fallo | seleccionar, escribir más o continuar con fallback |
| Resultados | `loading`, éxito, vacío, parcial, stale, error total | filtrar, ampliar, reintentar o modificar búsqueda |
| Card | normal, guardada, seguida, acción pendiente, error | abrir detalle, guardar, seguir o reintentar |
| Detalle | cargando, completo, parcial, no encontrado, error | reintentar, volver o conservar lista |
| Tracking | confirmación, snapshot inicial pendiente, activo, pausado, expirado | ver historial, editar, pausar o eliminar |
| Histórico | sin datos, pocos puntos, suficiente, stale | explicar confianza y última captura |
| Partner | disclosure visible, deeplink listo, error | reintentar o volver sin perder contexto |
| Filtros | cerrados, abiertos, aplicados, inválidos | aplicar, limpiar o cancelar |

## 9. Desktop y mobile

Los patrones de drawer existentes en `frontend/src/modules/quick-search/components/QuickSearchFiltersDrawer.tsx`, `frontend/src/modules/quick-search/components/QuickSearchAdvancedDrawer.tsx` y `frontend/src/modules/watchlist/components/CommunityPricingDrawer.tsx` sirven como referencias de integración. H03 exige conservar o mejorar su gestión de Escape, foco inicial, cierre y retorno de foco; no presupone que cada patrón existente sea perfecto ni autoriza copiar accesibilidad incompleta.


### Desktop

- El buscador ocupa el primer foco visual.
- Resultados y detalle pueden compartir workspace en dos columnas solo cuando la anchura lo permita.
- El detalle no debe desplazar la lista hasta hacer imposible reconocer la selección.
- Paridad, cercanos y comp sets se agrupan bajo el detalle o en bloques plegables.
- El scroll debe permitir volver a la card seleccionada.

### Mobile

- Una columna y scroll vertical natural.
- Resumen de búsqueda compacto y editable.
- Filtros en drawer/sheet con `role=dialog`, `aria-modal`, foco inicial, cierre con Escape, backdrop y retorno de foco.
- Detalle como drawer de altura suficiente o sección contextual; no como card diminuta dentro de otra card.
- CTA de seguir precio accesible pero sin cubrir precio, condiciones o botones de navegación.
- Historial y comparativas bajo disclosures.
- Touch targets mínimos según el contrato UI vigente.
- `prefers-reduced-motion` evita transiciones esenciales y no se usa motion para ocultar cambios de estado.

## 10. Reglas de navegación y selección

1. Una card seleccionada tiene un estado visual y semántico inequívoco.
2. Seleccionar una card no debe borrar filtros ni ejecutar una segunda búsqueda inesperada.
3. Abrir detalle es reversible con cierre y botón atrás.
4. Cambiar la búsqueda invalida la selección de hotel si el hotel ya no pertenece al contexto, salvo que se pueda cargar como deep link explícito.
5. El back del navegador no debe devolver al usuario a un formulario vacío si había una búsqueda válida.
6. Acciones de mutación muestran estado pendiente y resultado; no dependen solo de cambios silenciosos en una lista.
7. Un error de una señal secundaria no bloquea resultados ni detalle básico.
8. Deep links de notificación deben abrir la superficie mínima necesaria y comprobar ownership.
9. La navegación no puede convertir un dato mock en una promesa live.

## 11. Accesibilidad y rendimiento como contrato de IA

Las siguientes IAs deben implementar, no reinterpretar:

- encabezados semánticos en orden;
- landmarks `main`, navegación y regiones de resultados;
- estados anunciados con `role=status` o `role=alert` según severidad;
- etiquetas visibles o asociadas a todos los campos;
- teclado completo para tabs, autocomplete, filtros, detalle y acciones;
- foco gestionado en drawers y retorno al disparador;
- no usar color como única señal de precio, estado o freshness;
- reservar espacio para loading y evitar saltos de layout;
- cancelar o ignorar respuestas obsoletas cuando cambia la búsqueda;
- respetar reduced motion y viewport estrecho.

## 12. Handoff por fase

### H04 — Métricas y eventos

Instrumentar entrada a búsqueda, búsqueda completada, filtro aplicado, detalle abierto, favorito creado, tracking creado, alerta abierta y partner click, sin payloads sensibles.

### H05 — Freshness/provenance/confidence

Definir los estados que aparecen en buscador, cards, detalle, histórico, tracking y deeplink. La IA no debe inventar etiquetas `live`.

### H10 — Modelo de estancia/oferta

Convertir los parámetros de ocupación, habitaciones, condiciones y provider en invariantes de dominio y compatibilidad con registros actuales.

### H13 — Formulario

Implementar el buscador protagonista, la serialización URL, validación y restauración de búsqueda.

### H15 — Resultados

Entregar metadata de búsqueda, warnings, paginación, estados parcial/vacío/stale y cancelación de requests.

### H16/H18 — Cards y detalle

Implementar la jerarquía card → detalle contextual, una acción primaria, condiciones visibles y retorno sin perder contexto.

### H22 — Favorito vs tracking

Mantener semánticas distintas y diseñar confirmaciones separadas.

### H31-H34 — Visual, responsive e i18n

Aplicar identidad Viru, mobile-first, dark/light, español/inglés y touch/focus states sin alterar la arquitectura decidida aquí.

## 13. Gate de H03

H03 se considera cerrado cuando una IA de frontend puede responder sin inventar:

- ¿Qué es protagonista? Búsqueda y resultados comparables.
- ¿Dónde vive el detalle? En selección contextual compatible con `hotel_id` y `panel=detail`.
- ¿Qué se conserva al volver? Destino, fechas, ocupación, filtros, orden, página y selección razonable.
- ¿Qué se relega? Watchlist, tracking global, alertas, paridad, cercanos y comp sets.
- ¿Qué pasa en móvil? Drawer/sheet accesible para filtros y detalle progresivo.
- ¿Qué estados hay que diseñar? Idle, loading, éxito, vacío, partial, stale, errores y acciones mutantes.
- ¿Qué no se implementa ahora? Provider, DB, delivery, ranking final y visual final.

**Resultado:** H03 aprobado para pasar a H04 y a las fases de contrato/formulario/resultados, sin cerrar todavía la implementación visual o de datos.
