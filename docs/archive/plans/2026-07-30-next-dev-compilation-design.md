# Diseño de compilación anticipada para Next.js en desarrollo

**Estado:** aprobado
**Fecha:** 2026-07-30
**Fuente de verdad:** no
**Área:** frontend / experiencia de desarrollo

## Objetivo

Reducir el tiempo de compilación inicial y evitar que la primera visita a cada
sección de Viru Air quede bloqueada por la compilación bajo demanda de Next.js.

## Contexto observado

- El frontend usa Next.js 15.5.22.
- `npm run dev` arranca `next dev`, que en esta versión usa Webpack si no se
  solicita Turbopack.
- `next.config.js` mantiene un alias Webpack para `@`, aunque el mismo alias ya
  está definido en `tsconfig.json`.
- Next.js compila las rutas bajo demanda en desarrollo y desactiva el prefetch
  normal de `<Link>` en ese entorno.
- El árbol `frontend/src/app` contiene páginas públicas, privadas, de
  preferencias y administración que pueden descubrirse desde sus archivos
  `page.tsx`.

## Alternativas consideradas

### 1. Prefetch desde React

Usar `router.prefetch()` o confiar en los `<Link>`.

Descartado porque el prefetch de rutas no está activo en desarrollo y porque
necesitaría que un navegador ejecutase la aplicación antes de comenzar.

### 2. Calentamiento exclusivo desde `iniciar_viru.ps1`

Enviar peticiones a todas las rutas después de que el lanzador detecte el
frontend.

Descartado como solución principal porque no cubriría a quien arranque el
frontend directamente con `npm run dev` y duplicaría conocimiento del árbol de
rutas en PowerShell.

### 3. Turbopack y supervisor Node de desarrollo

Arrancar Next.js con Turbopack desde un supervisor local que espere a que la
portada responda y, después, solicite en segundo plano todas las páginas
estáticas con una cola de concurrencia uno.

Elegido porque acelera la compilación, funciona en Windows y desde ambos
flujos de arranque, y mantiene el calentamiento fuera del runtime de
producción y de los componentes de interfaz.

## Diseño aprobado

### Arranque

`npm run dev` ejecutará un script Node que:

1. lanza el binario local de Next.js con Turbopack;
2. conserva los argumentos adicionales de CLI;
3. detecta el puerto efectivo;
4. espera a que `/` responda;
5. inicia el calentamiento sin bloquear el proceso de Next ni la navegación.

El proceso hijo heredará la entrada y salida de la terminal para preservar los
logs y el comportamiento actual del lanzador.

### Descubrimiento de rutas

El calentador recorrerá `src/app/**/page.tsx` en cada arranque:

- eliminará grupos de rutas como `(private)` y `(public)`;
- ignorará slots paralelos y segmentos dinámicos;
- excluirá rutas API;
- normalizará y deduplicará las rutas;
- priorizará las superficies principales y ordenará el resto de forma
  determinista.

Así, las nuevas páginas estáticas se incorporarán automáticamente sin mantener
una lista manual.

### Calentamiento controlado

Las rutas se solicitarán una a una mediante HTTP local, consumiendo el cuerpo
completo para que Next termine la compilación. Cada petición tendrá timeout y
su fallo se registrará sin detener el servidor ni cancelar el resto de la
cola.

La variable `VIRU_ROUTE_WARMUP=0` permitirá desactivar el comportamiento para
diagnóstico. El calentamiento solo existirá en `npm run dev`; `next build` y
`next start` no cambiarán.

### Configuración de Next

Se eliminará la personalización Webpack que únicamente recrea el alias `@`.
`tsconfig.json` seguirá siendo la fuente del alias, compatible con Turbopack y
con el build de producción.

No se añadirá `optimizePackageImports`: Turbopack ya analiza esos imports y
añadir configuración experimental redundante aumentaría la superficie de
mantenimiento.

## Fallos y degradación

- Si Next no llega a responder, el calentador dejará de reintentar y Next
  seguirá vivo para que el error principal permanezca visible.
- Un 4xx o una redirección se considerarán respuestas válidas para completar
  la compilación de la ruta.
- Un 5xx, timeout o error de red quedará identificado por ruta y no bloqueará
  las demás.
- La cola secuencial evita una ráfaga de compilaciones que compita por CPU y
  memoria con la primera interacción del usuario.

## Verificación

1. Pruebas unitarias del descubrimiento, normalización, prioridad y exclusión
   de rutas.
2. Typecheck y suite frontend relevante.
3. `next build` para comprobar compatibilidad de producción.
4. Arranque real con `npm run dev`, observando Turbopack y la cola completa.
5. Navegación real a varias rutas ya calentadas, comprobando ausencia de una
   nueva compilación costosa y errores en consola.
6. Comparación reproducible de tiempos de primera petición entre el arranque
   anterior y el nuevo en un checkout temporal equivalente.

## Fuera de alcance

- Cambiar componentes, estilos o comportamiento visual.
- Ejecutar JavaScript de cada página durante el calentamiento.
- Precargar datos de usuario o llamar deliberadamente a APIs funcionales.
- Modificar el comportamiento de producción.
