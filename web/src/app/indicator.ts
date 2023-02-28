export interface Indicator {
  time: Date[];
  close: number[];
  buys: number[];
  sells: number[];

  // mixer
  signal?: number[];
  buy_w_signal?: number[];
  sell_w_signal?: number[];

  // hypnox
  i_score?: number[];
  p_score?: number[];

  // dd3
  ma1?: number[];
  ma2?: number[];
  ma3?: number[];

  // bb
  ma?: number[];
  bolu?: number[];
  bold?: number[];
}

export function sliceIndicators(indicators: Indicator, startIdx: number, endIdx: number): Indicator {
  if (indicators.time.length == 0) {
    return indicators;
  }

  if (startIdx == 0 && endIdx == indicators.time.length - 1) {
    return indicators;
  }

  return {
    time: indicators.time.slice(startIdx, endIdx),
    close: indicators.close.slice(startIdx, endIdx),
    buys: indicators.buys.slice(startIdx, endIdx),
    sells: indicators.sells.slice(startIdx, endIdx),

    signal: indicators.signal?.slice(startIdx, endIdx),
    buy_w_signal: indicators.buy_w_signal?.slice(startIdx, endIdx),
    sell_w_signal: indicators.sell_w_signal?.slice(startIdx, endIdx),

    i_score: indicators.i_score?.slice(startIdx, endIdx),
    p_score: indicators.p_score?.slice(startIdx, endIdx),

    ma1: indicators.ma1?.slice(startIdx, endIdx),
    ma2: indicators.ma2?.slice(startIdx, endIdx),
    ma3: indicators.ma3?.slice(startIdx, endIdx),

    ma: indicators.ma?.slice(startIdx, endIdx),
    bolu: indicators.bolu?.slice(startIdx, endIdx),
    bold: indicators.bold?.slice(startIdx, endIdx),
  };

}
