# Plan de Desarrollo: Resolución de Deuda y Escalabilidad (Visión IA)

**Estado:** activo  
**Fecha:** 2026-05-16  
**Autor:** IA  
**Área:** plan

## Contexto y Riesgos de IA

Este plan detalla el roadmap para resolver las zonas críticamente faltas de desarrollo en Viru Tracker. Al ser diseñado para ser ejecutado por una Inteligencia Artificial, el plan incluye mitigaciones específicas para nuestras vulnerabilidades intrínsecas:

1. **Riesgo de Pérdida de Contexto:** Archivos de miles de líneas (como diccionarios gigantes de aeropuertos o traducciones) provocan que la IA olvide el objetivo o trunque respuestas.
   - **Mitigación:** Toda migración de datos masivos (ej. listado mundial de aeropuertos) se hará mediante scripts programáticos (Python/Node) que descarguen los datos de fuentes públicas fiables y pueblen la Base de Datos automáticamente, evitando inyecciones de código masivas.
2. **Incapacidad ante Anti-Bot y CAPTCHAs:** Como IA, operar scrapers (como el actual de Ryanair) a largo plazo nos expone a bloqueos que no podré resolver autónomamente de manera fiable.
   - **Mitigación:** Es imprescindible integrar APIs oficiales orientadas a developers (ej. Duffel, Amadeus, Skyscanner API) utilizando credenciales estables (`API_KEY`) para el nuevo `Provider`.
3. **Regresiones por Refactorización Ciega:** Cambios drásticos en el core (`backend/app/api/v1/search.py`) pueden romper el sistema y llevar a bucles de depuración interminables debido a la falta de visión global del estado de ejecución.
   - **Mitigación:** Aplicaremos desarrollo incremental estricto mediante Feature Flags (`ff_new_provider`). El proveedor legacy se mantendrá intacto mientras desarrollamos y conectamos el nuevo a través del patrón Adapter ya definido (ADR-003).

---

## Fases de Ejecución

### Fase 1: Catálogo Dinámico de Aeropuertos y Búsqueda
Objetivo: Eliminar el listado hardcodeado en `frontend/src/modules/shared/airports.ts`.
- **Backend:** Crear el modelo SQLAlchemy y migraciones Alembic para la tabla `Airports`.
- **Datos:** Desarrollar `backend/scripts/seed_airports.py` para descargar el set de datos abierto de *OurAirports* o similar y poblar SQLite/PostgreSQL.
- **API:** Exponer `GET /api/v1/airports?q=...` para búsqueda aproximada (fuzzy search).
- **Frontend:** Implementar autocompletado en el selector de aeropuertos con debounce.

### Fase 2: Proveedor Agnostico y Robusto
Objetivo: Superar las limitaciones impuestas por el scraper público.
- **Backend:** Integrar el SDK de un GDS oficial o agregador. Desarrollar `AmadeusProvider` o `DuffelProvider` respetando la interfaz actual.
- **Testing:** Crear e integrar tests unitarios que simulen la respuesta de la nueva API, garantizando compatibilidad estructural.
- **Despliegue:** Envolver la llamada al proveedor en una comprobación de variable de entorno o feature flag `ff_new_provider`.

### Fase 3: Quick Search Completo y Búsquedas Globales
Objetivo: Dar sentido funcional a las rutas y filtros actualmente postpuestos.
- **Filtros:** Mover el *enforcement* de `max_stops`, `duration_max_min` y tiempos de viaje a la capa de lógica, justo después de recibir los datos del nuevo proveedor.
- **Feature Flags:** Activar e implementar la UI para `ff_everywhere_enabled` (buscar desde un origen sin destino fijo) y `ff_self_connect_enabled`, aprovechando las nuevas capacidades del GDS.

### Fase 4: i18n y Soporte Multi-Divisa
Objetivo: Preparar la plataforma para un público global (`ff_full_i18n`, `ff_country_content`).
- **Divisas:** Implementar conversión en caliente de moneda (vía caché o API libre como ExchangeRate-API) en el caso de que la respuesta del proveedor llegue en moneda extranjera.
- **Traducciones:** Consolidar las cadenas esparcidas a archivos de dominio en `frontend/src/i18n/`.

### Fase 5: Pipeline de Sugerencias y Predicción (Opcional)
Objetivo: Cumplir con la promesa de rastreo avanzado (`ff_prediction_enabled`, `ff_suggestions_pipeline`).
- **Sugerencias:** Reemplazar el alias legacy `/suggestions` por un dashboard real alimentado por análisis de histórico.
- **Predicción:** Modelar una regresión lineal simple basada en el histórico de precios almacenado en la DB local (Alertas/Watchlist).
