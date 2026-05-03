import { useMemo } from "react";

import { formatCurrency, formatRelativeTime } from "@/modules/shared/format";
import { getAirportMeta } from "@/modules/shared/airports";
import { monthDays, toIsoMonth } from "@/modules/watchlist/dateUtils";
import { formatDateTime } from "@/modules/watchlist/presentation";
import type {
  HistoryRow,
  HoverPoint,
  ListSort,
  RangeWindow,
  Watch,
  WatchMapInsight,
  WatchMapMode,
  WatchMapRouteView,
} from "@/modules/watchlist/types";

type WatchMetaEntry = {
  latest: HistoryRow | null;
  previous: HistoryRow | null;
  min: number | null;
  max: number | null;
};

type CompareCard = {
  date: string;
  latest: HistoryRow;
  previous: HistoryRow | null;
  delta: number;
  min: number;
  max: number;
};

type UseWatchlistDerivedInput = {
  items: Watch[];
  historyRows: HistoryRow[];
  selectedOrigin: string;
  selectedDestination: string;
  selectedDates: string[];
  selectedPoint: string;
  rangeWindow: RangeWindow;
  watchSearch: string;
  watchSort: ListSort;
  selectedWatchId: string;
  compareIds: string[];
  calendarCursor: string;
  chartBaseHeight: number;
  chartWidth: number;
  chartPad: { left: number; right: number; top: number; bottom: number };
  lineColors: string[];
};

