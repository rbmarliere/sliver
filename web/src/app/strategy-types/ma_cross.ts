import { Indicator } from "../indicator";
import { Strategy } from "../strategy";

export class MACrossStrategy extends Strategy {
  use_fast_ema: boolean = false;
  fast_period: number = 50;
  use_slow_ema: boolean = false;
  slow_period: number = 200;

  override getPlot(indicators: Indicator): any {
    let plot = super.getPlot(indicators);

    plot.data = plot.data.concat([
      {
        name: 'fast',
        x: indicators.time,
        y: indicators.fast,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
      {
        name: 'slow',
        x: indicators.time,
        y: indicators.slow,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
    ]);

    return plot;
  }

}
