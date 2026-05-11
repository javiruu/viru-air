"use client";

import { useEffect } from "react";

const SCROLLING_CLASS = "is-scrolling";
const SCROLLBAR_PROXIMITY_CLASS = "is-scrollbar-proximity";
const WHEEL_SCROLLING_CLASS = "is-wheel-scrolling";
const FADE_OUT_DELAY_MS = 2000;
const PROXIMITY_PX = 60;
const WHEEL_CLASS_HOLD_MS = 220;

export default function ScrollActivityScrollbar() {
  useEffect(() => {
    let timeoutId: ReturnType<typeof window.setTimeout> | null = null;
    let wheelTimeoutId: ReturnType<typeof window.setTimeout> | null = null;

    const showScrollbar = () => {
      document.documentElement.classList.add(SCROLLING_CLASS);
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
      timeoutId = window.setTimeout(() => {
        document.documentElement.classList.remove(SCROLLING_CLASS);
      }, FADE_OUT_DELAY_MS);
    };

    window.addEventListener("scroll", showScrollbar, { passive: true });

    const handleWheel = () => {
      document.documentElement.classList.add(WHEEL_SCROLLING_CLASS);
      if (wheelTimeoutId !== null) {
        window.clearTimeout(wheelTimeoutId);
      }
      wheelTimeoutId = window.setTimeout(() => {
        document.documentElement.classList.remove(WHEEL_SCROLLING_CLASS);
      }, WHEEL_CLASS_HOLD_MS);
    };

    const handlePointerMove = (event: MouseEvent) => {
      const nearScrollbar = window.innerWidth - event.clientX <= PROXIMITY_PX;
      document.documentElement.classList.toggle(SCROLLBAR_PROXIMITY_CLASS, nearScrollbar);
    };

    const handlePointerLeave = () => {
      document.documentElement.classList.remove(SCROLLBAR_PROXIMITY_CLASS);
    };

    window.addEventListener("mousemove", handlePointerMove, { passive: true });
    window.addEventListener("mouseleave", handlePointerLeave, { passive: true });
    window.addEventListener("wheel", handleWheel, { passive: true });

    return () => {
      window.removeEventListener("scroll", showScrollbar);
      window.removeEventListener("mousemove", handlePointerMove);
      window.removeEventListener("mouseleave", handlePointerLeave);
      window.removeEventListener("wheel", handleWheel);
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
      if (wheelTimeoutId !== null) {
        window.clearTimeout(wheelTimeoutId);
      }
      document.documentElement.classList.remove(SCROLLING_CLASS);
      document.documentElement.classList.remove(SCROLLBAR_PROXIMITY_CLASS);
      document.documentElement.classList.remove(WHEEL_SCROLLING_CLASS);
    };
  }, []);

  return null;
}
