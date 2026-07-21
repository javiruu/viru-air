# QA - Fallback operacional multi-proveedor sin coste

**Estado:** vivo
**Fecha:** 2026-07-21
**Área:** backend, migraciones y operación local
**Resultado:** PASS con limitaciones operativas explícitas

## Base de prueba

- ADR-006 y contrato live de Watchlist;
- adapters Amadeus, OpenSky, Aviationstack, AeroDataBox, FlightAware y ADS-B Exchange;
- ledger persistente de cuotas y bloqueos;
- recuperación del fallo real de `VIRU_PANEL.bat` desde Alembic 0034 con tablas creadas por ORM;
- modo por defecto sin proveedores de pago.

## Matriz de riesgo y evidencia

| Riesgo | Condición probada | Resultado esperado | Evidencia |
|---|---|---|---|
| gasto inesperado | zero-cost activo aunque existan keys de pago | FlightAware y ADS-B Exchange no se registran | `test_zero_cost_mode_never_registers_paid_providers` |
| cuota agotada | reserva local rechazada | continuar con el siguiente proveedor | `test_falls_back_after_quota_and_remote_failures_then_enriches_position` |
| exceso concurrente | 10 workers contra techo 3 | exactamente 3 reservas | `test_concurrent_reservations_cannot_exceed_hard_limit`, repetido 5 veces |
| reinicio de ventana | cambio de mes | consumo vuelve a cero sin exceder límite | `test_quota_reservation_stops_before_hard_limit_and_resets_next_month` |
| rate limit remoto | `429` con Retry-After | bloquear solo esa fuente y continuar | tests de adapters y orquestador |
| pago remoto | `402` | `payment_required`, bloqueo y fallback | `test_paid_provider_remote_failures_do_not_raise` |
| identidad ambigua | varias coincidencias equivalentes | no elegir automáticamente | tests Aviationstack y selección por adapter |
| gasto duplicado | primario ya incluye posición | no llamar enriquecimiento | `test_does_not_spend_position_quota_when_status_provider_has_position` |
| mezcla incoherente | estado de una fuente y ADS-B de otra | conservar estado/horarios primarios | test de fusión AeroDataBox + OpenSky |
| migración huérfana | Alembic 0034 y tablas 0035/0036 precreadas | reconciliar columnas, índices, unicidad y avanzar | `test_upgrade_repairs_orphan_live_tracking_tables_created_by_orm` |
| pérdida de datos | migración sobre base local real | upgrade a head sin borrar Watches/snapshots | copia previa + inspección SQLite posterior |
| aislamiento de usuario | Watch ajena | `404 watch_not_found` | integración Watchlist existente |

## Verificación runtime

- respaldo previo: `C:\Users\javiru\.codex\backups\viru-tracker\viru.db.pre-live-provider-fallback-20260721-220000.bak`;
- el launcher `iniciar_viru.ps1`, usado por el panel, completó auditoría, migración y arranque;
- backend `GET /health`: HTTP 200;
- frontend `/`: HTTP 200;
- revisión real de DB: head 0037, columnas reconciliadas, índices de lock normalizados, unicidad de snapshot presente y ledger creado con cero consumo;
- ninguna key de los seis proveedores estaba configurada durante el smoke, por lo que no se gastó cuota externa.

## Seguridad y calidad

- keys solo desde entorno y solo en headers o body OAuth; no se persisten ni se registran;
- URLs de proveedor proceden de configuración operativa, no de input HTTP;
- el endpoint conserva autenticación y filtro de propiedad de Watchlist;
- `pip check`: sin dependencias rotas;
- Bandit no está instalado; se realizó revisión manual focalizada de secretos, outbound HTTP y errores remotos;
- `ruff check app tests alembic`: verde;
- el formato de todos los módulos, migraciones y tests nuevos está validado; `models.py` y el check global conservan deuda previa fuera de alcance.

## Resultados automatizados finales

- suite backend completa: `1004 passed, 2 skipped` en 268,11 s;
- matriz focalizada de adapters, fallback, ledger, registry e integración live: 54 tests verdes;
- stress de reserva concurrente: 5 ejecuciones consecutivas verdes;
- migración limpia `upgrade → downgrade 0034 → upgrade`: head 0037 y `alembic check` sin operaciones nuevas;
- mypy aislado sobre los 9 módulos nuevos: sin issues;
- `ruff check app tests alembic`: verde;
- `oma docs verify`: 715 documentos y 5.344 referencias; ningún enlace roto nuevo en ADR-005/006, contrato, runbook, QA, índice o inventario. El baseline global conserva 309 hallazgos previos, principalmente ejemplos dentro de `.agents` y archivo histórico.

## Limitaciones residuales

- los contratos HTTP se validaron con payloads mínimos basados en la documentación oficial, sin gastar cuotas ni requerir cuentas del usuario;
- un smoke real por proveedor requiere credenciales propias y debe ejecutarse de uno en uno manteniendo los techos locales;
- cuotas y precios de terceros pueden cambiar; antes de elevar un límite hay que contrastar el dashboard del proveedor.

## Criterio de salida

El cierre exige suite backend completa, tests focalizados, lint, arranque real del panel, revisión del diff, migración real a head y publicación en `main`. Todas las puertas técnicas están superadas; la única limitación es que los smokes contra cuentas externas requieren credenciales del usuario y consumirían cuota.
