# Correcciones post-cierre de `/hoteles` — Plan de implementación

> **Para Claude/Codex:** REQUIRED SUB-SKILL: Usa `superpowers:executing-plans` para implementar este plan tarea por tarea.

**Goal:** Corregir 8 gaps detectados en `/hoteles` tras el cierre de las 10 fases: integrar el buscador por área real, unificar watchlist/tracked-offers, añadir histórico de snapshots, refactorizar HotelRadarPage, implementar DELETE comp-set, y polish de alertas.

**Architecture:** Backend FastAPI + SQLAlchemy. Frontend Next.js/TypeScript con módulos bajo `frontend/src/modules/hotels/`. CSS canónico en `frontend/src/styles/screens.css`. i18n en `frontend/src/i18n/domains/hotels.ts`. Testing backend con pytest, frontend con `npm run build` + `npx tsc --noEmit`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic, React 18, Next.js, TypeScript, CSS modules

**Source of truth:** `hoteles_3.txt` (plan de 10 fases), `docs/specs/hotels-intelligence-mvp.md`, `docs/qa/hotels-pending-closeout.md`, `AGENTS.md`

---

## Orden de ejecución

Las fases están ordenadas por dependencias:
1. **Fase A** — Backend independiente (DELETE comp-set)
2. **Fase B** — Refactor estructural habilitador (extraer hooks)
3. **Fase C** — Unificación de seguimientos (Watchlist → TrackedOffers + initial_price + snapshots)
4. **Fase D** — Buscador por área real (area-search UI + area-resolve autocomplete)
5. **Fase E** — Polish final (parity_break relegado, CSS, QA)

---

## Fase A: Backend — DELETE comp-set

### Task A1: Añadir endpoint `DELETE /api/v1/hotels/comp-sets/{comp_set_id}`

**Files:**
- Modify: `backend/app/api/v1/hotels.py` (insertar entre las rutas de comp-set existentes, después de L325 aprox.)
- Modify: `backend/app/services/hotels_service.py` (la función `delete_comp_set` ya existe)
- Test: `backend/tests/integration/test_hotels_api_flow.py` (añadir test)

**Contexto:** El frontend ya tiene `deleteHotelCompSet` en `api.ts:159` que llama a `/hotels/comp-sets/${compSetId}` con método DELETE, y `delete_comp_set` ya existe en `hotels_service.py:185`. Solo falta exponer el endpoint.

**Step 1: Añadir el endpoint en `hotels.py`**

Insertar después de la ruta `DELETE /comp-sets/{comp_set_id}/members/{member_id}` (aprox. L320):

```python
@router.delete("/comp-sets/{comp_set_id}")
def delete_comp_set(
    comp_set_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        hotels_service.delete_comp_set(db, user_id=current_user.id, comp_set_id=comp_set_id)
    except ValueError as exc:
        _raise_http_for_value_error(exc)
    except PermissionError as exc:
        _raise_http_for_permission_error(exc)
    return {"status": "ok"}
```

**Step 2: Añadir test de integración**

En `test_hotels_api_flow.py`, añadir:

```python
def test_hotels_comp_set_delete(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-comp-set-delete@viru.dev")
    headers = auth_headers(token)

    # Create a comp set
    ingest_mock_hotels(client, headers)
    search_resp = client.get("/api/v1/hotels/search", headers=headers, params={"limit": 1})
    hotel_id = search_resp.json()[0]["id"]

    create_resp = client.post(
        "/api/v1/hotels/comp-sets",
        headers=headers,
        json={"name": "To delete", "anchor_hotel_id": hotel_id},
    )
    assert create_resp.status_code == 200
    comp_set_id = create_resp.json()["id"]

    # Delete it
    delete_resp = client.delete(f"/api/v1/hotels/comp-sets/{comp_set_id}", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"status": "ok"}

    # Verify it's gone
    list_resp = client.get("/api/v1/hotels/comp-sets", headers=headers)
    assert comp_set_id not in [cs["id"] for cs in list_resp.json()]

    # Verify 404 on second delete
    second_delete = client.delete(f"/api/v1/hotels/comp-sets/{comp_set_id}", headers=headers)
    assert second_delete.status_code == 404
```

