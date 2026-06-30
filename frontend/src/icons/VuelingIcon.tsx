import React from "react";

type Props = {
  className?: string;
  size?: number;
  "aria-hidden"?: boolean;
};

/**
 * Vueling brand mark ("V" icon from Simple Icons).
 * Official brand color: #DD0035.
 */
export function VuelingIcon({ className, size = 24, "aria-hidden": ariaHidden = true }: Props) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="#DD0035"
      aria-hidden={ariaHidden}
    >
      <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm4.26 16.46h-2.742l-1.74-5.04-1.74 5.04H7.296L4.62 7.98h2.064l1.512 4.848L9.768 7.98h2.016l1.572 4.848L14.868 7.98h1.896l-1.512 4.848 1.608 4.848z" />
    </svg>
  );
}
