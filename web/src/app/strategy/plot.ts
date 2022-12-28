import { Strategy } from "../strategy";

export function getBasePlot(strategy: Strategy): any {
  return {
    config: getPlotConfig(),
    data: getPlotData(strategy.prices),
    layout: getPlotLayout(strategy.symbol),
  }
}

function getPlotLayout(title: string): any {
  return {
    height: 1100,
    showlegend: false,
    title: title,
    xaxis: {
      rangeslider: { visible: false },
      autorange: true,
      type: 'date',
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
      name: 'price',
      x: data.time,
      open: data.open,
      high: data.high,
      low: data.low,
      close: data.close,
      type: 'candlestick',
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
  ];
}

export function getHypnoxPlotData(data: any): any {
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

export function getHypnoxPlotLayout(): any {
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

