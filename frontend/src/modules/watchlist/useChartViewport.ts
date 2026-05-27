import {
  MouseEvent as ReactMouseEvent,
  PointerEvent as ReactPointerEvent,
  WheelEvent as ReactWheelEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

type ViewBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type Point = {
  x: number;
  y: number;
};

type ClientPoint = {
  clientX: number;
  clientY: number;
};

type ChartRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

type DragState = {
  pointerId: number;
  startClientX: number;
  startClientY: number;
  startViewBox: ViewBox;
  rect: ChartRect;
};

type PinchState = {
  startDistance: number;
  startMidChart: Point;
  startViewBox: ViewBox;
  rect: ChartRect;
};

type UseChartViewportInput = {
  chartWidth: number;
  chartHeight: number;
  resetKey: string;
  maxZoom?: number;
};

const EPSILON = 0.001;

export function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export function clampViewBox(baseViewBox: ViewBox, candidateViewBox: ViewBox): ViewBox {
  const width = clamp(candidateViewBox.width, EPSILON, baseViewBox.width);
  const height = clamp(candidateViewBox.height, EPSILON, baseViewBox.height);

  const maxX = baseViewBox.x + baseViewBox.width - width;
  const maxY = baseViewBox.y + baseViewBox.height - height;

  return {
    x: clamp(candidateViewBox.x, baseViewBox.x, maxX),
    y: clamp(candidateViewBox.y, baseViewBox.y, maxY),
    width,
    height,
  };
}

export function zoomViewBoxAtPoint({
  viewBox,
  baseViewBox,
  maxZoom,
  zoomFactor,
  center,
}: {
  viewBox: ViewBox;
  baseViewBox: ViewBox;
  maxZoom: number;
  zoomFactor: number;
  center: Point;
}): ViewBox {
  const minWidth = baseViewBox.width / maxZoom;
  const minHeight = baseViewBox.height / maxZoom;

  const nextWidth = clamp(viewBox.width * zoomFactor, minWidth, baseViewBox.width);
  const nextHeight = clamp(viewBox.height * zoomFactor, minHeight, baseViewBox.height);

  if (
    Math.abs(nextWidth - viewBox.width) < EPSILON &&
    Math.abs(nextHeight - viewBox.height) < EPSILON
  ) {
    return viewBox;
  }

  const ratioX = clamp((center.x - viewBox.x) / viewBox.width, 0, 1);
  const ratioY = clamp((center.y - viewBox.y) / viewBox.height, 0, 1);

  const nextX = center.x - ratioX * nextWidth;
  const nextY = center.y - ratioY * nextHeight;

  return clampViewBox(baseViewBox, {
    x: nextX,
    y: nextY,
    width: nextWidth,
    height: nextHeight,
  });
}

export function panViewBox({
  viewBox,
  baseViewBox,
  deltaX,
  deltaY,
}: {
  viewBox: ViewBox;
  baseViewBox: ViewBox;
  deltaX: number;
  deltaY: number;
}): ViewBox {
  return clampViewBox(baseViewBox, {
    x: viewBox.x + deltaX,
    y: viewBox.y + deltaY,
    width: viewBox.width,
    height: viewBox.height,
  });
}

function toChartRect(rect: DOMRect): ChartRect {
  return {
    left: rect.left,
    top: rect.top,
    width: rect.width,
    height: rect.height,
  };
}

function clientToChart(
  client: ClientPoint,
  rect: ChartRect,
  viewBox: ViewBox,
): Point | null {
  if (rect.width <= 0 || rect.height <= 0) return null;
  const ratioX = (client.clientX - rect.left) / rect.width;
  const ratioY = (client.clientY - rect.top) / rect.height;
  return {
    x: viewBox.x + ratioX * viewBox.width,
    y: viewBox.y + ratioY * viewBox.height,
  };
}

function midpoint(a: ClientPoint, b: ClientPoint): ClientPoint {
  return {
    clientX: (a.clientX + b.clientX) / 2,
    clientY: (a.clientY + b.clientY) / 2,
  };
}

function distance(a: ClientPoint, b: ClientPoint): number {
  const dx = b.clientX - a.clientX;
  const dy = b.clientY - a.clientY;
  return Math.hypot(dx, dy);
}

export function useChartViewport({
  chartWidth,
  chartHeight,
  resetKey,
  maxZoom = 6,
}: UseChartViewportInput) {
  const baseViewBox = useMemo<ViewBox>(
    () => ({ x: 0, y: 0, width: chartWidth, height: chartHeight }),
    [chartHeight, chartWidth],
  );
  const [viewBox, setViewBox] = useState<ViewBox>(baseViewBox);
  const [isDragging, setIsDragging] = useState(false);

  const dragRef = useRef<DragState | null>(null);
  const pinchRef = useRef<PinchState | null>(null);
  const pointersRef = useRef<Map<number, ClientPoint>>(new Map());

  useEffect(() => {
    setViewBox(baseViewBox);
    setIsDragging(false);
    dragRef.current = null;
    pinchRef.current = null;
    pointersRef.current.clear();
  }, [baseViewBox, resetKey]);

  const isZoomed = useMemo(
    () =>
      viewBox.width < baseViewBox.width - EPSILON || viewBox.height < baseViewBox.height - EPSILON,
    [baseViewBox.height, baseViewBox.width, viewBox.height, viewBox.width],
  );

  const resetZoom = useCallback(() => {
    setViewBox(baseViewBox);
    setIsDragging(false);
    dragRef.current = null;
    pinchRef.current = null;
    pointersRef.current.clear();
  }, [baseViewBox]);

  const resolveChartCoordinates = useCallback(
    (event: ReactMouseEvent<SVGSVGElement>) => {
      const rect = toChartRect(event.currentTarget.getBoundingClientRect());
      return clientToChart(
        { clientX: event.clientX, clientY: event.clientY },
        rect,
        viewBox,
      );
    },
    [viewBox],
  );

  const onWheel = useCallback(
    (event: ReactWheelEvent<SVGSVGElement>) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      const rect = toChartRect(event.currentTarget.getBoundingClientRect());
      const center = clientToChart(
        { clientX: event.clientX, clientY: event.clientY },
        rect,
        viewBox,
      );
      if (!center) return;

      const zoomFactor = event.deltaY < 0 ? 1 / 1.12 : 1.12;
      setViewBox((current) =>
        zoomViewBoxAtPoint({
          viewBox: current,
          baseViewBox,
          maxZoom,
          zoomFactor,
          center,
        }),
      );
    },
    [baseViewBox, maxZoom, viewBox],
  );

  const onPointerDown = useCallback(
    (event: ReactPointerEvent<SVGSVGElement>) => {
      const rect = toChartRect(event.currentTarget.getBoundingClientRect());
      event.currentTarget.setPointerCapture(event.pointerId);

      pointersRef.current.set(event.pointerId, {
        clientX: event.clientX,
        clientY: event.clientY,
      });

      if (pointersRef.current.size === 2) {
        const values = [...pointersRef.current.values()];
        const pinchDistance = distance(values[0], values[1]);
        const pinchMidClient = midpoint(values[0], values[1]);
        const pinchMidChart = clientToChart(pinchMidClient, rect, viewBox);
        if (pinchMidChart && pinchDistance > 0) {
          pinchRef.current = {
            startDistance: pinchDistance,
            startMidChart: pinchMidChart,
            startViewBox: viewBox,
            rect,
          };
          dragRef.current = null;
          setIsDragging(false);
        }
        return;
      }

      if (!isZoomed) return;
      dragRef.current = {
        pointerId: event.pointerId,
        startClientX: event.clientX,
        startClientY: event.clientY,
        startViewBox: viewBox,
        rect,
      };
    },
    [isZoomed, viewBox],
  );

  const onPointerMove = useCallback(
    (event: ReactPointerEvent<SVGSVGElement>) => {
      if (!pointersRef.current.has(event.pointerId)) return;

      pointersRef.current.set(event.pointerId, {
        clientX: event.clientX,
        clientY: event.clientY,
      });

      if (pointersRef.current.size >= 2 && pinchRef.current) {
        const values = [...pointersRef.current.values()];
        const currentDistance = distance(values[0], values[1]);
        if (currentDistance <= 0) return;

        const pinch = pinchRef.current;
        const currentMidClient = midpoint(values[0], values[1]);
        const currentMidChartAtStart = clientToChart(
          currentMidClient,
          pinch.rect,
          pinch.startViewBox,
        );
        if (!currentMidChartAtStart) return;

        const scale = pinch.startDistance / currentDistance;
        const zoomedViewBox = zoomViewBoxAtPoint({
          viewBox: pinch.startViewBox,
          baseViewBox,
          maxZoom,
          zoomFactor: scale,
          center: pinch.startMidChart,
        });

        const deltaX = pinch.startMidChart.x - currentMidChartAtStart.x;
        const deltaY = pinch.startMidChart.y - currentMidChartAtStart.y;
        const pannedViewBox = panViewBox({
          viewBox: zoomedViewBox,
          baseViewBox,
          deltaX,
          deltaY,
        });

        setViewBox(pannedViewBox);
        return;
      }

      const drag = dragRef.current;
      if (!drag || drag.pointerId !== event.pointerId || !isZoomed) return;

      const deltaPixelsX = event.clientX - drag.startClientX;
      const deltaPixelsY = event.clientY - drag.startClientY;
      const deltaX = -(deltaPixelsX * (drag.startViewBox.width / drag.rect.width));
      const deltaY = -(deltaPixelsY * (drag.startViewBox.height / drag.rect.height));

      setViewBox(
        panViewBox({
          viewBox: drag.startViewBox,
          baseViewBox,
          deltaX,
          deltaY,
        }),
      );
      setIsDragging(true);
    },
    [baseViewBox, isZoomed, maxZoom],
  );

  const onPointerUp = useCallback((event: ReactPointerEvent<SVGSVGElement>) => {
    pointersRef.current.delete(event.pointerId);
    if (dragRef.current?.pointerId === event.pointerId) {
      dragRef.current = null;
      setIsDragging(false);
    }
    if (pointersRef.current.size < 2) {
      pinchRef.current = null;
    }
  }, []);

  const onPointerCancel = useCallback((event: ReactPointerEvent<SVGSVGElement>) => {
    pointersRef.current.delete(event.pointerId);
    if (dragRef.current?.pointerId === event.pointerId) {
      dragRef.current = null;
      setIsDragging(false);
    }
    if (pointersRef.current.size < 2) {
      pinchRef.current = null;
    }
  }, []);

  const onPointerLeave = useCallback((event: ReactPointerEvent<SVGSVGElement>) => {
    pointersRef.current.delete(event.pointerId);
    if (dragRef.current?.pointerId === event.pointerId) {
      dragRef.current = null;
      setIsDragging(false);
    }
    if (pointersRef.current.size < 2) {
      pinchRef.current = null;
    }
  }, []);

  return {
    viewBox,
    isZoomed,
    isDragging,
    resetZoom,
    resolveChartCoordinates,
    onWheel,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    onPointerCancel,
    onPointerLeave,
  };
}

