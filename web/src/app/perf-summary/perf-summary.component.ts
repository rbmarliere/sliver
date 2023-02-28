import { Component, Input } from '@angular/core';
import { Metrics } from '../indicator/backtest';

@Component({
  selector: 'app-perf-summary',
  templateUrl: './perf-summary.component.html',
  styleUrls: ['./perf-summary.component.less']
})
export class PerfSummaryComponent {
  @Input() summary?: Metrics[];
  @Input() title?: string;

}
