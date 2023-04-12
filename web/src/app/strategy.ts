import { Indicator } from './indicator';
import { Metrics } from './metrics';
import { Position } from './position';
import { StrategyType } from './strategy-types/factory';
import { getMaxSeriesDrawdown, msToString, variance } from './utils';

export class Strategy {
  id: number = 0;
  symbol: string = '';
  exchange: string = '';
  description: string = '';
  type: StrategyType | null = null;
  active: boolean = false;
  signal: number = 0;
  market_id: number | null = null;
  timeframe: string = '';
  subscribed: boolean = false;
  buy_engine_id: number | null = null;
  sell_engine_id: number | null = null;
  stop_engine_id: number | null = null;

  static fromData<T extends Strategy>(this: new () => T, data: any): T {
    // https://stackoverflow.com/questions/50342844/how-to-create-a-child-class-in-typescript-using-parent-static-method
    return Object.assign(new this(), data);
  }

  public getMetrics(positions: Position[], indicators: Indicator): Metrics[] {
    if (positions.length == 0) {
      return [];
    }

    let total_timedelta = indicators.time[indicators.time.length - 1].getTime() - indicators.time[0].getTime();
    let total_days = total_timedelta / (1000 * 60 * 60 * 24);

    let pos_start = new Date(positions[0].entry_time!);
    let pos_end = new Date(positions[positions.length - 1].exit_time!);
    let trading_period = pos_end.getTime() - pos_start.getTime();
    let trading_days = trading_period / 1000 / 60 / 60 / 24

    let total_timedelta_in_market = 0;

    let winning_trades = 0;
    let losing_trades = 0;

    let gross_profit = 0;
    let gross_loss = 0;

    let avg_pnl = 0;
    let avg_roi = 0;
    let avg_winning_trade_roi = 0;
    let avg_winning_trade_pnl = 0;
    let avg_losing_trade_roi = 0;
    let avg_losing_trade_pnl = 0;

    let largest_winning_trade_roi = 0;
    let largest_losing_trade_roi = 0;

    let avg_time_in_winning_trades = 0;
    let avg_time_in_losing_trades = 0;

    let consecutive_winning_trades = 0;
    let max_consecutive_wins = 0;
    let consecutive_losing_trades = 0;
    let max_consecutive_losses = 0;

    let max_pos_drawdown = 0;
    let max_equity_runup = 0;

    let net_asset_value = 100;
    let bh_entry_cost = net_asset_value;
    let bh_entry_amount = net_asset_value / indicators.close[0];
    let init_nav = net_asset_value;

    let i = 0;
    for (let pos of positions) {
      i++;

      let timedelta = pos.exit_time!.getTime() - pos.entry_time.getTime();
      total_timedelta_in_market += timedelta;
      net_asset_value += net_asset_value * pos.roi / 100;
      avg_pnl = avg_pnl + (pos.pnl - avg_pnl) / i;
      avg_roi = avg_roi + (pos.roi - avg_roi) / i;

      if (pos.drawdown && pos.drawdown < max_pos_drawdown) {
        max_pos_drawdown = pos.drawdown;
      }

      let equity_runup = ((pos.max_equity! / pos.entry_cost) - 1) * 100;
      if (equity_runup > max_equity_runup) {
        max_equity_runup = equity_runup;
      }

      if (pos.pnl > 0) {
        gross_profit += pos.pnl;
        avg_time_in_winning_trades = avg_time_in_winning_trades + (timedelta - avg_time_in_winning_trades) / i;
        avg_winning_trade_pnl = avg_winning_trade_pnl + (pos.pnl - avg_winning_trade_pnl) / i;
        avg_winning_trade_roi = avg_winning_trade_roi + (pos.roi - avg_winning_trade_roi) / i;

        if (pos.roi > largest_winning_trade_roi) {
          largest_winning_trade_roi = pos.roi;
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
        avg_time_in_losing_trades = avg_time_in_losing_trades + (timedelta - avg_time_in_losing_trades) / i;
        avg_losing_trade_pnl = avg_losing_trade_pnl + (pos.pnl - avg_losing_trade_pnl) / i;
        avg_losing_trade_roi = avg_losing_trade_roi + (pos.roi - avg_losing_trade_roi) / i;

        if (pos.roi < largest_losing_trade_roi) {
          largest_losing_trade_roi = pos.roi;
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

    let max_series_drawdown = getMaxSeriesDrawdown(indicators.close);

    let vol = Math.sqrt(variance(positions.map(p => p.roi)));
    let downside_vol = Math.sqrt(variance(positions.filter(p => p.roi < 0).map(p => p.roi)));

    let bh_max_equity_runup = Math.max(...indicators.close) * bh_entry_amount;
    let bh_exit_cost = indicators.close[indicators.close.length - 1] * bh_entry_amount;
    let bh_roi = ((bh_exit_cost / bh_entry_cost) - 1) * 100;
    let bh_apr = (bh_roi / total_days) * 365
    let bh_sharpe = bh_roi / vol;
    let bh_sortino = bh_roi / downside_vol;
    let bh_calmar = bh_roi / max_series_drawdown;

    let roi = ((net_asset_value / init_nav) - 1) * 100;
    let apr = (roi / trading_days) * 365
    let sharpe = roi / vol;
    let sortino = roi / downside_vol;
    let calmar = bh_roi / max_pos_drawdown;

    let percent_profitable = (winning_trades / positions.length) * 100;

    let net_profit = gross_profit + gross_loss;
    let profit_factor = gross_profit / Math.abs(gross_loss);

    let payoff_ratio = avg_winning_trade_pnl / Math.abs(avg_losing_trade_pnl);

    let percent_of_time_in_market = (total_timedelta_in_market / trading_period) * 100;

    let bh_recovery_factor = bh_roi / (max_series_drawdown * -1);
    let recovery_factor = roi / (max_pos_drawdown * -1);

    let expected_value = (percent_profitable / 100) * avg_winning_trade_roi - ((100 - percent_profitable) / 100) * avg_losing_trade_roi;

    // https://www.investopedia.com/articles/fundamental-analysis/10/strategy-performance-reports.asp
    let metrics = [
      { key: 'SEP', value: '' },

      { key: 'title', value: 'Buy & Hold' },
      { key: 'Return on Investment', value: `${bh_roi.toFixed(2)}%` },
      { key: 'Annualized Return', value: `${bh_apr.toFixed(2)}%` },
      { key: 'Sharpe Ratio', value: bh_sharpe.toFixed(2) },
      { key: 'Sortino Ratio', value: bh_sortino.toFixed(2) },
      { key: 'Calmar Ratio', value: bh_calmar.toFixed(2) },

      { key: 'sep', value: '' },

      { key: 'Max. Equity Run-up', value: `${bh_max_equity_runup.toFixed(2)}%` },
      { key: 'Max. Drawdown', value: `${max_series_drawdown.toFixed(2)}%` },
      { key: 'Recovery Factor', value: bh_recovery_factor.toFixed(2) },

      { key: 'SEP', value: '' },

      { key: 'title', value: 'Strategy' },
      { key: 'Return on Investment', value: `${roi.toFixed(2)}%` },
      { key: 'Annualized Return', value: `${apr.toFixed(2)}%` },
      { key: 'Sharpe Ratio', value: sharpe.toFixed(2) },
      { key: 'Sortino Ratio', value: sortino.toFixed(2) },
      { key: 'Calmar Ratio', value: calmar.toFixed(2) },

      { key: 'sep', value: '' },

      { key: 'Max. Equity Run-up', value: `${max_equity_runup.toFixed(2)}%` },
      { key: 'Max. Drawdown', value: `${max_pos_drawdown.toFixed(2)}%` },
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

      { key: 'Avg. Trade Net Profit', value: `${avg_roi.toFixed(2)}%` },
      { key: 'Avg. Winning Trade', value: `${avg_winning_trade_roi.toFixed(2)}%` },
      { key: 'Avg. Losing Trade', value: `${avg_losing_trade_roi.toFixed(2)}%` },
      { key: 'Largest Winning Trade', value: `${largest_winning_trade_roi.toFixed(2)}%` },
      { key: 'Largest Losing Trade', value: `${largest_losing_trade_roi.toFixed(2)}%` },
      { key: 'Payoff Ratio', value: payoff_ratio.toFixed(2) },
      { key: 'Expected Value', value: `${expected_value.toFixed(2)}%` },

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

  public getPlot(indicators: Indicator): any {
    let height = 1100;
    if (window.innerWidth < 768) {
      height = 800;
    }

    return {
      config: {
        modeBarButtonsToRemove: ['select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d'],
      },
      layout: {
        height: height,
        showlegend: false,
        // title: title,
        xaxis: {
          rangeslider: { visible: false },
          autorange: true,
          type: 'date',
        },
        margin: {
          // b: 0,
          l: 32,
          pad: 0,
          r: 0,
          // t: 0,
        },
      },
      data: [
        {
          name: 'closing price',
          x: indicators.time,
          y: indicators.close,
          // high: data.high,
          // low: data.low,
          // close: data.close,
          type: 'line',
          xaxis: 'x',
          yaxis: 'y',
        },
        {
          name: 'buy signal',
          x: indicators.time,
          y: indicators.buys,
          type: 'scatter',
          mode: 'markers',
          marker: { color: 'green', size: 8 },
          xaxis: 'x',
          yaxis: 'y',
        },
        {
          name: 'sell signal',
          x: indicators.time,
          y: indicators.sells,
          type: 'scatter',
          mode: 'markers',
          marker: { color: 'red', size: 8 },
          xaxis: 'x',
          yaxis: 'y',
        },
      ]
    }
  }
}