**Step 3: Añadir test de propiedad (no borrar comp-set ajeno)**

```python
def test_hotels_comp_set_delete_ownership(client: TestClient) -> None:
    token_a = register_and_token(client, email="hotels-cs-owner-a@viru.dev")
    token_b = register_and_token(client, email="hotels-cs-owner-b@viru.dev")

    ingest_mock_hotels(client, auth_headers(token_a))
    search_resp = client.get("/api/v1/hotels/search", headers=auth_headers(token_a), params={"limit": 1})
    hotel_id = search_resp.json()[0]["id"]

    create_resp = client.post(
        "/api/v1/hotels/comp-sets",
        headers=auth_headers(token_a),
        json={"name": "Mine", "anchor_hotel_id": hotel_id},
    )
    comp_set_id = create_resp.json()["id"]

    # User B tries to delete User A's comp set
    resp = client.delete(f"/api/v1/hotels/comp-sets/{comp_set_id}", headers=auth_headers(token_b))
    assert resp.status_code == 403
```

**Step 4: Ejecutar tests**

```bash
cd backend
python -m pytest backend/tests/integration/test_hotels_api_flow.py::test_hotels_comp_set_delete backend/tests/integration/test_hotels_api_flow.py::test_hotels_comp_set_delete_ownership -v
```

Expected: 2 passed

**Step 5: Commit**

```bash
git add backend/app/api/v1/hotels.py backend/tests/integration/test_hotels_api_flow.py
git commit -m "feat(hotels): add DELETE /comp-sets/{id} endpoint with ownership check"
```

---

## Fase B: Refactor estructural — Extraer hooks de HotelRadarPage

**Files:**
- Create: `frontend/src/modules/hotels/hooks/useHotelSearch.ts`
- Create: `frontend/src/modules/hotels/hooks/useHotelWatchlist.ts`
- Create: `frontend/src/modules/hotels/hooks/useHotelCompSets.ts`
- Create: `frontend/src/modules/hotels/hooks/useHotelAlerts.ts`
- Create: `frontend/src/modules/hotels/hooks/useTrackedOffers.ts`
- Create: `frontend/src/modules/hotels/hooks/useHotelDetail.ts`
- Modify: `frontend/src/modules/hotels/HotelRadarPage.tsx`

**Contexto:** `HotelRadarPage.tsx` tiene ~530 líneas con ~30 variables de estado y 15+ handlers. Extraeremos hooks personalizados manteniendo el comportamiento EXACTAMENTE igual. Cada hook exporta estado y handlers; el page component solo orquesta.

### Task B1: Crear `useHotelSearch.ts`

Extraer: `query`, `city`, `loading`, `results`, `selectedHotelId`, `errorMessage`, `handleSearch`, `handleIngest`, `runSearch`, `setSelectedHotelId`, `selectedHotel`, `featureDisabled`

