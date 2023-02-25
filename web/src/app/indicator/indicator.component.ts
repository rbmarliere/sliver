import { Component, Input } from '@angular/core';
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
export class IndicatorComponent {

  @Input() strategy!: Strategy;

  backtestLog: any;
  plot: any;

  loading: Boolean = false;
  indicators?: Indicator;

  public keepOriginalOrder = (a: any, b: any) => a.key

  constructor(
    private indicatorService: IndicatorService,
  ) { }

  getIndicators(): void {
    this.loading = true;
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

    let start: Date;
    let end: Date;

    if (event['xaxis.range[0]'] === undefined) {
      start = this.indicators.time[0];
      end = this.indicators.time[this.indicators.time.length - 1];
    } else {
      start = new Date(event['xaxis.range[0]']);
      end = new Date(event['xaxis.range[1]']);
    }

    this.backtestLog = backtest(this.strategy, this.indicators, start, end);
  }

}
