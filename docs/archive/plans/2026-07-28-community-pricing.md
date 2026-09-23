# Community Pricing Implementation Plan

> **For Codex:** execute each task completely, keep one implementation owner, and verify the matching runtime surface before marking it done.

**Goal:** recopilar precios finales reales por viajero desde vuelos comprados o caducados de Watchlist y publicar estadísticas anónimas por ruta direccional durante 12 meses cuando existan al menos 3 usuarios distintos.

**Architecture:** una tabla propia y owner-scoped almacena una respuesta por vuelo de Watchlist. El backend deriva elegibilidad por compra o fecha caducada, construye una presentación agregada en lote y solo expone mínimo/máximo al superar el umbral de privacidad. El frontend añade una acción `Comprado` y un cajón de cola reutilizable, sin mezclar estos datos con Fare Memory ni `PriceSnapshot`.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL/SQLite de test, Next.js 15, React 19, TypeScript, CSS existente de Viru, pytest y Playwright/Chrome.

---

**Estado:** en ejecución
**Fecha:** 2026-07-28
**Área:** plan
**Fuente de verdad:** no; plan operativo respaldado por el diseño aprobado y los contratos vivos

## Task 1: Congelar contrato y regresiones de backend

**Files:**

- Create: `backend/tests/integration/test_community_pricing.py`
- Read: `backend/app/api/v1/watchlist.py`
- Read: `backend/app/domain/schemas.py`
- Read: `backend/app/infrastructure/db/models.py`

**Step 1: Write the failing tests**

- compra owner-scoped;
- elegibilidad por caducidad;
- validación `flew/price`;
- ocultación con menos de 3 usuarios;
- publicación con 3 usuarios;
- exclusión de ruta inversa y fecha anterior a 12 meses;
- edición y borrado de la propia respuesta.

**Step 2: Run the focused test**

Run: `uv run pytest backend/tests/integration/test_community_pricing.py -q`

Expected: FAIL porque modelo, schemas y endpoints todavía no existen.

## Task 2: Añadir persistencia y migración

**Files:**

- Modify: `backend/app/infrastructure/db/models.py`
- Create: `backend/alembic/versions/0039_add_community_pricing.py`
- Modify: `backend/app/domain/vocabulary.py`

**Step 1: Implement the minimal model**

- `CommunityPriceReport`;
- clave única por `watch_id`;
- FK a vuelo y usuario;
- checks de coherencia entre vuelo y precio;
- índices para propietario y agregación.

**Step 2: Verify migration**

Run: `uv run alembic -c backend/alembic.ini upgrade head`

Expected: migración aplicada sin heads divergentes.

## Task 3: Implementar contrato API y agregación privada

**Files:**

- Modify: `backend/app/domain/schemas.py`
- Create: `backend/app/services/community_pricing.py`
- Modify: `backend/app/api/v1/watchlist.py`

**Step 1: Add typed request/response models**

- respuesta propia;
- estado de elegibilidad;
- agregado con campos sensibles opcionales;
- entrada de reporte con validación de precio.

**Step 2: Add owner-scoped mutations**

- `POST /api/v1/watchlist/{watch_id}/mark-purchased`;
- `PUT /api/v1/watchlist/{watch_id}/community-price`;
- `DELETE /api/v1/watchlist/{watch_id}/community-price`.

**Step 3: Add batched presentation**

- cargar respuestas propias sin N+1;
- agregar por ruta direccional y ventana de 12 meses;
- contar usuarios distintos;
- ocultar rango hasta el umbral 3.

**Step 4: Make tests pass**

Run: `uv run pytest backend/tests/integration/test_community_pricing.py backend/tests/integration/test_watchlist_flow.py -q`

Expected: PASS.

## Task 4: Añadir tipos, mutaciones y estado frontend

**Files:**

- Modify: `frontend/src/modules/watchlist/types.ts`
- Modify: `frontend/src/modules/watchlist/useWatchlistMutations.ts`
- Modify: `frontend/src/modules/watchlist/useWatchlistActions.ts`
- Create: `frontend/src/modules/watchlist/useCommunityPricing.ts`

**Step 1: Model the UI states**

- pendiente por compra/caducidad;
- pregunta de vuelo;
- captura de precio;
- guardado, error y confirmación.

**Step 2: Add API mutations**

- marcar comprado;
- guardar/editar respuesta;
- eliminar respuesta;
- reemplazar el elemento actualizado en la lista.

**Step 3: Verify types**

Run: `npm --prefix frontend run typecheck`

Expected: PASS.

## Task 5: Construir cajón y acción de fila

**Files:**

- Create: `frontend/src/modules/watchlist/components/CommunityPricingDrawer.tsx`
- Modify: `frontend/src/modules/watchlist/components/SmartWatchListPanel.tsx`
- Modify: `frontend/src/app/(private)/watchlist/page.tsx`
- Modify: `frontend/src/i18n/domains/watchlist.ts`
- Modify: `frontend/src/styles/screens.css`

**Step 1: Add row affordances**

- `Comprado` para vuelos activos no caducados;
- `Responder` para pendientes;
- `Editar respuesta` para respuestas ya guardadas;
- resumen comunitario junto a la información secundaria.

**Step 2: Add accessible drawer**

- foco inicial y cierre con Escape;
- etiquetas asociadas al input;
- validación visible;
- cola de pendientes;
- experiencia lateral en escritorio y completa en móvil.

**Step 3: Add dual-theme styling**

- usar tokens existentes;
- sin colores huérfanos;
- estados hover/focus/reduced-motion;
- ancho y densidad compatibles con las filas actuales.

**Step 4: Verify build**

Run: `npm --prefix frontend run lint`

Run: `npm --prefix frontend run build`

Expected: PASS.

## Task 6: Documentar el contrato vivo

**Files:**

- Modify: `docs/product/watchlist.md`
- Create: `docs/reference/backend/community-pricing-contract.md`
- Modify: `docs/INDICE_UNICO.md`
- Modify: `docs/DOCS_INVENTORY.md`
- Modify: `HISTORY.md`

**Step 1: Record behavior and privacy**

- unidad de precio;
- ventana y dirección de ruta;
- umbral;
- endpoints;
- propiedad, edición y borrado.

**Step 2: Verify references**

Run: `rg -n "community-pricing|Community Pricing|precio por viajero" docs HISTORY.md`

Expected: contrato localizable desde índice e inventario, sin referencias rotas.

## Task 7: QA real, auditoría y publicación

**Files:**

- Test: `backend/tests/integration/test_community_pricing.py`
- Test: `/watchlist` en navegador real

**Step 1: Verify live API**

- arrancar backend con una base de QA aislada;
- crear usuarios y vuelos mediante API;
- ejecutar compra, `No volé`, precio válido y umbral de 3;
- probar entrada inválida y autorización cruzada.

**Step 2: Verify live UI**

- abrir `/watchlist`;
- pulsar `Comprado`;
- completar `Sí, volé` y precio;
- cerrar con `Ahora no` y reabrir desde la fila;
- verificar vuelo caducado;
- verificar tema claro/oscuro;
- verificar 375, 768 y 1280 px;
- inspeccionar consola y red.

**Step 3: Run required reviews**

- ejecutar revisión de trabajo;
- ejecutar auditoría de depuración con tres hipótesis y evidencia runtime;
- corregir cualquier hallazgo y repetir checks afectados.

**Step 4: Review and publish**

Run: `git diff --check`

Run: `git status --short`

- revisar diff completo;
- stage solo de archivos de Community Pricing;
- commit convencional en `main`;
- push a `origin/main`.
