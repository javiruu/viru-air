# Plan de mejoras de 10 fases para `/puerta-a-puerta` — Frontend

> **Para Claude/Codex:** REQUIRED SUB-SKILL: Usa `superpowers:executing-plans` para implementar este plan fase por fase.

**Goal:** Transformar `/puerta-a-puerta` de una feature técnicamente sólida pero visualmente plana a una experiencia Viru completa: cálida, animada, con jerarquía clara y personalidad aeronáutica, manteniendo el contrato dual-theme.

**Architecture:** Next.js 14 + TypeScript + React 18. Código bajo `frontend/src/modules/door-to-door/`. CSS canónico en `frontend/src/styles/screens.css` (213 clases `d2d-*` actuales). i18n en `frontend/src/i18n/domains/doorToDoor.ts` (ES + EN). Contrato backend: `docs/reference/backend/door-to-door-contract.md`. Identidad visual: `DESIGN.md`.

**Tech Stack:** React 18, Next.js 14, TypeScript, CSS custom properties (no libraries nuevas), Lucide Icons.

**Source of truth:** `docs/product/door-to-door.md`, `DESIGN.md`, `frontend/AGENTS.md`, `AGENTS.md`

---

## Diagnóstico inicial

### Lo que ya está bien
- **Tipado sólido:** `types.ts` con ~20 tipos bien definidos, unions discriminados para estados de confianza
- **Cobertura i18n completa:** ES + EN con ~150 claves de traducción
- **Motor de decisión independiente:** `decision.ts` con badges, reasons y deltas bien separados de la UI
- **Contrato backend claro:** documentado en `docs/reference/backend/door-to-door-contract.md`
- **Componentes de estado:** Empty, Loading, Error, No Coverage ya existen como componentes separados
- **Map Hub sembrado:** estructura de capacidades con transparencia operacional lista para evolucionar
- **Route Visual y Timeline:** componentes creados pero infrautilizados en el flujo principal

### Lo que necesita mejora
1. **Panel monolítico:** `DoorToDoorPanel.tsx` (~530 líneas) con 17 `useState`, 8 `useEffect`, 5 `useRef` — todo el estado en un solo componente
2. **Jerarquía visual plana:** Las secciones de resultados (real, deeplink, estimate) se muestran secuencialmente sin diferenciación visual fuerte
3. **Timeline sin conexión visual:** Líneas planas sin relación espacial entre tramos terrestres y aéreo
4. **Estados sin personalidad:** Empty/Loading/Error son funcionales pero no transmiten la calidez Viru
5. **Comparador escondido:** El `<details>` de comparación está cerrado por defecto en móvil, invisible para el usuario
6. **Filtros en `<details>`:** Sin animación de entrada/salida, sin preview de cómo afectan los resultados
7. **Route Visual no integrado:** El componente `DoorToDoorRouteVisual` existe pero no se usa en el flujo principal del panel
8. **Map Hub colapsado:** Toda la sección de cobertura está oculta por defecto; parece un apéndice técnico
9. **Sin micro-interacciones:** No hay hover elevation, glow contextual, ni transiciones entre estados
10. **Sin sticky context:** Al hacer scroll por las opciones, el usuario pierde el contexto del plan elegido/recomendado

---

## Plan de 10 fases

Las fases están ordenadas por dependencias: el refactor estructural (Fase 1) habilita todas las demás. Las fases 2-6 construyen la experiencia core de resultados. Las fases 7-9 añaden profundidad. La fase 10 es polish final.

---

## Fase 1: Refactor estructural — Extraer hooks de `DoorToDoorPanel`

**Objetivo:** Reducir `DoorToDoorPanel.tsx` de ~530 líneas a ~180 líneas de orquestación pura, extrayendo 4 hooks personalizados. Esto desbloquea todas las fases siguientes al hacer el código mantenible y testeable.

**Files:**
- Create: `frontend/src/modules/door-to-door/hooks/useDoorToDoorSearch.ts`
- Create: `frontend/src/modules/door-to-door/hooks/useDoorToDoorResults.ts`
- Create: `frontend/src/modules/door-to-door/hooks/useDoorToDoorHistory.ts`
- Create: `frontend/src/modules/door-to-door/hooks/useDoorToDoorMapHub.ts`
- Modify: `frontend/src/modules/door-to-door/DoorToDoorPanel.tsx`
- Modify: `frontend/src/modules/door-to-door/components/DoorToDoorFilters.tsx` (si se mueve lógica de preferencias)

### Task 1.1: Crear `useDoorToDoorSearch.ts`

Extraer toda la lógica de búsqueda, autocomplete y formulario:

```typescript
// frontend/src/modules/door-to-door/hooks/useDoorToDoorSearch.ts
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useI18n } from "@/i18n";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import {
  fetchDoorToDoorSuggestions,
  fetchSavedDoorToDoorLocation,
  searchDoorToDoor,
} from "@/modules/door-to-door/api";
import { apiFetch } from "@/modules/shared/api";
import { DEFAULT_PREFERENCES } from "@/modules/door-to-door/constants";
import type {
  DoorToDoorLocation,
  DoorToDoorPreferences,
  DoorToDoorResponse,
  DoorToDoorSuggestion,
  DoorToDoorSuggestionsMeta,
  Watch,
} from "@/modules/door-to-door/types";

export function useDoorToDoorSearch() {
  const searchParams = useSearchParams();
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const watchIdParam = searchParams?.get("watchId") || "";

  // Watch selection
  const [watches, setWatches] = useState<Watch[]>([]);
  const [selectedWatchId, setSelectedWatchId] = useState(watchIdParam);

  // Location inputs
  const defaultOrigin = useMemo<DoorToDoorLocation>(
    () => ({ type: "city", label: t("doorToDoor.defaults.origin"), lat: 36.834, lng: -2.463 }),
    [t]
  );
  const defaultDestination = useMemo<DoorToDoorLocation>(
    () => ({ type: "city", label: t("doorToDoor.defaults.destination") }),
    [t]
  );
  const [origin, setOrigin] = useState<DoorToDoorLocation>(defaultOrigin);
  const [finalDestination, setFinalDestination] = useState<DoorToDoorLocation>(defaultDestination);
  const [preferences, setPreferences] = useState<DoorToDoorPreferences>(DEFAULT_PREFERENCES);
  const [saveOrigin, setSaveOrigin] = useState(false);

  // Search state
  const [status, setStatus] = useState<"empty" | "loading" | "success" | "partial" | "error" | "no_coverage">("empty");
  const [response, setResponse] = useState<DoorToDoorResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const requestIdRef = useRef(0);

  // Derived
  const selectedWatch = useMemo(
    () => watches.find((w) => w.id === selectedWatchId) || null,
    [watches, selectedWatchId]
  );
  const isSubmitBlocked = status === "loading" || !selectedWatch;

  // Effects: sync watchId from URL, fetch watches + saved location, reset on watch change
  useEffect(() => { setSelectedWatchId(watchIdParam); }, [watchIdParam]);

  useEffect(() => {
    apiFetch<Watch[]>("/watchlist")
      .then((items) => {
        setWatches(items);
        setSelectedWatchId((c) => c || watchIdParam || items[0]?.id || "");
      })
      .catch(() => setWatches([]));
    fetchSavedDoorToDoorLocation()
      .then((saved) => { if (saved) setOrigin({ type: saved.type, label: saved.label, lat: saved.lat, lng: saved.lng }); })
      .catch(() => undefined);
  }, [watchIdParam]);

  useEffect(() => {
    setResponse(null);
    setErrorMessage("");
    setStatus("empty");
  }, [selectedWatchId]);

  // calculate() — same logic as current onSubmit handler
  const calculate = useCallback(async () => {
    if (!selectedWatch) {
      setStatus("empty");
      setErrorMessage(t("doorToDoor.chooseWatchedRoute"));
      return;
    }
    const normOrigin = origin.label.trim().replace(/\s+/g, " ").toLocaleLowerCase();
    const normDest = finalDestination.label.trim().replace(/\s+/g, " ").toLocaleLowerCase();
    if (normOrigin.length < 2 || normDest.length < 2) {
      setStatus("empty");
      setErrorMessage(t("doorToDoor.states.emptyBodyWithWatch"));
      notify({ tone: "error", title: t("doorToDoor.states.emptyTitleWithWatch") });
      return;
    }
    if (finalDestination.type !== "airport_only" && normOrigin === normDest) {
      setStatus("empty");
      setErrorMessage(t("doorToDoor.states.emptyBodyWithWatch"));
      notify({ tone: "error", title: t("doorToDoor.states.emptyTitleWithWatch") });
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setStatus("loading");
    setErrorMessage("");
    try {
      const data = await searchDoorToDoor({
        flight_watch_id: selectedWatch.id,
        origin,
        final_destination: finalDestination,
        preferences,
        save_origin_as_default: saveOrigin,
      });
      if (requestId !== requestIdRef.current) return;
      setResponse(data);
      const noCoverage = data.warnings.some((w) => w.code === "NO_COVERAGE");
      if (data.options.length === 0 || noCoverage) setStatus("no_coverage");
      else if (data.warnings.length > 0) setStatus("partial");
      else setStatus("success");
    } catch (error) {
      if (requestId !== requestIdRef.current) return;
      setErrorMessage(error instanceof Error ? error.message : "Error inesperado");
      setStatus("error");
    }
  }, [finalDestination, notify, origin, preferences, saveOrigin, selectedWatch, t]);

  return {
    // Watch
    watches, selectedWatchId, setSelectedWatchId, selectedWatch,
    // Locations
    origin, setOrigin, defaultOrigin,
    finalDestination, setFinalDestination, defaultDestination,
    // Preferences
    preferences, setPreferences, saveOrigin, setSaveOrigin,
    // Search
    status, response, errorMessage,
    calculate, isSubmitBlocked,
  };
}
```

