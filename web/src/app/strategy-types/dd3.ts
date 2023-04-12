import { Indicator } from "../indicator";
import { Strategy } from "../strategy";

interface DD3Indicator extends Indicator {
  ma1: number[];
  ma2: number[];
  ma3: number[];
}

export class DD3Strategy extends Strategy {
  override indicators: DD3Indicator | null = null;
  ma1_period: number = 3;
  ma2_period: number = 8;
  ma3_period: number = 20;

  override getPlot(): any {
    let plot = super.getPlot();

    plot.data = plot.data.concat([
      {
        name: 'ma1',
        x: this.indicators!.time,
        y: this.indicators!.ma1,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
      {
        name: 'ma2',
        x: this.indicators!.time,
        y: this.indicators!.ma2,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
      {
        name: 'ma3',
        x: this.indicators!.time,
        y: this.indicators!.ma3,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
    ]);

    return plot;
  }
}
