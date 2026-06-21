# QA visual `/hoteles`

**Estado:** vivo  
**Ultima revision:** 2026-06-21 (cierre Fases 59-61)  
**Fuente de verdad:** si  
**Area:** QA / Visual

## Resumen

Registro vivo de verificacion visual real del modulo `/hoteles`.

El objetivo de esta fase era cerrar la deuda pendiente de dark/light/responsive y del flujo principal del radar hotelero con evidencia reproducible, no solo con revision de codigo.

## Fases 59-61 cerradas

### Ajustes aplicados

1. Copy de proveedor reescrito para no prometer disponibilidad en vivo cuando la vista solo tiene contexto guardado o demo.
2. `tracked offers`, `comp set` y sugerencias cercanas reciben layout responsive dedicado en vez de depender de `list-row` generico.
3. La lectura de paridad y proveedor usa una evaluacion comun de senal para distinguir sin observaciones, senal limitada y comparativa puntuable.

### Evidencia esperada de cierre

1. El encabezado y el toggle de proveedor explican con honestidad que la vista no confirma booking en vivo.
2. En anchos intermedios y moviles las acciones de tracked offers y comp set ya no quedan forzadas a una sola fila rigida.
3. Cuando no hay observaciones, la UI muestra estado insuficiente en vez de aparentar una comparativa lista.

## Fase 57 cerrada

### Entorno usado

- Frontend local: `http://127.0.0.1:3000`
- Backend local: `http://127.0.0.1:8000/api/v1`
- Runner: `frontend/scripts/qa_hotels_phase57.mjs`
- Evidencia local: `docs/qa/evidence/hotels-2026-06-20-phase57/report.json`

### Escenarios verificados

- `desktop-dark`
- `desktop-light`
- `mobile-dark`
- `mobile-light`

Cada escenario genero capturas `full`, `results` y `sidebar`.

## Flujo validado

1. Buscar hoteles por ciudad (`Madrid`).
2. Seleccionar hotel desde resultados.
3. Crear tracked offer.
4. Anadir a seguimiento.
5. Crear alerta de precio.
6. Crear comparativa.
7. Anadir sugerencia cercana cuando aparece disponible.

## Evidencia obtenida

### Resultado funcional

- `resultCount >= 1` en los 4 escenarios.
- `trackedOfferCount = 1` tras la accion de tracking.
- `watchlistCount = 1` tras anadir a seguimiento.
- `alertRuleCount = 1` tras crear alerta.
- `compSetVisible = true` tras crear comparativa.

### Resultado visual

- Sin overflow horizontal en desktop ni mobile.
- Resultados y sidebar visibles despues de la interaccion real.
- Dark y light se renderizan con la misma estructura y sin errores de consola.
- El CTA de watchlist vuelve a ser clicable junto al CTA de tracking en las cards de resultados.

## Correcciones necesarias para cerrar la fase

### 1. CTA de watchlist oculto cuando existia tracking

- Archivo: `frontend/src/modules/hotels/components/HotelSearchPanel.tsx`
- Problema: al pasar `onTrackPrice`, la card dejaba de renderizar la accion de watchlist.
- Cierre: la card muestra ambas acciones a la vez.

### 2. Override global de `.card` contaminando el layout

- Archivo: `frontend/src/styles/screens.css`
- Problema: un bloque visual de weather reutilizaba `.card` de forma global con `width` y `height` fijos, deformando las cards de hoteles y bloqueando clicks reales.
- Cierre: esas reglas quedaron acotadas a `.cardm > .card`.

### 3. Runner visual alineado con el flujo real

- Archivo: `frontend/scripts/qa_hotels_phase57.mjs`
- Cierre:
  - scroll previo a CTAs fuera de viewport;
  - espera explicita de `POST` para alertas y comp sets;
  - desactivacion de pointer events de notificaciones durante la automatizacion;
  - omision de `ingest/mock` en este entorno para no depender de una feature flag desactivada.

## Nota de entorno

- `POST /api/v1/hotels/ingest/mock` devuelve `HOTEL_FEATURE_ENABLED is false` en este entorno local.
- La Fase 57 no cambia ese comportamiento.
- La verificacion visual se ejecuto sobre datos ya consultables del entorno y el flujo principal del radar, no sobre la ruta de ingesta mock.

## Verificaciones ejecutadas

- `cd frontend && node --import tsx --test tests/hotels-f56-audit.test.ts`
- `cd frontend && node --import tsx --test tests/hotels-signal-assessment.test.ts`
- `cd frontend && node scripts/qa_hotels_phase57.mjs`

## Estado final de esta deuda

- Verificacion visual real: cerrada.
- Responsive dark/light: cerrado.
- Flujo principal del radar hotelero: cerrado.
- Riesgo restante no cubierto por esta fase: disponibilidad real de ingesta mock/proveedor cuando `HOTEL_FEATURE_ENABLED` esta desactivado en el entorno.
