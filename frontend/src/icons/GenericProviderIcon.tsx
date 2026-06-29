import React from "react";

type Props = {
  className?: string;
  size?: number;
  "aria-hidden"?: boolean;
};

/**
 * Generic provider icon (fallback when no brand-specific icon exists).
 */
export function GenericProviderIcon({ className, size = 24, "aria-hidden": ariaHidden = true }: Props) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="#6B7280"
      aria-hidden={ariaHidden}
    >
      <rect x="2" y="2" width="20" height="20" rx="5" />
      <path d="M12 7v10M7 12h10" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
