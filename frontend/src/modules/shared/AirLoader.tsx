"use client";

import type { CSSProperties } from "react";
import { useI18n } from "@/i18n";

type AirLoaderTheme = "auto" | "dark" | "light";

type AirLoaderProps = {
  label?: string;
  ariaLabel?: string;
  theme?: AirLoaderTheme;
  size?: number;
  className?: string;
};

export default function AirLoader({
  label,
  ariaLabel,
  theme = "auto",
  size,
  className,
}: AirLoaderProps) {
  const { t } = useI18n();
  const resolvedLabel = label ?? t("shared.loader.flightLabel");
  const resolvedAriaLabel = ariaLabel ?? t("shared.loader.aria");
  const style = size ? ({ "--size": size } as CSSProperties) : undefined;
  const classes = className ? `air-loader ${className}` : "air-loader";

  return (
    <div
      className={classes}
      data-theme={theme}
      role="status"
      aria-live="polite"
      aria-label={resolvedAriaLabel}
      style={style}
    >
      <div className="cloud-layer back">
        <span className="cloud"></span><span className="cloud"></span><span className="cloud"></span>
        <span className="cloud"></span><span className="cloud"></span><span className="cloud"></span>
        <span className="cloud"></span><span className="cloud"></span><span className="cloud"></span>
        <span className="cloud"></span><span className="cloud"></span><span className="cloud"></span>
        <span className="cloud"></span>
      </div>

      <div className="plane-wrap">
        <span className="contrail"></span>
        <div className="plane">
          <span className="fuselage"></span>
          <span className="wing wing-main"></span>
          <span className="wing wing-tail"></span>
          <span className="window"></span>
        </div>
      </div>

      <div className="cloud-layer front">
        <span className="cloud"></span><span className="cloud"></span><span className="cloud"></span>
        <span className="cloud"></span><span className="cloud"></span><span className="cloud"></span>
        <span className="cloud"></span><span className="cloud"></span><span className="cloud"></span>
        <span className="cloud"></span><span className="cloud"></span><span className="cloud"></span>
        <span className="cloud"></span>
      </div>

      <p className="label" data-text={resolvedLabel}>
        {resolvedLabel}<span className="dots"></span>
      </p>
    </div>
  );
}