**Verificación:** `npx tsc --noEmit` en `frontend/` — sin errores de tipo.

### Task 1.2: Crear `useDoorToDoorResults.ts`

Extraer la lógica de opciones, plan elegido, badges, reasons, deltas, y trust:

```typescript
// frontend/src/modules/door-to-door/hooks/useDoorToDoorResults.ts
"use client";

import { useCallback, useMemo, useState } from "react";
import { useI18n } from "@/i18n";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { chooseDoorToDoorOption } from "@/modules/door-to-door/api";
import { getAlternativeDeltas, getDecisionBadges, getDecisionReasons, hasUncertainSources } from "@/modules/door-to-door/decision";
import type { DoorToDoorOption, DoorToDoorResponse } from "@/modules/door-to-door/types";

export function useDoorToDoorResults(
  response: DoorToDoorResponse | null,
  onHistoryRefresh: () => Promise<void>,
) {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [chosenOptionId, setChosenOptionId] = useState<string>(
    response?.summary.chosen_option_id || ""
  );

  // Filtered option groups
  const realResults = useMemo(
    () => response?.options.filter((o) => o.status === "real_result") ?? [],
    [response]
  );
  const realDeeplinks = useMemo(
    () => response?.options.filter((o) => o.status === "real_deeplink") ?? [],
    [response]
  );
  const estimateOptions = useMemo(
    () => response?.options.filter((o) => o.status === "estimate_only") ?? [],
    [response]
  );

  // Active plan resolution (chosen > recommended > first)
  const selectedPlan = useMemo(() => {
    if (!response || response.options.length === 0) return null;
    return (
      response.options.find((o) => o.id === response.summary.chosen_option_id) ||
      response.options.find((o) => o.id === chosenOptionId) ||
      response.options.find((o) => o.id === response.summary.recommended_option_id) ||
      response.options[0] ||
      null
    );
  }, [response, chosenOptionId]);

  // Decision badges for all options
  const quickBadgesByOption = useMemo(() => {
    if (!response) return {};
    return getDecisionBadges(response.options);
  }, [response]);

  // Recommended option + reasons
  const recommendedOption = useMemo(() => {
    if (!response) return null;
    return response.options.find((o) => o.id === response.summary.recommended_option_id) || response.options[0] || null;
  }, [response]);

  const recommendedReasons = useMemo(() => {
    if (!response || !recommendedOption) return [];
    return getDecisionReasons(recommendedOption, response.options);
  }, [response, recommendedOption]);

  // Alternative deltas (top 2)
  const alternativeDeltas = useMemo(() => {
    if (!response || !recommendedOption) return [];
    return getAlternativeDeltas(recommendedOption, response.options);
  }, [response, recommendedOption]);

  // Trust tone
  const trustTone = useMemo(() => {
    if (!selectedPlan) return "warning" as const;
    const confirmed = selectedPlan.sources.filter(
      (s) =>
        (s.source_type === "api" || s.source_type === "open_data" || s.source_type === "maps") &&
        (s.confidence === "live" || s.confidence === "cached")
    ).length;
    const uncertain = selectedPlan.sources.filter(
      (s) =>
        s.source_type === "deeplink" || s.source_type === "estimate" || s.source_type === "mock" ||
        s.confidence === "estimated" || s.confidence === "deeplink" || s.confidence === "unavailable"
    ).length;
    return confirmed > 0 && confirmed >= uncertain ? "success" : "warning";
  }, [selectedPlan]);

  // Warnings
  const warningCodes = useMemo(
    () => new Set((response?.warnings ?? []).map((w) => w.code)),
    [response?.warnings]
  );

  // Mark chosen
  const markChosen = useCallback(async (option: DoorToDoorOption) => {
    if (!response?.summary.history_id) return;
    try {
      await chooseDoorToDoorOption({
        historyId: response.summary.history_id,
        optionId: option.id,
        optionLabel: option.label,
        optionSummary: {
          total_price_min: option.total_price_min,
          total_price_max: option.total_price_max,
          transfer_count: option.transfer_count,
          total_duration_minutes: option.total_duration_minutes,
        },
      });
      setChosenOptionId(option.id);
      await onHistoryRefresh();
      notify({ tone: "success", title: t("doorToDoor.option.chosenSaved") });
    } catch {
      notify({ tone: "error", title: t("doorToDoor.option.chosenError") });
    }
  }, [response, onHistoryRefresh, t, notify]);

  return {
    chosenOptionId,
    realResults, realDeeplinks, estimateOptions,
    selectedPlan,
    quickBadgesByOption,
    recommendedOption, recommendedReasons,
    alternativeDeltas,
    trustTone,
    warningCodes,
    markChosen,
  };
}
```

**Verificación:** `npx tsc --noEmit`.

### Task 1.3: Crear `useDoorToDoorHistory.ts`

