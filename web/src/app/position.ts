import { Indicator } from "./indicator";

export interface Position {
  id: number;
  market: string;
  strategy_id: number;
  status: string;
  target_cost: number;
  entry_cost: number;
  entry_amount: number;
  entry_time: Date;
  entry_price: number;
  exit_price: number;
  exit_time: Date;
  exit_amount: number;
  exit_cost: number;
  fee: number;
  pnl: number;
  roi: number;
  stopped: boolean;
}

export function getPositions(indicators: Indicator): Position[] {
  let positions = [];

  let curr = false;
  let currPos = {
    id: 0,
    market: "",
    strategy_id: 0,
    status: "closed",
    target_cost: 0,
    entry_cost: 0,
    entry_amount: 0,
    entry_time: new Date(0),
    entry_price: 0,
    exit_price: 0,
    exit_time: new Date(0),
    exit_amount: 0,
    exit_cost: 0,
    fee: 0,
    pnl: 0,
    roi: 0,
    stopped: false,
  };

  for (let i = 0; i < indicators.time.length; i++) {
    if (indicators.buys[i] > 0) {
      if (!curr) {
        curr = true;

        currPos.entry_cost = indicators.close[i];
        currPos.entry_amount = 1; // TODO make this dynamic
        currPos.entry_time = new Date(indicators.time[i]);
        currPos.entry_price = indicators.close[i];

      }
    } else if (indicators.sells[i] > 0) {
      if (curr) {
        curr = false;

        currPos.exit_price = indicators.close[i];
        currPos.exit_time = new Date(indicators.time[i]);
        currPos.exit_amount = 1;
        currPos.exit_cost = indicators.close[i];
        currPos.pnl = currPos.exit_price - currPos.entry_price;
        currPos.roi = (currPos.exit_price / currPos.entry_price - 1) * 100;

        positions.push(currPos);
      }
    }
  }

  return positions;
}