```typescript
// frontend/src/modules/hotels/hooks/useHotelSearch.ts
"use client";

import { useCallback, useMemo, useState } from "react";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { ingestHotelsMock, searchHotels, HotelsRequestError } from "../api";
import type { HotelSearchOut } from "../types";

function resolveHotelMessage(error: unknown, t: ReturnType<typeof useI18n>["t"]): string {
  // ... copiar exactamente la función existente de HotelRadarPage
}

export function useHotelSearch(onAfterIngest?: () => Promise<void>) {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<HotelSearchOut[]>([]);
  const [selectedHotelId, setSelectedHotelId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectedHotel = useMemo(
    () => results.find((item) => item.id === selectedHotelId) ?? null,
    [results, selectedHotelId]
  );
  const featureDisabled = Boolean(errorMessage && errorMessage.includes("HOTEL_FEATURE_ENABLED"));

  const runSearch = useCallback(async () => {
    const list = await searchHotels({ q: query || undefined, city: city || undefined, limit: 30 });
    setResults(list);
    if (!list.some((item) => item.id === selectedHotelId)) {
      setSelectedHotelId(list[0]?.id ?? null);
    }
  }, [query, city, selectedHotelId]);

  const handleSearch = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      await runSearch();
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      setErrorMessage(message);
      notify({ tone: "error", title: message });
    } finally {
      setLoading(false);
    }
  }, [runSearch, t, notify]);

  const handleIngest = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const ingest = await ingestHotelsMock();
      notify({ tone: "success", title: t("hotels.messages.ingestSuccess", { count: ingest.hotels_processed }) });
      await runSearch();
      await onAfterIngest?.();
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      setErrorMessage(message);
      notify({ tone: "error", title: message });
    } finally {
      setLoading(false);
    }
  }, [runSearch, t, notify, onAfterIngest]);

  return {
    query, setQuery, city, setCity, loading,
    results, selectedHotelId, setSelectedHotelId, selectedHotel,
    errorMessage, featureDisabled,
    handleSearch, handleIngest, runSearch,
  };
}
```

### Task B2: Crear `useHotelDetail.ts`

Extraer: `rates`, `hotelDetail`, `loadingRates`, `paritySignals`, `parityLoading`, `parityError`

```typescript
// frontend/src/modules/hotels/hooks/useHotelDetail.ts
"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { getHotelDetail, getHotelRates, getHotelParity, HotelsRequestError } from "../api";
import type { HotelDetailOut, HotelRateOut, HotelParityOut } from "../types";

export function useHotelDetail(selectedHotelId: string | null) {
  const { t } = useI18n();
  const [rates, setRates] = useState<HotelRateOut[]>([]);
  const [hotelDetail, setHotelDetail] = useState<HotelDetailOut | null>(null);
  const [loadingRates, setLoadingRates] = useState(false);
  const [paritySignals, setParitySignals] = useState<HotelParityOut[]>([]);
  const [parityLoading, setParityLoading] = useState(false);
  const [parityError, setParityError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedHotelId) {
      setHotelDetail(null);
      setRates([]);
      setParitySignals([]);
      setParityError(null);
      setParityLoading(false);
      return;
    }
    let cancelled = false;
    setLoadingRates(true);
    setParityLoading(true);
    setParityError(null);
    Promise.allSettled([
      getHotelDetail(selectedHotelId),
      getHotelRates(selectedHotelId),
      getHotelParity(selectedHotelId),
    ]).then(([detailResult, ratesResult, parityResult]) => {
      if (cancelled) return;
      setHotelDetail(detailResult.status === "fulfilled" ? detailResult.value : null);
      setRates(ratesResult.status === "fulfilled" ? ratesResult.value : []);
      if (parityResult.status === "fulfilled") {
        setParitySignals(parityResult.value);
        setParityError(null);
      } else {
        setParitySignals([]);
        setParityError(parityResult.reason instanceof HotelsRequestError ? parityResult.reason.message : t("shared.errors.generic"));
      }
    }).finally(() => {
      if (cancelled) return;
      setLoadingRates(false);
      setParityLoading(false);
    });
    return () => { cancelled = true; };
  }, [selectedHotelId, t]);

  return { rates, hotelDetail, loadingRates, paritySignals, parityLoading, parityError };
}
```

### Task B3: Crear `useHotelWatchlist.ts`

Extraer: todo el estado de watchlist + hydrate + handlers + `busyHotelIds`

### Task B4: Crear `useHotelCompSets.ts`

Extraer: todo el estado de comp sets + anchor + nearby + handlers

### Task B5: Crear `useHotelAlerts.ts`

Extraer: `alertRules`, `alertEvents`, loading/error states, `busyRuleIds`, `alertCreateBusy`, handlers de create/toggle/delete

### Task B6: Crear `useTrackedOffers.ts`

Extraer: `trackedOffers`, loading, `busyOfferIds`, `busyHotelIds`, `refreshTrackedOffers`, `handleTrackPrice`, `handleStopTracking`

