import { Engine } from "./engine";
import { Indicator } from "./indicator";

export interface Position {
  id: number;
  market: string;
  strategy_id: number;
  status: string;
  side: string;
  target_amount: number;
  target_cost: number;
  entry_cost: number;
  entry_amount: number;
  entry_time: Date;
  entry_price: number;
  exit_price: number;
  exit_time: Date | null;
  exit_amount: number;
  exit_cost: number;
  fee: number;
  pnl: number;
  roi: number;
  stopped: boolean;

  last_high?: number;
  last_low?: number;

  balance?: number;
  max_equity?: number;
  min_equity?: number;
  drawdown?: number;
}

export function getLongPositions(indicators: Indicator, stopEngine: Engine | null): Position[] {
  let init_balance = 100;
  let balance = init_balance;
  let fee = 0.001;

  let positions = [];

  let curr = false;
  let pos = {
    id: 0,
    market: "",
    strategy_id: 0,
    status: "closed",
    side: "long",
    target_amount: 0,
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

    last_high: 0,
    last_low: 0,

    balance: init_balance,
    max_equity: 0,
    min_equity: 0,
    drawdown: 0,
  };

  let maxDrawdown = 0;

  for (let i = 0; i < indicators.time.length; i++) {
    let stopPrice = checkStop(pos, stopEngine, indicators.high[i], indicators.low[i]);
    let stopped = stopPrice > 0;

    let cooledDown = checkStopCooldown(pos, stopEngine, indicators.time[i]);

    if (indicators.buys[i] > 0 && !cooledDown) {
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

        pos.last_high = pos.entry_price;
        pos.last_low = pos.entry_price;

      }
    } else if (indicators.sells[i] > 0 || stopped) {
      if (curr) {
        curr = false;

        pos.exit_price = indicators.close[i];
        if (stopped) {
          pos.exit_price = stopPrice;
        }

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
      let currMaxEquity = indicators.high[i] * pos.entry_amount;
      let currMinEquity = indicators.low[i] * pos.entry_amount;

      let currDrawdown = (currMinEquity - pos.max_equity) / pos.max_equity * 100;
      if (currDrawdown < maxDrawdown) {
        maxDrawdown = currDrawdown;
      }

      if (currMaxEquity > pos.max_equity) {
        pos.max_equity = currMaxEquity;
        pos.min_equity = currMaxEquity;
      }

      if (currMinEquity < pos.min_equity) {
        pos.min_equity = currMinEquity;
      }

    }
  }

  return positions;
}

export function getShortPositions(indicators: Indicator, stopEngine: Engine | null): Position[] {
  let init_balance = 100;
  let balance = init_balance;
  let fee = 0.001;

  let positions = [];

  let curr = false;
  let pos = {
    id: 0,
    market: "",
    strategy_id: 0,
    status: "closed",
    side: "short",
    target_amount: 0,
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

    last_high: 0,
    last_low: 0,

    balance: init_balance,
    max_equity: 0,
    min_equity: 0,
    drawdown: 0,
  };

  let maxDrawdown = 0;

  for (let i = 0; i < indicators.time.length; i++) {
    let stopPrice = checkStop(pos, stopEngine, indicators.high[i], indicators.low[i]);
    let stopped = stopPrice > 0;

    let cooledDown = checkStopCooldown(pos, stopEngine, indicators.time[i]);

    if (indicators.sells[i] > 0 && !cooledDown) {
      if (!curr) {
        curr = true;

        maxDrawdown = 0;

        pos.entry_time = new Date(indicators.time[i]);
        pos.entry_price = indicators.close[i];

        pos.entry_amount = balance;
        pos.entry_cost = pos.entry_amount * pos.entry_price;
        pos.exit_cost = pos.entry_cost

        pos.max_equity = pos.entry_cost;
        pos.min_equity = pos.entry_cost;

        pos.last_high = pos.entry_price;
        pos.last_low = pos.entry_price;

      }
    } else if (indicators.buys[i] > 0 || stopped) {
      if (curr) {
        curr = false;

        pos.exit_price = indicators.close[i];
        if (stopped) {
          pos.exit_price = stopPrice;
        }

        pos.exit_time = new Date(indicators.time[i]);
        pos.exit_amount = pos.exit_cost / pos.exit_price;

        pos.fee = pos.entry_amount * fee + pos.exit_amount * fee;

        pos.pnl = pos.exit_amount - pos.entry_amount - pos.fee;
        pos.roi = (pos.pnl / pos.entry_amount) * 100;

        balance = balance + pos.pnl;
        pos.balance = balance;

        pos.drawdown = maxDrawdown;

        pos.stopped = stopped;

        positions.push({ ...pos });
      }
    }

    if (pos.entry_amount > 0) {
      let currMaxEquity = indicators.high[i] * pos.entry_amount;
      let currMinEquity = indicators.low[i] * pos.entry_amount;

      let currDrawdown = (currMinEquity - pos.max_equity) / pos.max_equity * 100;
      if (currDrawdown < maxDrawdown) {
        maxDrawdown = currDrawdown;
      }

      if (currMaxEquity > pos.max_equity) {
        pos.max_equity = currMaxEquity;
        pos.min_equity = currMaxEquity;
      }

      if (currMinEquity < pos.min_equity) {
        pos.min_equity = currMinEquity;
      }

    }
  }

  return positions;
}

function checkStop(pos: Position, engine: Engine | null, high: number, low: number): number {
  if (pos.entry_price == 0) {
    return 0;
  }

  if (engine === null) {
    return 0;
  }

  if (engine.stop_gain <= 0 && engine.stop_loss <= 0) {
    return 0;
  }

  if (high > pos.last_high!) {
    pos.last_high = high;
  }

  if (low < pos.last_low!) {
    pos.last_low = low;
  }

  if (engine.stop_gain > 0) {
    let currGain = 0;

    if (engine.trailing_gain) {

      if (low > pos.entry_price) {
        currGain = ((pos.last_high! - low) / low * 100) * -1;
        if (currGain > engine.stop_gain) {
          return pos.last_high! * (1 - engine.stop_gain / 100);
        }
      }

    } else {
      currGain = (high - pos.entry_price) / pos.entry_price * 100;
      if (currGain > engine.stop_gain) {
        return pos.entry_price * (1 + engine.stop_gain / 100);
      }
    }

  }

  if (engine.stop_loss > 0) {
    let currLoss = 0;

    if (engine.trailing_loss) {

      if (high < pos.entry_price) {
        currLoss = (pos.last_low! - high) / high * 100;
        if (currLoss > engine.stop_loss) {
          return pos.last_low! * (1 + engine.stop_loss / 100);
        }
      }

    } else {
      currLoss = ((low - pos.entry_price) / pos.entry_price * 100) * -1;
      if (currLoss > engine.stop_loss) {
        return pos.entry_price * (1 - engine.stop_loss / 100);
      }
    }

  }

  return 0;
}

function checkStopCooldown(pos: Position, engine: Engine | null, time: Date): boolean {
  let cooldown_in_min = engine?.stop_cooldown || 0;

  if (cooldown_in_min <= 0 || !pos.stopped) {
    return false;
  }

  let now = new Date(time);
  let last = pos.exit_time!;

  let diff_in_min = (now.getTime() - last.getTime()) / 1000 / 60;

  return diff_in_min < cooldown_in_min;
}