export function useWatchlistDerived({
  items,
  historyRows,
  selectedOrigin,
  selectedDestination,
  selectedDates,
  selectedPoint,
  rangeWindow,
  watchSearch,
  watchSort,
  selectedWatchId,
  compareIds,
  calendarCursor,
  chartBaseHeight,
  chartWidth,
  chartPad,
  lineColors,
}: UseWatchlistDerivedInput) {
  const watchMeta = useMemo(() => {
    const map = new Map<string, WatchMetaEntry>();
    const grouped = historyRows.reduce<Record<string, HistoryRow[]>>((acc, row) => {
      acc[row.watchId] = acc[row.watchId] || [];
      acc[row.watchId].push(row);
      return acc;
    }, {});
    Object.entries(grouped).forEach(([watchId, rows]) => {
      const sorted = rows.slice().sort((a, b) => new Date(a.capturedAt).getTime() - new Date(b.capturedAt).getTime());
      const latest = sorted[sorted.length - 1] || null;
      const previous = sorted.length > 1 ? sorted[sorted.length - 2] : null;
      const prices = sorted.map((row) => row.price);
      map.set(watchId, {
        latest,
        previous,
        min: prices.length > 0 ? Math.min(...prices) : null,
        max: prices.length > 0 ? Math.max(...prices) : null,
      });
    });
    return map;
  }, [historyRows]);

  const lastUpdatedGlobal = useMemo(() => {
    if (historyRows.length === 0) return "";
    const latest = historyRows.reduce((acc, row) => {
      const current = new Date(row.capturedAt).getTime();
      return current > acc ? current : acc;
    }, 0);
    return latest ? formatRelativeTime(new Date(latest).toISOString()) : "";
  }, [historyRows]);

  const allOrigins = useMemo(() => Array.from(new Set(items.map((watch) => watch.origin_iata))).sort(), [items]);

  const allDestinations = useMemo(
    () =>
      Array.from(
        new Set(
          items
            .filter((watch) => (selectedOrigin ? watch.origin_iata === selectedOrigin : true))
            .map((watch) => watch.destination_iata),
        ),
      ).sort(),
    [items, selectedOrigin],
  );

  const allTravelDates = useMemo(
    () =>
      Array.from(
        new Set(
          items
            .filter((watch) => (selectedOrigin ? watch.origin_iata === selectedOrigin : true))
            .filter((watch) => (selectedDestination ? watch.destination_iata === selectedDestination : true))
            .map((watch) => watch.travel_date_local),
        ),
      ).sort(),
    [items, selectedOrigin, selectedDestination],
  );

  const smartListItems = useMemo(() => {
    const needle = watchSearch.trim().toUpperCase();
    const filtered = items.filter((item) => {
      if (!needle) return true;
      const route = `${item.origin_iata} ${item.destination_iata} ${item.travel_date_local}`.toUpperCase();
      return route.includes(needle);
    });
    return filtered.slice().sort((a, b) => {
      const metaA = watchMeta.get(a.id);
      const metaB = watchMeta.get(b.id);
      const latestA = metaA?.latest?.price ?? Infinity;
      const latestB = metaB?.latest?.price ?? Infinity;
      const deltaA = metaA?.latest && metaA.previous ? Math.abs(metaA.latest.price - metaA.previous.price) : -1;
      const deltaB = metaB?.latest && metaB.previous ? Math.abs(metaB.latest.price - metaB.previous.price) : -1;
      const freshA = metaA?.latest ? new Date(metaA.latest.capturedAt).getTime() : 0;
      const freshB = metaB?.latest ? new Date(metaB.latest.capturedAt).getTime() : 0;
      if (watchSort === "price_asc") return latestA - latestB;
      if (watchSort === "price_desc") return latestB - latestA;
      if (watchSort === "delta") return deltaB - deltaA;
      return freshB - freshA;
    });
  }, [items, watchMeta, watchSearch, watchSort]);

  const hasSearchFilter = watchSearch.trim().length > 0;

  const selectedWatch = useMemo(
    () => items.find((item) => item.id === selectedWatchId) || null,
    [items, selectedWatchId],
  );

  const filteredRows = useMemo(
    () =>
      historyRows
        .filter((row) => (selectedOrigin ? row.origin === selectedOrigin : true))
        .filter((row) => (selectedDestination ? row.destination === selectedDestination : true))
        .filter((row) => (selectedDates.length > 0 ? selectedDates.includes(row.travelDate) : true))
        .sort((a, b) => new Date(a.capturedAt).getTime() - new Date(b.capturedAt).getTime()),
    [historyRows, selectedOrigin, selectedDestination, selectedDates],
  );

  const chartRows = useMemo(() => {
    if (rangeWindow === "all") return filteredRows;
    if (filteredRows.length === 0) return filteredRows;
    const maxTime = Math.max(...filteredRows.map((row) => new Date(row.capturedAt).getTime()));
    const days = Number(rangeWindow);
    const cutoff = maxTime - days * 24 * 60 * 60 * 1000;
    return filteredRows.filter((row) => new Date(row.capturedAt).getTime() >= cutoff);
  }, [filteredRows, rangeWindow]);

  const chartIsCompact = chartRows.length > 0 && chartRows.length <= 3;
  const chartHeight = chartIsCompact ? 260 : chartBaseHeight;

  const groupedByDateFull = useMemo(() => {
    return selectedDates.reduce<Record<string, HistoryRow[]>>((acc, date) => {
      acc[date] = filteredRows.filter((row) => row.travelDate === date);
      return acc;
    }, {});
  }, [filteredRows, selectedDates]);

  const groupedByDate = useMemo(() => {
    return selectedDates.reduce<Record<string, HistoryRow[]>>((acc, date) => {
      acc[date] = chartRows.filter((row) => row.travelDate === date);
      return acc;
    }, {});
  }, [chartRows, selectedDates]);

  const pointOptions = useMemo(() => {
    if (selectedDates.length !== 1) return [];
    const rows = groupedByDate[selectedDates[0]] || [];
    return rows.map((row) => ({
      value: row.capturedAt,
      label: `${formatDateTime(row.capturedAt)} - ${formatCurrency(row.price, row.currency)}`,
    }));
  }, [groupedByDate, selectedDates]);

  const summary = useMemo(() => {
    if (selectedDates.length !== 1) return null;
    const rows = groupedByDate[selectedDates[0]] || [];
    if (rows.length === 0) return null;
    const prices = rows.map((row) => row.price);
    const avg = prices.reduce((acc, val) => acc + val, 0) / prices.length;
    return {
      avg,
      min: Math.min(...prices),
      max: Math.max(...prices),
      total: prices.length,
      currency: rows[0].currency,
    };
  }, [groupedByDate, selectedDates]);

  const compareCards = useMemo(() => {
    if (selectedDates.length !== 2) return null;
    const cards = selectedDates.map((date) => {
      const rows = (groupedByDateFull[date] || [])
        .slice()
        .sort((a, b) => new Date(a.capturedAt).getTime() - new Date(b.capturedAt).getTime());
      if (rows.length === 0) return null;
      const latest = rows[rows.length - 1];
      const previous = rows.length > 1 ? rows[rows.length - 2] : null;
      const delta = previous ? latest.price - previous.price : 0;
      const min = Math.min(...rows.map((row) => row.price));
      const max = Math.max(...rows.map((row) => row.price));
      return { date, latest, previous, delta, min, max };
    });
    const filtered = cards.filter(Boolean) as CompareCard[];
    return filtered.length === 2 ? filtered : null;
  }, [groupedByDateFull, selectedDates]);

  const chartModel = useMemo(() => {
    const dateKeys = selectedDates.filter((date) => (groupedByDate[date] || []).length > 0);
    if (dateKeys.length === 0) return null;
    const points = dateKeys.flatMap((date) => groupedByDate[date]);
    const minX = Math.min(...points.map((point) => new Date(point.capturedAt).getTime()));
    const maxX = Math.max(...points.map((point) => new Date(point.capturedAt).getTime()));
    const minYRaw = Math.min(...points.map((point) => point.price));
    const maxYRaw = Math.max(...points.map((point) => point.price));
    const minY = minYRaw === maxYRaw ? minYRaw - 1 : minYRaw;
    const maxY = minYRaw === maxYRaw ? maxYRaw + 1 : maxYRaw;

    const xSpan = Math.max(1, maxX - minX);
    const ySpan = Math.max(1, maxY - minY);
    const innerW = chartWidth - chartPad.left - chartPad.right;
    const innerH = chartHeight - chartPad.top - chartPad.bottom;

    const mapX = (value: number) => chartPad.left + ((value - minX) / xSpan) * innerW;
    const mapY = (value: number) => chartPad.top + innerH - ((value - minY) / ySpan) * innerH;

    return dateKeys.map((date, index) => {
      const rows = groupedByDate[date]
        .slice()
        .sort((a, b) => new Date(a.capturedAt).getTime() - new Date(b.capturedAt).getTime());
      const color = lineColors[index % lineColors.length];
      const pointsMapped = rows.map((row) => ({
        ...row,
        x: mapX(new Date(row.capturedAt).getTime()),
        y: mapY(row.price),
      }));
      return {
        date,
        color,
        path: pointsMapped.map((point) => `${point.x},${point.y}`).join(" "),
        points: pointsMapped,
      };
    });
  }, [groupedByDate, selectedDates, chartHeight, chartWidth, chartPad, lineColors]);

  const flatChartPoints = useMemo<HoverPoint[]>(() => {
    if (!chartModel) return [];
    return chartModel.flatMap((serie) =>
      serie.points.map((point) => ({
        ...point,
        color: serie.color,
        date: serie.date,
      })),
    );
  }, [chartModel]);

  const selectedPointData = useMemo(() => {
    if (!selectedPoint) return null;
    return flatChartPoints.find((point) => point.capturedAt === selectedPoint) || null;
  }, [flatChartPoints, selectedPoint]);

  const calendarEvents = useMemo(() => {
    const source = filteredRows.length > 0 ? filteredRows : historyRows;
    return source.reduce<Record<string, { min: number; max: number; count: number }>>((acc, row) => {
      const current = acc[row.travelDate];
      if (!current) {
        acc[row.travelDate] = { min: row.price, max: row.price, count: 1 };
      } else {
        current.min = Math.min(current.min, row.price);
        current.max = Math.max(current.max, row.price);
        current.count += 1;
      }
      return acc;
    }, {});
  }, [filteredRows, historyRows]);

  const visibleMonth = calendarCursor || toIsoMonth(Object.keys(calendarEvents)[0] || "");
  const monthCells = monthDays(visibleMonth);

  const calendarRange = useMemo(() => {
    const days = monthCells.filter(Boolean);
    const events = days
      .map((day) => (day ? calendarEvents[day] : undefined))
      .filter((event): event is { min: number; max: number; count: number } => Boolean(event));
    if (events.length === 0) return null;
    const min = Math.min(...events.map((event) => event.min));
    const max = Math.max(...events.map((event) => event.max));
    return { min, max };
  }, [calendarEvents, monthCells]);

  const calendarCurrency = useMemo(
    () => filteredRows[0]?.currency ?? historyRows[0]?.currency ?? "EUR",
    [filteredRows, historyRows],
  );

  const compareOptions = useMemo(() => {
    return items.map((item) => {
      const meta = watchMeta.get(item.id);
      const latest = meta?.latest ?? null;
      const previous = meta?.previous ?? null;
      const delta = latest && previous ? latest.price - previous.price : 0;
      const volatility = meta?.min != null && meta?.max != null ? meta.max - meta.min : null;
      return {
        id: item.id,
        origin: item.origin_iata,
        destination: item.destination_iata,
        travelDate: item.travel_date_local,
        latest,
        previous,
        delta,
        volatility,
        min: meta?.min ?? null,
        max: meta?.max ?? null,
      };
    });
  }, [items, watchMeta]);

  const compareSelection = useMemo(() => {
    return compareOptions.filter((option) => compareIds.includes(option.id));
  }, [compareOptions, compareIds]);

  const compareBadges = useMemo(() => {
    if (compareSelection.length === 0) return null;
    const withPrice = compareSelection.filter((option) => option.latest);
    const bestPrice = withPrice.reduce((acc, option) => {
      if (!acc) return option;
      if (!option.latest) return acc;
      return option.latest.price < (acc.latest?.price ?? Infinity) ? option : acc;
    }, null as typeof withPrice[number] | null);
    const freshest = withPrice.reduce((acc, option) => {
      if (!acc) return option;
      if (!option.latest) return acc;
      return new Date(option.latest.capturedAt).getTime() > new Date(acc.latest?.capturedAt ?? 0).getTime()
        ? option
        : acc;
    }, null as typeof withPrice[number] | null);
    const stable = compareSelection.reduce((acc, option) => {
      if (!acc) return option;
      if (option.volatility == null) return acc;
      if (acc.volatility == null) return option;
      return option.volatility < acc.volatility ? option : acc;
    }, null as typeof compareSelection[number] | null);
    return {
      bestPriceId: bestPrice?.id ?? null,
      freshestId: freshest?.id ?? null,
      stableId: stable?.id ?? null,
    };
  }, [compareSelection]);

  const watchMapRoutes = useMemo<WatchMapRouteView[]>(() => {
    const compareSet = new Set(compareIds);
    const compareCapped = compareSelection.slice(0, 4).map((item) => item.id);
    const activeIds = compareCapped.length > 0 ? new Set(compareCapped) : selectedWatchId ? new Set([selectedWatchId]) : compareSet;

    const routes = items
      .filter((watch) => activeIds.has(watch.id))
      .map((watch) => {
        const originMeta = getAirportMeta(watch.origin_iata);
        const destinationMeta = getAirportMeta(watch.destination_iata);
        if (!originMeta || !destinationMeta) return null;
        const meta = watchMeta.get(watch.id);
        const latest = meta?.latest ?? null;
        const previous = meta?.previous ?? null;
        const trend: "up" | "down" | "flat" =
          !latest || !previous ? "flat" : latest.price > previous.price ? "up" : latest.price < previous.price ? "down" : "flat";

        return {
          watchId: watch.id,
          origin: watch.origin_iata,
          destination: watch.destination_iata,
          originCoordinates: [originMeta.longitude, originMeta.latitude] as [number, number],
          destinationCoordinates: [destinationMeta.longitude, destinationMeta.latitude] as [number, number],
          priceCurrent: latest?.price ?? null,
          priceTarget: watch.target_price ?? null,
          currency: latest?.currency ?? "EUR",
          trend,
          isPrimary: watch.id === selectedWatchId,
          isCompared: compareSet.has(watch.id),
          volatility: meta?.min != null && meta?.max != null ? meta.max - meta.min : null,
          freshnessTs: latest?.capturedAt ?? null,
        };
      })
      .filter((entry): entry is WatchMapRouteView => Boolean(entry));

    if (routes.length > 0) return routes;
    const fallback = items.find((watch) => watch.id === selectedWatchId) ?? items[0];
    if (!fallback) return [];
    const originMeta = getAirportMeta(fallback.origin_iata);
    const destinationMeta = getAirportMeta(fallback.destination_iata);
    if (!originMeta || !destinationMeta) return [];
    const meta = watchMeta.get(fallback.id);

    return [
      {
        watchId: fallback.id,
        origin: fallback.origin_iata,
        destination: fallback.destination_iata,
        originCoordinates: [originMeta.longitude, originMeta.latitude],
        destinationCoordinates: [destinationMeta.longitude, destinationMeta.latitude],
        priceCurrent: meta?.latest?.price ?? null,
        priceTarget: fallback.target_price ?? null,
        currency: meta?.latest?.currency ?? "EUR",
        trend: "flat",
        isPrimary: true,
        isCompared: false,
        volatility: meta?.min != null && meta?.max != null ? meta.max - meta.min : null,
        freshnessTs: meta?.latest?.capturedAt ?? null,
      },
    ];
  }, [compareIds, compareSelection, items, selectedWatchId, watchMeta]);

  const watchMapMode = useMemo<WatchMapMode>(() => {
    const compareCount = watchMapRoutes.filter((route) => route.isCompared).length;
    return compareCount >= 2 ? "compare" : "single";
  }, [watchMapRoutes]);

  const watchMapInsight = useMemo<WatchMapInsight>(() => {
    if (watchMapRoutes.length === 0) {
      return {
        type: "neutral",
        text: "No hay rutas activas para mostrar en el mapa.",
        relatedWatchIds: [],
      };
    }

    const activeRoutes = watchMapRoutes.filter((route) => route.isCompared || route.isPrimary);
    const withPrice = activeRoutes.filter((route) => route.priceCurrent != null);
    if (withPrice.length > 1) {
      const cheapest = withPrice.reduce((acc, route) => ((route.priceCurrent ?? Infinity) < (acc.priceCurrent ?? Infinity) ? route : acc));
      return {
        type: "opportunity",
        text: `Oportunidad activa: ${cheapest.origin} -> ${cheapest.destination} tiene el precio más bajo ahora.`,
        relatedWatchIds: [cheapest.watchId],
      };
    }

    const withVolatility = activeRoutes.filter((route) => route.volatility != null);
    if (withVolatility.length > 1) {
      const stable = withVolatility.reduce((acc, route) => ((route.volatility ?? Infinity) < (acc.volatility ?? Infinity) ? route : acc));
      return {
        type: "stability",
        text: `Más estable ahora: ${stable.origin} -> ${stable.destination}.`,
        relatedWatchIds: [stable.watchId],
      };
    }

    const primary = activeRoutes.find((route) => route.isPrimary) ?? activeRoutes[0];
    return {
      type: "neutral",
      text: `Ruta en foco: ${primary.origin} -> ${primary.destination}.`,
      relatedWatchIds: [primary.watchId],
    };
  }, [watchMapRoutes]);

  return {
    watchMeta,
    lastUpdatedGlobal,
    allOrigins,
    allDestinations,
    allTravelDates,
    smartListItems,
    hasSearchFilter,
    selectedWatch,
    filteredRows,
    chartRows,
    chartIsCompact,
    chartHeight,
    pointOptions,
    summary,
    compareCards,
    chartModel,
    flatChartPoints,
    selectedPointData,
    calendarEvents,
    visibleMonth,
    monthCells,
    calendarRange,
    calendarCurrency,
    compareOptions,
    compareSelection,
    compareBadges,
    watchMapRoutes,
    watchMapMode,
    watchMapInsight,
  };
}