### Task B7: Reescribir `HotelRadarPage.tsx` para usar los hooks

El page component debe quedar reducido a ~150 líneas de orquestación pura. Mantener:
- `collapsedPanels` + `toggleCollapse`
- `useEffect` de initial load
- El JSX render

**Paso clave de verificación:** Después de extraer cada hook, verificar que `npx tsc --noEmit` pasa.

### Task B8: Typecheck después de todos los hooks

```bash
cd frontend
npx tsc --noEmit
```

Expected: No errors.

### Task B9: Commit

```bash
git add frontend/src/modules/hotels/hooks/ frontend/src/modules/hotels/HotelRadarPage.tsx
git commit -m "refactor(hotels): extract hooks from HotelRadarPage (useHotelSearch, useHotelDetail, useHotelWatchlist, useHotelCompSets, useHotelAlerts, useTrackedOffers)"
```

---

## Fase C: Unificación de seguimientos

### Task C1: Cambiar título del WatchlistPanel para diferenciarlo

**File:** `frontend/src/i18n/domains/hotels.ts`

Cambiar `watchlist.title` de "Seguimientos activos" a "Hoteles guardados" (ES) y "Saved hotels" (EN). Esto diferencia el panel de watchlist (simple guardado sin tracking de precio) del panel de tracked offers (tracking diario con precio).

```typescript
// En hotelsEs
watchlist: {
  title: "Hoteles guardados",  // antes: "Seguimientos activos"
  // ...
}

// En hotelsEn
watchlist: {
  title: "Saved hotels",  // antes: "Active tracking"
  // ...
}
```

### Task C2: Añadir `initial_price` al panel de TrackedOffers

**File:** `frontend/src/modules/hotels/components/HotelTrackedOffersPanel.tsx`

Añadir una fila que muestre `initial_price` debajo de `current_price` (cuando `initial_price` no sea null y sea distinto de `current_price`):

```tsx
{offer.initial_price !== null && offer.initial_price !== offer.current_price ? (
  <div className="hotel-tracked-offer-price-row">
    <span className="panel-note">{t("hotels.trackedOffers.initialPrice")}</span>
    <span className="panel-note">
      {formatPrice(offer.initial_price, offer.currency, localeTag)}
    </span>
  </div>
) : null}
```

### Task C3: Añadir botón "Ver historial" y panel de snapshots

**Files:**
- Modify: `frontend/src/modules/hotels/components/HotelTrackedOffersPanel.tsx`
- Create: `frontend/src/modules/hotels/components/HotelTrackedOfferSnapshots.tsx`
- Modify: `frontend/src/i18n/domains/hotels.ts` (nuevas claves i18n)

**Nuevo componente `HotelTrackedOfferSnapshots.tsx`:**

Recibe `offerId: string`. Al montarse, llama a `getTrackedOfferSnapshots(offerId)`. Muestra lista simple de snapshots (fecha, precio, proveedor).

Añadir i18n keys:
- `trackedOffers.viewHistory`: "Ver historial" / "View history"
- `trackedOffers.snapshotsTitle`: "Historial de precios" / "Price history"
- `trackedOffers.snapshotsEmpty`: "Aún no hay registros diarios." / "No daily records yet."

### Task C4: Typecheck y build

```bash
cd frontend
npx tsc --noEmit && npm run build
```

Expected: OK.

### Task C5: Commit

```bash
git add frontend/
git commit -m "feat(hotels): unify tracking UI — add initial_price, snapshots history, differentiate watchlist vs tracked-offers"
```

---

## Fase D: Buscador por área real

Esta es la fase más grande. Transforma el `HotelSearchPanel` de nombre+ciudad a zona+fechas+huéspedes.

### Task D1: Rediseñar `HotelSearchPanel` con campos de área

**File:** `frontend/src/modules/hotels/components/HotelSearchPanel.tsx`

Nuevo diseño del formulario:

```
┌─────────────────────────────────────────────────┐
│  ¿A dónde quieres ir?                           │
│  ┌──────────────────────┐ ┌──────┐ ┌──────────┐│
│  │ Madrid Centro     ▼  │ │ 5 km │ │ 2 huesp. ││
│  └──────────────────────┘ └──────┘ └──────────┘│
│  ┌────────────┐ ┌────────────┐                  │
│  │ Check-in   │ │ Check-out  │                  │
│  └────────────┘ └────────────┘                  │
│  [Buscar hoteles]  [Cargar datos de prueba]     │
└─────────────────────────────────────────────────┘
```

Campos nuevos:
- `areaQuery`: texto con sugerencias de `area-resolve`
- `radiusKm`: select (1, 3, 5, 10, 20 km) — default 5
- `checkIn` / `checkOut`: inputs type="date"
- `guests`: number input (1-20), default 2

Mantener el buscador legacy por nombre/ciudad como fallback colapsable.

El componente recibe props adicionales:
```typescript
interface HotelSearchPanelProps {
  // legacy
  query: string; city: string;
  // nuevos
  areaQuery: string; radiusKm: number;
  checkIn: string; checkOut: string; guests: number;
  // handlers
  onAreaQueryChange: (v: string) => void;
  onRadiusKmChange: (v: number) => void;
  onCheckInChange: (v: string) => void;
  onCheckOutChange: (v: string) => void;
  onGuestsChange: (v: number) => void;
  // acciones
  onAreaSearch: () => void;
  // sugerencias de área
  areaSuggestions: Array<{ label: string; lat: number; lng: number; confidence: string }>;
  onAreaSuggestionSelect: (suggestion: { label: string; lat: number; lng: number }) => void;
  areaResolving: boolean;
  // legacy
  onSearch: () => void; onIngest: () => void;
  loading: boolean;
}
```

### Task D2: Añadir lógica de `area-resolve` con debounce en `useHotelSearch.ts`

Añadir al hook `useHotelSearch`:

```typescript
const [areaQuery, setAreaQuery] = useState("");
const [radiusKm, setRadiusKm] = useState(5);
const [checkIn, setCheckIn] = useState("");
const [checkOut, setCheckOut] = useState("");
const [guests, setGuests] = useState(2);
const [areaSuggestions, setAreaSuggestions] = useState<AreaSuggestion[]>([]);
const [areaResolving, setAreaResolving] = useState(false);
const [resolvedArea, setResolvedArea] = useState<{ lat: number; lng: number; label: string } | null>(null);

// Debounced area resolve
useEffect(() => {
  if (areaQuery.trim().length < 2) {
    setAreaSuggestions([]);
    return;
  }
  const timer = setTimeout(async () => {
    setAreaResolving(true);
    try {
      const result = await areaResolve(areaQuery.trim());
      setAreaSuggestions([{ label: result.area_label, lat: result.latitude, lng: result.longitude, confidence: result.confidence }]);
    } catch {
      setAreaSuggestions([]);
    } finally {
      setAreaResolving(false);
    }
  }, 400);
  return () => clearTimeout(timer);
}, [areaQuery]);
```

### Task D3: Conectar `area-search` al botón de búsqueda principal

Cuando el usuario hace submit con área resuelta, llamar a `areaSearch()` en vez de `searchHotels()`. Los resultados de `areaSearch` se mapean a `HotelSearchOut` para mantener compatibilidad con el resto de la UI:

```typescript
const handleAreaSearch = useCallback(async () => {
  if (!resolvedArea || !checkIn || !checkOut) return;
  setLoading(true);
  setErrorMessage(null);
  try {
    const areaResults = await areaSearch({
      latitude: resolvedArea.lat,
      longitude: resolvedArea.lng,
      radius_km: radiusKm,
      check_in: checkIn,
      check_out: checkOut,
      guests,
    });
    // Mapear a HotelSearchOut para compatibilidad
    const mapped: HotelSearchOut[] = areaResults.map(r => ({
      id: r.hotel_id,
      canonical_name: r.canonical_name,
      city: r.city,
      country_code: r.country_code,
      stars: r.stars,
    }));
    setResults(mapped);
    if (!mapped.some(item => item.id === selectedHotelId)) {
      setSelectedHotelId(mapped[0]?.id ?? null);
    }
  } catch (error) {
    const message = resolveHotelMessage(error, t);
    setErrorMessage(message);
    notify({ tone: "error", title: message });
  } finally {
    setLoading(false);
  }
}, [resolvedArea, checkIn, checkOut, guests, radiusKm, selectedHotelId, t, notify]);
```

### Task D4: CSS para los nuevos campos del buscador

**File:** `frontend/src/styles/screens.css`

Añadir estilos para:
- `.hotel-area-search-grid`: grid de 3 columnas para área/radio/huéspedes
- `.hotel-date-grid`: grid de 2 columnas para check-in/check-out
- `.hotel-area-suggestions`: dropdown de sugerencias de área
- `.hotel-area-suggestion-item`: ítem de sugerencia con hover state
- Responsive: en viewport estrecho, grid de 1 columna

```css
.hotel-area-search-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: var(--gap-sm);
}

.hotel-date-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--gap-sm);
}

.hotel-area-suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  z-index: 10;
  max-height: 200px;
  overflow-y: auto;
}

.hotel-area-suggestion-item {
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  transition: background 150ms;
}
.hotel-area-suggestion-item:hover,
.hotel-area-suggestion-item:focus-visible {
  background: var(--hover-bg);
}
```

### Task D5: Typecheck, build y test

```bash
cd frontend
npx tsc --noEmit
npm run build
```

### Task D6: Commit

```bash
git add frontend/
git commit -m "feat(hotels): integrate area-search into main search UI with area-resolve autocomplete, date picker, and guests selector"
```

---

## Fase E: Polish final

### Task E1: Relegar `parity_break` en el formulario de alertas

**File:** `frontend/src/modules/hotels/components/HotelAlertsPanel.tsx`

Mover `parity_break` del dropdown principal a una sección colapsable "Avanzado" debajo, o añadir un separador visual en el `<select>`:

Opción más simple: mover `parity_break` al final del `<select>` con un `<option disabled>── Avanzado ──</option>` antes, y renombrarlo a "Diferencia entre proveedores (avanzado)".

```tsx
<select>
  <option value="price_below">{ruleTypeLabel.price_below}</option>
  <option value="percentage_drop">{ruleTypeLabel.percentage_drop}</option>
  <option value="price_above">{ruleTypeLabel.price_above}</option>
  <option value="percentage_increase">{ruleTypeLabel.percentage_increase}</option>
  <option value="provider_changed">{ruleTypeLabel.provider_changed}</option>
  <option value="availability_returned">{ruleTypeLabel.availability_returned}</option>
  <option disabled>── {t("hotels.alerts.advancedSection")} ──</option>
  <option value="parity_break">{t("hotels.alerts.ruleTypes.parityBreakAdvanced")}</option>
</select>
```

Añadir i18n:
- `alerts.advancedSection`: "Avanzado" / "Advanced"
- `alerts.ruleTypes.parityBreakAdvanced`: "Diferencia entre proveedores (avanzado)" / "Provider spread (advanced)"

### Task E2: Eliminar referencias a `deleteHotelCompSet` no implementado del frontend

**File:** `frontend/src/modules/hotels/api.ts`

La función `deleteHotelCompSet` existe en api.ts:159 pero ahora que hemos implementado el endpoint en Fase A, hay que verificar que se use. Si no se usa en ninguna parte, añadir el handler en `useHotelCompSets.ts` y conectarlo en `HotelCompSetPanel.tsx`.

### Task E3: Limpiar i18n — quitar claves duplicadas

Revisar que no queden claves i18n huérfanas tras los cambios. Las claves `watchlist.title` y `trackedOffers.title` ya no colisionan.

### Task E4: QA final — tests backend + build frontend

