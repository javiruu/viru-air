import type { ReactNode } from "react";

export default function PrivateTopBar({ children }: { children: ReactNode }) {
  return (
    <div className="private-account-controls-bar">
      {children}
    </div>
  );
}
