# Runbook - Live flight tracking desde Watchlist

**Estado:** vivo
**Última revisión:** 2026-07-21
**Fuente de verdad:** sí
**Área:** runbook

## Propósito

Activar, comprobar, degradar y retirar de forma segura la cadena operacional usada por `GET /api/v1/watchlist/{watch_id}/live`.

La integración es opcional. Sin credencial, Watchlist, precios, histórico, alertas y mapa de rutas siguen operativos; el panel live muestra `not_configured` o `identity_missing` según corresponda.

## Prerrequisitos

- migraciones Alembic hasta `0037_reconcile_live_snapshot_uniqueness` aplicadas;
- backend y frontend desplegados desde la misma revisión;
- cuenta de proveedor con acceso al endpoint de vuelos;
- una Watch guardada desde un resultado exacto de Quick Search para probar el estado enlazado;
- logs de backend disponibles sin volcado de variables de entorno.

## Configuración

El bloque completo y copiable vive en `backend/.env.example`. Los controles principales son:

```dotenv
LIVE_FLIGHT_ZERO_COST_ONLY=true
LIVE_FLIGHT_ALLOW_PAID_PROVIDERS=false
LIVE_FLIGHT_PROVIDER_TIMEOUT_SECONDS=8
LIVE_FLIGHT_OPENSKY_ANONYMOUS=true
AVIATIONSTACK_MONTHLY_REQUEST_LIMIT=90
AERODATABOX_MONTHLY_UNIT_LIMIT=540
OPENSKY_DAILY_CREDIT_LIMIT=360
FLIGHTAWARE_MONTHLY_REQUEST_LIMIT=0
ADSB_EXCHANGE_MONTHLY_REQUEST_LIMIT=0
```

- la cadena de estado es Amadeus → Aviationstack → AeroDataBox → FlightAware;
- si la posición sigue ausente, se recorren en el mismo orden los adapters restantes capaces de aportarla: Aviationstack, AeroDataBox, OpenSky y, solo en modo de pago, FlightAware y ADS-B Exchange;
- un proveedor ya consultado no se llama otra vez para enriquecer la misma observación;
- Amadeus usa `test` por defecto; producción exige un límite mensual explícito;
- Aviationstack y AeroDataBox solo se registran con key y paran antes de su cuota gratuita;
- OpenSky anónimo funciona sin key y se limita localmente a 360 créditos diarios;
- FlightAware y ADS-B Exchange nunca se registran con `LIVE_FLIGHT_ZERO_COST_ONLY=true`;
- para habilitar un proveedor de pago hacen falta tres decisiones explícitas: desactivar zero-cost, permitir proveedores de pago y fijar un límite positivo;
- no pongas keys en URL, logs, capturas, reportes ni comandos compartidos.

`flight_provider_quota` persiste consumo, ventana y bloqueos. Un reinicio no reinicia el contador. Los `429` respetan `Retry-After`; un `402` bloquea el proveedor y la cadena continúa.

## Activación gradual

1. Aplica la migración:

   ```bash
   cd backend
   python -m alembic upgrade head
   ```

2. Despliega con zero-cost activo y sin keys; OpenSky queda disponible para enriquecimiento cuando otro proveedor aporta `callsign` o `icao24`.
3. Añade de uno en uno Amadeus test, Aviationstack o AeroDataBox desde el secret store y reinicia solo el backend.
4. Selecciona una Watch exacta próxima en `/watchlist`.
5. Comprueba que la primera llamada devuelve una de estas salidas válidas:
   - `live` / `ok` con observación;
   - `no_coverage` / `no_match`;
   - `no_coverage` / `ambiguous`.
6. Repite la consulta antes del TTL y confirma que reutiliza el snapshot.
7. Abre dos clientes a la vez y comprueba en logs que el lease evita dos llamadas remotas para la misma identidad.

## Smoke API

Con un token de una cuenta QA y una Watch propia:

```bash
curl -sS \
  -H "Authorization: Bearer <redacted>" \
  "http://127.0.0.1:8000/api/v1/watchlist/<watch-id>/live?refresh=true"
```

Criterios:

- HTTP 200 para outcomes operacionales esperables;
- `watch_id` coincide con la Watch consultada;
- `refresh_after_seconds >= 30`;
- ninguna pierna tiene posición parcial: latitud y longitud aparecen juntas o `position=null`;
- no aparecen API keys ni payload remoto crudo;
- una Watch ajena devuelve el mismo `404 watch_not_found` que una inexistente.

