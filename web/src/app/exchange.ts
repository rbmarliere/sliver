import { Asset } from "./asset";
import { Market } from "./market";

export interface Exchange {
  name: string
  rate_limit: number
  precision_mode: number
  padding_mode: number
  timeframes: string[]
  assets: Asset[]
  markets: Market[]
}
