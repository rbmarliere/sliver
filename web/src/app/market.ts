export interface Market {
  symbol: string
  exchange_name: string
  id: number
  base_id: number
  quote_id: number
  amount_precision: number
  price_precision: number
  amount_min: number
  cost_min: number
  price_min: number
}
