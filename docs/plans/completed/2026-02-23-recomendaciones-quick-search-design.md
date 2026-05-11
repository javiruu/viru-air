# Recomendaciones + Quick Search (modo país) - Diseño

Fecha: 2026-02-23

## Resumen
Unificamos Quick Search y Recomendaciones con un modo “país” cuando el usuario selecciona un país en el selector sin elegir un aeropuerto. En ese caso, la búsqueda se hace a nivel país y los resultados se ordenan por un score ponderado por defecto, manteniendo libertad para ordenar por precio/duración/riesgo/frescura. Se añade una nueva página `/recomendaciones` con el mismo motor y filtros avanzados, y un botón en el dashboard para acceder a ella.

## Objetivos
- Hacer la búsqueda rápida más intuitiva para usuarios casuales.
- Mantener capacidades avanzadas para usuarios expertos (filtros y ordenaciones existentes).
- Evitar duplicación de lógica entre Quick Search y Recomendaciones.

## No Objetivos
- No crear un motor de ranking nuevo.
- No eliminar el uso de IATA ni el selector existente.

## Arquitectura / Alcance
- **Frontend**: adaptar Quick Search para aceptar selecciones de país sin aeropuerto; añadir página `/recomendaciones` reutilizando el mismo flujo y filtros.
- **Backend**: si es necesario, extender `/search/quick` para aceptar país-only (lista de aeropuertos) con límites de combinaciones ya existentes.

## UX / Comportamiento
- Si el usuario selecciona un país sin aeropuerto en el selector:
  - UI refleja “País completo” (p. ej., “España (todos los aeropuertos)”).
  - Se activa un modo país-only.
  - La búsqueda se ejecuta con los aeropuertos del país seleccionado.
- Resultados:
  - Orden por defecto: score ponderado actual.
  - Orden alternativo: precio, duración, riesgo, frescura (igual que ahora).
- Recomendaciones:
  - Nueva ruta `/recomendaciones` con el mismo formulario y filtros que Quick Search.
  - Orientada a “elige países y busca”.
  - Botón nuevo en dashboard para acceder.

## Copy / UI
- Añadir textos para:
  - Estado país-only (tooltip/ayuda).
  - Indicador de “todos los aeropuertos del país”.
- Recomendaciones comparte estilos y layout con Quick Search para consistencia.

## Datos y Ranking
- Búsqueda país-only genera combinaciones de aeropuertos entre países.
- Mantener límites de combinaciones para evitar explosión de resultados.
- Score ponderado como orden por defecto; usuario puede reordenar.

## Errores y Edge Cases
- País sin aeropuertos disponibles: mensaje explícito.
- País-only + aeropuerto: permitido (mezcla país ? aeropuerto).
- Si no hay resultados: usar los mismos estados y CTA de “relajar filtros”.

## Testing
- País-only origen y destino.
- País-only origen + aeropuerto destino.
- Ordenación por precio/duración/riesgo/frescura.
- Filtros avanzados aplicados.
- Estados vacíos y de error.
