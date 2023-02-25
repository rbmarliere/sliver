export interface Order {
  id: number;
  exchange_order_id: string;
  market: string;
  time: Date;
  status: string;
  type: string;
  side: string;
  price: number;
  amount: number;
  cost: number;
  filled: number;
  fee: number;
}
