import { Indicator } from "../indicator";
import { Strategy } from "../strategy";

interface Mixin {
  strategy_id: number;
  buy_weight: number;
  sell_weight: number;
}

interface MixerIndicator extends Indicator {
  signal: number[];
  buy_w_signal: number[];
  sell_w_signal: number[];
}

export class MixerStrategy extends Strategy {
  override indicators: MixerIndicator | null = null;
  buy_threshold: number = 1;
  sell_threshold: number = -1;
  mixins: Mixin[] = [];

  override getPlot(): any {
    let plot = super.getPlot();

    plot.data = plot.data.concat([
      {
        name: 'signal',
        x: this.indicators!.time,
        y: this.indicators!.signal,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y2',
      },
      {
        name: 'buy_w_signal',
        x: this.indicators!.time,
        y: this.indicators!.buy_w_signal,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y3',
      },
      {
        name: 'sell_w_signal',
        x: this.indicators!.time,
        y: this.indicators!.sell_w_signal,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y4',
      },
    ]);

    plot.layout = {
      ...plot.layout,
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

    return plot;
  }

}