```typescript
// frontend/src/modules/door-to-door/hooks/useDoorToDoorHistory.ts
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchDoorToDoorHistory } from "@/modules/door-to-door/api";
import type { DoorToDoorHistoryItem } from "@/modules/door-to-door/types";

export function useDoorToDoorHistory(selectedWatchId: string, triggerVersion: number) {
  const [history, setHistory] = useState<DoorToDoorHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const requestIdRef = useRef(0);

  const refreshHistory = useCallback(async () => {
    if (!selectedWatchId) {
      setHistory([]);
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    try {
      const items = await fetchDoorToDoorHistory(selectedWatchId);
      if (requestId !== requestIdRef.current) return;
      setHistory(items);
    } catch {
      if (requestId !== requestIdRef.current) return;
      setHistory([]);
    }
  }, [selectedWatchId]);

  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory, triggerVersion]);

  useEffect(() => {
    setShowHistory(false);
  }, [selectedWatchId]);

  return { history, showHistory, setShowHistory, refreshHistory };
}
```

### Task 1.4: Crear `useDoorToDoorMapHub.ts`

Extraer provider status + map capabilities + saved places:

```typescript
// frontend/src/modules/door-to-door/hooks/useDoorToDoorMapHub.ts
"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchDoorToDoorProviderStatus } from "@/modules/door-to-door/api";
import { buildMapCapabilities, filterSavedPlacesForWatch } from "@/modules/door-to-door/mapHub";
import type {
  DoorToDoorProviderStatus,
  DoorToDoorResponse,
  DoorToDoorSavedPlace,
} from "@/modules/door-to-door/types";

export function useDoorToDoorMapHub(response: DoorToDoorResponse | null, selectedWatchId: string) {
  const [providerStatus, setProviderStatus] = useState<DoorToDoorProviderStatus[]>([]);
  const [savedPlaces, setSavedPlaces] = useState<DoorToDoorSavedPlace[]>([]);

  // Fetch provider status once
  useEffect(() => {
    fetchDoorToDoorProviderStatus()
      .then((items) => setProviderStatus(items))
      .catch(() => setProviderStatus([]));
  }, []);

  // Load/sync saved places from localStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem("viru_d2d_saved_places_v1");
      if (!raw) return;
      const parsed = JSON.parse(raw) as DoorToDoorSavedPlace[];
      if (Array.isArray(parsed)) setSavedPlaces(parsed.slice(0, 12));
    } catch { setSavedPlaces([]); }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("viru_d2d_saved_places_v1", JSON.stringify(savedPlaces.slice(0, 12)));
  }, [savedPlaces]);

  // Derived
  const providerStatusSummary = useMemo(() => {
    const enabled = providerStatus.filter((p) => p.enabled);
    const realEnabled = enabled.filter((p) => p.source_type !== "mock" && p.source_type !== "estimate");
    const estimateEnabled = enabled.filter((p) => p.source_type === "mock" || p.source_type === "estimate");
    return { enabled: enabled.length, realEnabled: realEnabled.length, estimateEnabled: estimateEnabled.length };
  }, [providerStatus]);

  const mapCapabilities = useMemo(
    () => buildMapCapabilities(response, providerStatus),
    [response, providerStatus]
  );

  const visibleSavedPlaces = useMemo(
    () => filterSavedPlacesForWatch(savedPlaces, selectedWatchId),
    [savedPlaces, selectedWatchId]
  );

  return {
    providerStatus, providerStatusSummary,
    mapCapabilities,
    savedPlaces, setSavedPlaces, visibleSavedPlaces,
  };
}
```

### Task 1.5: Reescribir `DoorToDoorPanel.tsx` para usar los hooks

El page component queda reducido a ~180 líneas de orquestación pura:

```typescript
// frontend/src/modules/door-to-door/DoorToDoorPanel.tsx (reescrito)
"use client";

import React, { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/i18n";
import { useDoorToDoorSearch } from "@/modules/door-to-door/hooks/useDoorToDoorSearch";
import { useDoorToDoorResults } from "@/modules/door-to-door/hooks/useDoorToDoorResults";
import { useDoorToDoorHistory } from "@/modules/door-to-door/hooks/useDoorToDoorHistory";
import { useDoorToDoorMapHub } from "@/modules/door-to-door/hooks/useDoorToDoorMapHub";
// ... component imports

export function DoorToDoorPanel() {
  const router = useRouter();
  const { t, localeTag } = useI18n();

  const search = useDoorToDoorSearch();
  const [triggerVersion, setTriggerVersion] = useState(0);
  const history = useDoorToDoorHistory(search.selectedWatchId, triggerVersion);
  const results = useDoorToDoorResults(search.response, history.refreshHistory);
  const mapHub = useDoorToDoorMapHub(search.response, search.selectedWatchId);

  const [showTrustModal, setShowTrustModal] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // ... mobile detection effect (keep existing)

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (search.status === "loading") return;
    await search.calculate();
    setTriggerVersion((v) => v + 1);
  }

  // ... render (JSX — mismo que actual pero usando search.*, results.*, history.*, mapHub.*)
}
```

**Verificación clave:** Después de cada hook, `npx tsc --noEmit` debe pasar. Después del refactor completo, `npm run build` debe ser exitoso.

### Task 1.6: Extraer constantes `DEFAULT_PREFERENCES` a archivo separado

Crear `frontend/src/modules/door-to-door/constants.ts`:

```typescript
import type { DoorToDoorPreferences } from "@/modules/door-to-door/types";

export const DEFAULT_PREFERENCES: DoorToDoorPreferences = {
  min_airport_buffer_minutes: 120,
  max_price: 80,
  passengers: 1,
  luggage: "cabin",
  allow_bus: true,
  allow_train: true,
  allow_rideshare: true,
  allow_shuttle: true,
  allow_taxi: false,
  allow_car: true,
  public_transport_only: false,
  sort_by: "best_balance",
};
```

### Task 1.7: Typecheck + build + commit

```bash
cd frontend
npx tsc --noEmit
npm run build
```

Expected: Sin errores.

```bash
git add frontend/src/modules/door-to-door/
git commit -m "refactor(d2d): extract hooks from DoorToDoorPanel — useDoorToDoorSearch, useDoorToDoorResults, useDoorToDoorHistory, useDoorToDoorMapHub"
```

---

## Fase 2: Polish de estados — Empty, Loading, Error con personalidad Viru

**Objetivo:** Transformar los componentes de estado actuales (funcionales pero genéricos) en experiencias con calidez, animación y carácter aeronáutico Viru.

**Principios aplicados:** `DESIGN.md` §5 (motion con intención), §2 (calidez antes que frialdad)

### Task 2.1: Rediseñar `DoorToDoorEmptyState`

**File:** `frontend/src/modules/door-to-door/components/DoorToDoorEmptyState.tsx`

Mejoras:
- Sustituir el `d2d-radar-dot` estático por un animated compass/radar CSS pulsante
- Añadir ilustración abstracta de ruta (tres puntos conectados: 🏠 → ✈️ → 📍)
- Microcopy más cálido y contextual (diferencia entre "sin watch" y "con watch pero sin ruta")
- Entrada con fade + slide-up (4px)

```tsx
export function DoorToDoorEmptyState({ hasWatch }: { hasWatch: boolean }) {
  const { t } = useI18n();
  return (
    <section className="panel panel-soft d2d-state-card d2d-empty-state" role="status">
      <div className="d2d-empty-visual" aria-hidden="true">
        <div className="d2d-empty-route">
          <span className="d2d-empty-dot d2d-empty-origin" />
          <span className="d2d-empty-line" />
          <span className="d2d-empty-plane">✈</span>
          <span className="d2d-empty-line" />
          <span className="d2d-empty-dot d2d-empty-dest" />
        </div>
      </div>
      <h2>{hasWatch ? t("doorToDoor.states.emptyTitleWithWatch") : t("doorToDoor.states.emptyTitleNoWatch")}</h2>
      <p>{hasWatch ? t("doorToDoor.states.emptyBodyWithWatch") : t("doorToDoor.states.emptyBodyNoWatch")}</p>
    </section>
  );
}
```

