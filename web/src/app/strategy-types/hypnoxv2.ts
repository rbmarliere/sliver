import { Indicator } from "../indicator";
import { Metrics } from "../metrics";
import { Position } from "../position";
import { Strategy } from "../strategy";
import { mean, median, variance } from "../utils";

interface Hypnoxv2Indicator extends Indicator {
  score: number[];
}

export class Hypnoxv2Strategy extends Strategy {
  override indicators: Hypnoxv2Indicator | null = null;
  hypnoxv2_tweet_filter: string = '';
  hypnoxv2_upper_threshold: number = 0;
  hypnoxv2_lower_threshold: number = 0;

  override getMetrics(positions: Position[], indicators: Hypnoxv2Indicator): Metrics[] {
    let metrics = super.getMetrics(positions, indicators);

    if (!indicators.score || indicators.score.length == 0) {
      return metrics;
    }

    let scores = indicators.score;

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

  override getPlot(): any {
    let plot = super.getPlot();

    plot.data = plot.data.concat([
      {
        name: 'score',
        x: this.indicators!.time,
        y: this.indicators!.score,
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
