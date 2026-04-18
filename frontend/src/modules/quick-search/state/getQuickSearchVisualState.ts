type SearchState = "idle" | "loading" | "success" | "empty" | "error" | "rate";

export type QuickSearchVisualState =
  | "idle"
  | "loading"
  | "success_with_results"
  | "success_empty"
  | "error"
  | "rate";

type Args = {
  searchState: SearchState;
  showLoader: boolean;
  loadingVisualHold: boolean;
  visibleResultsCount: number;
};

export function getQuickSearchVisualState({
  searchState,
  showLoader,
  loadingVisualHold,
  visibleResultsCount,
}: Args): QuickSearchVisualState {
  if (searchState === "loading" || showLoader || loadingVisualHold) {
    return "loading";
  }

  if (searchState === "error" || searchState === "rate" || searchState === "idle") {
    return searchState;
  }

  if (searchState === "empty") {
    return "success_empty";
  }

  return visibleResultsCount > 0 ? "success_with_results" : "success_empty";
}
