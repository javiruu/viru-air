# Plan de Implementación - Fusión Watchlist + Histórico

Fecha: 2026-02-18  
Scope: Frontend privado (`/watchlist`, `/history`, `/dashboard`)  
Estado: En ejecución

## 1. Objetivo
Crear un **Panel de Control de Seguimiento de Vuelos Unificado** donde vigilancia y análisis convivan en una sola pantalla, sin perder ninguna funcionalidad existente y con una UX más clara y agradable.

## 2. Funcionalidades que se preservan (No regresión)
- Múltiples vuelos vigilados simultáneamente.
- Precio actual visible por vuelo.
- Refresh rápido por vuelo y por vista filtrada.
- Alta de nuevo vuelo desde CTA principal.
- Comparativa de tendencias entre vuelos (2 fechas y multi-vuelo hasta 3).
- Filtros por origen, destino, fecha y punto de consulta.
- Gráfico histórico detallado con hover/tooltip.
- Indicadores de media, mínimo, máximo y número de puntos.
- Selector de rango temporal y vista acotada.
- Calendario/heatmap y explicación de precio orientativo.

## 3. Diseño UX objetivo (una pantalla)
### A. Control general (cabecera)
- Título: **Seguimiento de Vuelos**.
- CTA primario: **Añadir vuelo**.
- Indicadores: vuelos activos + última actualización global.

### B. Lista inteligente de vuelos
- Tarjetas compactas y seleccionables con:
  - ruta, fecha, precio actual, variación, frescura.
  - refresh individual.
  - mini tendencia visual (sparkline ligero) cuando haya datos.
- Acciones de productividad:
  - filtro por texto (ruta/fecha),
  - orden por frescura/precio/variación.

### C. Análisis principal del vuelo seleccionado
- Bloque protagonista: gráfico histórico grande y elegante.
- Controles: rango temporal, zoom/reset, punto de consulta.
- KPIs visibles: media, mínimo, máximo, número de puntos.
- Tooltip claro y detalle contextual de punto seleccionado.

### D. Herramientas secundarias
- Comparativa de 2 fechas.
- Comparativa multi-vuelo (hasta 3).
- Calendario + lectura de calor.
- Bloque de ayuda: “¿Qué significa este precio?”.

## 4. Cambios técnicos previstos
1. `frontend/src/app/(private)/watchlist/page.tsx`
- Reestructurar cabecera y paneles para jerarquía visual unificada.
- Añadir estado de vuelo seleccionado desde la lista.
- Añadir filtro + ordenación de tarjetas.
- Conectar selección de tarjeta con análisis (filtros + fecha activa).
- Añadir mini-sparkline por vuelo a partir del histórico ya cargado.

2. `frontend/src/app/(private)/history/page.tsx`
- Mantener compatibilidad de ruta redirigiendo al panel unificado (`/watchlist`).

3. `frontend/src/app/(private)/dashboard/page.tsx`
- Actualizar CTAs de Histórico para apuntar a Watchlist unificada.
- Ajustar copy para reforzar “panel unificado”.

4. `frontend/src/styles/globals.css`
- Añadir estilos de layout del panel unificado.
- Estados de tarjeta seleccionada/hover/teclado.
- Estilos de mini-sparkline y controles de lista inteligente.

5. Documentación
- Crear índice de documentación en `docs/INDICE_UNICO.md`.
- Añadir checklist PR ejecutable en `docs/qa/watchlist-history-fusion-pr-checklist.md`.

## 5. Criterios de aceptación
- El usuario puede gestionar y analizar vuelos **sin cambiar de pantalla**.
- `/history` no actúa como sección independiente funcional; redirige al panel unificado.
- Todas las funciones listadas en sección 2 siguen operativas.
- El vuelo seleccionado domina visualmente el análisis.
- UX clara en desktop y mobile (sin saturación visual).

## 6. Verificación técnica
```powershell
cd frontend
npm run test
npm run lint
```

Verificaciones específicas:
```powershell
rg -n 'href="/history"' frontend/src/app
rg -n 'Seguimiento de Vuelos|panel unificado|histórico integrado' frontend/src/app/(private)
rg -n 'watch-smart|watch-spark|watch-selected' frontend/src/styles/globals.css
```

## 7. Riesgos y mitigaciones
- Riesgo: complejidad creciente en `watchlist/page.tsx`.
  - Mitigación: mantener utilidades en módulos (`dateUtils`) y separar helpers puros para cálculos de lista.
- Riesgo: regresiones de copy/flujo por cambio de navegación.
  - Mitigación: actualizar CTAs y mantener redirección de compatibilidad desde `/history`.

## 8. Log esperado
Se registrará ejecución completa en `logs_ia/` con:
- archivos modificados,
- pruebas ejecutadas,
- hallazgos/residuos,
- próximos pasos.
