import { Indicator, sliceIndicators } from '../indicator';
import { BasePosition, getPositions } from '../position';
import { Strategy } from '../strategy';
import { getStrategyTypeName } from '../strategy/strategy-types';
import { mean, median, msToString, variance } from './utils';

export interface Metrics {
  key: string;
  value: string | number;
}

export function backtest(strategy: Strategy, indicators: Indicator, start: Date, end: Date): Metrics[] {

  let startIdx = indicators.time.findIndex((t) => t >= start);
  let endIdx = indicators.time.findIndex((t) => t >= end);

  indicators = sliceIndicators(indicators, startIdx, endIdx);

  let positions = getPositions(indicators);

  let metrics = getMetrics(positions);

  if (getStrategyTypeName(strategy.type) == "HYPNOX")
    metrics = metrics.concat(getHypnoxMetrics(indicators))

  return metrics;
}

export function getMetrics(positions: BasePosition[]): Metrics[] {

  if (positions.length == 0) {
    return [{ key: '', value: 'no positions found' }];
  }

  let first_price = positions[0].entry_price;
  let start = new Date(positions[positions.length - 1].entry_time);

  // order positions by exit_time desc
  let pos_desc = positions.sort((a, b) => {
    return new Date(b.exit_time).getTime() - new Date(a.exit_time).getTime();
  });
  let end = new Date(pos_desc[0].exit_time);
  let last_price = pos_desc[0].exit_price;

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

  return [
    { key: 'title', value: 'Results' },

    { key: 'Gross Profit', value: 0 },
    { key: 'Gross Loss', value: 0 },
    { key: 'Net Profit', value: (balance - init_balance).toFixed(2) },

    { key: 'sep', value: '' },

    { key: 'Return on Investment', value: `${roi.toFixed(2)}%` },
    { key: 'Buy and Hold ROI', value: `${roi_bh.toFixed(2)}%` },

    { key: 'sep', value: '' },

    { key: 'total timedelta', value: msToString(total_timedelta) },
    { key: 'number of trades', value: positions.length },
    { key: 'avg time in', value: msToString(avg_time) },
    { key: 'avg time out', value: msToString(avg_time_oom) },
    { key: 'avg roi', value: `${avg_roi.toFixed(2)}%` },
  ];
}

function getHypnoxMetrics(indicators: Indicator): Metrics[] {
  if (!indicators.i_score || !indicators.p_score) {
    return [];
  }

  if (indicators.i_score.length == 0 || indicators.p_score.length == 0) {
    return [];
  }

  let intensities = indicators.i_score;
  let polarities = indicators.p_score;

  let i_median = median(intensities);
  let i_stdev = Math.sqrt(parseFloat(variance(intensities)));
  let i_mean = mean(intensities);
  let p_stdev = Math.sqrt(parseFloat(variance(polarities)));
  let p_median = median(polarities);
  let p_mean = mean(polarities);

  return [
    { key: 'SEP', value: '' },

    { key: 'title', value: 'Intensity' },
    { key: 'Standard Deviation', value: i_stdev.toFixed(4) },
    { key: 'Median', value: i_median },
    { key: 'Mean', value: i_mean },

    { key: 'title', value: 'Polarity' },
    { key: 'Standard Deviation', value: p_stdev.toFixed(4) },
    { key: 'Median', value: p_median },
    { key: 'Mean', value: p_mean },
  ];
}


