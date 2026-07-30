# QA — compilación anticipada de rutas Next.js

**Fecha:** 2026-07-30

**Entorno:** Next.js 15.5.22, Node.js local, Windows, Chromium controlado por navegador

**Resultado:** PASS

## Comportamiento observado

1. El baseline con Webpack quedó listo en 5,5 s, pero la primera visita a `/`
   tardó 19,286 s; `/quick-search`, 9,723 s; y `/watchlist`, 7,444 s. Recorrer
   por primera vez las 32 rutas estáticas consumió 102,655 s.
2. Con Turbopack, una pasada comparable quedó lista en 1,859 s y sirvió `/` en
   4,608 s. El supervisor descubrió 32 rutas y calentó las 31 restantes de
   forma secuencial, sin fallos.
3. Después del calentamiento, un recorrido completo por las 32 rutas sumó
   23,206 s y ninguna petición superó 586 ms.
4. En un arranque especialmente frío después de `next build`, la portada tardó
   115 s en compilar. La espera pasiva de cinco minutos mantuvo viva la cola y
   el proceso terminó calentando 31/31 rutas, sin bloquear el servidor.
5. `VIRU_ROUTE_WARMUP=0 npm run dev -- --port 3023` arrancó Turbopack en el
   puerto solicitado, informó que el calentamiento estaba desactivado y no
   inició la cola.

## Cobertura manual

- Se abrieron `/`, `/ayuda`, `/watchlist`, `/quick-search`, `/hoteles`,
  `/preferencias` y `/admin` después del calentamiento.
- `/` y `/ayuda` conservaron el shell, no generaron overflow horizontal y no
  registraron errores ni warnings en consola.
- Las rutas privadas alcanzaron su estado de autenticación sin provocar una
  nueva compilación de módulo.
- La consulta experimental `scroll-state` del header continuó presente como
  mejora progresiva, sin pasar por el parser CSS incompatible de Turbopack.

## Evidencia automática

- Pruebas del supervisor: descubrimiento, prioridad, puerto efectivo, opt-out,
  secuencia, aislamiento de HTTP 500 y cancelación activa.
- Suite frontend completa: 470 pruebas superadas, 0 fallos y 17 E2E omitidos
  por no estar disponibles los servicios locales en los puertos 3000/8000.
- Typecheck sin emisión ejecutado correctamente desde `/frontend`.
- Build aislado: compilación, lint, typecheck y generación de 35 páginas.

## Auditoría de depuración

1. **Hipótesis: se omiten o inventan rutas.** Descartada: el descubrimiento
   devolvió exactamente las 32 páginas estáticas presentes en `src/app`; las
   rutas dinámicas y slots paralelos quedaron excluidos por contrato.
2. **Hipótesis: el calentamiento satura o bloquea el arranque.** Descartada: la
   portada responde antes de la cola, la concurrencia máxima observada es uno y
   un fallo HTTP 500 no impide continuar con la siguiente ruta.
3. **Hipótesis: Turbopack rompe compatibilidad o producción.** Descartada: se
   aisló la única incompatibilidad, la consulta CSS `scroll-state`, y el build
   de producción generó las 35 páginas. Los fallos `ENOENT` observados durante
   la revisión procedían de ejecutar `next dev` y `next build` simultáneamente
   sobre la misma `.next`; el build aislado finalizó correctamente.
