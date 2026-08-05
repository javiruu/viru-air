# H00 — Baseline reproducible de `/hoteles`

**Estado:** completo  
**Fecha de ejecución:** 2026-08-04  
**Área:** QA / hoteles  
**Fuente de verdad:** este reporte describe la ejecución de H00; el comportamiento sigue teniendo como fuente el código y los tests.

## Objetivo

Congelar una fotografía reproducible de la superficie hotelera antes de iniciar cambios de producto. Este baseline distingue tres cosas que no deben mezclarse:

1. capacidades presentes en código;
2. tests/build que pasan;
3. servicios operativos realmente levantados y disponibles.

## Alcance inspeccionado

- Ruta: `frontend/src/app/(private)/hoteles/page.tsx`.
- Orquestación: `frontend/src/modules/hotels/HotelRadarPage.tsx`.
- Frontend hotelero: `frontend/src/modules/hotels/**`.
- API y servicio: `backend/app/api/v1/hotels.py`, `backend/app/services/hotels_service.py`.
- Providers: `backend/app/hotels/mock_provider.py`, `backend/app/hotels/makcorps_provider.py`.
- Worker: `backend/app/worker/hotels_sweep.py`.
- Tests backend: `backend/tests/unit/test_hotels_*.py`, `backend/tests/integration/test_hotels_*.py`.
- Tests frontend: `frontend/tests/hotels-f56-audit.test.ts`, `frontend/tests/hotels-signal-assessment.test.ts`.
- QA visual disponible en documentación: `docs/qa/hotels-visual-qa.md` y `docs/qa/hotels-pending-closeout.md`.

## Capacidades detectadas

| Superficie | Estado observado | Evidencia |
|---|---|---|
| Ruta privada `/hoteles` | Presente y conectada a `HotelRadarPage` | `frontend/src/app/(private)/hoteles/page.tsx` |
| Búsqueda por nombre/ciudad | Presente | `useHotelSearch`, `GET /api/v1/hotels/search` |
| Búsqueda por área | Presente | `area-resolve`, `area-search`, fechas, huéspedes, radio |
| Catálogo y detalle | Presente | `HotelProperty`, `/hotels/{hotel_id}` |
| Rates/snapshots | Presente | `HotelRateSnapshot`, `/rates` |
| Favoritos simples | Presente | `HotelWatchlistItem`, panel y CRUD |
| Tracking de oferta | Presente en base técnica | `HotelTrackedOffer`, snapshots y panel |
| Alertas | Presente en reglas/eventos e inbox | alert rules, events, notification sources |
| Paridad | Presente y relegada a señal secundaria | `HotelParityService`, panel de señal |
| Hoteles cercanos | Presente como comp set/sugerencias | `HotelCompSet`, `nearby-suggestions` |
| Provider mock | Presente para fixtures/test/demo | `mock_provider.py`, fixture JSON |
| Provider Makcorps | Adapter presente; sujeto a límites externos | `makcorps_provider.py` |
| Sweep | Worker separado presente; no se arranca desde el API | `backend/app/worker/hotels_sweep.py` |

## Verificación ejecutada

### Backend

```bash
cd backend
python -m pytest tests/unit/test_hotels_*.py tests/integration/test_hotels_*.py -q
```

**Resultado:** `192 passed in 72.88s (0:01:12)`.

### Frontend

```bash
cd frontend
npx tsc --noEmit
node --import tsx --test tests/hotels-f56-audit.test.ts tests/hotels-signal-assessment.test.ts
npm run build
```

**Resultados:**

- TypeScript: correcto, sin errores.
- Tests focalizados: `10 passed`, `0 failed`, `0 skipped`.
- Build: correcto; Next compiló y generó `35` rutas.

### Documentación

```bash
oma docs verify docs/plans/2026-08-04-hoteles-master-roadmap.md --no-urls
```

**Resultado en la verificación disponible al cerrar H00:** referencias sin errores.

## Estado operativo del entorno usado

- El backend respondió en `http://127.0.0.1:8000/health` con HTTP `200`.
- El frontend no estaba escuchando en `http://127.0.0.1:3000/hoteles` durante esta ejecución; por tanto, no se repitió browser QA en esta sesión.
- La configuración local contiene claves/nombres de configuración de hoteles, pero este reporte no expone valores secretos.
- `HOTEL_SWEEP_ENABLED` figura como configuración local presente, pero el worker no se consideró operativo solo por existir la variable: debe ejecutarse y verificarse explícitamente en H09.
- La documentación viva anterior registra QA visual de junio, pero la ruta de evidencia JSON referenciada allí no está disponible en el árbol actual inspeccionado. Se conserva la documentación como contexto histórico, no como evidencia nueva de esta ejecución.

## Matriz hecho / parcial / no verificado

| Área | Clasificación H00 | Motivo |
|---|---|---|
| Compilación y tipado frontend | Hecho | `tsc` y build pasan |
| Tests hoteleros backend | Hecho | 192 tests pasan |
| Tests estructurales/señales frontend | Hecho | 10 tests pasan |
| Ruta frontend levantada en esta sesión | No verificado | frontend no escuchaba en puerto 3000 |
| Browser QA nuevo dark/light/mobile | No verificado en esta sesión | requiere servidores levantados y cuenta/datos |
| Ingesta mock operativa por defecto | Parcial | está soportada, pero el flag de entorno puede desactivarla |
| Provider Makcorps estable | Parcial | adapter existe; cobertura, cuotas y 429 requieren H07 |
| Sweeps periódicos garantizados | No hecho | worker separado, H09 es el gate operativo |
| Delivery externo de alertas hoteleras | No verificado | persistencia/inbox existen; delivery real se valida en H28 |
| Tracking live de producción | No hecho | bloqueado por provider, scheduler, confianza y delivery |

## Riesgos que pasan a H01-H02 y siguientes

1. No presentar el estado técnico como madurez de producto.
2. No llamar “live” a una tarifa solo porque existe un snapshot.
3. No rediseñar alrededor de Makcorps hasta medir sus capacidades y límites.
4. No duplicar lo que ya existe: H01/H02 deben decidir jerarquía y valor, no rehacer el inventario técnico.
5. Repetir browser QA cuando haya una instancia reproducible de frontend/backend; el baseline actual deja esa deuda explícita.

## Gate de H00

**Aprobado con limitaciones documentadas.** Las siguientes IAs pueden empezar H01 y H02. H09, H07 y H40 siguen pendientes y no se consideran cerrados por este baseline.

## Handoff

- H01 debe convertir esta base en visión, personas, jobs, no-objetivos y métricas.
- H02 debe convertir referencias externas en patrones aplicables, separando hechos observados de inferencias.
- H03 puede usar H01/H02 para diseñar la nueva jerarquía, pero no debe asumir que el provider real ya está resuelto.
