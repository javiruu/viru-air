# QA manual — estimación automática de precio comparable

**Fecha:** 2026-07-28

**Rutas:** `/quick-search`, `/watchlist`

**Entorno:** build de producción local, Chromium controlado por navegador

**Resultado:** PASS

## Escenarios observados

1. En `/quick-search`, búsqueda real `MAD → VLC` para 2026-07-29:
   - el resultado Vueling mostró precio base 49,03 EUR;
   - al seleccionar cabina 10 kg, maleta 20 kg, seguro, Fast Track y prioridad,
     el total cambió a `Desde 73,03 EUR`;
   - seguro, Fast Track y prioridad quedaron identificados como tres extras sin
     tarifa pública calculable;
   - la estimación enlazó la tabla oficial de tarifas de Vueling;
   - no apareció ningún campo para introducir importes.
2. En `/watchlist`, ruta `AGP → ATH` con precio observado 220,98 EUR:
   - la misma cesta mostró `Desde 244,98 EUR`;
   - el resumen mantuvo tres extras sin tarifa pública;
   - tras pulsar `Guardar cesta` y recargar, permanecieron seleccionados los
     cinco extras y se conservó el mismo total.
3. Estados de honestidad comprobados mediante pruebas focalizadas:
   - los paquetes Ryanair y Wizz de cabina + prioridad se cobran una sola vez;
   - los servicios por vuelo multiplican viajeros por número de tramos;
   - Flex Pack de Vueling se cobra una vez por viajero y reserva;
   - itinerarios con aerolíneas mezcladas, divisas no soportadas y aerolíneas
     desconocidas no heredan una tarifa incorrecta;
   - cualquier extra no calculable fuerza una presentación `Desde`.

## Cobertura visual y de interacción

- Escritorio, tema claro: selección, total, aviso y fuente oficial visibles.
- Viewport móvil 390 × 844: total y fuente oficial permanecen visibles.
- Tema oscuro en móvil: misma jerarquía y total conservados.
- Consola de la pasada final: cero errores.
- Persistencia real: guardado y lectura posterior mediante recarga completa.

## Evidencia técnica relacionada

- Frontend focalizado: 20/20 pruebas superadas.
- Backend focalizado: 20/20 pruebas superadas; Ruff sin hallazgos.
- Build de producción: compilación, typecheck y 35 páginas generadas.
- Suite frontend completa: 463/466; permanecen tres fallos E2E ajenos a este
  cambio (selector de fecha con timeout, TestSprite real con timeout y contrato
  ultra-strict sin `origin`).
