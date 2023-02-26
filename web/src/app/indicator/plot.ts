import { Indicator } from "../indicator";
import { Strategy } from "../strategy";
import { getStrategyTypeName } from "../strategy/strategy-types";


export function getPlot(strategy: Strategy, indicators: Indicator): any {
  let plot = getBasePlot(indicators);

  if (getStrategyTypeName(strategy.type) === 'HYPNOX') {
    plot.data = plot.data.concat(getHypnoxPlotData(indicators));
    plot.layout = { ...plot.layout, ...getHypnoxPlotLayout(), }
  } else if (getStrategyTypeName(strategy.type) === 'DD3') {
    plot.data = plot.data.concat(getDD3PlotData(indicators));
  } else if (getStrategyTypeName(strategy.type) === 'MIXER') {
    plot.data = plot.data.concat(getMixerPlotData(indicators));
    plot.layout = { ...plot.layout, ...getMixerPlotLayout(), }
  } else if (getStrategyTypeName(strategy.type) === 'BB') {
    plot.data = plot.data.concat(getBBPlotData(indicators));
  }

  return plot;
}

function getBasePlot(indicators: Indicator): any {
  return {
    config: getPlotConfig(),
    data: getPlotData(indicators),
    layout: getPlotLayout(),
  }
}

function getPlotLayout(): any {
  let height = 1100;
  if (window.innerWidth < 768) {
    height = 800;
  }

  return {
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
  }
}

function getPlotConfig(): any {
  return {
    modeBarButtonsToRemove: ['select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d'],
  }
}

function getPlotData(data: any): any {
  return [
    {
      name: 'closing price',
      x: data.time,
      y: data.close,
      // high: data.high,
      // low: data.low,
      // close: data.close,
      type: 'line',
      xaxis: 'x',
      yaxis: 'y',
    },
    {
      name: 'buy signal',
      x: data.time,
      y: data.buys,
      type: 'scatter',
      mode: 'markers',
      marker: { color: 'green', size: 8 },
      xaxis: 'x',
      yaxis: 'y',
    },
    {
      name: 'sell signal',
      x: data.time,
      y: data.sells,
      type: 'scatter',
      mode: 'markers',
      marker: { color: 'red', size: 8 },
      xaxis: 'x',
      yaxis: 'y',
    },
  ]
}

function getHypnoxPlotData(data: any): any {
  return [
    {
      name: 'i_score',
      x: data.time,
      y: data.i_score,
      type: 'line',
      xaxis: 'x',
      yaxis: 'y2',
    },
    {
      name: 'p_score',
      x: data.time,
      y: data.p_score,
      type: 'line',
      xaxis: 'x',
      yaxis: 'y2',
    },
  ]
}

function getHypnoxPlotLayout(): any {
  return {
    showlegend: false,
    xaxis: {
      rangeslider: { visible: false },
      autorange: true,
      type: 'date',
    },
    yaxis: { domain: [0.33, 1] },
    yaxis2: { domain: [0, 0.33] },
  }
}

function getDD3PlotData(data: any): any {
  return [
    {
      name: 'ma1',
      x: data.time,
      y: data.ma1,
      type: 'line',
      xaxis: 'x',
      yaxis: 'y',
    },
    {
      name: 'ma2',
      x: data.time,
      y: data.ma2,
      type: 'line',
      xaxis: 'x',
      yaxis: 'y',
    },
    {
      name: 'ma3',
      x: data.time,
      y: data.ma3,
      type: 'line',
      xaxis: 'x',
      yaxis: 'y',
    },
  ]
}

function getMixerPlotData(data: any): any {
  return [
    {
      name: 'signal',
      x: data.time,
      y: data.signal,
      type: 'line',
      xaxis: 'x',
      yaxis: 'y2',
    },
    {
      name: 'buy_w_signal',
      x: data.time,
      y: data.buy_w_signal,
      type: 'line',
      xaxis: 'x',
      yaxis: 'y3',
    },
    {
      name: 'sell_w_signal',
      x: data.time,
      y: data.sell_w_signal,
      type: 'line',
      xaxis: 'x',
      yaxis: 'y4',
    },
  ]
}

function getMixerPlotLayout(): any {
  return {
    showlegend: false,
    xaxis: {
      rangeslider: { visible: false },
      autorange: true,
      type: 'date',
    },
    yaxis: { domain: [0.31, 1] },
    yaxis2: { domain: [0.20, 0.30] },
    yaxis3: { domain: [0.10, 0.20] },
    yaxis4: { domain: [0, 0.10] },
  }
}

function getBBPlotData(data: any): any {
  return [
    {
      name: 'ma',
      x: data.time,
      y: data.ma,
      type: 'line',
      xaxis: 'x',
      yaxis: 'y',
    },
    {
      name: 'upper band',
      x: data.time,
      y: data.bolu,
      type: 'line',
      xaxis: 'x',
      yaxis: 'y',
    },
    {
      name: 'lower band',
      x: data.time,
      y: data.bold,
      type: 'line',
      xaxis: 'x',
      yaxis: 'y',
    },
  ]
}
