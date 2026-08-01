# Inteligencia comunitaria de rutas — diseño aprobado

**Estado:** aprobado  
**Fecha:** 2026-08-01  
**Área:** producto, backend, frontend  
**Fuente de verdad:** no; decisión de diseño para la implementación

## Objetivo

Convertir señales comunitarias ya existentes en una capa útil y discreta dentro de Dashboard, Quick Search y Watchlist:

- mostrar los 10 corredores más buscados durante los últimos 7 días;
- contextualizar resultados con rangos de precios pagados por viajeros de Viru;
- señalar rutas seguidas o en tendencia sin recargar las filas;
- sugerir rutas relacionadas a partir de co-ocurrencia anónima de Watchlist;
- usar el rango comunitario como referencia cuando no existe historial personal.

## Fuente de popularidad

`QuickSearchPopularityCounter` conserva su función acumulada. No puede reconstruir una ventana semanal exacta, por lo que se añade un agregado diario anónimo por ruta direccional y moneda.

- cada búsqueda válida incrementa el acumulado histórico y el bucket del día;
- la ventana semanal suma hoy y los seis días anteriores;
- no se inventa backfill: la cobertura exacta comienza al desplegar la migración;
- `MAD → BCN` y `BCN → MAD` son corredores distintos;
- no se almacenan usuarios, consultas completas ni identificadores personales.

Una ruta está `En tendencia` cuando ocupa una de las primeras `ceil(total_rutas * 0,20)` posiciones de la ventana, con orden estable por búsquedas descendentes y códigos IATA para desempatar.

## Privacidad comunitaria

- los rangos de precios reutilizan el umbral vigente de 3 usuarios distintos;
- las rutas relacionadas exigen al menos 3 usuarios distintos que compartan la ruta origen y la sugerida;
- las respuestas públicas solo incluyen ruta, conteos agregados, rango publicado y estado de tendencia;
- nunca se exponen identidades, vuelos concretos, fechas individuales ni precios atribuibles.

## Contrato ligero

La señal vive en endpoints comunitarios separados del payload pesado de Quick Search:

- `GET /api/v1/community/routes/popular`: top 10 de los últimos 7 días;
- `POST /api/v1/community/routes/insights`: precio público y popularidad para un lote de rutas;
- `GET /api/v1/community/routes/{origin}/{destination}/related`: hasta 3 rutas relacionadas.

Cada consumidor degrada de forma independiente. Un fallo comunitario nunca bloquea una búsqueda, una fila de Watchlist ni el historial personal.

## Superficie visual

### Dashboard

La sección `Descubrimiento` pasa a dos columnas en escritorio:

- izquierda: tarjeta `Corredores más buscados`, etiqueta `Esta semana`, banda horizontal de 10 celdas y lista compacta de 10 rutas;
- derecha: la tarjeta existente `Oportunidad personal`;
- en móvil, corredores aparece antes que la oportunidad;
- cada ruta abre Quick Search con origen y destino precargados.

La imagen de la variante Lazyweb es la autoridad de composición, jerarquía, espaciado y copy. La banda es una señal visual ultraligera, no un gráfico analítico ni un mapa geográfico.

### Quick Search

Cuando el rango es público, cada resultado muestra una sola línea secundaria:

> 3 viajeros de Viru pagaron 45–78 € por persona en esta ruta.

Con menos de 3 viajeros no se muestra precio ni tamaño de muestra.

### Watchlist

La fila reserva un único hueco compacto de señal:

- `12 siguiendo` cuando `watchers_count > 5`;
- `En tendencia` cuando la ruta pertenece al top 20 %;
- `12 siguiendo · En tendencia` cuando coinciden ambas señales.

El drawer añade `Quienes miran MAD → BCN también miran…` con hasta 3 enlaces a Quick Search.

### Historial

Si no hay snapshots personales y existe un rango público, el panel muestra una banda `Referencia comunidad · 45–78 €/persona`. Los días del calendario permanecen neutrales porque el agregado comunitario no tiene granularidad por fecha.

## Criterios de aceptación

- la ventana semanal usa buckets diarios exactos y no el acumulado histórico;
- el dashboard reproduce la estructura del mockup en 1280 px y se adapta a 768/375 px;
- las diez celdas de la banda corresponden a las diez rutas ordenadas;
- todos los enlaces precargan origen y destino en Quick Search;
- el umbral de privacidad se respeta en precios y co-ocurrencia;
- las cinco superficies funcionan en tema claro y oscuro;
- errores o ausencia de señal comunitaria producen estados vacíos discretos sin romper el flujo principal.
