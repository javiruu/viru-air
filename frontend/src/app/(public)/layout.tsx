import type { ReactNode } from "react";

import PublicShellHeader from "@/modules/shared/PublicShellHeader";
import ViruFooterBlock from "@/modules/shared/ViruFooterBlock";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <PublicShellHeader />
      {children}
      <ViruFooterBlock />
    </>
  );
}
