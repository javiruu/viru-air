# Community Route Intelligence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** exponer popularidad semanal exacta y señales comunitarias anónimas en Dashboard, Quick Search y Watchlist, reproduciendo la variante Lazyweb `Corredores más buscados`.

**Architecture:** un rollup diario anónimo complementa el contador acumulado existente. Un servicio comunitario agrupa popularidad, rangos públicos y co-ocurrencia con umbrales de privacidad, expuestos por endpoints ligeros. El frontend consume esos contratos en lote y degrada cada señal sin afectar los flujos principales.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, Next.js 15, React 19, TypeScript, CSS Modules, pytest, Node test runner y navegador Chrome/Playwright.

---

**Estado:** en ejecución  
**Fecha:** 2026-08-01  
**Área:** plan  
**Fuente de verdad:** no; plan operativo respaldado por el diseño aprobado y los contratos vivos

## Task 1: Proteger el contrato de popularidad diaria

**Files:**

- Modify: `backend/tests/unit/test_quick_search_popularity.py`
- Modify: `backend/app/infrastructure/db/models.py`
- Create: `backend/alembic/versions/0040_add_quick_search_popularity_daily.py`
- Modify: `backend/app/services/quick_search_popularity.py`

**Steps:**

1. Añadir una prueba roja que exija acumulado histórico y bucket diario en una sola operación.
2. Crear modelo y migración con unicidad por día, ruta y moneda, sin backfill falso.
3. Hacer pasar `backend/tests/unit/test_quick_search_popularity.py` y la auditoría Alembic.

## Task 2: Crear inteligencia comunitaria privada

**Files:**

- Create: `backend/tests/integration/test_community_route_intelligence.py`
- Create: `backend/app/services/community_route_intelligence.py`
- Create: `backend/app/api/v1/community_routes.py`
- Modify: `backend/app/domain/schemas.py`
- Modify: `backend/app/api/v1/router.py`

**Steps:**

1. Escribir pruebas rojas para top semanal, top 20 %, lote de precios y rutas relacionadas.
2. Implementar consultas agregadas direccionales y umbral de 3 usuarios distintos.
3. Exponer `popular`, `insights` y `related` con modelos Pydantic y autenticación existente.
4. Verificar casos públicos, privados, ruta inversa y respuesta vacía.

## Task 3: Construir `Corredores más buscados`

**Files:**

- Create: `frontend/src/modules/community-routes/communityRoutesApi.ts`
- Create: `frontend/src/modules/community-routes/communityRoutesTypes.ts`
- Create: `frontend/src/modules/community-routes/CommunityCorridorsPanel.tsx`
- Create: `frontend/src/modules/community-routes/CommunityCorridorsPanel.module.css`
- Modify: `frontend/src/app/(private)/dashboard/page.tsx`
- Modify: `frontend/src/i18n/domains/dashboard.ts`

**Steps:**

1. Añadir normalización del contrato y prueba de datos incompletos.
2. Implementar la banda de 10 celdas, ranking compacto, estados vacío/carga y enlaces precargados.
3. Integrar la cuadrícula Descubrimiento 42/58 con la oportunidad existente.
4. Comparar 1280 px con el mockup y comprobar adaptación 768/375, claro/oscuro.

## Task 4: Añadir precios a Quick Search

**Files:**

- Modify: `frontend/src/modules/quick-search/components/QuickSearchResultsList.tsx`
- Create: `frontend/src/modules/community-routes/useCommunityRouteInsights.ts`
- Modify: `frontend/src/i18n/domains/quickSearch.ts`

**Steps:**

1. Solicitar en lote las rutas visibles sin N+1.
2. Mostrar la frase pública con moneda y ocultarla bajo umbral.
3. Verificar búsqueda normal, rango disponible y degradación del endpoint comunitario.

## Task 5: Añadir señales y rutas relacionadas a Watchlist

**Files:**

- Modify: `frontend/src/modules/watchlist/components/WatchRow.tsx`
- Modify: `frontend/src/modules/watchlist/components/CommunityPricingDrawer.tsx`
- Create: `frontend/src/modules/community-routes/CommunityRouteSignal.tsx`
- Create: `frontend/src/modules/community-routes/RelatedCommunityRoutes.tsx`
- Modify: `frontend/src/i18n/domains/watchlist.ts`

**Steps:**

1. Reutilizar el lote de insights para un badge compacto por fila.
2. Cargar hasta 3 rutas relacionadas cuando se abre el drawer.
3. Verificar conteo >5, tendencia, estado combinado, privacidad y navegación.

## Task 6: Añadir referencia comunitaria al historial vacío

**Files:**

- Modify: `frontend/src/modules/watchlist/components/HistoryIntegratedPanel.tsx`
- Create: `frontend/src/modules/community-routes/CommunityPriceReferenceBand.tsx`

**Steps:**

1. Detectar ausencia de snapshots personales y rango comunitario público.
2. Mostrar una banda de referencia sin colorear días concretos.
3. Preservar el historial personal cuando existe y verificar ambos estados.

## Task 7: Actualizar contratos y evidencias

**Files:**

- Modify: `docs/reference/backend/community-pricing-contract.md`
- Modify: `docs/reference/backend/quick-search-contract.md`
- Modify: `docs/product/dashboard.md`
- Modify: `docs/product/quick-search.md`
- Modify: `docs/product/watchlist.md`
- Modify: `HISTORY.md`
- Create: `docs/qa/reports/2026-08-01-community-route-intelligence.md`

**Steps:**

1. Documentar ventana, endpoints, privacidad, degradación y fecha de cobertura exacta.
2. Ejecutar pruebas backend y frontend focalizadas, comprobación de tipos y build de producción.
3. Probar API viva y las superficies `/dashboard`, `/quick-search` y `/watchlist` en navegador real.
4. Registrar comparación con el mockup, temas, breakpoints, consola y red.

## Task 8: Revisar y publicar

**Steps:**

1. Ejecutar revisión de trabajo y auditoría runtime con tres hipótesis y evidencia.
2. Revisar `git diff --check`, diff completo y estado del árbol.
3. Stagear solo cambios de esta entrega, crear commits atómicos en `main` y hacer push a `origin/main`.
