import { Indicator } from "../indicator";
import { Strategy } from "../strategy";

interface Mixin {
  strategy_id: number;
  buy_weight: number;
  sell_weight: number;
}

export class MixerStrategy extends Strategy {
  buy_threshold: number = 1;
  sell_threshold: number = -1;
  mixins: Mixin[] = [];

  override getPlot(indicators: Indicator): any {
    let plot = super.getPlot(indicators);

    plot.data = plot.data.concat([
      {
        name: 'signal',
        x: indicators.time,
        y: indicators.signal,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y2',
      },
      {
        name: 'buy_w_signal',
        x: indicators.time,
        y: indicators.buy_w_signal,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y3',
      },
      {
        name: 'sell_w_signal',
        x: indicators.time,
        y: indicators.sell_w_signal,
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

