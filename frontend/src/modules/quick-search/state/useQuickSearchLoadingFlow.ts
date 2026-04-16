import { Dispatch, MutableRefObject, SetStateAction, useEffect } from "react";

import { QuickSearchLoadingPhase } from "@/modules/quick-search/types";

type SearchState = "idle" | "loading" | "success" | "empty" | "error" | "rate";
type QuickSearchLoadingFlowArgs = {
  searchState: SearchState;
  showLoader: boolean;
  loadingVisualHold: boolean;
  targetProgress: number;
  displayProgress: number;
  prefersReducedMotion: boolean;
  setShowLoader: Dispatch<SetStateAction<boolean>>;
  setShowBoarding: Dispatch<SetStateAction<boolean>>;
  setLoadingVisualHold: Dispatch<SetStateAction<boolean>>;
  setDisplayProgress: Dispatch<SetStateAction<number>>;
  setLoadingPhase: Dispatch<SetStateAction<QuickSearchLoadingPhase>>;
  setTargetProgress: Dispatch<SetStateAction<number>>;
  activeLoadingRequestRef: MutableRefObject<number | null>;
  prevSearchStateRef: MutableRefObject<SearchState>;
  requestIdRef: MutableRefObject<number>;
  progressRafRef: MutableRefObject<number | null>;
  animFromRef: MutableRefObject<number>;
  animToRef: MutableRefObject<number>;
  animStartTsRef: MutableRefObject<number>;
  animDurationMsRef: MutableRefObject<number>;
  lastTargetRef: MutableRefObject<number>;
  isAnimatingRef: MutableRefObject<boolean>;
  displayProgressRef: MutableRefObject<number>;
  commitRafRef: MutableRefObject<number | null>;
  boardingThresholdTimerRef: MutableRefObject<number | null>;
  takeoffHoldTimerRef: MutableRefObject<number | null>;
  loadingStartRef: MutableRefObject<number | null>;
  hideTimeoutRef: MutableRefObject<number | null>;
  debugLastTickLogTsRef: MutableRefObject<number>;
  debugLog: (message: string) => void;
};

