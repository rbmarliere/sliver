export interface Strategy {
  symbol: string
  market_id: number
  id: number
  subscribed: boolean
  active: boolean
  description: string
  mode: string
  timeframe: string
  signal: string
  refresh_interval: number
  next_refresh: string
  num_orders: number
  bucket_interval: number
  spread: number
  min_roi: number
  stop_loss: number
  i_threshold: number
  p_threshold: number
  tweet_filter: string
  lm_ratio: number
  model_i: string
  model_p: string
}
