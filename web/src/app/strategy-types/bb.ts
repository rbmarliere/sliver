import { Indicator } from "../indicator";
import { Strategy } from "../strategy";

interface BBIndicator extends Indicator {
  ma: number[];
  bolu: number[];
  bold: number[];
}

export class BBStrategy extends Strategy {
  override indicators: BBIndicator | null = null;
  use_ema: boolean = false;
  ma_period: number = 20;
  num_std: number = 2;

  override getPlot(): any {
    let plot = super.getPlot();

    plot.data = plot.data.concat([
      {
        name: 'ma',
        x: this.indicators!.time,
        y: this.indicators!.ma,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
      {
        name: 'upper band',
        x: this.indicators!.time,
        y: this.indicators!.bolu,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
      {
        name: 'lower band',
        x: this.indicators!.time,
        y: this.indicators!.bold,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
    ]);

    return plot;
  }

}
