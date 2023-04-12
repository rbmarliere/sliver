import { Indicator } from "../indicator";
import { Strategy } from "../strategy";

interface MACrossIndicator extends Indicator {
  fast: number[];
  slow: number[];
}

export class MACrossStrategy extends Strategy {
  override indicators: MACrossIndicator | null = null;
  use_fast_ema: boolean = false;
  fast_period: number = 50;
  use_slow_ema: boolean = false;
  slow_period: number = 200;

  override getPlot(): any {
    let plot = super.getPlot();

    plot.data = plot.data.concat([
      {
        name: 'fast',
        x: this.indicators!.time,
        y: this.indicators!.fast,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
      {
        name: 'slow',
        x: this.indicators!.time,
        y: this.indicators!.slow,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
    ]);

    return plot;
  }

}
