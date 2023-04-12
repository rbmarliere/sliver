export interface Indicator {
  time: Date[];
  open: number[];
  high: number[];
  low: number[];
  close: number[];
  buys: number[];
  sells: number[];
}

export function sliceIndicators(indicators: Indicator, startIdx: number, endIdx: number): any {
  if (indicators.time.length == 0) {
    return indicators;
  }

  if (startIdx == 0 && endIdx == indicators.time.length - 1) {
    return indicators;
  }

  let sliced = {};
  for (let key in indicators) {
    if (Array.isArray(indicators[key as keyof Indicator])) {
      (sliced as any)[key] = indicators[key as keyof Indicator].slice(startIdx, endIdx);
    }
  }

  return sliced;
}
