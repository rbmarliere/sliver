interface Balance {
  ticker: string;
  free: number;
  used: number;
  total: number;
  free_value: number;
  used_value: number;
  total_value: number;
}

export interface Inventory {
  free_value: number;
  used_value: number;
  total_value: number;
  positions_reserved: number;
  positions_value: number;
  net_liquid: number;
  max_risk: number;
  balances: Balance[];
}
