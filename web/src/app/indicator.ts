export interface Indicator {
  time: Date[];
  open: number[];
  high: number[];
  low: number[];
  close: number[];
  volume: number[];
  buys: number[];
  sells: number[];

  // hypnox
  i_score?: number[];
  p_score?: number[];

  // dd3
  ma1?: number[];
  ma2?: number[];
  ma3?: number[];
}
