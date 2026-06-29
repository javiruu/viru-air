import React from "react";

type Props = {
  className?: string;
  size?: number;
  "aria-hidden"?: boolean;
};

/**
 * Duffel brand icon.
 * Brand color: #1F2937 (dark gray).
 */
export function DuffelIcon({ className, size = 24, "aria-hidden": ariaHidden = true }: Props) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="#1F2937"
      aria-hidden={ariaHidden}
    >
      <rect x="1.5" y="1.5" width="21" height="21" rx="6" />
      <path
        d="M7.5 7.5h4.8c2.8 0 4.7 1.8 4.7 4.5s-1.9 4.5-4.7 4.5H7.5zm2.2 2v5h2.3c1.6 0 2.7-1 2.7-2.5s-1.1-2.5-2.7-2.5z"
        fill="#F3F4F6"
      />
    </svg>
  );
}
