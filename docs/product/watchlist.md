# Watchlist

**Estado:** vivo  
**Última revisión:** 2026-07-29
**Fuente de verdad:** si  
**Área:** product

## Resumen

Watchlist es el centro operativo de Viru Air y absorbe el historico como parte de la misma experiencia de decision.

## Precio comparable guardado

Las Watches creadas desde Quick Search conservan la cesta usada para comparar
el vuelo: viajeros, equipaje de 10 kg o 20 kg, seguro, Fast Track, embarque
prioritario, asiento y cambios flexibles. El usuario selecciona los extras,
pero no introduce sus importes: Watchlist vuelve a aplicar automáticamente el
catálogo público de la aerolínea guardada y el número de vuelos del itinerario.

El resumen muestra un total, un rango o un precio `Desde` según la precisión de
la tarifa publicada y enlaza su fuente oficial. Si algún extra seleccionado no
tiene una tarifa pública calculable, muestra el total parcial y lo identifica
como pendiente, sin presentar una cifra falsa.

## Seguimiento operacional del vuelo

Una Watch guardada desde un resultado exacto de Quick Search puede enlazar una o varias piernas y mostrar, sin desplazar la lectura de precio:

- estado normalizado, número y ruta;
- salida/llegada programada, estimada o real;
- retraso, terminal y puerta cuando la fuente los entrega;
- posición en el mapa solo cuando ha sido observada y validada;
- predicción temprana de retraso para vuelos programados, enlazando la matrícula
  con su tramo entrante y explicando riesgo, confianza, margen de escala y
  señales usadas;
- frescura y estados honestos de falta de identidad, cobertura o proveedor.

Las Watches manuales o antiguas mantienen precio e histórico. Viru revisa sus
capturas frescas de más nueva a más antigua: descarta las que no tienen una
identidad completa en Fare Memory, enlaza la primera coincidencia única por
ruta, fecha, proveedor y hora, y se detiene sin elegir si encuentra varias
salidas plausibles. Así puede recuperar un vuelo exacto ya conocido sin gastar
cuota aunque una captura posterior venga incompleta. Si falta esa evidencia, la
UI ofrece volver a Quick Search. En multi-leg, solo el primer tramo queda
expandido y los siguientes se consultan bajo demanda.

La predicción vive dentro del bloque operacional, no compite con precio ni
histórico y nunca sustituye el horario oficial. Reutiliza la señal de snapshots
compartidos del Flight Tracking Hub, pero solo enlaza rutas exactas guardadas
por la misma persona; mira hasta 25 horas atrás y no provoca llamadas externas
nuevas. Si Viru no puede demostrar la rotación exacta sin cruzar datos entre
cuentas, muestra una señal compacta de datos insuficientes en lugar de inventar
una predicción.

Contrato y operación:

- [Live flight tracking desde Watchlist](../reference/backend/live-flight-tracking-contract.md)
- [Runbook live flight tracking](../runbooks/runbook-live-flight-tracking.md)

## Precio de la comunidad

Cada fila de Watchlist tiene un icono comunitario discreto arriba a la
izquierda. Al abrirlo aparece un hub lateral que reúne el rango anónimo pagado
por viajero, el tamaño o umbral de la muestra, cuántas personas siguen la ruta,
las garantías de privacidad y la aportación propia. Abrir el hub es siempre de
solo lectura: no marca el vuelo como comprado ni dispara otra mutación.

Cuando un vuelo caduca, el icono indica que hay una aportación pendiente sin
abrirse automáticamente. Si la persona pulsa `Comprado` dentro del hub:

1. confirma si finalmente se montó en ese vuelo;
2. si la respuesta es afirmativa, solicita el precio final pagado por viajero;
3. permite dejarlo para más tarde, corregir la respuesta o eliminarla.

Las acciones comunitarias no se mezclan con `Pausar`, `Reanudar` o `Eliminar`
en la fila, y no existe una pantalla comunitaria paralela.

El importe es el total final por persona, no el total de la reserva ni una
estimación de Viru. En esta primera versión la moneda es EUR.

Las respuestas viven separadas de Fare Memory: Fare Memory conserva precios
observados de proveedores y Community Pricing conserva experiencias declaradas
por viajeros. Solo se publica el rango mínimo–máximo de una ruta direccional
cuando hay al menos tres viajeros distintos con vuelo realizado y precio válido
en los últimos 365 días. Antes de ese umbral, la UI solo indica cuántas
aportaciones faltan; no expone precios, identidades, vuelos concretos ni fechas
de respuesta.

Contrato:

- [Community Pricing](../reference/backend/community-pricing-contract.md)

## Contenido principal

- Presencia funcional confirmada en:
  - [Overview del proyecto](../overview/project-overview.md)
  - [Estado actual](../overview/current-state.md)
- Mapa de lenguaje y entidades:
  - [Product language map](../reference/product-language-map.md)
- Material operativo relacionado:
  - [Runbook watchlist uniqueness migration](../runbooks/runbook-watchlist-uniqueness-migration.md)

## Relacionado

- [Backend](../engineering/backend.md)
- [Frontend](../engineering/frontend.md)
