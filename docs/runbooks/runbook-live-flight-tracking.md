# Runbook - Live flight tracking desde Watchlist

**Estado:** vivo
**Última revisión:** 2026-07-21
**Fuente de verdad:** sí
**Área:** runbook

## Propósito

Activar, comprobar, degradar y retirar de forma segura el proveedor operacional usado por `GET /api/v1/watchlist/{watch_id}/live`.

La integración es opcional. Sin credencial, Watchlist, precios, histórico, alertas y mapa de rutas siguen operativos; el panel live muestra `not_configured` o `identity_missing` según corresponda.

## Prerrequisitos

- migración Alembic `0035_add_live_flight_tracking` aplicada;
- backend y frontend desplegados desde la misma revisión;
- cuenta de proveedor con acceso al endpoint de vuelos;
- una Watch guardada desde un resultado exacto de Quick Search para probar el estado enlazado;
- logs de backend disponibles sin volcado de variables de entorno.

## Configuración

```dotenv
AVIATIONSTACK_API_KEY=
AVIATIONSTACK_BASE_URL=https://api.aviationstack.com/v1
AVIATIONSTACK_TIMEOUT_SECONDS=8
```

- `AVIATIONSTACK_API_KEY` vacío desactiva el adapter de forma segura.
- `AVIATIONSTACK_BASE_URL` es configuración de despliegue, nunca entrada del usuario.
- un timeout ausente, inválido o no positivo usa el valor seguro por defecto.
- no pongas la key en URL, logs, capturas, reportes ni comandos compartidos.

## Activación gradual

1. Aplica la migración:

   ```bash
   cd backend
   python -m alembic upgrade head
   ```

2. Despliega primero sin `AVIATIONSTACK_API_KEY` y comprueba que una Watch exacta responde `coverage=not_configured` sin errores de página.
3. Configura la key en el secret store del entorno y reinicia solo el backend.
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
| key ausente | `not_configured` | configurar solo si el entorno debe tener tracking |
| key inválida / 401 / 403 | `temporarily_unavailable` | corregir o rotar secret; no exponer el detalle al cliente |
| cuota / 429 | `temporarily_unavailable`, posible dato previo | respetar `refresh_after_seconds`; revisar cuota antes de ampliar rollout |
| timeout, DNS o 5xx | `temporarily_unavailable`, posible dato previo | comprobar proveedor y red; no aumentar polling |
| cero coincidencias | `no_coverage` / `no_match` | verificar identidad y ventana horaria |
| varias coincidencias iguales | `no_coverage` / `ambiguous` | no elegir automáticamente; revisar identidad guardada |
| Watch legacy | `identity_missing` | usar el CTA hacia Quick Search y guardar un resultado exacto |
| mapa sin posición | ruta y aviso sin marcador | es correcto: no interpolar coordenadas |

## Verificación automatizada

```bash
cd backend
python -m pytest tests/unit/test_aviationstack_operational_provider.py \
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

1. elimina `AVIATIONSTACK_API_KEY` del entorno;
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

La bajada elimina `flight_operational_refresh_lock`, `flight_operational_snapshot` y `watch_tracked_flight_leg`. No elimina `flight_watch` ni `price_snapshot`.

Para restaurar:

```bash
python -m alembic upgrade head
```

## Referencias

- [Contrato live flight tracking](../reference/backend/live-flight-tracking-contract.md)
- [ADR-005](../adr/ADR-005-live-operational-flight-tracking.md)
- [Plan de implementación](../archive/plans/2026-07-21-live-flight-tracking-watchlist.md)
