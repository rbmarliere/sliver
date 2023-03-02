import { Indicator } from '../indicator';
import { Position } from '../position';
import { Strategy } from '../strategy';
import { getStrategyTypeName } from '../strategy/strategy-types';
import { getMaxSeriesDrawdown, mean, median, msToString, variance } from './utils';

export interface Metrics {
  key: string;
  value: string | number;
}

export function backtest(strategy: Strategy, indicators: Indicator, positions: Position[]): Metrics[] {

  let metrics = getMetrics(positions, getMaxSeriesDrawdown(indicators.close));

  if (getStrategyTypeName(strategy.type) == "HYPNOX")
    metrics = metrics.concat(getHypnoxMetrics(indicators))

  return metrics;
}

export function getMetrics(positions: Position[], max_series_drawdown: number): Metrics[] {

  if (positions.length == 0)
    return [{ key: '', value: 'no positions found' }];

  let start = new Date(positions[0].entry_time);

  let end = new Date(positions[positions.length - 1].exit_time);
  let trading_period = end.getTime() - start.getTime();
  let trading_days = trading_period / 1000 / 60 / 60 / 24

  let total_timedelta_in_market = 0;
  let total_entry_cost = 0;
  let total_pnl = 0;

  let winning_trades = 0;
  let losing_trades = 0;

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

  let consecutive_winning_trades = 0;
  let max_consecutive_wins = 0;
  let consecutive_losing_trades = 0;
  let max_consecutive_losses = 0;

  let max_pos_drawdown = 0;
  let max_equity_runup = 0;

  let net_asset_value = 100;
  let init_nav = net_asset_value;

  for (let i = 0; i < positions.length; i++) {
    let pos = positions[i];
    let timedelta = pos.exit_time.getTime() - pos.entry_time.getTime();
    total_timedelta_in_market += timedelta;
    total_entry_cost += pos.entry_cost;
    total_pnl += pos.pnl;
    net_asset_value += net_asset_value * pos.roi / 100;

    if (pos.drawdown && pos.drawdown < max_pos_drawdown) {
      max_pos_drawdown = pos.drawdown;
    }

    let equity_runup = ((pos.max_equity! / pos.entry_cost) - 1) * 100;
    if (equity_runup > max_equity_runup) {
      max_equity_runup = equity_runup;
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
        if (consecutive_losing_trades > max_consecutive_losses) {
          max_consecutive_losses = consecutive_losing_trades;
        }
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
        if (consecutive_winning_trades > max_consecutive_wins) {
          max_consecutive_wins = consecutive_winning_trades;
        }
        consecutive_winning_trades = 0;
      }
      consecutive_losing_trades++;
      losing_trades++;

    }

  }

  let vol = Math.sqrt(variance(positions.map(p => p.roi)));
  let downside_vol = Math.sqrt(variance(positions.filter(p => p.roi < 0).map(p => p.roi)));

  let bh_entry_cost = positions[0].entry_cost;
  let bh_exit_cost = positions[positions.length - 1].exit_price * positions[0].entry_amount;
  let bh_roi = ((bh_exit_cost / bh_entry_cost) - 1) * 100;
  let bh_apr = (bh_roi / trading_days) * 365
  let bh_sharpe = bh_roi / vol;
  let bh_sortino = bh_roi / downside_vol;
  let bh_calmar = bh_roi / max_pos_drawdown;

  let roi = ((net_asset_value / init_nav) - 1) * 100;
  let apr = (roi / trading_days) * 365
  let sharpe = roi / vol;
  let sortino = roi / downside_vol;
  let calmar = bh_roi / max_pos_drawdown;

  let avg_trade_net_profit = (gross_profit / winning_trades) + (gross_loss / losing_trades);
  let avg_trade_net_profit_pct = (avg_trade_net_profit / positions[0].balance!) * 100;

  let percent_profitable = (winning_trades / positions.length) * 100;

  let net_profit = gross_profit + gross_loss;
  let profit_factor = gross_profit / Math.abs(gross_loss);

  let payoff_ratio = avg_winning_trade / Math.abs(avg_losing_trade);

  let total_timedelta = end.getTime() - start.getTime();
  let percent_of_time_in_market = (total_timedelta_in_market / total_timedelta) * 100;

  let bh_recovery_factor = bh_roi / (max_series_drawdown * -1);
  let recovery_factor = roi / (max_pos_drawdown * -1);

  // https://www.investopedia.com/articles/fundamental-analysis/10/strategy-performance-reports.asp
  let metrics = [
    { key: 'title', value: 'Performance Summary' },

    { key: 'SEP', value: '' },

    { key: 'subtitle', value: 'Buy & Hold' },
    { key: 'Return on Investment', value: `${bh_roi.toFixed(2)}%` },
    { key: 'Annualized Return', value: `${bh_apr.toFixed(2)}%` },
    { key: 'Sharpe Ratio', value: bh_sharpe.toFixed(2) },
    { key: 'Sortino Ratio', value: bh_sortino.toFixed(2) },
    { key: 'Calmar Ratio', value: bh_calmar.toFixed(2) },

    { key: 'sep', value: '' },

    { key: 'Max. Drawdown (Series)', value: `${max_series_drawdown.toFixed(2)}%` },
    { key: 'Recovery Factor', value: bh_recovery_factor.toFixed(2) },

    { key: 'SEP', value: '' },

    { key: 'subtitle', value: 'Strategy' },
    { key: 'Return on Investment', value: `${roi.toFixed(2)}%` },
    { key: 'Annualized Return', value: `${apr.toFixed(2)}%` },
    { key: 'Sharpe Ratio', value: sharpe.toFixed(2) },
    { key: 'Sortino Ratio', value: sortino.toFixed(2) },
    { key: 'Calmar Ratio', value: calmar.toFixed(2) },

    { key: 'sep', value: '' },

    { key: 'Max. Equity Run-up', value: `${max_equity_runup.toFixed(2)}%` },
    { key: 'Max. Drawdown (Trade to Trade)', value: `${max_pos_drawdown.toFixed(2)}%` },
    { key: 'Recovery Factor', value: recovery_factor.toFixed(2) },

    { key: 'SEP', value: '' },

    { key: 'Total Net Profit', value: net_profit.toFixed(2) },
    { key: 'Gross Profit', value: gross_profit.toFixed(2) },
    { key: 'Gross Loss', value: gross_loss.toFixed(2) },
    { key: 'Profit Factor', value: profit_factor.toFixed(2) },

    { key: 'sep', value: '' },

    { key: 'Total Number of Trades', value: positions.length },
    { key: 'Winning Trades', value: winning_trades },
    { key: 'Losing Trades', value: losing_trades },
    { key: 'Percent Profitable', value: `${percent_profitable.toFixed(2)}%` },

    { key: 'sep', value: '' },

    { key: 'Avg. Trade Net Profit', value: `${avg_trade_net_profit_pct.toFixed(2)}%` },
    { key: 'Avg. Winning Trade', value: `${avg_winning_trade_pct.toFixed(2)}%` },
    { key: 'Avg. Losing Trade', value: `${avg_losing_trade_pct.toFixed(2)}%` },
    { key: 'Largest Winning Trade', value: `${largest_winning_trade_pct.toFixed(2)}%` },
    { key: 'Largest Losing Trade', value: `${largest_losing_trade_pct.toFixed(2)}%` },
    { key: 'Payoff Ratio', value: payoff_ratio.toFixed(2) },

    { key: 'sep', value: '' },

    { key: 'Max. Consecutive Wins', value: max_consecutive_wins },
    { key: 'Max. Consecutive Losses', value: max_consecutive_losses },
    { key: 'Avg. Time in Winning Trades', value: msToString(avg_time_in_winning_trades) },
    { key: 'Avg. Time in Losing Trades', value: msToString(avg_time_in_losing_trades) },

    { key: 'sep', value: '' },

    { key: 'Trading Period', value: msToString(trading_period) },
    { key: 'Percent of Time in Market', value: `${percent_of_time_in_market.toFixed(2)}%` },
  ];

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


