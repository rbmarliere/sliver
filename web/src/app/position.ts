import { Engine } from "./engine";
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

  balance?: number;
  max_equity?: number;
  min_equity?: number;
  drawdown?: number;
}

export function getPositions(indicators: Indicator, stopEngine: Engine): Position[] {
  let init_balance = 1000;
  let balance = init_balance;
  let fee = 0.001;

  let positions = [];

  let curr = false;
  let pos = {
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

    balance: init_balance,
    max_equity: 0,
    min_equity: 0,
    drawdown: 0,
  };

  let maxDrawdown = 0;

  for (let i = 0; i < indicators.time.length; i++) {
    let stopped = checkStop(pos, stopEngine, indicators.close[i]);

    if (indicators.buys[i] > 0) {
      if (!curr) {
        curr = true;

        maxDrawdown = 0;

        pos.entry_time = new Date(indicators.time[i]);
        pos.entry_price = indicators.close[i];

        pos.entry_amount = balance / pos.entry_price;
        pos.entry_cost = pos.entry_amount * pos.entry_price;
        pos.exit_amount = pos.entry_amount

        pos.max_equity = pos.entry_cost;
        pos.min_equity = pos.entry_cost;

      }
    } else if (indicators.sells[i] > 0 || stopped) {
      if (curr) {
        curr = false;

        pos.exit_price = indicators.close[i];
        pos.exit_time = new Date(indicators.time[i]);
        pos.exit_cost = pos.exit_amount * pos.exit_price;

        pos.fee = pos.entry_cost * fee + pos.exit_cost * fee;

        pos.pnl = pos.exit_cost - pos.entry_cost - pos.fee;
        pos.roi = (pos.pnl / pos.entry_cost) * 100;

        balance = balance + pos.pnl;
        pos.balance = balance;

        pos.drawdown = maxDrawdown;

        pos.stopped = stopped;

        positions.push({ ...pos });
      }
    }

    if (pos.entry_amount > 0) {
      let currEquity = indicators.close[i] * pos.entry_amount;

      let currDrawdown = (currEquity - pos.max_equity) / pos.max_equity * 100;
      if (currDrawdown < maxDrawdown) {
        maxDrawdown = currDrawdown;
      }

      if (currEquity > pos.max_equity) {
        pos.max_equity = indicators.close[i] * pos.entry_amount;
        pos.min_equity = pos.max_equity;
      }

      if (currEquity < pos.min_equity) {
        pos.min_equity = indicators.close[i] * pos.entry_amount;
      }

    }
  }

  return positions;
}

function checkStop(pos: Position, engine: Engine, close: number): boolean {
  // TODO trailing
  // "chop" current position

  if (pos.entry_price == 0) {
    return false;
  }

  if (engine.stop_loss <= 0) {
    return false;
  }

  let r = ((close / pos.entry_price) - 1) * 100;
  if (r * -1 > engine.stop_loss) {
    return true;
  }

  return false
}
