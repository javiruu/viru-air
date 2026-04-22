"use client";

import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";

const QUOTE_TEXT = "Hecho 100% con vibe-coding y amor";
const TYPING_SPEED_MS = 42;
const START_DELAY_MS = 0.3;

export default function AnimatedQuoteBlock() {
  const [visibleChars, setVisibleChars] = useState(0);
  const characters = useMemo(() => Array.from(QUOTE_TEXT), []);
  const isComplete = visibleChars >= characters.length;

  useEffect(() => {
    setVisibleChars(0);

    const timeoutId = window.setTimeout(() => {
      const intervalId = window.setInterval(() => {
        setVisibleChars((current) => {
          if (current >= characters.length) {
            window.clearInterval(intervalId);
            return current;
          }

          return current + 1;
        });
      }, TYPING_SPEED_MS);
    }, START_DELAY_MS * 1000);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [characters]);

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
                y: [0, -3, 0],
                scale: [1, 1.012, 1],
              }
            : undefined
        }
        transition={
          isComplete
            ? {
                duration: 3.8,
                ease: "easeInOut",
                repeat: Number.POSITIVE_INFINITY,
              }
            : undefined
        }
      >
        <span className="support-about-quote-mark" aria-hidden="true">
          &ldquo;
        </span>
        <p aria-label={QUOTE_TEXT}>
          {characters.slice(0, visibleChars).join("")}
          <span
            className={`support-about-quote-caret${isComplete ? " is-hidden" : ""}`}
            aria-hidden="true"
          />
        </p>
      </motion.div>
    </motion.blockquote>
  );
}