CSS nuevo en `screens.css`:
```css
.d2d-empty-visual { display: flex; justify-content: center; padding: 1.5rem 0; }
.d2d-empty-route { display: flex; align-items: center; gap: 0; animation: d2d-route-pulse 2.5s ease-in-out infinite; }
.d2d-empty-dot { width: 12px; height: 12px; border-radius: 50%; }
.d2d-empty-origin { background: var(--accent-warm); box-shadow: 0 0 8px var(--accent-warm); }
.d2d-empty-dest { background: var(--accent-cool); box-shadow: 0 0 8px var(--accent-cool); }
.d2d-empty-line { width: 32px; height: 2px; background: var(--border-color); }
.d2d-empty-plane { font-size: 1.25rem; color: var(--accent-warm); }
@keyframes d2d-route-pulse {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}
```

### Task 2.2: Rediseñar `DoorToDoorLoadingState` con skeleton cards

**File:** `frontend/src/modules/door-to-door/components/DoorToDoorLoadingState.tsx`

Sustituir el spinner genérico por skeleton cards que previsualizan la estructura de resultados:

```tsx
export function DoorToDoorLoadingState() {
  const { t } = useI18n();
  return (
    <section className="d2d-loading-state" role="status" aria-live="polite" aria-label={t("doorToDoor.states.loadingTitle")}>
      <div className="d2d-loading-header">
        <div className="d2d-loading-radar" aria-hidden="true">
          <span /><span /><span />
        </div>
        <div>
          <h2>{t("doorToDoor.states.loadingTitle")}</h2>
          <p className="panel-note">{t("doorToDoor.states.loadingBody")}</p>
        </div>
      </div>
      {/* Skeleton cards */}
      <div className="d2d-loading-skeletons" aria-hidden="true">
        {[1, 2, 3].map((i) => (
          <div key={i} className="d2d-skeleton-card">
            <div className="d2d-skeleton-line w-60" />
            <div className="d2d-skeleton-line w-40" />
            <div className="d2d-skeleton-line w-80" />
            <div className="d2d-skeleton-line w-30" />
          </div>
        ))}
      </div>
    </section>
  );
}
```

CSS:
```css
.d2d-loading-skeletons { display: flex; flex-direction: column; gap: var(--gap-md); margin-top: 1rem; }
.d2d-skeleton-card {
  background: var(--panel-bg);
  border-radius: var(--radius-md);
  padding: 1rem;
  display: flex; flex-direction: column; gap: 0.5rem;
}
.d2d-skeleton-line {
  height: 0.75rem;
  background: linear-gradient(90deg, var(--border-color) 25%, var(--hover-bg) 50%, var(--border-color) 75%);
  background-size: 200% 100%;
  animation: d2d-shimmer 1.5s ease-in-out infinite;
  border-radius: var(--radius-sm);
}
.d2d-skeleton-line.w-60 { width: 60%; }
.d2d-skeleton-line.w-40 { width: 40%; }
.d2d-skeleton-line.w-80 { width: 80%; }
.d2d-skeleton-line.w-30 { width: 30%; }
@keyframes d2d-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

### Task 2.3: Mejorar `DoorToDoorErrorState` con ilustración de error amigable

Añadir un icono grande con animación sutil y copy más humano:

```tsx
export function DoorToDoorErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { t } = useI18n();
  return (
    <section className="notice notice-error d2d-error-state" role="alert">
      <div className="d2d-error-visual" aria-hidden="true">
        <span className="d2d-error-icon">⚡</span>
      </div>
      <div>
        <strong>{t("doorToDoor.states.errorTitle")}</strong>
        <p>{message || t("doorToDoor.states.errorBody")}</p>
      </div>
      <button className="btn-secondary btn-compact" type="button" onClick={onRetry}>
        {t("doorToDoor.states.retry")}
      </button>
    </section>
  );
}
```

### Task 2.4: Typecheck + build + commit

```bash
cd frontend && npx tsc --noEmit && npm run build
```

---

## Fase 3: Timeline visual — Conexión entre tramos con boarding-pass cues

**Objetivo:** Transformar el timeline de una lista plana de segmentos a una línea de tiempo conectada visualmente, donde el tramo aéreo se destaca con identidad de boarding pass y los tramos terrestres muestran su modo de transporte.

**Inspiración:** Boarding pass aesthetic, Aviation Dark-Luxe (`DESIGN.md` §1)

### Task 3.1: Rediseñar el timeline en `DoorToDoorPanel.tsx`

Sustituir el actual `<ol className="d2d-segment-timeline">` por una timeline conectada:

```tsx
<ol className="d2d-connected-timeline" aria-label={t("doorToDoor.timeline.title")}>
  {timelineLegs.map((leg, index) => (
    <li key={`${leg.type}-${leg.mode}-${index}`} className={`d2d-timeline-leg ${leg.type === "flight" ? "is-flight" : "is-ground"}`}>
      {/* Connector line from previous leg */}
      {index > 0 && <span className="d2d-timeline-connector" aria-hidden="true" />}
      {/* Leg card */}
      <article className={`d2d-leg-card ${leg.type === "flight" ? "d2d-leg-flight" : `d2d-leg-${leg.mode}`}`}>
        {leg.type === "flight" ? (
          <FlightSegment leg={leg} localeTag={localeTag} />
        ) : (
          <GroundSegment leg={leg} localeTag={localeTag} />
        )}
      </article>
    </li>
  ))}
</ol>
```

CSS para la timeline conectada:
```css
.d2d-connected-timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  position: relative;
}
.d2d-timeline-leg {
  position: relative;
  padding-left: 2rem;
}
.d2d-timeline-connector {
  position: absolute;
  left: 0.5rem;
  top: -1.5rem;
  bottom: 50%;
  width: 2px;
  background: linear-gradient(to bottom, var(--accent-warm), var(--border-color));
}
/* Flight segment card — boarding pass feel */
.d2d-leg-flight {
  border-left: 3px solid var(--accent-warm);
  background: linear-gradient(135deg, var(--panel-bg), var(--hover-bg));
}
.d2d-leg-flight::before {
  content: "";
  position: absolute;
  top: 0; bottom: 0; left: 2rem;
  width: 1px;
  background: repeating-linear-gradient(
    to bottom,
    var(--accent-warm) 0,
    var(--accent-warm) 4px,
    transparent 4px,
    transparent 8px
  );
  opacity: 0.3;
}
/* Ground leg cards */
.d2d-leg-ground {
  border-left: 3px solid var(--border-color);
}
```

### Task 3.2: Añadir animación de revelado secuencial

Cada tramo aparece con un stagger de 120ms:

```css
.d2d-timeline-leg {
  animation: d2d-leg-reveal 0.35s ease-out both;
}
.d2d-timeline-leg:nth-child(1) { animation-delay: 0ms; }
.d2d-timeline-leg:nth-child(2) { animation-delay: 120ms; }
.d2d-timeline-leg:nth-child(3) { animation-delay: 240ms; }
.d2d-timeline-leg:nth-child(4) { animation-delay: 360ms; }
@keyframes d2d-leg-reveal {
  from { opacity: 0; transform: translateX(-8px); }
  to   { opacity: 1; transform: translateX(0); }
}
```

### Task 3.3: Typecheck + build + commit

---

## Fase 4: Tarjetas de opción con jerarquía visual por status

**Objetivo:** Diferenciar visualmente las opciones según su tipo (real_result, real_deeplink, estimate_only) y estado (recomendada, elegida, normal) para que el usuario entienda la jerarquía de confianza de un vistazo.

**File principal:** `frontend/src/modules/door-to-door/components/DoorToDoorOptionCard.tsx`

### Task 4.1: Jerarquía visual por status

- **`real_result`:** Tratamiento premium — borde sutil success, fondo ligeramente elevado, más densidad de información
- **`real_deeplink`:** Badge "Búsqueda externa" prominente, borde dashed subtle, indicador de enlace externo
- **`estimate_only`:** Tratamiento translúcido/muted, tipografía ligeramente más clara, disclaimer visible
- **`is-chosen`:** Borde dorado (`var(--accent-warm)`), glow sutil
- **`is-recommended`:** Estrella o indicador sutil en la esquina superior derecha

```tsx
<article className={`
  d2d-option-card
  ${isRealResult ? "is-real" : ""}
  ${isRealDeeplink ? "is-deeplink" : ""}
  ${isEstimate ? "is-estimate" : ""}
  ${chosen ? "is-chosen" : ""}
  ${isRecommended ? "is-recommended" : ""}
`}>
  {isRecommended && <span className="d2d-recommended-star" aria-label={t("doorToDoor.option.recommended")}>★</span>}
  {/* ... */}
