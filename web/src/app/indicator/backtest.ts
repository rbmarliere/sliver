import { Indicator } from '../indicator';
import { Position } from '../position';
import { Strategy } from '../strategy';
import { getStrategyTypeName } from '../strategy/strategy-types';
import { mean, median, variance } from './utils';

export interface Metrics {
  key: string;
  value: string | number;
}

export function backtest(strategy: Strategy, indicators: Indicator, positions: Position[]): Metrics[] {

  let metrics = getMetrics(positions);

  if (getStrategyTypeName(strategy.type) == "HYPNOX")
    metrics = metrics.concat(getHypnoxMetrics(indicators))

  return metrics;
}

export function getMetrics(positions: Position[]): Metrics[] {

  if (positions.length == 0)
    return [{ key: '', value: 'no positions found' }];

  // let first_price = positions[0].entry_price;
  let start = new Date(positions[positions.length - 1].entry_time);

  // order positions by exit_time desc
  let pos_desc = positions.sort((a, b) => {
    return new Date(b.exit_time).getTime() - new Date(a.exit_time).getTime();
  });
  let end = new Date(pos_desc[0].exit_time);
  let trading_period = end.getTime() - start.getTime();
  // let last_price = pos_desc[0].exit_price;

  let total_timedelta_in_market = 0;
  let total_entry_cost = 0;
  let total_pnl = 0;

  let winning_trades = 0;
  let losing_trades = 0;
  let even_trades = 0;

  let gross_profit = 0;
  let gross_loss = 0;

  let avg_winning_trade = 0;
  let avg_winning_trade_pct = 0;
  let avg_losing_trade = 0;
  let avg_losing_trade_pct = 0;

  let largest_winning_trade = 0;
  let largest_winning_trade_pct = 0;
  let largest_losing_trade = 0;
  let largest_losing_trade_pct = 0;

  let avg_time_in_winning_trades = 0;
  let avg_time_in_losing_trades = 0;
  let avg_time_in_even_trades = 0;

  let consecutive_winning_trades = 0;
  let max_consecutive_wins = 0;
  let consecutive_losing_trades = 0;
  let max_consecutive_losses = 0;

  let max_drawdown_tt_value = 0;
  let max_drawdown_tt_pct = 0;
  let greatest_equity_value = 0;
  let greatest_equity_pct = 0;
  let lowest_equity_value = 9999999999999;

  for (let i = 0; i < positions.length; i++) {
    let pos = positions[i];
    let timedelta = pos.exit_time.getTime() - pos.entry_time.getTime();
    total_timedelta_in_market += timedelta;
    total_entry_cost += pos.entry_cost;
    total_pnl += pos.pnl;

    if (pos.max_equity_value && pos.min_equity_value && pos.drawdown) {
      if (pos.max_equity_value > greatest_equity_value) {
        greatest_equity_value = pos.max_equity_value;
        greatest_equity_pct = (greatest_equity_value / pos.entry_cost - 1) * 100;
      }
      if (pos.min_equity_value < lowest_equity_value)
        lowest_equity_value = pos.min_equity_value;
      if (pos.drawdown < max_drawdown_tt_value) {
        max_drawdown_tt_value = pos.max_equity_value - pos.min_equity_value;
        max_drawdown_tt_pct = pos.drawdown;
      }
    }

    if (pos.pnl > 0) {
      gross_profit += pos.pnl;
      avg_time_in_winning_trades = (avg_time_in_winning_trades * i + timedelta) / (i + 1);
      avg_winning_trade = (avg_winning_trade * i + pos.pnl) / (i + 1);
      avg_winning_trade_pct = (avg_winning_trade_pct * i + pos.roi) / (i + 1);

      if (pos.pnl > largest_winning_trade) {
        largest_winning_trade = pos.pnl;
        largest_winning_trade_pct = (pos.pnl / pos.entry_cost) * 100;
      }

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
      avg_losing_trade_pct = (avg_losing_trade_pct * i + pos.roi) / (i + 1);

      if (pos.pnl < largest_losing_trade) {
        largest_losing_trade = pos.pnl;
        largest_losing_trade_pct = (pos.pnl / pos.entry_cost) * 100;
      }

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

  }

  let bh_entry_cost = positions[0].entry_cost;
  let bh_exit_cost = pos_desc[0].exit_cost
  let bh_pnl = bh_exit_cost - bh_entry_cost;
  let bh_roi = (bh_pnl / bh_entry_cost) * 100;
  let bh_apr = (bh_roi / (trading_period / 1000 / 60 / 60 / 24)) * 365
  let bh_sharpe = bh_roi / Math.sqrt(variance(positions.map(p => p.roi)));
  let bh_sortino = bh_roi / Math.sqrt(variance(positions.filter(p => p.roi < 0).map(p => p.roi)));

  let roi = (total_pnl / total_entry_cost) * 100;
  let apr = (roi / (trading_period / 1000 / 60 / 60 / 24)) * 365
  let sharpe = roi / Math.sqrt(variance(positions.map(p => p.roi)));
  let sortino = roi / Math.sqrt(variance(positions.filter(p => p.roi < 0).map(p => p.roi)));

  let avg_trade_net_profit = (gross_profit / winning_trades) + (gross_loss / losing_trades);
  let avg_trade_net_profit_pct = (avg_trade_net_profit / total_entry_cost) * 100;

  let percent_profitable = (winning_trades / positions.length) * 100;

  let net_profit = gross_profit + gross_loss;
  let profit_factor = gross_profit / Math.abs(gross_loss);

  let payoff_ratio = avg_winning_trade / Math.abs(avg_losing_trade);

  let total_timedelta = end.getTime() - start.getTime();
  let percent_of_time_in_market = (total_timedelta_in_market / total_timedelta) * 100;

  let max_drawdown_pv_value = greatest_equity_value - lowest_equity_value;
  let max_drawdown_pv_pct = (lowest_equity_value - greatest_equity_value) / greatest_equity_value * 100;
  let net_profit_vs_dd_pv = (net_profit / max_drawdown_pv_value) * 100;
  let net_profit_vs_dd_tt = (net_profit / max_drawdown_tt_value) * 100;

  // https://www.investopedia.com/articles/fundamental-analysis/10/strategy-performance-reports.asp
  let metrics = [
    { key: 'title', value: 'Performance Summary' },

    { key: 'sep', value: '' },

    { key: 'subtitle', value: 'Buy & Hold' },
    { key: 'Return on Investment', value: bh_roi },
    { key: 'Annualized Return', value: bh_apr },
    { key: 'Sharpe Ratio', value: bh_sharpe },
    { key: 'Sortino Ratio', value: bh_sortino },

    { key: 'sep', value: '' },

    { key: 'subtitle', value: 'Strategy' },
    { key: 'Return on Investment', value: roi },
    { key: 'Annualized Return', value: apr },
    { key: 'Sharpe Ratio', value: sharpe },
    { key: 'Sortino Ratio', value: sortino },

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

    { key: 'Avg. Trade Net Profit', value: `${avg_trade_net_profit} (${avg_trade_net_profit_pct}%)` },
    { key: 'Avg. Winning Trade', value: `${avg_winning_trade} (${avg_winning_trade_pct}%)` },
    { key: 'Avg. Losing Trade', value: `${avg_losing_trade} (${avg_losing_trade_pct}%)` },
    { key: 'Largest Winning Trade', value: `${largest_winning_trade} (${largest_winning_trade_pct}%)` },
    { key: 'Largest Losing Trade', value: `${largest_losing_trade} (${largest_losing_trade_pct}%)` },
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

  ];

  if (max_drawdown_tt_value > 0) {
    metrics = metrics.concat([
      { key: 'SEP', value: '' },

      { key: 'Max. Equity Run-up', value: `${greatest_equity_value} (${greatest_equity_pct}%)` },
      { key: 'Drawdown (Peak to Valley)', value: `${max_drawdown_pv_value} (${max_drawdown_pv_pct}%)` },
      { key: 'Net Profit as % of Drawdown', value: net_profit_vs_dd_pv },

      { key: 'sep', value: '' },

      { key: 'Drawdown (Trade to Trade)', value: `${max_drawdown_tt_value} (${max_drawdown_tt_pct}%)` },
      { key: 'Net Profit as % of Drawdown', value: net_profit_vs_dd_tt },
    ]);
  }

  return metrics;
}

function getHypnoxMetrics(indicators: Indicator): Metrics[] {
  if (!indicators.i_score || !indicators.p_score)
    return [];

  if (indicators.i_score.length == 0 || indicators.p_score.length == 0)
    return [];

  let intensities = indicators.i_score;
  let polarities = indicators.p_score;

  let i_median = median(intensities);
  let i_stdev = Math.sqrt(variance(intensities));
  let i_mean = mean(intensities);
  let p_stdev = Math.sqrt(variance(polarities));
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


