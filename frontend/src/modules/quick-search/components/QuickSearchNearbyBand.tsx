import React, { memo } from "react";
import { Slider } from "@/components/ui/slider";
import { QuickSearchCopyKey } from "@/modules/shared/quickSearchCopy";

type QuickSearchNearbyBandProps = {
  includeNearbyOrigins: boolean;
  includeNearbyDestinations: boolean;
  radiusKm: number;
  t: (key: QuickSearchCopyKey) => string;
  setIncludeNearbyOrigins: (value: boolean) => void;
  setIncludeNearbyDestinations: (value: boolean) => void;
  setRadiusKm: (value: number) => void;
};

export const QuickSearchNearbyBand = memo(function QuickSearchNearbyBand(props: QuickSearchNearbyBandProps) {
  const isAnyNearby = props.includeNearbyOrigins || props.includeNearbyDestinations;
  const handleRadiusChange = (values: number[]) => {
    const nextRadius = values[0];
    if (typeof nextRadius === "number") {
      props.setRadiusKm(nextRadius);
    }
  };

  return (
    <div className="qs-nearby-band" data-ui="qs-nearby-band">
      <div className="qs-nearby-band-header">
        <span className="qs-nearby-title">{props.t("nearbyTitle")}</span>
        <span className="qs-nearby-subtitle">{props.t("nearbySubtitle")}</span>
      </div>
      <div className="qs-nearby-band-controls">
        <label className={`qs-chip-toggle ${props.includeNearbyOrigins ? 'active' : ''}`}>
          <input 
            type="checkbox" 
            className="sr-only"
            checked={props.includeNearbyOrigins} 
            onChange={(e) => props.setIncludeNearbyOrigins(e.target.checked)} 
          />
          {props.t("nearbyOrigin")}
        </label>
        <label className={`qs-chip-toggle ${props.includeNearbyDestinations ? 'active' : ''}`}>
          <input 
            type="checkbox" 
            className="sr-only"
            checked={props.includeNearbyDestinations} 
            onChange={(e) => props.setIncludeNearbyDestinations(e.target.checked)} 
          />
          {props.t("nearbyDestination")}
        </label>
        
        {isAnyNearby && (
          <div className="qs-nearby-distance">
            <span className="qs-nearby-distance-label">{props.t("nearbyDistanceLabel")}</span>
            <Slider
              aria-label={props.t("nearbyDistanceAria")}
              className="qs-nearby-slider"
              min={50}
              max={500}
              step={50}
              value={[props.radiusKm]}
              onValueChange={handleRadiusChange}
            />
            <span className="qs-nearby-distance-value">{props.radiusKm} km</span>
          </div>
        )}
      </div>
    </div>
  );
});
