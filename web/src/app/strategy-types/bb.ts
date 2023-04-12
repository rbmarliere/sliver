import { Indicator } from "../indicator";
import { Strategy } from "../strategy";

export class BBStrategy extends Strategy {
  use_ema: boolean = false;
  ma_period: number = 20;
  num_std: number = 2;

  override getPlot(indicators: Indicator): any {
    let plot = super.getPlot(indicators);

    plot.data = plot.data.concat([
      {
        name: 'ma',
        x: indicators.time,
        y: indicators.ma,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
      {
        name: 'upper band',
        x: indicators.time,
        y: indicators.bolu,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
      {
        name: 'lower band',
        x: indicators.time,
        y: indicators.bold,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
    ]);

    return plot;
  }

}
