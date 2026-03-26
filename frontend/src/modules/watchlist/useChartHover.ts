import { MouseEvent, useCallback, useState } from "react";

import type { HoverPoint } from "@/modules/watchlist/types";

type UseChartHoverInput = {
  points: HoverPoint[];
  chartWidth: number;
  chartHeight: number;
  snapThreshold?: number;
};

export function useChartHover({ points, chartWidth, chartHeight, snapThreshold = 520 }: UseChartHoverInput) {
  const [hoverPoint, setHoverPoint] = useState<HoverPoint | null>(null);

  const handleChartMove = useCallback(
    (event: MouseEvent<SVGSVGElement>) => {
      if (!points.length) return;
      const rect = event.currentTarget.getBoundingClientRect();
      if (!rect.width || !rect.height) return;

      const x = (event.clientX - rect.left) * (chartWidth / rect.width);
      const y = (event.clientY - rect.top) * (chartHeight / rect.height);

      let best: HoverPoint | null = null;
      let bestDist = Infinity;

      points.forEach((point) => {
        const dx = point.x - x;
        const dy = point.y - y;
        const dist = dx * dx + dy * dy;
        if (dist < bestDist) {
          bestDist = dist;
          best = point;
        }
      });

      if (best && bestDist < snapThreshold) {
        setHoverPoint(best);
      } else {
        setHoverPoint(null);
      }
    },
    [points, chartWidth, chartHeight, snapThreshold],
  );

  const clearHover = useCallback(() => {
    setHoverPoint(null);
  }, []);

  return { hoverPoint, handleChartMove, clearHover };
}
