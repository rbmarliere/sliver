import { Indicator } from "../indicator";
import { Strategy } from "../strategy";


interface LaNinaIndicator extends Indicator {
  rsi: number[];
  root_ma: number[];
  ma1: number[];
  ma2: number[];
  ma3: number[];
  trend: number[];
}

export class LaNinaStrategy extends Strategy {
  override indicators: LaNinaIndicator | null = null;

  lanina_rsi_period: number = 14;
  lanina_rsi_scalar: number = 100;

  lanina_buy_rsi_min_threshold: number = 30;
  lanina_buy_rsi_max_threshold: number = 70;
  lanina_sell_rsi_min_threshold: number = 30;

  lanina_root_ma_period: number = 20;
  lanina_root_ma_mode: string = 'sma';
  lanina_ma1_period: number = 3;
  lanina_ma1_mode: string = 'sma';
  lanina_ma2_period: number = 8;
  lanina_ma2_mode: string = 'sma';
  lanina_ma3_period: number = 20;
  lanina_ma3_mode: string = 'sma';

  lanina_buy_ma_min_offset: number = 0;
  lanina_buy_ma_max_offset: number = 0;
  lanina_sell_ma_min_offset: number = 0;

  lanina_cross_active: boolean = false;
  lanina_cross_buyback_offset: number = 0;
  lanina_cross_min_closes_below: number = 0;
  lanina_cross_reversed_below: boolean = false;

  override getPlot(): any {
    let plot = super.getPlot();

    plot.data = plot.data.concat([
      {
        name: 'rsi',
        x: this.indicators!.time,
        y: this.indicators!.rsi,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y3',
      },
      {
        name: 'trend',
        x: this.indicators!.time,
        y: this.indicators!.trend,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y2',
      },
      {
        name: 'root_ma',
        x: this.indicators!.time,
        y: this.indicators!.root_ma,
        type: 'line',
        xaxis: 'x',
        yaxis: 'y',
      },
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

    plot.layout = {
      ...plot.layout,
      showlegend: false,
      xaxis: {
        rangeslider: { visible: false },
        autorange: true,
        type: 'date',
      },
      yaxis: { domain: [0.33, 1] },
      yaxis2: { domain: [0.20, 0.33] },
      yaxis3: { domain: [0, 0.20] }
    };

    return plot;
  }
}
