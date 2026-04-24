"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";

import AirLoader from "@/modules/shared/AirLoader";

const FAILSAFE_TIMEOUT_MS = 10000;

function isModifiedEvent(event: MouseEvent | PointerEvent | KeyboardEvent): boolean {
  return event.metaKey || event.ctrlKey || event.shiftKey || event.altKey;
}

function isExternalOrInvalidHref(rawHref: string): boolean {
  return (
    rawHref.startsWith("#")
    || rawHref.startsWith("mailto:")
    || rawHref.startsWith("tel:")
    || rawHref.startsWith("javascript:")
  );
}

function isSameDocumentHashNavigation(url: URL): boolean {
  return (
    url.origin === window.location.origin
    && url.pathname === window.location.pathname
    && url.search === window.location.search
    && url.hash.length > 0
  );
}

function shouldStartForAnchor(anchor: HTMLAnchorElement, event: MouseEvent | PointerEvent | KeyboardEvent): boolean {
  if (isModifiedEvent(event)) return false;
  if (anchor.hasAttribute("download")) return false;

  const target = anchor.getAttribute("target");
  if (target && target.toLowerCase() !== "_self") return false;

  const rawHref = anchor.getAttribute("href");
  if (!rawHref || isExternalOrInvalidHref(rawHref)) return false;

  let resolved: URL;
  try {
    resolved = new URL(anchor.href, window.location.href);
  } catch {
    return false;
  }

  if (resolved.origin !== window.location.origin) return false;
  if (isSameDocumentHashNavigation(resolved)) return false;

  return true;
}

export default function NavigationPendingOverlay() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const routeKey = useMemo(() => {
    const qs = searchParams?.toString() || "";
    return `${pathname || ""}?${qs}`;
  }, [pathname, searchParams]);

  const [isPending, setIsPending] = useState(false);
  const timeoutRef = useRef<number | null>(null);
  const pointerTriggeredRef = useRef(false);

  useEffect(() => {
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsPending(false);
  }, [routeKey]);

  useEffect(() => {
    function startPending() {
      if (!isPending) {
        setIsPending(true);
      }
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = window.setTimeout(() => {
        timeoutRef.current = null;
        setIsPending(false);
      }, FAILSAFE_TIMEOUT_MS);
    }

    function onPointerDownCapture(event: PointerEvent) {
      if (event.button !== 0) return;
      const target = event.target;
      if (!(target instanceof Element)) return;
      const anchor = target.closest("a[href]");
      if (!(anchor instanceof HTMLAnchorElement)) return;
      if (!shouldStartForAnchor(anchor, event)) return;
      pointerTriggeredRef.current = true;
      startPending();
    }

    function onClickCapture(event: MouseEvent) {
      if (event.button !== 0) return;
      if (pointerTriggeredRef.current) {
        pointerTriggeredRef.current = false;
        return;
      }
      const target = event.target;
      if (!(target instanceof Element)) return;
      const anchor = target.closest("a[href]");
      if (!(anchor instanceof HTMLAnchorElement)) return;
      if (!shouldStartForAnchor(anchor, event)) return;
      startPending();
    }

    function onKeyDownCapture(event: KeyboardEvent) {
      if (event.key !== "Enter") return;
      const target = event.target;
      if (!(target instanceof Element)) return;
      const anchor = target.closest("a[href]");
      if (!(anchor instanceof HTMLAnchorElement)) return;
      if (!shouldStartForAnchor(anchor, event)) return;
      startPending();
    }

    function onPopState() {
      startPending();
    }

    document.addEventListener("pointerdown", onPointerDownCapture, true);
    document.addEventListener("click", onClickCapture, true);
    document.addEventListener("keydown", onKeyDownCapture, true);
    window.addEventListener("popstate", onPopState);

    return () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      document.removeEventListener("pointerdown", onPointerDownCapture, true);
      document.removeEventListener("click", onClickCapture, true);
      document.removeEventListener("keydown", onKeyDownCapture, true);
      window.removeEventListener("popstate", onPopState);
    };
  }, [isPending]);

  if (!isPending) return null;

  return (
    <div className="navigation-pending-overlay" role="status" aria-live="polite" aria-label="Cargando navegación">
      <section className="panel panel-soft navigation-pending-overlay__card">
        <AirLoader size={0.9} />
      </section>
    </div>
  );
}
