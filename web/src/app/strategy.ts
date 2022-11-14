export interface Strategy {
    id: number,
    subscribed: boolean,
    market_id: number,
    description: string,
    mode: string,
    timeframe: string,
    signal: string,
    refresh_interval: number,
    next_refresh: Date,
    num_orders: number,
    bucket_interval: number,
    spread: number,
    min_roi: number,
    stop_loss: number,
    i_threshold: number,
    p_threshold: number,
    tweet_filter: string
}
