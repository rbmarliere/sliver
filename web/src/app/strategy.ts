export interface BaseStrategy {
  id: number;
  symbol: string;
  exchange: string;
  // creator_id: number;
  description: string;
  type: number | null;
  active: boolean;
  // deleted: boolean;
  signal: string;
  market_id: number | null;
  timeframe: string;
  refresh_interval: number;
  next_refresh: string;
  num_orders: number;
  min_buckets: number;
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
}
