"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

export default function PrivateTopBar({ children }: { children: ReactNode }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isLeaving, setIsLeaving] = useState(false);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || typeof IntersectionObserver === "undefined") {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        const nextIsLeaving = entry.boundingClientRect.top < 0 && entry.intersectionRatio < 1;
        setIsLeaving(nextIsLeaving);
      },
      {
        threshold: [0, 1],
      },
    );

    observer.observe(node);

    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={containerRef}
      className={`private-account-anchor${isLeaving ? " is-leaving" : ""}`}
    >
      {children}
    </div>
  );
}
