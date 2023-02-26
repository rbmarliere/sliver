import { Indicator } from "./indicator";

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

export function getPositions(indicators: Indicator): BasePosition[] {
  let positions = [];

  let curr = false;
  let currPos = {
    entry_price: 0,
    entry_time: new Date(0),
    exit_price: 0,
    exit_time: new Date(0),
  };

  for (let i = 0; i < indicators.time.length; i++) {
    if (indicators.buys[i] > 0) {
      if (!curr) {
        curr = true;
        currPos.entry_price = indicators.close[i];
        currPos.entry_time = new Date(indicators.time[i]);
      }
    } else if (indicators.sells[i] > 0) {
      if (curr) {
        curr = false;
        currPos.exit_price = indicators.close[i];
        currPos.exit_time = new Date(indicators.time[i]);
        positions.push({
          entry_price: currPos.entry_price,
          entry_time: currPos.entry_time,
          exit_price: currPos.exit_price,
          exit_time: currPos.exit_time,
        });
      }
    }
  }
  return positions;
}
