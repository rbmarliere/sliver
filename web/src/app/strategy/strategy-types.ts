import { Strategy } from "../strategy";
import { getBaseBacktestLog, getHypnoxBacktestLog } from "./backtest";
import { getBasePlot, getDD3PlotData, getHypnoxPlotData, getHypnoxPlotLayout } from "./plot";

export interface StrategyType {
  value: number;
  name: string;
}

export function getStrategyTypes(): StrategyType[] {
  return [
    {
      value: 0,
      name: 'MANUAL',
    },
    {
      value: 1,
      name: 'RANDOM',
    },
    {
      value: 2,
      name: 'HYPNOX',
    },
    {
      value: 3,
      name: 'DD3',
    }
  ];
}

export function getPlot(strategy: Strategy): any {
  let plot = getBasePlot(strategy);

  if (strategy.type === 0) {
    // MANUAL
  } else if (strategy.type === 1) {
    // RANDOM
  } else if (strategy.type === 2) {
    // HYPNOX
    plot.data = plot.data.concat(getHypnoxPlotData(strategy.prices));
    plot.layout = {
      ...plot.layout, ...getHypnoxPlotLayout(),
    }
  } else if (strategy.type === 3) {
    // DD3
    plot.data = plot.data.concat(getDD3PlotData(strategy.prices));
  }

  return plot;
}

export function backtest(strategy: Strategy, _start: string, _end: string): string {
  let start = new Date(_start);
  let end = new Date(_end);

  let backtest_log = getBaseBacktestLog(strategy.prices, start, end);

  if (strategy.type === 0) {
    // MANUAL
  } else if (strategy.type === 1) {
    // RANDOM
  } else if (strategy.type === 2) {
    // HYPNOX
    backtest_log = backtest_log.concat(getHypnoxBacktestLog(strategy.prices, start, end));
  }

  return backtest_log;
}
