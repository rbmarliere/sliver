interface Balance {
  ticker: string;
  total: number;
}

export interface Inventory {
  balances: Balance[];
}
