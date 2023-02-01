export interface Position {
  id: number
  market: string
  strategy_id: number
  status: string
  target_cost: number
  entry_cost: number
  entry_amount: number
  entry_price: number
  exit_price: number
  exit_amount: number
  exit_cost: number
  fee: number
  pnl: number
  roi: number
}
