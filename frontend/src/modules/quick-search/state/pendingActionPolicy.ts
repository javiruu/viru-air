export type PendingActionVisibility = {
  consoleAction: boolean;
  toolbarAction: boolean;
  contextRailNotice: boolean;
  contextRailAction: boolean;
};

/**
 * Keep a single actionable pending CTA in quick-search.
 * The filter console owns "Aplicar y buscar"; other zones may stay informative.
 */
export function getPendingActionVisibility(pendingSearchChanges: boolean): PendingActionVisibility {
  return {
    consoleAction: pendingSearchChanges,
    toolbarAction: false,
    contextRailNotice: pendingSearchChanges,
    contextRailAction: false,
  };
}
