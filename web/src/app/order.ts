export interface Order {
  exchange_order_id: string
  time: string
  status: string
  type: string
  side: string
  price: number
  amount: number
  cost: number
  filled: number
  fee: number
}
