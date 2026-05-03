import type { ReactNode } from "react";

import ViruFooterBlock from "@/modules/shared/ViruFooterBlock";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <>
      {children}
      <ViruFooterBlock />
    </>
  );
}
