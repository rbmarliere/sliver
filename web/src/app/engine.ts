export interface Engine {
  id: number;
  description: string;
  refresh_interval: number;
  num_orders: number;
  bucket_interval: number;
  min_buckets: number;
  spread: number;
  stop_gain: number;
  trailing_gain: boolean;
  stop_loss: number;
  trailing_loss: boolean;
  lm_ratio: number;
}
