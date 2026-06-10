import type { ReactNode } from "react";

export default function PrivateTopBar({ children }: { children: ReactNode }) {
  return (
    <div className="shell-header private-account-anchor">
      {children}
    </div>
  );
}
