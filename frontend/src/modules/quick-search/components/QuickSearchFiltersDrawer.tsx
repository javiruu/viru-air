import { ReactNode, RefObject } from "react";

type Props = {
  open: boolean;
  title: string;
  subtitle: string;
  closeLabel: string;
  closeRef: RefObject<HTMLButtonElement | null>;
  onClose: () => void;
  children: ReactNode;
};

export function QuickSearchFiltersDrawer({
  open,
  title,
  subtitle,
  closeLabel,
  closeRef,
  onClose,
  children,
}: Props) {
  if (!open) return null;

  return (
    <>
      <button type="button" className="qs-filters-backdrop" aria-label={closeLabel} onClick={onClose} />
      <aside className={`panel panel-soft qs-filters-panel ${open ? "is-open" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <header className="qs-filters-header">
          <div>
            <h3>{title}</h3>
            <p className="muted">{subtitle}</p>
          </div>
          <button ref={closeRef} type="button" className="btn-ghost btn-compact qs-filters-close" onClick={onClose}>
            {closeLabel}
          </button>
        </header>
        {children}
      </aside>
    </>
  );
}
