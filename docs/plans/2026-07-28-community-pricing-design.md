# Community pricing — diseño aprobado

**Estado:** aprobado
**Fecha:** 2026-07-28
**Área:** producto, backend, frontend
**Fuente de verdad:** no; decisión de diseño para la implementación

## Objetivo

Convertir vuelos ya usados de la Watchlist en evidencia comunitaria real y anónima:

- cuando un vuelo caduque o el usuario lo marque como `Comprado`, Viru pregunta si llegó a volar;
- si voló, Viru pide el precio final pagado por viajero;
- Viru agrega respuestas por ruta direccional durante los últimos 12 meses;
- el rango solo se hace público cuando existen al menos 3 usuarios distintos.

Ejemplo público:

> 3 viajeros de Viru pagaron 67–89 € por persona.

## Decisiones cerradas

### Unidad de precio

El dato solicitado es el precio final por viajero, con tasas y extras incluidos. No se solicita el total de la reserva ni se divide automáticamente entre pasajeros.

### Unidad de agregación

La agregación es por ruta direccional exacta:

- `AGP → FCO` y `FCO → AGP` son comunidades distintas;
- solo entran vuelos cuya fecha de viaje esté dentro de una ventana móvil de 12 meses;
- el tamaño de muestra cuenta usuarios distintos, no respuestas anónimas ilimitadas del mismo usuario.

### Umbral de privacidad

Antes de 3 viajeros distintos:

> Tu precio ya suma. Mostraremos el rango cuando haya 3 viajeros.

Desde 3 viajeros distintos:

> 3 viajeros de Viru pagaron 67–89 € por persona.

La API pública no expone identidad, respuestas individuales, marcas de tiempo individuales ni precios brutos atribuibles.

### Propiedad y edición

- existe una sola respuesta por usuario y vuelo de Watchlist;
- el usuario puede editar o eliminar su propia respuesta;
- la relación con el usuario se conserva internamente solo para deduplicación, autorización y cálculo del umbral;
- solo las respuestas `voló = sí` con precio válido participan en el agregado.

## Flujo

### Entrada por compra

1. El usuario pulsa `Comprado` en una fila activa de `/watchlist`.
2. El vuelo deja de estar en seguimiento activo.
3. Se abre la cola de Community Pricing con la pregunta `¿Llegaste a volar?`.

### Entrada por caducidad

1. La fecha del vuelo queda en el pasado.
2. El backend lo presenta como elegible para Community Pricing sin reescribir el histórico.
3. Al abrir `/watchlist`, el primer vuelo pendiente se ofrece una sola vez por sesión.

### Respuesta

1. `Sí, volé` abre el campo de precio final por viajero.
2. `No volé` guarda una respuesta sin precio y cierra ese pendiente.
3. `Ahora no` cierra el cajón, pero mantiene el vuelo en la cola.
4. Tras guardar, el usuario ve el estado de privacidad o el rango comunitario disponible.

## Superficie visual

La experiencia vive dentro de Watchlist:

- acción `Comprado` acomodada junto a las acciones existentes de cada fila;
- cajón lateral derecho en escritorio y hoja de ancho completo en móvil;
- cola breve de vuelos pendientes, procesada de uno en uno;
- jerarquía cálida y aeronáutica de Viru, compatible con tema claro y oscuro;
- sin convertir la fila en un formulario permanente ni añadir una pantalla independiente.

## Modelo de datos

Se crea una entidad separada de Fare Memory y de `PriceSnapshot`.

`CommunityPriceReport` contiene:

- vuelo de Watchlist y usuario propietario;
- si llegó a volar;
- precio final por viajero, solo cuando voló;
- moneda;
- motivo que activó el flujo (`purchased` o `expired`);
- fechas de creación y actualización.

La tabla impone una respuesta única por vuelo de Watchlist y consistencia entre `flew` y `price_per_traveler`.

## Contrato de agregación

Para cada ruta direccional:

- ventana: fecha de viaje entre hoy menos 12 meses y hoy;
- entradas: respuestas con `flew = true` y precio positivo;
- muestra: `count(distinct user_id)`;
- rango: mínimo y máximo de los precios válidos;
- publicación: solo si la muestra es al menos 3.

Los vuelos futuros marcados como comprados pueden recoger respuesta, pero no entran en estadísticas hasta que su fecha de viaje haya pasado.

## Límites de esta entrega

- moneda inicial: EUR;
- no se publican mediana, percentiles ni comparativas por aerolínea;
- no hay recompensas ni gamificación;
- no se reutiliza Fare Memory como almacén de respuestas comunitarias;
- no se envían notificaciones externas: la captura ocurre dentro de Watchlist.

## Criterios de aceptación

- un propietario puede marcar su vuelo como comprado;
- un vuelo caducado aparece pendiente sin mutar su fecha ni crear snapshots;
- se puede guardar `No volé` sin precio;
- `Sí, volé` exige un precio final por viajero válido;
- otro usuario no puede leer, editar ni borrar una respuesta individual;
- con 1 o 2 usuarios la API oculta el rango;
- con 3 usuarios distintos la API publica tamaño de muestra y rango;
- la ruta inversa y los vuelos de más de 12 meses quedan fuera;
- el flujo funciona en tema claro/oscuro y en móvil/escritorio.
