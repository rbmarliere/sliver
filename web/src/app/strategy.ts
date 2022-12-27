export interface Price {
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
}

export interface BaseStrategy {
  id: number;
  symbol: string;
  exchange: string;
  // "creator_id": fields.Integer,
  description: string;
  type: number;
  active: boolean;
  // "deleted": fields.Boolean,
  signal: string;
  market_id: number;
  timeframe: string;
  refresh_interval: number;
  next_refresh: string;
  num_orders: number;
  bucket_interval: number;
  spread: number;
  min_roi: number;
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

  prices: Price;
}
