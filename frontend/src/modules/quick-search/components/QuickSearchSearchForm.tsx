import type { FormEventHandler, ReactNode, RefObject } from "react";

type Props = {
  formRef: RefObject<HTMLFormElement | null>;
  isReady: boolean;
  routePulse: boolean;
  onSubmit: FormEventHandler<HTMLFormElement>;
  children: ReactNode;
};

export function QuickSearchSearchForm({ formRef, isReady, routePulse, onSubmit, children }: Props) {
  return (
    <form
      ref={formRef}
      className={`panel form quick-search-panel ${isReady ? "ready" : ""} ${routePulse ? "route-pulse" : ""}`}
      onSubmit={onSubmit}
      aria-describedby="qs-workspace-hint"
    >
      {children}
    </form>
  );
}
