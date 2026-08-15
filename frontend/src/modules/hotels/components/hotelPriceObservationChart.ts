export type HotelPriceObservationInput = {
  readonly id: string;
  readonly observedAt: string;
  readonly amount: number | null;
  readonly eligible: boolean;
  readonly totalPrice: boolean;
};

export type HotelPriceObservationChartPoint = {
  readonly id: string;
  readonly observedAt: string;
  readonly amount: number;
  readonly x: number;
  readonly y: number;
};

const chartWidth = 640;
const chartHeight = 154;
const chartPadding = 22;

function observationTime(value: string) {
  const time = Date.parse(value);
  return Number.isFinite(time) ? time : Number.MAX_SAFE_INTEGER;
}

export function buildHotelPriceObservationChart(
  observations: readonly HotelPriceObservationInput[],
  hasCompleteSeries: boolean,
) {
  const comparable = observations
    .filter((observation) => (
      observation.eligible
      && observation.totalPrice
      && observation.amount !== null
      && observation.amount > 0
    ))
    .sort((left, right) => observationTime(left.observedAt) - observationTime(right.observedAt));

  if (comparable.length === 0) {
    return {
      points: [] as HotelPriceObservationChartPoint[],
      minAmount: null,
      maxAmount: null,
      hasContinuousLine: false,
    };
  }

  const amounts = comparable.map((observation) => observation.amount as number);
  const minAmount = Math.min(...amounts);
  const maxAmount = Math.max(...amounts);
  const valueRange = maxAmount - minAmount;
  const drawableWidth = chartWidth - (chartPadding * 2);
  const drawableHeight = chartHeight - (chartPadding * 2);

  return {
    points: comparable.map((observation, index) => {
      const x = comparable.length === 1
        ? chartWidth / 2
        : chartPadding + ((drawableWidth * index) / (comparable.length - 1));
      const y = valueRange === 0
        ? chartHeight / 2
        : chartPadding + (drawableHeight * (1 - ((observation.amount! - minAmount) / valueRange)));
      return {
        id: observation.id,
        observedAt: observation.observedAt,
        amount: observation.amount!,
        x,
        y,
      };
    }),
    minAmount,
    maxAmount,
    hasContinuousLine: hasCompleteSeries && comparable.length > 1,
  };
}
