import { useRef, useState } from "react";

import {
  CountryAirports,
  QuickSearchAutocompleteField,
  QuickSearchFieldErrors,
  RelaxUndoPayload,
} from "@/modules/quick-search/types";

/**
 * Form-only state for quick-search.
 * Extracted from useQuickSearchMainState so that result/loading/UI state can
 * be managed independently per search side (outbound / return).
 */
export function useQuickSearchFormState(initialOrigin: string, initialDestination: string) {
  // ── Route ──
  const [origin, setOrigin] = useState(initialOrigin);
  const [destination, setDestination] = useState(initialDestination);
  const [travelDate, setTravelDate] = useState("");
  const [returnDate, setReturnDate] = useState("");
  const [isReturn, setIsReturn] = useState(false);
  const [adults, setAdults] = useState(1);

  // ── Country scope ──
  const [originCountryOnly, setOriginCountryOnly] = useState<CountryAirports | null>(null);
  const [destinationCountryOnly, setDestinationCountryOnly] = useState<CountryAirports | null>(null);
  const [originSelectedCountryCode, setOriginSelectedCountryCode] = useState<string | null>(null);
  const [destinationSelectedCountryCode, setDestinationSelectedCountryCode] = useState<string | null>(null);

  // ── Time window ──
  const [departAfter, setDepartAfter] = useState("07:00");
  const [departBefore, setDepartBefore] = useState("22:00");

  // ── Stops ──
  const [includeStops, setIncludeStops] = useState(false);
  const [maxStops, setMaxStops] = useState(1);
  const [bufferMin, setBufferMin] = useState("");

  // ── Coverage ──
  const [radiusKm, setRadiusKm] = useState(150);
  const [includeNearbyOrigins, setIncludeNearbyOrigins] = useState(false);
  const [includeNearbyDestinations, setIncludeNearbyDestinations] = useState(false);
  const [excludeOrigins, setExcludeOrigins] = useState<string[]>([]);
  const [excludeDestinations, setExcludeDestinations] = useState<string[]>([]);
  const [excludeOriginInput, setExcludeOriginInput] = useState("");
  const [excludeDestinationInput, setExcludeDestinationInput] = useState("");

  // ── Search constraints ──
  const [strictFilters, setStrictFilters] = useState(true);
  const [daysBefore, setDaysBefore] = useState(0);
  const [daysAfter, setDaysAfter] = useState(0);
  const [applyFlexReturn, setApplyFlexReturn] = useState(false);

  // ── Visible filters ──
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [durationMax, setDurationMax] = useState("");
  const [sortBy, setSortBy] = useState<"ranking" | "price" | "duration" | "freshness">("ranking");

  // ── Airport picker ──
  const [activePicker, setActivePicker] = useState<"origin" | "destination" | null>(null);
  const [airportSearch, setAirportSearch] = useState("");
  const [recentAirports, setRecentAirports] = useState<string[]>([]);
  const [selectedCountry, setSelectedCountry] = useState<CountryAirports | null>(null);
  const [countrySelectionTouched, setCountrySelectionTouched] = useState(false);
  const [airportSelectionTouched, setAirportSelectionTouched] = useState(false);

  // ── Field interaction ──
  const [isEditing, setIsEditing] = useState(false);
  const [routePulse, setRoutePulse] = useState(false);
  const [originTouched, setOriginTouched] = useState(false);
  const [destinationTouched, setDestinationTouched] = useState(false);
  const [dateTouched, setDateTouched] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<QuickSearchFieldErrors>({});
  const [activeAutocompleteField, setActiveAutocompleteField] = useState<QuickSearchAutocompleteField | null>(null);
  const [activeAutocompleteIndex, setActiveAutocompleteIndex] = useState(-1);

  // ── Filter drawer ──
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);

  // ── Form‑scoped refs ──
  const blurTimer = useRef<number | null>(null);
  const autocompleteBlurTimer = useRef<number | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);
  const filtersToggleRef = useRef<HTMLButtonElement | null>(null);
  const filtersCloseRef = useRef<HTMLButtonElement | null>(null);
  const explainPopoverRef = useRef<HTMLDetailsElement | null>(null);
  const explainTriggerRef = useRef<HTMLElement | null>(null);
  const relaxUndoRef = useRef<RelaxUndoPayload | null>(null);
  const lastPickerTriggerRef = useRef<HTMLButtonElement | null>(null);
  const airportSearchInputRef = useRef<HTMLInputElement | null>(null);

  return {
    // Route
    origin,
    setOrigin,
    destination,
    setDestination,
    travelDate,
    setTravelDate,
    returnDate,
    setReturnDate,
    isReturn,
    setIsReturn,
    adults,
    setAdults,

    // Country scope
    originCountryOnly,
    setOriginCountryOnly,
    destinationCountryOnly,
    setDestinationCountryOnly,
    originSelectedCountryCode,
    setOriginSelectedCountryCode,
    destinationSelectedCountryCode,
    setDestinationSelectedCountryCode,

    // Time window
    departAfter,
    setDepartAfter,
    departBefore,
    setDepartBefore,

    // Stops
    includeStops,
    setIncludeStops,
    maxStops,
    setMaxStops,
    bufferMin,
    setBufferMin,

    // Coverage
    radiusKm,
    setRadiusKm,
    includeNearbyOrigins,
    setIncludeNearbyOrigins,
    includeNearbyDestinations,
    setIncludeNearbyDestinations,
    excludeOrigins,
    setExcludeOrigins,
    excludeDestinations,
    setExcludeDestinations,
    excludeOriginInput,
    setExcludeOriginInput,
    excludeDestinationInput,
    setExcludeDestinationInput,

    // Search constraints
    strictFilters,
    setStrictFilters,
    daysBefore,
    setDaysBefore,
    daysAfter,
    setDaysAfter,
    applyFlexReturn,
    setApplyFlexReturn,

    // Visible filters
    priceMin,
    setPriceMin,
    priceMax,
    setPriceMax,
    durationMax,
    setDurationMax,
    sortBy,
    setSortBy,

    // Airport picker
    activePicker,
    setActivePicker,
    airportSearch,
    setAirportSearch,
    recentAirports,
    setRecentAirports,
    selectedCountry,
    setSelectedCountry,
    countrySelectionTouched,
    setCountrySelectionTouched,
    airportSelectionTouched,
    setAirportSelectionTouched,

    // Field interaction
    isEditing,
    setIsEditing,
    routePulse,
    setRoutePulse,
    originTouched,
    setOriginTouched,
    destinationTouched,
    setDestinationTouched,
    dateTouched,
    setDateTouched,
    fieldErrors,
    setFieldErrors,
    activeAutocompleteField,
    setActiveAutocompleteField,
    activeAutocompleteIndex,
    setActiveAutocompleteIndex,

    // Filter drawer
    isFiltersOpen,
    setIsFiltersOpen,

    // Form refs
    blurTimer,
    autocompleteBlurTimer,
    formRef,
    filtersToggleRef,
    filtersCloseRef,
    explainPopoverRef,
    explainTriggerRef,
    relaxUndoRef,
    lastPickerTriggerRef,
    airportSearchInputRef,
  };
}

export type QuickSearchFormState = ReturnType<typeof useQuickSearchFormState>;
