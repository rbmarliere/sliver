import { Indicator, sliceIndicators } from '../indicator';
import { getPositions, Position } from '../position';
import { Strategy } from '../strategy';
import { getStrategyTypeName } from '../strategy/strategy-types';
import { mean, median, variance } from './utils';

export interface Metrics {
  key: string;
  value: string | number;
}

export function backtest(strategy: Strategy, indicators: Indicator, start: Date, end: Date): Metrics[] {

  let startIdx = indicators.time.findIndex((t) => t >= start);
  let endIdx = indicators.time.findIndex((t) => t >= end);

  indicators = sliceIndicators(indicators, startIdx, endIdx);

  // TODO init_balance = 10000 as a param?
  let positions = getPositions(indicators);

  let metrics = getMetrics(positions);

  if (getStrategyTypeName(strategy.type) == "HYPNOX")
    metrics = metrics.concat(getHypnoxMetrics(indicators))

  return metrics;
}

export function getMetrics(positions: Position[]): Metrics[] {

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
  let trading_period = end.getTime() - start.getTime();
  // let last_price = pos_desc[0].exit_price;

  let total_timedelta_in_market = 0;

  let winning_trades = 0;
  let losing_trades = 0;
  let even_trades = 0;

  let gross_profit = 0;
  let gross_loss = 0;

  let avg_winning_trade = 0;
  let avg_losing_trade = 0;

  let largest_winning_trade = 0;
  let largest_losing_trade = 0;

  let avg_time_in_winning_trades = 0;
  let avg_time_in_losing_trades = 0;
  let avg_time_in_even_trades = 0;

  let consecutive_winning_trades = 0;
  let max_consecutive_wins = 0;
  let consecutive_losing_trades = 0;
  let max_consecutive_losses = 0;

  for (let i = 0; i < positions.length; i++) {
    let pos = positions[i];
    let timedelta = pos.exit_time.getTime() - pos.entry_time.getTime();
    total_timedelta_in_market += timedelta;

    if (pos.pnl > 0) {
      gross_profit += pos.pnl;
      avg_time_in_winning_trades = (avg_time_in_winning_trades * i + timedelta) / (i + 1);
      avg_winning_trade = (avg_winning_trade * i + pos.pnl) / (i + 1);

      if (pos.pnl > largest_winning_trade)
        largest_winning_trade = pos.pnl;

      if (consecutive_losing_trades > 0) {
        if (consecutive_losing_trades > max_consecutive_losses)
          max_consecutive_losses = consecutive_losing_trades;
        consecutive_losing_trades = 0;
      }
      consecutive_winning_trades++;
      winning_trades++;


    } else if (pos.pnl < 0) {
      gross_loss += pos.pnl;
      avg_time_in_losing_trades = (avg_time_in_losing_trades * i + timedelta) / (i + 1);
      avg_losing_trade = (avg_losing_trade * i + pos.pnl) / (i + 1);

      if (pos.pnl < largest_losing_trade)
        largest_losing_trade = pos.pnl;

      if (consecutive_winning_trades > 0) {
        if (consecutive_winning_trades > max_consecutive_wins)
          max_consecutive_wins = consecutive_winning_trades;
        consecutive_winning_trades = 0;
      }
      consecutive_losing_trades++;
      losing_trades++;


    } else {
      avg_time_in_even_trades = (avg_time_in_even_trades * i + timedelta) / (i + 1);
      even_trades++;
    }

    // avg_time = (avg_time * i + timedelta) / (i + 1);
    // let entry_amount = balance / pos.entry_price;
    // let pricedelta = pos.exit_price - pos.entry_price;
    // let pnl = pricedelta * entry_amount;
    // let new_balance = balance + pnl;
    // let roi = (new_balance / balance - 1) * 100;
    // avg_roi = (avg_roi * i + roi) / (i + 1);
    // balance = new_balance;
  }

  let avg_trade_net_profit = (avg_winning_trade * winning_trades + avg_losing_trade * losing_trades) / (winning_trades + losing_trades);

  let percent_profitable = (winning_trades / positions.length) * 100;

  let net_profit = gross_profit + gross_loss;
  let profit_factor = gross_profit / Math.abs(gross_loss);

  let payoff_ratio = avg_winning_trade / Math.abs(avg_losing_trade);

  // let init_bh_amount = init_balance / first_price;
  // let exit_bh_value = init_bh_amount * last_price;

  // let roi = (balance / init_balance - 1) * 100;
  // let roi_bh = (exit_bh_value / init_balance - 1) * 100;

  let total_timedelta = end.getTime() - start.getTime();
  let percent_of_time_in_market = (total_timedelta_in_market / total_timedelta) * 100;

  // https://www.investopedia.com/articles/fundamental-analysis/10/strategy-performance-reports.asp
  return [
    { key: 'title', value: 'Performance Summary' },

    { key: 'sep', value: '' },

    { key: 'subtitle', value: 'Buy & Hold' },
    // { key: 'Return on Investment', value: bh_roi },
    // { key: 'Annualized Return', value: bh_apr },
    // { key: 'Exposure', value: bh_exposure },
    // { key: 'Sharpe Ratio', value: bh_sharpe },
    // { key: 'Risk Return Ratio', value: bh_risk_return_ratio },

    { key: 'sep', value: '' },

    { key: 'subtitle', value: 'Strategy' },
    // { key: 'Return on Investment', value: roi },
    // { key: 'Annualized Return', value: apr },
    // { key: 'Exposure', value: exposure },
    // { key: 'Sharpe Ratio', value: sharpe },
    // { key: 'Risk Return Ratio', value: risk_return_ratio },

    { key: 'sep', value: '' },

    { key: 'Total Net Profit', value: net_profit },
    { key: 'Gross Profit', value: gross_profit },
    { key: 'Gross Loss', value: gross_loss },
    { key: 'Profit Factor', value: profit_factor },

    { key: 'SEP', value: '' },

    { key: 'Total Number of Trades', value: positions.length },
    { key: 'Winning Trades', value: winning_trades },
    { key: 'Losing Trades', value: losing_trades },
    { key: 'Even Trades', value: even_trades },
    { key: 'Percent Profitable', value: percent_profitable },

    { key: 'sep', value: '' },

    { key: 'Avg. Trade Net Profit', value: avg_trade_net_profit },
    // { key: 'Avg. Trade Net Profit (%)', value: avg_trade_net_profit_pct },
    { key: 'Avg. Winning Trade', value: avg_winning_trade },
    // { key: 'Avg. Winning Trade (%)', value: avg_winning_trade_pct },
    { key: 'Avg. Losing Trade', value: avg_losing_trade },
    // { key: 'Avg. Losing Trade (%)', value: avg_losing_trade_pct },
    { key: 'Largest Winning Trade', value: largest_winning_trade },
    // { key: 'Largest Winning Trade (%)', value: largest_winning_trade_pct },
    { key: 'Largest Losing Trade', value: largest_losing_trade },
    // { key: 'Largest Losing Trade (%)', value: largest_losing_trade_pct },
    { key: 'Payoff Ratio', value: payoff_ratio },

    { key: 'sep', value: '' },

    { key: 'Max. Consecutive Wins', value: max_consecutive_wins },
    { key: 'Max. Consecutive Losses', value: max_consecutive_losses },
    { key: 'Avg. Time in Winning Trades', value: avg_time_in_winning_trades },
    { key: 'Avg. Time in Losing Trades', value: avg_time_in_losing_trades },
    { key: 'Avg. Time in Even Trades', value: avg_time_in_even_trades },

    { key: 'sep', value: '' },

    { key: 'Trading Period', value: trading_period },
    { key: 'Percent of Time in Market', value: percent_of_time_in_market },
    // { key: 'Max. Equity Run-up', value: max_equity_runup },

    { key: 'sep', value: '' },

    { key: 'subtitle', value: 'Max. Drawdown (Peak to Valley)' },
    // { key: 'Value', value: max_drawdown_pv_value },
    // { key: 'Net Profit as % of Drawdown', value: net_profit_vs_dd_pv },

    { key: 'sep', value: '' },

    { key: 'subtitle', value: 'Max. Drawdown (Trade to Trade)' },
    // { key: 'Value', value: max_drawdown_tt_value },
    // { key: 'Net Profit as % of Drawdown', value: net_profit_vs_dd_tt },

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


