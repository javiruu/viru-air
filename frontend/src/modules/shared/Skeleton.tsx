import React, { type CSSProperties, type ElementType, type ReactNode } from "react";

type SkeletonVariant = "line" | "pill" | "block" | "circle" | "card";

type SkeletonProps = {
  as?: ElementType;
  variant?: SkeletonVariant;
  width?: number | string;
  height?: number | string;
  className?: string;
  ariaHidden?: boolean;
};

type SkeletonContainerProps = {
  className?: string;
  ariaLabel?: string;
  children?: ReactNode;
};

function withUnit(value: number | string | undefined): string | number | undefined {
  if (typeof value === "number") return `${value}px`;
  return value;
}

function joinClassName(...parts: Array<string | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function Skeleton({
  as: Tag = "span",
  variant = "line",
  width,
  height,
  className,
  ariaHidden = true,
}: SkeletonProps) {
  const style: CSSProperties = {};
  if (width !== undefined) style.width = withUnit(width);
  if (height !== undefined) style.height = withUnit(height);

  return (
    <Tag
      className={joinClassName("vt-skeleton", `vt-skeleton--${variant}`, className)}
      style={style}
      aria-hidden={ariaHidden}
    />
  );
}

export function SkeletonPanel({ className, ariaLabel, children }: SkeletonContainerProps) {
  return (
    <section
      className={joinClassName("panel panel-soft loading-skeleton-panel", className)}
      role="status"
      aria-live="polite"
      aria-label={ariaLabel}
      aria-busy="true"
    >
      {children ?? (
        <>
          <Skeleton variant="pill" width="34%" height={18} />
          <Skeleton variant="line" width="74%" />
          <Skeleton variant="line" width="58%" />
          <div className="loading-skeleton-row">
            <Skeleton variant="card" className="loading-skeleton-card" />
            <Skeleton variant="card" className="loading-skeleton-card" />
          </div>
        </>
      )}
    </section>
  );
}

export function SkeletonForm({ className, ariaLabel, children }: SkeletonContainerProps) {
  return (
    <section
      className={joinClassName("panel panel-soft loading-skeleton-form", className)}
      role="status"
      aria-live="polite"
      aria-label={ariaLabel}
      aria-busy="true"
    >
      {children ?? (
        <>
          <Skeleton variant="pill" width="42%" height={18} />
          <div className="loading-skeleton-field">
            <Skeleton variant="line" width="28%" />
            <Skeleton variant="block" height={42} />
          </div>
          <div className="loading-skeleton-field">
            <Skeleton variant="line" width="34%" />
            <Skeleton variant="block" height={42} />
          </div>
          <Skeleton variant="pill" width={148} height={36} className="loading-skeleton-cta" />
        </>
      )}
    </section>
  );
}

type SkeletonListProps = SkeletonContainerProps & {
  rows?: number;
};

export function SkeletonList({ className, ariaLabel, rows = 4, children }: SkeletonListProps) {
  return (
    <section
      className={joinClassName("panel panel-soft loading-skeleton-list", className)}
      role="status"
      aria-live="polite"
      aria-label={ariaLabel}
      aria-busy="true"
    >
      {children ?? (
        <>
          <Skeleton variant="pill" width="40%" height={18} />
          <div className="loading-skeleton-list-rows">
            {Array.from({ length: rows }).map((_, index) => (
              <article className="loading-skeleton-list-row" key={`skeleton-list-row-${index}`}>
                <div className="loading-skeleton-list-main">
                  <Skeleton variant="line" width="54%" />
                  <Skeleton variant="line" width="38%" />
                </div>
                <Skeleton variant="pill" width={84} height={22} />
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export function SkeletonOverlay({ className, ariaLabel, children }: SkeletonContainerProps) {
  return (
    <div
      className={joinClassName("loading-skeleton-overlay", className)}
      role="status"
      aria-live="polite"
      aria-label={ariaLabel}
      aria-busy="true"
    >
      <div className="panel panel-soft loading-skeleton-overlay__card">
        {children ?? (
          <div className="loading-skeleton-overlay__stack">
            <Skeleton variant="circle" width={56} height={56} />
            <Skeleton variant="pill" width={180} height={18} />
            <Skeleton variant="line" width={220} />
            <Skeleton variant="line" width={150} />
          </div>
        )}
      </div>
    </div>
  );
}
