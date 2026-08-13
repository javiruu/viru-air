# Limpieza masiva y retirada segura de legado

**Estado:** vivo
**Fecha:** 2026-08-13
**Fuente de verdad:** sí
**Área:** mantenimiento, contratos y migración

## Objetivo

Eliminar código interno huérfano sin cortar rutas, contratos o datos persistidos que continúan activos. La retirada de compatibilidad queda condicionada a evidencia agregada de uso cero durante 30 días consecutivos.

## Inventario verificable inicial

- El inventario de `frontend/src` y `backend/app` contiene 522 archivos fuente.
- El compilador TypeScript, con `noUnusedLocals` y `noUnusedParameters`, no encontró símbolos sin uso.
- Ruff, con las reglas de importaciones y variables sin uso (`F401`, `F841`), no encontró hallazgos en `backend/app` ni `backend/tests`.
- Las rutas públicas `/history`, `/alerts`, `/preferences` y `/suggestions`, los normalizadores de transporte y los campos hoteleros `legacy_*` tienen referencias activas o datos persistidos; no son candidatos a borrado inmediato.

Este inventario se repite antes de cada lote. Un resultado de herramientas estáticas no autoriza retirar por sí solo una compatibilidad pública o persistida.

## Fase 1: limpieza inmediata demostrable

1. Eliminar imports, exports, helpers, estados, pruebas y archivos sin referencias comprobables.
2. Ejecutar análisis de referencias, TypeScript/Python estricto, pruebas cercanas y build.
3. Publicar cada lote en un commit pequeño y reversible.

La línea base de esta fase es el commit `a172c3f0`, que eliminó código muerto interno sin afectar contratos activos.

## Fase 2: compatibilidad de Quick Search

Los aliases legacy de Quick Search continúan aceptándose por defecto. Cada alias detectado emite `quick_search_legacy_alias_used` con solo:

- `alias`;
- `app_env`;
- `contract_version=quick_search.v2`.

No se registra identificador de usuario, payload, ruta ni `query_trace_id`. El evento está deduplicado por alias dentro de cada solicitud.

El modo se controla con `QUICK_SEARCH_LEGACY_ALIASES_MODE`:

- `observe` (predeterminado): compatibilidad activa y medición agregada.
- `block`: rechaza aliases con `400 quick_search_legacy_aliases_blocked`; se usa primero en desarrollo y canary.

Secuencia de retirada:

1. Mantener `observe` en producción y consolidar uso diario por alias y entorno.
2. Activar `block` en desarrollo y canary; comprobar que el payload canónico sigue funcionando y que no hay llamadas a proveedores para solicitudes rechazadas.
3. Tras 30 días consecutivos de uso agregado cero en producción, retirar aliases, sus pruebas de compatibilidad y la documentación asociada en una release separada.
4. Verificar contratos canónicos, rutas afectadas y rollback antes de promocionar la retirada.

## Hoteles: migración antes de borrar

Los campos y relaciones hoteleras heredadas no se retiran junto con Quick Search. La futura retirada requiere una release de expansión/contracción:

1. Backfill de referencias canónicas sobre una copia verificable de los datos.
2. Validación de integridad, conteos y lecturas canónicas antes de cambiar escrituras.
3. Canary con lecturas canónicas y rollback operativo.
4. Release posterior que elimine columnas, índices, tests y lógica antigua, solo después de confirmar que no quedan lectores ni datos dependientes.

## Evidencia mínima por retirada

- Búsqueda de referencias y contratos afectados.
- TypeScript/Python estricto, pruebas relevantes y build.
- Migración ejecutada sobre copia de datos cuando haya persistencia.
- Canary sin aliases y comprobación real de las rutas afectadas.
- Revisión de diff y commit reversible directamente en `main`.
