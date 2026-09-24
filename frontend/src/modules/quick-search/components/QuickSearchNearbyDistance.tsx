import { memo } from "react";
import { Slider } from "@/components/ui/slider";
import type { QuickSearchCopyKey } from "@/modules/shared/quickSearchCopy";

type QuickSearchNearbyDistanceProps = {
  isAnyNearby: boolean;
  radiusKm: number;
  t: (key: QuickSearchCopyKey) => string;
  setRadiusKm: (value: number) => void;
};

export const QuickSearchNearbyDistance = memo(function QuickSearchNearbyDistance({
  isAnyNearby,
  radiusKm,
  t,
  setRadiusKm,
}: QuickSearchNearbyDistanceProps) {
  const handleRadiusChange = (values: number[]) => {
    const nextRadius = values[0];
    if (typeof nextRadius === "number") {
      setRadiusKm(nextRadius);
    }
  };

  return (
    <div
      className="qs-nearby-distance-wrapper"
      data-ui="qs-nearby-distance"
      style={{
        gridTemplateRows: isAnyNearby ? "1fr" : "0fr",
        opacity: isAnyNearby ? 1 : 0,
        marginBottom: isAnyNearby ? "1rem" : "0",
      }}
    >
      <div style={{ minHeight: 0 }}>
        <div className="qs-nearby-distance" style={{ margin: "0" }}>
          <span className="qs-nearby-distance-label">{t("nearbyDistanceLabel")}</span>
          <Slider
            aria-label={t("nearbyDistanceAria")}
            className="qs-nearby-slider"
            min={50}
            max={500}
            step={50}
            value={[radiusKm]}
            onValueChange={handleRadiusChange}
          />
          <span className="qs-nearby-distance-value">{radiusKm} km</span>
        </div>
      </div>
    </div>
  );
});