export function useQuickSearchLoadingFlow({
  searchState,
  showLoader,
  loadingVisualHold,
  targetProgress,
  displayProgress,
  prefersReducedMotion,
  setShowLoader,
  setShowBoarding,
  setLoadingVisualHold,
  setDisplayProgress,
  setLoadingPhase,
  setTargetProgress,
  activeLoadingRequestRef,
  prevSearchStateRef,
  requestIdRef,
  progressRafRef,
  animFromRef,
  animToRef,
  animStartTsRef,
  animDurationMsRef,
  lastTargetRef,
  isAnimatingRef,
  displayProgressRef,
  commitRafRef,
  boardingThresholdTimerRef,
  takeoffHoldTimerRef,
  loadingStartRef,
  hideTimeoutRef,
  debugLastTickLogTsRef,
  debugLog,
}: QuickSearchLoadingFlowArgs) {
  useEffect(() => {
    const minVisibleMs = 240;
    if (hideTimeoutRef.current) {
      window.clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }
    if (searchState === "loading") {
      loadingStartRef.current = typeof performance !== "undefined" ? performance.now() : Date.now();
      setShowLoader(true);
      return;
    }
    if (!showLoader) return;
    const now = typeof performance !== "undefined" ? performance.now() : Date.now();
    const startedAt = loadingStartRef.current ?? now;
    const elapsed = Math.max(0, now - startedAt);
    const remaining = Math.max(0, minVisibleMs - elapsed);
    hideTimeoutRef.current = window.setTimeout(() => {
      setShowLoader(false);
      hideTimeoutRef.current = null;
      loadingStartRef.current = null;
    }, remaining);
    return () => {
      if (hideTimeoutRef.current) {
        window.clearTimeout(hideTimeoutRef.current);
        hideTimeoutRef.current = null;
      }
    };
  }, [searchState, showLoader, setShowLoader, hideTimeoutRef, loadingStartRef]);

  useEffect(() => {
    displayProgressRef.current = displayProgress;
  }, [displayProgress, displayProgressRef]);

  useEffect(() => {
    const calcDuration = (delta: number) => {
      if (delta <= 10) return 220;
      if (delta <= 30) return 420;
      if (delta <= 60) return 680;
      return 900;
    };
    const easeOutCubic = (t: number) => 1 - (1 - t) ** 3;
    const flushProgress = (value: number) => {
      displayProgressRef.current = value;
      setDisplayProgress(value);
      animFromRef.current = value;
      animToRef.current = value;
      lastTargetRef.current = value;
      isAnimatingRef.current = false;
      if (progressRafRef.current) {
        window.cancelAnimationFrame(progressRafRef.current);
        progressRafRef.current = null;
      }
    };
    const animate = (ts: number) => {
      const from = animFromRef.current;
      const to = animToRef.current;
      const duration = Math.max(1, animDurationMsRef.current);
      const elapsed = ts - animStartTsRef.current;
      const progress = Math.max(0, Math.min(1, elapsed / duration));
      let next = from + easeOutCubic(progress) * (to - from);
      if (to >= from) {
        next = Math.min(next, to);
      } else {
        next = Math.max(next, to);
      }
      const nextSafe = to >= 0 ? Math.min(next, to) : next;
      const prevInt = Math.round(displayProgressRef.current);
      const nextInt = Math.round(nextSafe);
      if (process.env.NODE_ENV !== "production") {
        if (ts - debugLastTickLogTsRef.current >= 120 || progress >= 1) {
          debugLastTickLogTsRef.current = ts;
          debugLog(`tick from=${from.toFixed(1)} to=${to.toFixed(1)} display=${nextSafe.toFixed(1)} t=${progress.toFixed(2)}`);
        }
      }
      if (nextInt !== prevInt || progress >= 1) {
        displayProgressRef.current = nextSafe;
        setDisplayProgress(nextSafe);
      }
      if (progress >= 1) {
        isAnimatingRef.current = false;
        progressRafRef.current = null;
        displayProgressRef.current = to;
        setDisplayProgress(to);
        return;
      }
      progressRafRef.current = window.requestAnimationFrame(animate);
    };
    if (prefersReducedMotion) {
      flushProgress(targetProgress);
      return;
    }
    const targetUnchanged = targetProgress === lastTargetRef.current;
    if (targetUnchanged) {
      if (isAnimatingRef.current) return;
      if (displayProgressRef.current === targetProgress) return;
    } else if (progressRafRef.current) {
      debugLog("cancel RAF (new segment)");
      window.cancelAnimationFrame(progressRafRef.current);
      progressRafRef.current = null;
      isAnimatingRef.current = false;
    }
    const from = displayProgressRef.current;
    const to = targetProgress;
    if (from === to) {
      flushProgress(to);
      return;
    }
    const delta = Math.abs(to - from);
    animFromRef.current = from;
    animToRef.current = to;
    animStartTsRef.current = typeof performance !== "undefined" ? performance.now() : 0;
    animDurationMsRef.current = calcDuration(delta);
    lastTargetRef.current = to;
    isAnimatingRef.current = true;
    progressRafRef.current = window.requestAnimationFrame(animate);
  }, [
    targetProgress,
    prefersReducedMotion,
    debugLog,
    setDisplayProgress,
    animDurationMsRef,
    animFromRef,
    animStartTsRef,
    animToRef,
    debugLastTickLogTsRef,
    displayProgressRef,
    isAnimatingRef,
    lastTargetRef,
    progressRafRef,
  ]);

  useEffect(() => {
    if (boardingThresholdTimerRef.current) {
      window.clearTimeout(boardingThresholdTimerRef.current);
      boardingThresholdTimerRef.current = null;
    }
    if (searchState === "loading") {
      setShowBoarding(false);
      boardingThresholdTimerRef.current = window.setTimeout(() => {
        setShowBoarding(true);
      }, 300);
      return () => {
        if (boardingThresholdTimerRef.current) {
          window.clearTimeout(boardingThresholdTimerRef.current);
          boardingThresholdTimerRef.current = null;
        }
      };
    }
    if (!loadingVisualHold) {
      setShowBoarding(false);
    }
  }, [searchState, loadingVisualHold, setShowBoarding, boardingThresholdTimerRef]);

  useEffect(() => {
    if (commitRafRef.current) {
      window.cancelAnimationFrame(commitRafRef.current);
      commitRafRef.current = null;
    }
    const prev = prevSearchStateRef.current;
    if (prev === "loading" && (searchState === "success" || searchState === "empty")) {
      const requestId = activeLoadingRequestRef.current;
      if (requestId !== null && requestId === requestIdRef.current) {
        setLoadingVisualHold(true);
        const raf1 = window.requestAnimationFrame(() => {
          const raf2 = window.requestAnimationFrame(() => {
            if (requestId !== requestIdRef.current) return;
            debugLog("target -> 100 (committed)");
            setLoadingPhase("committed");
            setTargetProgress(100);
          });
          commitRafRef.current = raf2;
        });
        commitRafRef.current = raf1;
        if (takeoffHoldTimerRef.current) {
          window.clearTimeout(takeoffHoldTimerRef.current);
          takeoffHoldTimerRef.current = null;
        }
        takeoffHoldTimerRef.current = window.setTimeout(() => {
          if (requestId !== requestIdRef.current) return;
          setLoadingVisualHold(false);
        }, 240);
      }
    } else if (searchState === "rate" || searchState === "error" || searchState === "idle") {
      setLoadingVisualHold(false);
      setShowBoarding(false);
    }
    prevSearchStateRef.current = searchState;
  }, [
    searchState,
    debugLog,
    setLoadingPhase,
    setLoadingVisualHold,
    setShowBoarding,
    setTargetProgress,
    activeLoadingRequestRef,
    commitRafRef,
    prevSearchStateRef,
    requestIdRef,
    takeoffHoldTimerRef,
  ]);

  useEffect(() => () => {
    if (progressRafRef.current) {
      debugLog("cancel RAF (cleanup)");
      window.cancelAnimationFrame(progressRafRef.current);
      progressRafRef.current = null;
    }
    if (commitRafRef.current) {
      window.cancelAnimationFrame(commitRafRef.current);
      commitRafRef.current = null;
    }
    if (boardingThresholdTimerRef.current) {
      window.clearTimeout(boardingThresholdTimerRef.current);
      boardingThresholdTimerRef.current = null;
    }
    if (takeoffHoldTimerRef.current) {
      window.clearTimeout(takeoffHoldTimerRef.current);
      takeoffHoldTimerRef.current = null;
    }
    if (hideTimeoutRef.current) {
      window.clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }
    loadingStartRef.current = null;
  }, [
    debugLog,
    boardingThresholdTimerRef,
    commitRafRef,
    hideTimeoutRef,
    loadingStartRef,
    progressRafRef,
    takeoffHoldTimerRef,
  ]);
}
