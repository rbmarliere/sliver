export interface BasePosition {
  entry_time: Date;
  exit_time: Date;
  entry_price: number;
  exit_price: number;
}

export interface Position extends BasePosition {
  id: number;
  market: string;
  strategy_id: number;
  status: string;
  target_cost: number;
  entry_cost: number;
  entry_amount: number;
  exit_amount: number;
  exit_cost: number;
  fee: number;
  pnl: number;
  roi: number;
  stopped: boolean;
}

