import React, { memo } from "react";
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

  return (
    <div className="qs-nearby-band" data-ui="qs-nearby-band">
      <div className="qs-nearby-band-header">
        <span className="qs-nearby-title">Aeropuertos cercanos</span>
        <span className="qs-nearby-subtitle">Actívalo si puedes salir o llegar desde otro aeropuerto.</span>
      </div>
      <div className="qs-nearby-band-controls">
        <label className={`qs-chip-toggle ${props.includeNearbyOrigins ? 'active' : ''}`}>
          <input 
            type="checkbox" 
            className="sr-only"
            checked={props.includeNearbyOrigins} 
            onChange={(e) => props.setIncludeNearbyOrigins(e.target.checked)} 
          />
          Cerca del origen
        </label>
        <label className={`qs-chip-toggle ${props.includeNearbyDestinations ? 'active' : ''}`}>
          <input 
            type="checkbox" 
            className="sr-only"
            checked={props.includeNearbyDestinations} 
            onChange={(e) => props.setIncludeNearbyDestinations(e.target.checked)} 
          />
          Cerca del destino
        </label>
        
        {isAnyNearby && (
          <div className="qs-nearby-distance">
            <span>Distancia máxima:</span>
            <select
              value={props.radiusKm}
              onChange={(e) => props.setRadiusKm(Number(e.target.value))}
              className="qs-input qs-input-compact"
            >
              {[50, 100, 150, 200, 250, 300, 400, 500].map((d) => (
                <option key={d} value={d}>{d} km</option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  );
});
