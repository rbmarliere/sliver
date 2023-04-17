import { Indicator } from "../indicator";
import { Strategy } from "../strategy";

interface ElNinoIndicator extends Indicator {
  ma: number[];
  rsi: number[];
}

export class ElNinoStrategy extends Strategy {
  override indicators: ElNinoIndicator | null = null;
  elnino_ma_period: number = 9;
  elnino_use_ema: boolean = false;
  elnino_buy_ma_offset: number = 0;
  elnino_buy_rsi_min_threshold: number = 30;
  elnino_buy_rsi_max_threshold: number = 70;
  elnino_sell_ma_offset: number = 0;
  elnino_sell_rsi_min_threshold: number = 70;
  elnino_rsi_period: number = 14;
  elnino_rsi_scalar: number = 14;

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
        name: 'rsi',
        x: this.indicators!.time,
        y: this.indicators!.rsi,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y2',
      }
    ]);

    plot.layout = {
      ...plot.layout,
      showlegend: false,
      xaxis: {
        rangeslider: { visible: false },
        autorange: true,
        type: 'date',
      },
      yaxis: { domain: [0.33, 1] },
      yaxis2: { domain: [0, 0.33] }
    };

    return plot;
  }
}