## Señales de observabilidad

El backend emite eventos estructurados sin identidad de usuario:

- `live_flight_provider_observed`;
- `live_flight_refresh outcome=observed|cache_hit|cooldown_hit|singleflight_busy|user_cooldown|no_match|ambiguous|rate_limited|unavailable|not_configured`;
- `live_flight_retention outcome=ok|failed`.

No uses número completo, token, correo o key como dimensión de métrica.

## Fallos esperados

| Síntoma | Estado esperado | Acción |
|---|---|---|
| key de estado ausente | `not_configured` o dato previo | configurar un proveedor gratuito; OpenSky solo no inventa identidad |
| key inválida / 401 / 403 | `temporarily_unavailable` | corregir o rotar secret; no exponer el detalle al cliente |
| cuota local agotada / 429 | fallback o `temporarily_unavailable` | esperar cambio de ventana o `Retry-After`; no subir límites sin revisar el plan |
| pago requerido / 402 | fallback o `temporarily_unavailable` | mantener proveedor bloqueado; no habilitarlo en zero-cost |
| timeout, DNS o 5xx | `temporarily_unavailable`, posible dato previo | comprobar proveedor y red; no aumentar polling |
| cero coincidencias | `no_coverage` / `no_match` | verificar identidad y ventana horaria |
| varias coincidencias iguales | `no_coverage` / `ambiguous` | no elegir automáticamente; revisar identidad guardada |
| Watch legacy | `identity_missing` | usar el CTA hacia Quick Search y guardar un resultado exacto |
| mapa sin posición | ruta y aviso sin marcador | es correcto: no interpolar coordenadas |

## Verificación automatizada

```bash
cd backend
python -m pytest tests/unit/test_aviationstack_operational_provider.py \
  tests/unit/test_operational_provider_adapters.py \
  tests/unit/test_multi_provider_operational_provider.py \
  tests/unit/test_live_flight_provider_quota.py \
  tests/unit/test_operational_provider_registry.py \
  tests/unit/test_alembic_audit.py \
  tests/unit/test_live_flight_snapshot_retention.py \
  tests/integration/test_watchlist_live_tracking.py -q
python -m ruff check app tests

cd ../frontend
npm test -- --test-name-pattern="live flight|watchlist live UI|save result"
npm exec tsc -- --noEmit
npm run build
node scripts/qa_watchlist_live_tracking.mjs
```

La evidencia browser queda en:

- `docs/qa/reports/2026-07-21-watchlist-live-flight-tracking.json`;
- `docs/qa/screenshots/watchlist-live-flight-tracking/`.

## Desactivación y rollback

### Desactivar proveedor sin rollback de datos

1. deja `LIVE_FLIGHT_ZERO_COST_ONLY=true`, vacía las keys y, si se necesita aislamiento total, usa `LIVE_FLIGHT_OPENSKY_ANONYMOUS=false`;
2. reinicia el backend;
3. confirma `provider_status=not_configured`;
4. verifica que precios e histórico siguen disponibles.

Las identidades y observaciones anteriores pueden conservarse; la UI las marca stale cuando corresponda.

### Rollback de migración

Solo si la versión de aplicación ya fue retirada y se acepta eliminar los datos operacionales:

```bash
cd backend
python -m alembic downgrade 0034
```

La bajada elimina primero `flight_provider_quota` y después las tablas operacionales de 0035. No elimina `flight_watch` ni `price_snapshot`.

La revisión 0035 reconcilia de forma segura el estado observado en instalaciones donde un arranque ORM creó las tablas antes de que Alembic avanzara desde 0034: añade las dos columnas conocidas que faltaban, normaliza los índices del lease y rechaza cualquier deriva desconocida en lugar de marcarla como migrada.

Para restaurar:

```bash
python -m alembic upgrade head
```

## Referencias

- [Contrato live flight tracking](../reference/backend/live-flight-tracking-contract.md)
- [ADR-005](../adr/ADR-005-live-operational-flight-tracking.md)
- [ADR-006](../adr/ADR-006-zero-cost-operational-provider-fallback.md)
- [Plan de implementación](../archive/plans/2026-07-21-live-flight-tracking-watchlist.md)