```bash
cd backend
python -m pytest backend/tests/unit/test_hotels_*.py backend/tests/integration/test_hotels_api_flow.py -v

cd frontend
npx tsc --noEmit
npm run build
```

Expected: Todos los tests backend pasan, build frontend OK.

### Task E5: Commit final

```bash
git add -A
git commit -m "chore(hotels): polish — relegate parity_break to advanced alerts, wire delete comp-set UI, cleanup i18n"
```

---

## Plan de commits

| Commit | Fase | Mensaje |
|--------|------|---------|
| 1 | A1 | `feat(hotels): add DELETE /comp-sets/{id} endpoint with ownership check` |
| 2 | B1-B7 | `refactor(hotels): extract hooks from HotelRadarPage (6 hooks)` |
| 3 | C1-C4 | `feat(hotels): unify tracking UI — add initial_price, snapshots history, differentiate watchlist vs tracked-offers` |
| 4 | D1-D5 | `feat(hotels): integrate area-search into main search UI with area-resolve autocomplete` |
| 5 | E1-E4 | `chore(hotels): polish — relegate parity_break, wire delete comp-set, cleanup` |

---

## Archivos modificados (resumen)

| Archivo | Fase | Tipo de cambio |
|---------|------|----------------|
| `backend/app/api/v1/hotels.py` | A | Añadir endpoint DELETE comp-set |
| `backend/tests/integration/test_hotels_api_flow.py` | A | Añadir tests |
| `frontend/src/modules/hotels/hooks/useHotelSearch.ts` | B | NUEVO — extraer lógica de búsqueda |
| `frontend/src/modules/hotels/hooks/useHotelDetail.ts` | B | NUEVO — extraer lógica de detalle |
| `frontend/src/modules/hotels/hooks/useHotelWatchlist.ts` | B | NUEVO — extraer lógica de watchlist |
| `frontend/src/modules/hotels/hooks/useHotelCompSets.ts` | B | NUEVO — extraer lógica de comp sets |
| `frontend/src/modules/hotels/hooks/useHotelAlerts.ts` | B | NUEVO — extraer lógica de alertas |
| `frontend/src/modules/hotels/hooks/useTrackedOffers.ts` | B | NUEVO — extraer lógica de tracked offers |
| `frontend/src/modules/hotels/HotelRadarPage.tsx` | B, D | Reescribir con hooks + integrar area-search |
| `frontend/src/modules/hotels/components/HotelSearchPanel.tsx` | D | Rediseñar con área/fechas/huéspedes |
| `frontend/src/modules/hotels/components/HotelTrackedOffersPanel.tsx` | C | Añadir initial_price + botón historial |
| `frontend/src/modules/hotels/components/HotelTrackedOfferSnapshots.tsx` | C | NUEVO — panel de snapshots |
| `frontend/src/modules/hotels/components/HotelAlertsPanel.tsx` | E | Relegar parity_break |
| `frontend/src/i18n/domains/hotels.ts` | C, D, E | Nuevas claves i18n |
| `frontend/src/styles/screens.css` | D | Estilos para área-search |

---

## Riesgos

1. **Rotura de compatibilidad en HotelRadarPage**: Al extraer hooks, hay riesgo de cambiar el comportamiento si no se copia exactamente la lógica. Mitigación: extraer hook por hook, verificar typecheck tras cada uno.

2. **area-search con mock provider**: El mock provider tiene datos estáticos con fechas fijas. Si el usuario elige fechas que no coinciden con los datos mock, no verá resultados. Mitigación: documentar en UI que con mock provider solo funcionan ciertas fechas, o hacer que el mock sea más flexible.

3. **CSS responsiveness**: Los nuevos grids del buscador deben colapsar correctamente en móvil. Mitigación: probar con `@media` queries existentes y verificar en viewport estrecho.

4. **Regresión en búsqueda legacy**: El usuario debe poder seguir usando el buscador por nombre/ciudad si no quiere usar área. Mitigación: mantener el buscador legacy como pestaña o panel colapsable.
