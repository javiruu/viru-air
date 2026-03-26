# Diseño - Recomendaciones IA (Explorer)

Fecha: 2026-02-23

## Contexto
La pantalla de `/recomendaciones` debe ser distinta a Búsqueda rápida y usar IA real para priorizar destinos. Además de precio, incorpora señales de clima, tendencias y fechas flexibles. El usuario puede elegir países completos o aeropuertos y ajustar el orden con pesos.

## Objetivo
- Ofrecer una experiencia "explorador" con panel de señales + grid de recomendaciones.
- Conectar a un endpoint real con IA y degradación segura si no hay IA.
- Mantener filtros compatibles con Quick Search.

## No objetivos
- No reemplazar Quick Search ni Watchlist.
- No introducir nuevos proveedores externos más allá del stack actual (Ryanair + Open-Meteo).

## UX y UI
- Layout en dos columnas: panel izquierdo de señales/filtros + panel derecho de resultados.
- Hero editorial con narrativa de IA, sin replicar el formulario de Quick Search.
- Selección de país completo cuando no se elige aeropuerto.
- Chips de tendencia y razones IA por tarjeta.

## API y datos
Nuevo endpoint: `POST /api/v1/recommendations`

Entrada (resumen):
- `origin_iata`, `destination_iata` (string o CSV/lista)
- `travel_date`, `days_before`, `days_after`
- Filtros: `radius_km`, `include_nearby_origins`, `include_nearby_destinations`, `depart_after`, `depart_before`, `exclude_origins`, `exclude_destinations`
- Ponderación: `weights`
- `locale`

Salida:
- `items`: recomendaciones con score, señales, clima y tags IA
- `ai`: indicador de uso de IA y error si aplica

## Ranking
1. Generar candidatos combinando IATA y fecha (limitado).
2. Calcular señales: precio, clima, velocidad estimada y tendencia simple.
3. Llamar a IA para ranking + motivo breve.
4. Si falla IA, usar scoring heurístico.

## Errores y degradación
- Si falta `OPENAI_API_KEY`, devolver ranking heurístico con aviso.
- Si el proveedor de vuelos falla en algún tramo, se omite ese tramo sin romper toda la respuesta.

## Testing
- Smoke manual en `/recomendaciones` con países y aeropuertos.
- Verificar que el payload acepta listas IATA (modo país).
- Validar degradación: IA apagada y ranking heurístico.
