import React from "react";

type Props = {
  className?: string;
  size?: number;
  "aria-hidden"?: boolean;
};

export function IberiaIcon({ className, size = 24, "aria-hidden": ariaHidden = true }: Props) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width={size}
      height={size}
      aria-hidden={ariaHidden}
    >
      <rect x="1.5" y="1.5" width="21" height="21" rx="6" fill="#D71920" />
      <path d="M8 6.8h2.55v10.4H8z" fill="#FFCC00" />
      <path d="M12.15 6.8h3.65c1.7 0 2.8.98 2.8 2.38 0 1.02-.55 1.72-1.45 2.06 1.05.3 1.75 1.08 1.75 2.32 0 1.6-1.22 2.64-3.02 2.64h-3.73zm2.35 1.9v1.8h.96c.56 0 .9-.34.9-.9 0-.54-.34-.9-.9-.9zm0 3.7v1.9h1.18c.6 0 .96-.36.96-.94 0-.6-.36-.96-.96-.96z" fill="#FFFFFF" />
      <path d="M4.85 6.8h1.55v10.4H4.85z" fill="#FFFFFF" opacity="0.92" />
    </svg>
  );
}