</article>
```

CSS:
```css
.d2d-option-card.is-real {
  border-color: var(--state-success-border);
  background: linear-gradient(135deg, var(--panel-bg), color-mix(in srgb, var(--state-success) 3%, var(--panel-bg)));
}
.d2d-option-card.is-deeplink {
  border-style: dashed;
  border-color: var(--state-info-border);
}
.d2d-option-card.is-estimate {
  opacity: 0.82;
  border-color: transparent;
}
.d2d-option-card.is-chosen {
  border-color: var(--accent-warm);
  box-shadow: 0 0 12px color-mix(in srgb, var(--accent-warm) 15%, transparent);
}
.d2d-option-card.is-recommended .d2d-recommended-star {
  position: absolute;
  top: 0.5rem;
  right: 0.75rem;
  color: var(--accent-warm);
  font-size: 0.9rem;
}
```

### Task 4.2: Hover elevation y selección con transición

```css
.d2d-option-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  cursor: pointer;
}
.d2d-option-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
.d2d-option-card:focus-within {
  outline: 2px solid var(--accent-warm);
  outline-offset: 2px;
}
```

### Task 4.3: Typecheck + build + commit

---

## Fase 5: Sticky decision bar + Navegación entre secciones

**Objetivo:** Añadir una barra sticky que aparece al hacer scroll past los resultados, mostrando el resumen del plan elegido/recomendado y permitiendo saltar entre secciones. Resuelve el problema de perder contexto durante el scroll.

### Task 5.1: Implementar `DoorToDoorStickyBar`

**Crear:** `frontend/src/modules/door-to-door/components/DoorToDoorStickyBar.tsx`

```tsx
"use client";

import React, { useEffect, useState } from "react";
import { ArrowDown, Clock, DollarSign, Shield } from "lucide-react";
import { useI18n } from "@/i18n";
import type { DoorToDoorOption } from "@/modules/door-to-door/types";

