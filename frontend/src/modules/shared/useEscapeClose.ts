import { useEffect } from "react";

/**
 * Calls `onClose` whenever the user presses the Escape key while the hook is
 * mounted and `enabled` is true. Used to dismiss transient surfaces (modals,
 * drawers, date pickers, popovers) in accordance with WAI-ARIA Authoring
 * Practices for dialogs and landmarks.
 *
 * The listener is attached to `document` so it works for portals too.
 *
 * Multiple instances may be active at once — each one closes its own surface
 * when Escape is pressed. To opt out temporarily (for example while a child
 * picker is open) pass `enabled = false`.
 *
 * `onClose` should be stable across renders (e.g. wrapped with `useCallback`)
 * to avoid re-registering the document listener on every render.
 */
export function useEscapeClose(onClose: () => void, enabled: boolean = true): void {
  useEffect(() => {
    if (!enabled) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [enabled, onClose]);
}

export default useEscapeClose;
