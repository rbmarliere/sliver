export interface BaseStrategy {
  id: number;
  symbol: string;
  exchange: string;
  // creator_id: number;
  description: string;
  type: number | null;
  active: boolean;
  // deleted: boolean;
  signal: number;
  market_id: number | null;
  timeframe: string;
  // next_refresh: string;
  orders_interval: number;
  num_orders: number;
  min_buckets: number;
  bucket_interval: number;
  spread: number;
  stop_gain: number;
  trailing_gain: boolean;
  stop_loss: number;
  trailing_loss: boolean;
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

  // mixer
  buy_threshold?: number;
  sell_threshold?: number;
  strategies?: number[];
  weights?: number[];
}
