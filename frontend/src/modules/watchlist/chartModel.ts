import type { HistoryRow } from "@/modules/watchlist/types";

type ChartPad = {
  readonly left: number;
  readonly right: number;
  readonly top: number;
  readonly bottom: number;
};

type BuildWatchlistChartModelInput = {
  readonly groupedByDate: Readonly<Record<string, readonly HistoryRow[]>>;
  readonly selectedDates: readonly string[];
  readonly chartHeight: number;
  readonly chartWidth: number;
  readonly chartPad: ChartPad;
  readonly lineColors: readonly string[];
};

export type WatchlistChartPoint = HistoryRow & {
  readonly x: number;
  readonly y: number;
};

export type WatchlistChartSerie = {
  readonly date: string;
  readonly color: string;
  readonly path: string;
  readonly areaPoints: string;
  readonly points: readonly WatchlistChartPoint[];
};

function paddedPriceDomain(minYRaw: number, maxYRaw: number) {
  if (minYRaw === maxYRaw) {
    const padding = Math.max(Math.abs(minYRaw) * 0.05, 1);
    return { minY: minYRaw - padding, maxY: maxYRaw + padding };
  }

  const padding = Math.max((maxYRaw - minYRaw) * 0.12, 1);
  return { minY: minYRaw - padding, maxY: maxYRaw + padding };
}

export function buildWatchlistChartModel({
  groupedByDate,
  selectedDates,
  chartHeight,
  chartWidth,
  chartPad,
  lineColors,
}: BuildWatchlistChartModelInput): WatchlistChartSerie[] | null {
  const dateKeys = selectedDates.filter((date) => (groupedByDate[date] ?? []).length > 0);
  if (dateKeys.length === 0) return null;

  const sourcePoints = dateKeys.flatMap((date) => groupedByDate[date] ?? []);
  const minX = Math.min(...sourcePoints.map((point) => new Date(point.capturedAt).getTime()));
  const maxX = Math.max(...sourcePoints.map((point) => new Date(point.capturedAt).getTime()));
  const minYRaw = Math.min(...sourcePoints.map((point) => point.price));
  const maxYRaw = Math.max(...sourcePoints.map((point) => point.price));
  const { minY, maxY } = paddedPriceDomain(minYRaw, maxYRaw);

  const xSpan = Math.max(1, maxX - minX);
  const ySpan = Math.max(1, maxY - minY);
  const innerW = chartWidth - chartPad.left - chartPad.right;
  const innerH = chartHeight - chartPad.top - chartPad.bottom;
  const baselineY = chartHeight - chartPad.bottom;

  const mapX = (value: number) => chartPad.left + ((value - minX) / xSpan) * innerW;
  const mapY = (value: number) => chartPad.top + innerH - ((value - minY) / ySpan) * innerH;

  return dateKeys.map((date, index) => {
    const rows = (groupedByDate[date] ?? [])
      .slice()
      .sort((a, b) => new Date(a.capturedAt).getTime() - new Date(b.capturedAt).getTime());
    const color = lineColors[index % lineColors.length] ?? "var(--accent-2)";
    const points = rows.map((row) => ({
      ...row,
      x: mapX(new Date(row.capturedAt).getTime()),
      y: mapY(row.price),
    }));
    const linePoints = points.map((point) => `${point.x},${point.y}`).join(" ");
    const firstPoint = points[0];
    const lastPoint = points[points.length - 1];
    const areaPoints =
      firstPoint && lastPoint ? `${firstPoint.x},${baselineY} ${linePoints} ${lastPoint.x},${baselineY}` : "";

    return {
      date,
      color,
      path: linePoints,
      areaPoints,
      points,
    };
  });
}
