import { Strategy } from "../strategy";

export class WindrunnerStrategy extends Strategy {
  windrunner_model: string = '';
  windrunner_upper_threshold: number = 0;
  windrunner_lower_threshold: number = 0;
  hypnox_model: string = '';
  hypnox_threshold: number = 0;
  hypnox_filter: string = '';
  bb_num_std: number = 2;
  bb_ma_period: number = 20;
  bb_use_ema: boolean = false;
  macd_fast_period: number = 12;
  macd_slow_period: number = 26;
  macd_signal_period: number = 9;
  macd_use_ema: boolean = false;
  atr_period: number = 14;
  atr_ma_mode: string = 'sma';
  renko_step: number = 0;
  renko_use_atr: boolean = false;
}
