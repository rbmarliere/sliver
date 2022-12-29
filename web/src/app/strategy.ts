export interface BaseStrategy {
  id: number;
  symbol: string;
  exchange: string;
  // creator_id: number;
  description: string;
  type: number;
  active: boolean;
  // deleted: boolean;
  signal: string;
  market_id: number;
  timeframe: string;
  refresh_interval: number;
  next_refresh: string;
  num_orders: number;
  bucket_interval: number;
  spread: number;
  stop_gain: number;
  stop_loss: number;
  lm_ratio: number;
  subscribed: boolean;
}

export interface Strategy extends BaseStrategy {
  // hypnox
  i_threshold?: number;
  p_threshold?: number;
  tweet_filter?: string;
  model_i?: string;
  model_p?: string;

  // dd3
  ma1_period?: number;
  ma2_period?: number;
  ma3_period?: number;


  prices: {
    time: string[];
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
}