export function DoorToDoorStickyBar({
  plan,
  trustTone,
  activeSection,
  onSectionClick,
}: {
  plan: DoorToDoorOption | null;
  trustTone: "success" | "warning";
  activeSection: string;
  onSectionClick: (section: string) => void;
}) {
  const { t, localeTag } = useI18n();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => setVisible(!entry.isIntersecting),
      { threshold: 0 }
    );
    const sentinel = document.getElementById("d2d-results-sentinel");
    if (sentinel) observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  if (!plan || !visible) return null;

  const sections = [
    { id: "results", label: t("doorToDoor.sections.realResults") },
    { id: "timeline", label: t("doorToDoor.sections.tripSummary") },
    { id: "compare", label: t("doorToDoor.option.comparatorTitle") },
    { id: "maphub", label: t("doorToDoor.sections.coveragePanelTitle") },
  ];

  return (
    <nav className="d2d-sticky-bar" aria-label={t("doorToDoor.stickyBar.aria")}>
      <div className="d2d-sticky-summary">
        <strong>{plan.label}</strong>
        <span className="d2d-sticky-metrics">
          <span><DollarSign size={14} /> {plan.total_price_min ?? "--"}-{plan.total_price_max ?? "--"} {plan.currency}</span>
          <span><Clock size={14} /> {plan.total_duration_minutes ? `${Math.floor(plan.total_duration_minutes / 60)}h${String(plan.total_duration_minutes % 60).padStart(2, "0")}` : "--"}</span>
          <span><Shield size={14} className={trustTone === "success" ? "state-success" : "state-warning"} /></span>
        </span>
      </div>
      <div className="d2d-sticky-nav" role="tablist">
        {sections.map((s) => (
          <button
            key={s.id}
            role="tab"
            aria-selected={activeSection === s.id}
            className={`d2d-sticky-nav-item ${activeSection === s.id ? "is-active" : ""}`}
            onClick={() => onSectionClick(s.id)}
          >
            {s.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
```

### Task 5.2: CSS para la sticky bar

```css
.d2d-sticky-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--panel-bg);
  border-bottom: 1px solid var(--border-color);
  padding: 0.5rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  animation: d2d-sticky-enter 0.25s ease-out;
  backdrop-filter: blur(8px);
}
@keyframes d2d-sticky-enter {
  from { opacity: 0; transform: translateY(-100%); }
  to   { opacity: 1; transform: translateY(0); }
}
.d2d-sticky-summary { display: flex; align-items: center; gap: 1rem; }
.d2d-sticky-metrics { display: flex; gap: 0.75rem; font-size: 0.8rem; color: var(--text-secondary); }
.d2d-sticky-metrics span { display: flex; align-items: center; gap: 0.25rem; }
.d2d-sticky-nav { display: flex; gap: 0.25rem; }
.d2d-sticky-nav-item {
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.d2d-sticky-nav-item:hover { background: var(--hover-bg); }
.d2d-sticky-nav-item.is-active { background: var(--accent-warm); color: #121212; }

@media (max-width: 768px) {
  .d2d-sticky-bar { flex-direction: column; padding: 0.5rem; }
  .d2d-sticky-nav { overflow-x: auto; width: 100%; }
}
```

### Task 5.3: Integrar en `DoorToDoorPanel.tsx`

Añadir el sentinel y la sticky bar antes de las secciones de resultados.

### Task 5.4: Typecheck + build + commit

---

## Fase 6: Comparador rediseñado con visual trade-off

**Objetivo:** Transformar el comparador actual (tabla de texto en `<details>`) en una visualización de trade-offs con barras horizontales, indicadores de mejor/peor codificados por color, y una animación de entrada atractiva.

### Task 6.1: Rediseñar el comparador como `DoorToDoorComparator`

**Modificar:** La sección del comparador en `DoorToDoorPanel.tsx` (o extraer a componente)

```tsx
<section className="panel panel-soft d2d-comparator" aria-label={t("doorToDoor.option.comparatorTitle")}>
  <h3 className="d2d-comparator-title">{t("doorToDoor.option.comparatorTitle")}</h3>
  <p className="panel-note">{t("doorToDoor.option.comparatorSubtitle", { baseline: recommendedOption?.label })}</p>
  
  <div className="d2d-comparator-chart" role="list">
    {alternativeDeltas.map((delta) => (
      <div key={delta.option_id} className="d2d-comparator-row" role="listitem">
        <strong className="d2d-comparator-option-name">{delta.option_label}</strong>
        
        {/* Price bar */}
        <div className="d2d-comparator-metric">
          <span className="d2d-comparator-label">{t("doorToDoor.option.compare.price")}</span>
          <div className="d2d-comparator-bar-track">
            <div
              className={`d2d-comparator-bar ${delta.delta_price != null && delta.delta_price <= 0 ? "is-better" : "is-worse"}`}
              style={{ width: `${Math.min(Math.abs(delta.delta_price ?? 0) / 40 * 100, 100)}%` }}
            />
          </div>
          <span className={`d2d-comparator-value ${delta.delta_price != null && delta.delta_price <= 0 ? "is-better" : "is-worse"}`}>
            {formatDelta(delta.delta_price, "€")}
          </span>
        </div>
        {/* Repeat for duration, buffer, risk */}
      </div>
    ))}
  </div>
</section>
```

### Task 6.2: Animación de barras

```css
.d2d-comparator-bar {
  height: 6px;
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  animation: d2d-bar-grow 0.5s ease-out both;
}
.d2d-comparator-bar.is-better { background: var(--state-success); }
.d2d-comparator-bar.is-worse  { background: var(--state-error); }
@keyframes d2d-bar-grow {
  from { width: 0% !important; }
}
```

### Task 6.3: Typecheck + build + commit

---

## Fase 7: Filtros como panel lateral con animación slide-out

**Objetivo:** Sustituir el `<details>` que contiene los filtros por un panel lateral que se desliza desde la derecha con una animación suave, mejorando la experiencia de ajuste de preferencias sin perder el contexto de los resultados.

### Task 7.1: Crear `DoorToDoorFilterPanel`

**Crear:** `frontend/src/modules/door-to-door/components/DoorToDoorFilterPanel.tsx`

```tsx
"use client";

import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { useI18n } from "@/i18n";
import { DoorToDoorFilters } from "@/modules/door-to-door/components/DoorToDoorFilters";
import type { DoorToDoorPreferences } from "@/modules/door-to-door/types";

export function DoorToDoorFilterPanel({
  open,
  onClose,
  preferences,
  onChange,
}: {
  open: boolean;
  onClose: () => void;
  preferences: DoorToDoorPreferences;
  onChange: (next: DoorToDoorPreferences) => void;
}) {
  const { t } = useI18n();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
      panelRef.current?.focus();
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  if (!open) return null;

  return (
    <>
      <div className="d2d-filter-overlay" onClick={onClose} aria-hidden="true" />
      <aside
        ref={panelRef}
        className="d2d-filter-slideout"
        role="dialog"
        aria-modal="true"
        aria-label={t("doorToDoor.filters.title")}
        tabIndex={-1}
      >
        <div className="d2d-filter-slideout-header">
          <h2>{t("doorToDoor.filters.title")}</h2>
          <button className="btn-ghost btn-compact" onClick={onClose} aria-label={t("shared.actions.close")}>
            <X size={18} />
          </button>
        </div>
        <div className="d2d-filter-slideout-body">
          <DoorToDoorFilters preferences={preferences} onChange={onChange} embedded />
        </div>
      </aside>
    </>
  );
}
```

### Task 7.2: CSS para el slide-out panel

```css
.d2d-filter-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.3);
  z-index: 30;
  animation: d2d-overlay-in 0.2s ease-out;
}
.d2d-filter-slideout {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(380px, 90vw);
  z-index: 31;
  background: var(--panel-bg);
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  animation: d2d-slide-in 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  overflow-y: auto;
}
@keyframes d2d-slide-in {
  from { transform: translateX(100%); }
  to   { transform: translateX(0); }
}
@keyframes d2d-overlay-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.d2d-filter-slideout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid var(--border-color);
}
.d2d-filter-slideout-body { padding: 1rem; flex: 1; }
```

### Task 7.3: Añadir presets de filtros

Añadir botones de preset rápido en el slide-out:

```tsx
<div className="d2d-filter-presets">
  <span className="d2d-filter-label">{t("doorToDoor.filters.presets")}</span>
  <div className="d2d-filter-preset-buttons">
    <button onClick={() => onChange({ ...DEFAULT_PREFERENCES, sort_by: "cheapest" })}>
      {t("doorToDoor.filters.presetCheap")}
    </button>
    <button onClick={() => onChange({ ...DEFAULT_PREFERENCES, sort_by: "fastest" })}>
      {t("doorToDoor.filters.presetFast")}
    </button>
    <button onClick={() => onChange({ ...DEFAULT_PREFERENCES, sort_by: "fewest_changes", min_airport_buffer_minutes: 180 })}>
      {t("doorToDoor.filters.presetSafe")}
    </button>
  </div>
</div>
```

i18n nuevas claves:
- `filters.presets`: "Preajustes" / "Presets"
- `filters.presetCheap`: "Económico" / "Budget"
- `filters.presetFast`: "Rápido" / "Fast"
- `filters.presetSafe`: "Seguro" / "Safe"

### Task 7.4: Verificación i18n

```bash
cd frontend
grep -rn 't("doorToDoor\.' src/modules/door-to-door/ --include="*.tsx" --include="*.ts" | grep -oP 'doorToDoor\.[^")]+' | sort -u
```
Verificar que cada clave extraída existe en `src/i18n/domains/doorToDoor.ts` tanto en `doorToDoorEs` como en `doorToDoorEn`.

**Nota sobre presets:** Los botones de preset solo modifican las preferencias, no disparan automáticamente una búsqueda. El usuario debe hacer clic en "Calcular ruta completa" tras aplicar un preset. Esto evita búsquedas accidentales mientras el usuario explora las opciones. Si se desea auto-trigger en el futuro, añadir una prop `onPresetApply` al `DoorToDoorFilterPanel`.

### Task 7.5: Typecheck + build + commit

---

## Fase 8: Integración del Route Visual (radar abstracto) en el flujo principal

**Objetivo:** El componente `DoorToDoorRouteVisual` ya existe pero no se usa en el flujo principal del panel. Integrarlo encima del timeline como overview visual de la ruta completa.

### Task 8.1: Integrar `DoorToDoorRouteVisual` en el panel

Insertar entre la sección de resultados y el timeline:

```tsx
{selectedPlan && response?.flight ? (
  <DoorToDoorRouteVisual option={selectedPlan} flight={response.flight} />
) : null}
```

### Task 8.2: Mejorar el diseño del Route Visual

Rediseñar `DoorToDoorRouteVisual.tsx` para que sea más impactante visualmente:

- Línea de ruta con gradiente que conecta los 4 puntos
- Modos de transporte con iconos coloreados
- IATA codes en tipografía monoespaciada destacada
- Animación de trazado de ruta al aparecer

```tsx
export function DoorToDoorRouteVisual({ option, flight }: { option: DoorToDoorOption | null; flight?: DoorToDoorFlight | null }) {
  const { t } = useI18n();
  // ...
  return (
    <section className="panel d2d-route-visual" aria-label={t("doorToDoor.routeVisual.aria")}>
      <div className="d2d-route-visual-header">
        <h3>{t("doorToDoor.routeVisual.title")}</h3>
      </div>
      <div className="d2d-route-strip">
        {stops.map((stop, index) => (
          <React.Fragment key={`${stop}-${index}`}>
            <div className="d2d-route-stop">
              <span className="d2d-route-stop-num">{index + 1}</span>
              <strong>{stop}</strong>
            </div>
            {index < stops.length - 1 ? (
              <div className={`d2d-route-segment d2d-route-segment-${segments[index]?.mode || "ground"}`}>
                <div className="d2d-route-segment-line" />
                <small>{segments[index]?.label}</small>
              </div>
            ) : null}
          </React.Fragment>
        ))}
      </div>
    </section>
  );
}
```

### Task 8.3: Typecheck + build + commit

---

## Fase 9: Map Hub como dashboard vivo (no colapsado)

**Objetivo:** Transformar el Map Hub de una sección técnica colapsada en `<details>` a un dashboard de capacidades visible e integrado, con indicadores de estado animados y conexión visual a la ruta actual.

### Task 9.1: Rediseñar la sección Map Hub

Sustituir el `<details>` por una sección siempre visible con grid horizontal de capability cards:

```tsx
<section className="panel panel-soft d2d-map-hub" aria-label={t("doorToDoor.sections.coveragePanelTitle")}>
  <div className="d2d-section-head">
    <h2>{t("doorToDoor.sections.coveragePanelTitle")}</h2>
    <span>{t("doorToDoor.sections.coveragePanelBody")}</span>
  </div>
  
  {/* Horizontal scroll de capability cards */}
  <div className="d2d-map-hub-scroll" role="list">
    {CAPABILITY_CARDS.map((card) => {
      const capability = mapCapabilities.find((c) => c.key === card.key);
      if (!capability) return null;
      return (
        <article
          key={card.key}
          role="listitem"
          className={`d2d-map-card d2d-map-card-horizontal is-${capability.state}`}
        >
          <div className="d2d-map-card-icon">
            {capability.state === "available" ? <span className="d2d-capability-dot is-live" /> : null}
            <span className={`d2d-capability-state-icon is-${capability.state}`}>
              {capability.state === "available" ? "✓" : capability.state === "partial" ? "◐" : "○"}
            </span>
          </div>
          <strong>{t(card.titleKey)}</strong>
          <p>{t(card.descriptionKey)}</p>
          <span className={`status-pill ${capabilityStatusClass(capability.state)} d2d-capability-pill`}>
            {t(`doorToDoor.mapHub.state.${capability.state}`)}
          </span>
        </article>
      );
    })}
  </div>
</section>
```

### Task 9.2: CSS para el scroll horizontal

```css
.d2d-map-hub-scroll {
  display: flex;
  gap: var(--gap-md);
  overflow-x: auto;
  padding-bottom: 0.5rem;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
}
.d2d-map-hub-scroll::-webkit-scrollbar { height: 4px; }
.d2d-map-hub-scroll::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 2px; }
.d2d-map-card-horizontal {
  flex: 0 0 220px;
  scroll-snap-align: start;
  padding: 0.75rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--panel-bg);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.d2d-map-card-horizontal:hover {
  border-color: var(--accent-warm);
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.d2d-capability-dot.is-live {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--state-success);
  animation: d2d-live-pulse 2s ease-in-out infinite;
}
@keyframes d2d-live-pulse {
  0%, 100% { box-shadow: 0 0 0 0 var(--state-success); }
  50% { box-shadow: 0 0 0 4px transparent; }
}
```

### Task 9.3: Mantener la sección de Saved Places

La sección de lugares guardados se mantiene debajo del scroll horizontal, como antes, pero sin el `<details>` wrapper.

### Task 9.4: Typecheck + build + commit

---

## Fase 10: Micro-interacciones, polish final y QA dual-theme

**Objetivo:** Añadir la capa final de micro-interacciones que hacen que la interfaz se sienta "viva y cuidada" (`DESIGN.md` §9), y verificar todo en dark + light mode.

### Task 10.1: Micro-interacciones globales

Añadir al CSS de `screens.css`:

```css
/* Card hover elevation */
.d2d-option-card, .d2d-leg-card, .d2d-map-card-horizontal {
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),
              box-shadow 0.2s cubic-bezier(0.16, 1, 0.3, 1),
              border-color 0.2s ease;
}
.d2d-option-card:hover,
.d2d-leg-card:hover,
.d2d-map-card-horizontal:hover {
  transform: translateY(-1px);
}

