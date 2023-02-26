import { Indicator } from '../indicator';
import { BasePosition } from '../position';
import { Strategy } from '../strategy';
import { getStrategyTypeName } from '../strategy/strategy-types';
import { mean, median, msToString, variance } from './utils';

export function backtest(strategy: Strategy, indicators: Indicator, start: Date, end: Date): object {

  let indexes = getIndexes(indicators, start, end);
  let positions = getPositions(indicators, indexes);

  let first_price = indicators.close[indexes[0]];
  let last_price = indicators.close[indexes[indexes.length - 1]];

  let metrics = getMetrics(positions, start, end, first_price, last_price);

  if (getStrategyTypeName(strategy.type) == "HYPNOX") {
    metrics = { ...metrics, ...getHypnoxMetrics(indicators, indexes) };
  }

  return metrics;
}

export function getMetrics(positions: BasePosition[], start: Date, end: Date, first_price: number, last_price: number): object {

  if (positions.length == 0) {
    return { '': 'no positions found' };
  }

  let init_balance = 10000;
  let balance = 10000;
  let avg_time = 0;
  let avg_roi = 0;
  let total_timedelta_in_position = 0;

  for (let i = 0; i < positions.length; i++) {
    let pos = positions[i];

    let entry_amount = balance / pos.entry_price;
    let pricedelta = pos.exit_price - pos.entry_price;
    let pnl = pricedelta * entry_amount;
    let timedelta = pos.exit_time.getTime() - pos.entry_time.getTime();

    total_timedelta_in_position += timedelta;

    avg_time = (avg_time * i + timedelta) / (i + 1);

    let new_balance = balance + pnl;
    let roi = (new_balance / balance - 1) * 100;
    avg_roi = (avg_roi * i + roi) / (i + 1);

    balance = new_balance;
  }

  let init_bh_amount = init_balance / first_price;
  let exit_bh_value = init_bh_amount * last_price;

  let roi = (balance / init_balance - 1) * 100;
  let roi_bh = (exit_bh_value / init_balance - 1) * 100;

  let total_timedelta = end.getTime() - start.getTime();
  let avg_time_oom = (total_timedelta - total_timedelta_in_position) / positions.length;

  return {
    'initial balance': init_balance.toFixed(2),
    'final balance': balance.toFixed(2),
    'pnl': (balance - init_balance).toFixed(2),
    'sep': '',
    'roi': `${roi.toFixed(4)}`,
    'b&h final balance': exit_bh_value.toFixed(2),
    'b&h roi': `${roi_bh.toFixed(4)}%`,
    'total timedelta': msToString(total_timedelta),
    'number of trades': positions.length,
    'avg time in': msToString(avg_time),
    'avg time out': msToString(avg_time_oom),
    'avg roi': `${avg_roi.toFixed(4)}%`,
  };
}

function getHypnoxMetrics(indicators: Indicator, indexes: number[]): object {
  if (!indicators.i_score || !indicators.p_score) {
    return {};
  }

  if (indicators.i_score.length == 0 || indicators.p_score.length == 0) {
    return {};
  }

  let intensities = indicators.i_score.slice(indexes[0], indexes[indexes.length - 1]);
  let polarities = indicators.p_score.slice(indexes[0], indexes[indexes.length - 1]);

  let i_median = median(intensities);
  let i_stdev = Math.sqrt(parseFloat(variance(intensities)));
  let i_mean = mean(intensities);
  let p_stdev = Math.sqrt(parseFloat(variance(polarities)));
  let p_median = median(polarities);
  let p_mean = mean(polarities);

  return {
    'i stdev': i_stdev.toFixed(4),
    'i median': i_median,
    'i mean': i_mean,
    'sep': '',
    'p stdev': p_stdev.toFixed(4),
    'p median': p_median,
    'p mean': p_mean,
  };
}


function getIndexes(indicators: Indicator, start: Date, end: Date): number[] {
  let indexes = [];
  for (let i = 0; i < indicators.time.length; i++) {
    let current = new Date(indicators.time[i]);
    if (current >= start && current <= end) {
      indexes.push(i);
    }
  }
  return indexes;
}

function getPositions(indicators: Indicator, indexes: number[]): BasePosition[] {
  let positions = [];
  let curr = false;
  let currPos = {
    entry_price: 0,
    entry_time: new Date(0),
    exit_price: 0,
    exit_time: new Date(0),
  };
  for (let i = 0; i < indexes.length; i++) {
    let idx = indexes[i];
    if (indicators.buys[idx] > 0) {
      if (!curr) {
        curr = true;
        currPos.entry_price = indicators.close[idx];
        currPos.entry_time = new Date(indicators.time[idx]);
      }
    } else if (indicators.sells[idx] > 0) {
      if (curr) {
        curr = false;
        currPos.exit_price = indicators.close[idx];
        currPos.exit_time = new Date(indicators.time[idx]);
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
