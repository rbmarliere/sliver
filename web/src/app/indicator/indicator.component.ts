import { Component, Input, OnInit } from '@angular/core';
import { Indicator } from '../indicator';
import { IndicatorService } from '../indicator.service';
import { Strategy } from '../strategy';
import { backtest } from './backtest';
import { getPlot } from './plot';

@Component({
  selector: 'app-indicator',
  templateUrl: './indicator.component.html',
  styleUrls: ['./indicator.component.less']
})
export class IndicatorComponent implements OnInit {

  @Input() strategy!: Strategy;

  backtest_log: any;
  private indicators?: Indicator;
  loading: Boolean = true;
  plot: any;

  constructor(
    private indicatorService: IndicatorService,
  ) { }

  ngOnInit(): void {
    this.getIndicators();
  }

  getIndicators(): void {
    this.indicatorService.getIndicators(this.strategy).subscribe({
      next: (res) => {
        this.indicators = res;
        this.loading = false;
        this.plot = getPlot(this.strategy, this.indicators);
        this.zoom(0);
      }
    });
  }

  zoom(event: any): void {
    if (!this.indicators) {
      return;
    }

    if (this.indicators.time === null) {
      return;
    }

    const start = event['xaxis.range[0]'];
    const end = event['xaxis.range[1]'];

    if (start) {
      this.backtest_log = backtest(this.strategy, this.indicators, start, end);
    } else {
      this.backtest_log = backtest(
        this.strategy,
        this.indicators,
        this.indicators.time[0],
        this.indicators.time[this.indicators.time.length - 1]
      );
    }
  }

}