/* Button press compression */
.btn-primary:active,
.btn-secondary:active,
.btn-ghost:active {
  transform: scale(0.98);
  transition: transform 0.1s ease;
}

/* Section entry animation */
.d2d-results-section,
.d2d-comparator,
.d2d-map-hub,
.d2d-chosen-trust {
  animation: d2d-section-enter 0.4s ease-out both;
}
@keyframes d2d-section-enter {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Stagger delays for sections */
.d2d-chosen-trust      { animation-delay: 0ms; }
.d2d-results-section   { animation-delay: 80ms; }
.d2d-comparator        { animation-delay: 160ms; }
.d2d-map-hub           { animation-delay: 240ms; }

/* Status pill color transitions */
.status-pill {
  transition: background-color 0.25s ease, color 0.25s ease, border-color 0.25s ease;
}

/* Focus-visible ring for all interactive elements */
:focus-visible {
  outline: 2px solid var(--accent-warm);
  outline-offset: 2px;
  border-radius: 2px;
}

/* Smooth autocomplete transition */
.d2d-autocomplete .qs-autocomplete {
  animation: d2d-autocomplete-in 0.15s ease-out;
}
@keyframes d2d-autocomplete-in {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Chosen option transition */
.d2d-option-card.is-chosen {
  transition: border-color 0.3s ease, box-shadow 0.3s ease, background 0.3s ease;
}
```

### Task 10.2: Animación del trust modal

```css
.d2d-trust-overlay {
  animation: d2d-overlay-in 0.2s ease-out;
}
.d2d-trust-modal {
  animation: d2d-modal-enter 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes d2d-modal-enter {
  from { opacity: 0; transform: scale(0.96) translateY(8px); }
  to   { opacity: 1; transform: scale(1) translateY(0); }
}
```

### Task 10.3: Mobile responsive refinements

- La sticky bar colapsa a solo el resumen en móvil (métricas ocultas, solo label + precio)
- Las capability cards pasan a grid de 2 columnas en tablet, 1 columna en móvil
- El slide-out de filtros ocupa 100vw en móvil
- El comparador usa barras más finas (4px) en móvil
- Las tarjetas de opción eliminan el hover elevation en touch devices (`@media (hover: none)`)

### Task 10.4: QA dual-theme

Verificar en dark mode y light mode:
- Contraste de texto legible en todos los estados
- Los acentos (`var(--accent-warm)`, `var(--state-success)`, etc.) funcionan en ambos temas
- Las animaciones no causan flickering en ninguno de los dos temas
- Los skeleton loaders son visibles en ambos temas
- Las sombras y glows son apropiados para cada tema (más sutiles en light)

### Task 10.5: Typecheck final + build + tests

```bash
cd frontend
npx tsc --noEmit
npm run build
```

### Task 10.6: Commit final

```bash
git add frontend/src/modules/door-to-door/ frontend/src/styles/screens.css frontend/src/i18n/domains/doorToDoor.ts
git commit -m "feat(d2d): micro-interactions polish — hover elevation, section stagger, focus rings, modal animation, responsive refinements, dual-theme QA"
```

---

## Resumen de commits

| Commit | Fase | Mensaje |
|--------|------|---------|
| 1 | Fase 1 | `refactor(d2d): extract hooks from DoorToDoorPanel (useDoorToDoorSearch, useDoorToDoorResults, useDoorToDoorHistory, useDoorToDoorMapHub)` |
| 2 | Fase 2 | `feat(d2d): redesign empty/loading/error states with Viru personality — animated route, skeleton cards, warm error` |
| 3 | Fase 3 | `feat(d2d): redesigned connected timeline — boarding-pass cues, staggered leg reveal, flight segment accent` |
| 4 | Fase 4 | `feat(d2d): visual hierarchy for option cards by status — real/deeplink/estimate differentiation, chosen glow, hover elevation` |
| 5 | Fase 5 | `feat(d2d): sticky decision bar with section navigation — persistent context while scrolling` |
| 6 | Fase 6 | `feat(d2d): redesigned comparator with horizontal trade-off bars and color-coded deltas` |
| 7 | Fase 7 | `feat(d2d): filter slide-out panel with animation + quick presets (budget/fast/safe)` |
| 8 | Fase 8 | `feat(d2d): integrate route visual (abstract radar) into main results flow above timeline` |
| 9 | Fase 9 | `feat(d2d): transform Map Hub into alive dashboard — horizontal scroll, live pulse dots, removed collapse` |
| 10 | Fase 10 | `feat(d2d): micro-interactions polish — hover elevation, section stagger, focus rings, modal animation, responsive refinements` |

## Archivos afectados (resumen)

| Archivo | Fase(s) | Tipo |
|---------|---------|------|
| `DoorToDoorPanel.tsx` | 1, 3, 5, 6, 7, 8 | Reescribir con hooks + integrar mejoras |
| `hooks/useDoorToDoorSearch.ts` | 1 | NUEVO |
| `hooks/useDoorToDoorResults.ts` | 1 | NUEVO |
| `hooks/useDoorToDoorHistory.ts` | 1 | NUEVO |
| `hooks/useDoorToDoorMapHub.ts` | 1 | NUEVO |
| `constants.ts` | 1 | NUEVO |
| `DoorToDoorEmptyState.tsx` | 2 | Rediseñar |
| `DoorToDoorLoadingState.tsx` | 2 | Rediseñar con skeletons |
| `DoorToDoorErrorState.tsx` | 2 | Mejorar |
| `DoorToDoorOptionCard.tsx` | 4 | Jerarquía visual + hover |
| `DoorToDoorStickyBar.tsx` | 5 | NUEVO |
| `DoorToDoorComparator.tsx` | 6 | NUEVO (extraer del panel) |
| `DoorToDoorFilterPanel.tsx` | 7 | NUEVO (slide-out) |
| `DoorToDoorRouteVisual.tsx` | 8 | Rediseñar + integrar |
| `screens.css` | 2-10 | ~150 nuevas líneas CSS |
| `doorToDoor.ts` (i18n) | 5, 7, 8 | ~15 nuevas claves ES + EN |

## Riesgos y mitigaciones

1. **Regresión funcional tras el refactor de hooks (Fase 1):** El comportamiento debe ser exactamente igual. Mitigación: extraer hook por hook en dos sub-commits (1a: `useDoorToDoorSearch` + `useDoorToDoorResults`, 1b: `useDoorToDoorHistory` + `useDoorToDoorMapHub`), verificar `npx tsc --noEmit` tras cada uno, y hacer `npm run build` tras el refactor completo.

2. **Rotura del Suspense boundary (Fase 1):** El hook `useDoorToDoorSearch` llama a `useSearchParams()` de Next.js, que requiere un `<Suspense>` boundary. La `page.tsx` actual ya tiene uno. Verificar que tras el refactor el `DoorToDoorPanel` sigue estando dentro de ese `<Suspense>` en `page.tsx`.

3. **Hydration mismatch por localStorage (Fase 1):** El hook `useDoorToDoorMapHub` lee `localStorage` para saved places. Aunque usa el guard `typeof window === "undefined"`, puede haber diferencias entre el render del servidor y el del cliente. Mitigación: añadir un patrón de `const [mounted, setMounted] = useState(false)` en `useEffect` y solo renderizar saved places cuando `mounted === true`.

4. **Overflow horizontal en móvil (Fases 5, 9):** La sticky bar y el scroll horizontal del Map Hub deben ser responsive. Mitigación: probar en viewport de 375px (iPhone SE) y 768px (iPad).

5. **Rendimiento de animaciones en dispositivos lentos (Fase 10):** ~10 animaciones CSS simultáneas pueden causar jank en móviles antiguos. Mitigación: usar `transform` y `opacity` exclusivamente para animaciones; testear con CPU throttling (Chrome DevTools → Performance → 4x slowdown); añadir `will-change: transform, opacity` en elementos animados.

6. **Regresión en light mode:** Los cambios visuales deben funcionar en ambos temas. Mitigación: verificar cada fase en light mode antes de commitear.

7. **Claves i18n huérfanas (Fases 5, 7, 8):** Cada nueva llamada a `t("doorToDoor.*")` debe tener su clave en `doorToDoor.ts` (ES + EN). Mitigación: en cada fase que añada i18n, ejecutar `grep -rn "t(\"doorToDoor\." frontend/src/modules/door-to-door/` y verificar que todas las claves existen en `doorToDoor.ts`.

8. **A11y:** Las animaciones deben respetar `prefers-reduced-motion`. Mitigación: añadir media query al final de la Fase 10.

```css
@media (prefers-reduced-motion: reduce) {
  .d2d-option-card,
  .d2d-leg-card,
  .d2d-timeline-leg,
  .d2d-section-enter,
  .d2d-sticky-bar,
  .d2d-filter-slideout,
  .d2d-trust-modal {
    animation: none !important;
    transition: none !important;
  }
}
```

---

## Consideraciones para fases futuras

### Search form UX (no incluido en este plan)

El formulario de búsqueda actual es funcional pero no guía al usuario paso a paso. Una futura iteración podría:
- Añadir un step indicator sutil: "1. Elige vuelo → 2. Define origen → 3. Define destino"
- Colapsar el formulario tras la primera búsqueda exitosa para maximizar el espacio de resultados
- Mostrar un resumen inline del vuelo seleccionado con el IATA y la fecha en formato boarding-pass
- Pre-rellenar el destino final basado en el aeropuerto de llegada si el usuario tiene ubicación guardada

### i18n verification step

En cada fase que añada nuevas claves i18n, verificar que existen en ambos idiomas:

```bash
cd frontend
grep -rn 't("doorToDoor\.' src/modules/door-to-door/ --include="*.tsx" --include="*.ts" | grep -oP 'doorToDoor\.[^")]+' | sort -u
```

Cada clave debe existir tanto en `doorToDoorEs` como en `doorToDoorEn` dentro de `src/i18n/domains/doorToDoor.ts`.

### Presets de filtros

Los botones de preset (Fase 7) solo modifican las preferencias — no disparan automáticamente una búsqueda. El usuario debe hacer clic en "Calcular ruta completa" tras aplicar un preset. Esto evita búsquedas accidentales mientras explora opciones.

---

## Plan de ejecución

Cada fase debe implementarse, verificarse (typecheck + build), y commitearse antes de pasar a la siguiente. Las dependencias son secuenciales: la Fase 1 desbloquea todas las demás; las Fases 2-10 pueden hacerse en orden pero cada una es independiente visualmente.
