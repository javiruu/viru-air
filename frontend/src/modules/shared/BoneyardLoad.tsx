"use client";

import { type CSSProperties, type ReactNode } from "react";
import { Skeleton as BoneyardFrame } from "boneyard-js/react";

import "@/bones/registry";

type LoadShape = "line" | "chip" | "block" | "round" | "card";

type LoadReferenceProps = {
  shape?: LoadShape;
  width?: number | string;
  height?: number | string;
  className?: string;
};

type BoneyardLoadProps = {
  name: string;
  className?: string;
  ariaLabel?: string;
  inline?: boolean;
  children: ReactNode;
};

type BoneyardSectionProps = Omit<BoneyardLoadProps, "children"> & {
  children?: ReactNode;
};

function classNames(...parts: Array<string | undefined>) {
  return parts.filter(Boolean).join(" ");
}

function withUnit(value: number | string | undefined): string | number | undefined {
  return typeof value === "number" ? `${value}px` : value;
}

export function LoadReference({
  shape = "line",
  width,
  height,
  className,
}: LoadReferenceProps) {
  const style: CSSProperties = {};

  if (width !== undefined) style.width = withUnit(width);
  if (height !== undefined) style.height = withUnit(height);

  return (
    <span
      aria-hidden="true"
      className={classNames("boneyard-reference", `boneyard-reference--${shape}`, className)}
      style={style}
    />
  );
}

export function BoneyardLoad({ name, className, ariaLabel, inline = false, children }: BoneyardLoadProps) {
  return (
    <section
      className={classNames("boneyard-status", inline ? "boneyard-status--inline" : undefined)}
      role="status"
      aria-live="polite"
      aria-label={ariaLabel}
      aria-busy="true"
    >
      <BoneyardFrame
        name={name}
        loading
        className={classNames("boneyard-frame", className)}
        fixture={children}
        animate="shimmer"
        stagger={24}
        transition={220}
        select="viewport"
        snapshotConfig={{ excludeSelectors: ["[data-boneyard-ignore]"] }}
      >
        {children}
      </BoneyardFrame>
    </section>
  );
}

export function BoneyardInline({
  name,
  className,
  ariaLabel,
  shape,
  width,
  height,
}: Omit<BoneyardLoadProps, "children" | "inline"> & LoadReferenceProps) {
  return (
    <BoneyardLoad name={name} className={className} ariaLabel={ariaLabel} inline>
      <LoadReference shape={shape} width={width} height={height} />
    </BoneyardLoad>
  );
}

function PanelReference() {
  return (
    <div className="boneyard-stack">
      <LoadReference shape="chip" width="34%" height={18} />
      <LoadReference width="74%" />
      <LoadReference width="58%" />
      <div className="boneyard-reference-row">
        <LoadReference shape="card" />
        <LoadReference shape="card" />
      </div>
    </div>
  );
}

function FormReference() {
  return (
    <div className="boneyard-stack">
      <LoadReference shape="chip" width="42%" height={18} />
      <div className="boneyard-field-reference">
        <LoadReference width="28%" />
        <LoadReference shape="block" height={42} />
      </div>
      <div className="boneyard-field-reference">
        <LoadReference width="34%" />
        <LoadReference shape="block" height={42} />
      </div>
      <LoadReference shape="chip" width={148} height={36} className="boneyard-action-reference" />
    </div>
  );
}

function ListReference({ rows }: { rows: number }) {
  return (
    <div className="boneyard-stack">
      <LoadReference shape="chip" width="40%" height={18} />
      <div className="boneyard-list-reference">
        {Array.from({ length: rows }).map((_, index) => (
          <article className="boneyard-list-reference-row" key={`load-reference-row-${index}`}>
            <div className="boneyard-list-reference-main">
              <LoadReference width="54%" />
              <LoadReference width="38%" />
            </div>
            <LoadReference shape="chip" width={84} height={22} />
          </article>
        ))}
      </div>
    </div>
  );
}

export function BoneyardPanel({ name, className, ariaLabel, children }: BoneyardSectionProps) {
  return (
    <BoneyardLoad name={name} className={classNames("panel panel-soft boneyard-panel", className)} ariaLabel={ariaLabel}>
      {children ?? <PanelReference />}
    </BoneyardLoad>
  );
}

export function BoneyardForm({ name, className, ariaLabel, children }: BoneyardSectionProps) {
  return (
    <BoneyardLoad name={name} className={classNames("panel panel-soft boneyard-form", className)} ariaLabel={ariaLabel}>
      {children ?? <FormReference />}
    </BoneyardLoad>
  );
}

export function BoneyardList({
  name,
  className,
  ariaLabel,
  rows = 4,
  children,
}: BoneyardSectionProps & { rows?: number }) {
  return (
    <BoneyardLoad name={name} className={classNames("panel panel-soft boneyard-list", className)} ariaLabel={ariaLabel}>
      {children ?? <ListReference rows={rows} />}
    </BoneyardLoad>
  );
}

export function BoneyardOverlay({ name, className, ariaLabel, children }: BoneyardSectionProps) {
  const reference = children ?? (
    <div className="panel panel-soft boneyard-overlay-card">
      <div className="boneyard-overlay-stack">
        <LoadReference shape="round" width={56} height={56} />
        <LoadReference shape="chip" width={180} height={18} />
        <LoadReference width={220} />
        <LoadReference width={150} />
      </div>
    </div>
  );

  return (
    <div className={classNames("boneyard-overlay", className)}>
      <BoneyardLoad name={name} ariaLabel={ariaLabel}>
        {reference}
      </BoneyardLoad>
    </div>
  );
}
