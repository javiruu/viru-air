# QA - inteligencia comunitaria de rutas

**Fecha:** 2026-08-01

**Entorno:** FastAPI, SQLite aislado, Next.js 15.5.22 en producción y Chromium controlado por navegador

**Resultado:** PASS

## Comportamiento observado

1. El panel `Corredores más buscados` mostró las diez rutas de los últimos siete días, una banda de calor de diez segmentos y el orden esperado. Al activar la primera fila navegó a `/quick-search?origin=MAD&destination=BCN` con ambos aeropuertos precargados.
2. Una búsqueda real MAD-BCN devolvió un vuelo y mostró `3 viajeros de Viru pagaron 45–78 € por persona en esta ruta.` sin exponer respuestas individuales.
3. La fila MAD-BCN del Watchlist mostró `6 siguiendo · En tendencia`; MAD-LIS, con menos seguidores y fuera del top 20 %, no mostró un indicador comunitario falso.
4. El histórico sin snapshots personales mostró una única referencia comunitaria de 45–78 €/persona, sin colorear fechas como si existieran observaciones diarias.
5. El drawer comunitario mostró MAD-LIS bajo `Quienes miran MAD → BCN también miran…`, con tres viajeros y la explicación del umbral anónimo.

## Fidelidad visual

- A 1280 × 900, el bloque comunitario conserva la composición de dos columnas del mockup: panel estrecho a la izquierda y Oportunidades a la derecha.
- A 768 × 900 y 375 × 812, los bloques se apilan y permanecen visibles las diez filas, el rango, el contador y los enlaces.
- Los temas claro y oscuro conservan contraste, identidad cálida y la jerarquía del heat strip.
- La comparación detectó y corrigió una interferencia del estilo histórico `.module-card-opportunity`, cuyo `grid-column: span 4` apilaba la tarjeta en escritorio. El override local deja el grid 42/58 bajo control del nuevo módulo.

## Evidencia automática

- Backend focalizado: 17 pruebas superadas, 0 fallos.
- Frontend focalizado: 24 pruebas superadas, 0 fallos; incluye redacción de muestras privadas y lotes de 100 rutas.
- TypeScript: `npx tsc --noEmit` sin errores.
- Build de producción aislado: compilación, typecheck y 35 páginas generadas.
- Migración completa ejecutada sobre SQLite aislado hasta `0040_add_qs_popularity_daily`.
- `git diff --check` sin errores después de normalizar el documento de producto.

## API viva

- `GET /community/routes/popular`: 10 rutas; MAD-BCN en primera posición.
- `POST /community/routes/insights`: dos rutas solicitadas; muestra pública 3 y rango 45–78 EUR para MAD-BCN.
- `GET /community/routes/MAD/BCN/related`: una ruta; MAD-LIS con tres viajeros.

## Auditoría de depuración

1. **Hipótesis: la tarjeta se apila por el breakpoint nuevo.** Refutada. El viewport medido era 1280 px y el grid nuevo estaba activo; el valor observado `grid-column: span 4` venía del componente de Oportunidades existente. Tras limitarlo a `auto`, la composición volvió a ser lateral.
2. **Hipótesis: la API entrega menos de diez corredores o altera el orden.** Refutada. La respuesta viva devolvió diez elementos y el máximo quedó primero.
3. **Hipótesis: el frontend pierde los agregados en su normalización.** Refutada. El navegador mostró el rango, el badge combinado, el fallback histórico y la co-ocurrencia con los mismos valores que la API.

## Observaciones no bloqueantes

- La consola no registró errores. Conserva un warning previo de bootstrap de Quick Search y warnings del mapa sin estilo, ajenos a esta funcionalidad.
- React Doctor no marcó archivos comunitarios nuevos; sus 25 avisos en el alcance de cambios corresponden a componentes grandes o modificaciones locales anteriores y no se ampliaron en este trabajo.
