export interface Order {
  time: Date,
  status: string,
  type: string,
  side: string,
  price: number,
  amount: number,
  cost: number,
  filled: number,
  fee: number
}
