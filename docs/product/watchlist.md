# Watchlist

**Estado:** vivo  
**Última revisión:** 2026-07-28
**Fuente de verdad:** si  
**Área:** product

## Resumen

Watchlist es el centro operativo de Viru Air y absorbe el historico como parte de la misma experiencia de decision.

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
