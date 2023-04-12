import { Indicator } from "../indicator";
import { Strategy } from "../strategy";

export class DD3Strategy extends Strategy {
  ma1_period: number = 3;
  ma2_period: number = 8;
  ma3_period: number = 20;

  override getPlot(indicators: Indicator): any {
    let plot = super.getPlot(indicators);

    plot.data = plot.data.concat([
      {
        name: 'ma1',
        x: indicators.time,
        y: indicators.ma1,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
      {
        name: 'ma2',
        x: indicators.time,
        y: indicators.ma2,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
      {
        name: 'ma3',
        x: indicators.time,
        y: indicators.ma3,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
    ]);

    return plot;
  }
}
