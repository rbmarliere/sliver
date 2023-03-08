import { FormArray } from "@angular/forms";

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
  subscribed: boolean;
  buy_engine_id: number | null;
  sell_engine_id: number | null;
  stop_engine_id: number | null;
}

export interface Strategy extends BaseStrategy {
  // hypnox
  threshold?: number;
  filter?: string;
  model?: string;
  mode?: string;
  operator?: string;

  // dd3
  ma1_period?: number;
  ma2_period?: number;
  ma3_period?: number;

  // mixer
  buy_threshold?: number;
  sell_threshold?: number;
  strategies?: number[];
  buy_weights?: number[];
  sell_weights?: number[];
  mixins?: FormArray;

  // bb
  use_ema?: boolean;
  ma_period?: number;
  num_std?: number;

  // ma_cross
  use_fast_ema?: boolean;
  fast_period?: number;
  use_slow_ema?: boolean;
  slow_period?: number;
}
