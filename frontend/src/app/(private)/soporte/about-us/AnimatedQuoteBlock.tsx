"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";

export const ABOUT_US_QUOTE_TEXT = "Hecho 100% con vibe-coding y amor";
const TYPING_SPEED_MS = 42;
const START_DELAY_MS = 320;
const HOLD_DELAY_MS = 1500;

export default function AnimatedQuoteBlock() {
  const [visibleChars, setVisibleChars] = useState(0);
  const prefersReducedMotion = useReducedMotion();
  const intervalRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);
  const characters = useMemo(() => Array.from(ABOUT_US_QUOTE_TEXT), []);
  const isComplete = visibleChars >= characters.length;

  useEffect(() => {
    setVisibleChars(0);

    if (prefersReducedMotion) {
      setVisibleChars(characters.length);
      return undefined;
    }

    timeoutRef.current = window.setTimeout(() => {
      intervalRef.current = window.setInterval(() => {
        setVisibleChars((current) => {
          if (current >= characters.length) {
            if (intervalRef.current !== null) {
              window.clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
            return current;
          }

          return current + 1;
        });
      }, TYPING_SPEED_MS);
    }, START_DELAY_MS);

    return () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [characters, prefersReducedMotion]);

  return (
    <motion.blockquote
      className="support-about-quote"
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{
        opacity: 1,
        y: 0,
        scale: 1,
      }}
      transition={{ duration: 0.55, ease: "easeOut" }}
    >
      <motion.div
        className="support-about-quote-frame"
        animate={
          isComplete
            ? {
                y: [0, -4, 0],
                scale: [1, 1.014, 1],
                boxShadow: [
                  "0 28px 52px rgba(32, 28, 21, 0.12)",
                  "0 34px 62px rgba(32, 28, 21, 0.16)",
                  "0 28px 52px rgba(32, 28, 21, 0.12)",
                ],
              }
            : undefined
        }
        transition={
          isComplete
            ? {
                delay: HOLD_DELAY_MS / 1000,
                duration: 4.2,
                ease: "easeInOut",
                repeat: Number.POSITIVE_INFINITY,
              }
            : undefined
        }
      >
        <span className="support-about-quote-kicker">Viru Tracker note</span>
        <span className="support-about-quote-mark" aria-hidden="true">
          &ldquo;
        </span>
        <p aria-label={ABOUT_US_QUOTE_TEXT}>
          {characters.slice(0, visibleChars).join("")}
          <span
            className={`support-about-quote-caret${isComplete ? " is-hidden" : ""}`}
            aria-hidden="true"
          />
        </p>
        <span className="support-about-quote-underline" aria-hidden="true" />
      </motion.div>
    </motion.blockquote>
  );
}
