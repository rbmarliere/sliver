import { Indicator } from '../indicator';
import { Metrics } from '../metrics';
import { Position } from '../position';
import { mean, median, variance } from '../utils';
import { Strategy } from "../strategy";

export class HypnoxStrategy extends Strategy {
  threshold: number = 0;
  filter: string = '';
  model: string = '';
  mode: string = '';
  operator: string = '';

  override getMetrics(positions: Position[], indicators: Indicator): Metrics[] {
    let metrics = super.getMetrics(positions, indicators);

    if (!indicators.z_score || indicators.z_score.length == 0) {
      return metrics;
    }

    let scores = indicators.z_score;

    let scores_stdev = Math.sqrt(variance(scores));
    let scores_mean = mean(scores);
    let scores_median = median(scores);

    return metrics.concat([
      { key: 'SEP', value: '' },

      { key: 'Standard Deviation', value: scores_stdev.toFixed(4) },
      { key: 'Median', value: scores_median.toFixed(4) },
      { key: 'Mean', value: scores_mean.toFixed(4) },
    ]);
  }

  override getPlot(indicators: Indicator): any {
    let plot = super.getPlot(indicators);

    plot.data = plot.data.concat([
      {
        name: 'z_score',
        x: indicators.time,
        y: indicators.z_score,
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
