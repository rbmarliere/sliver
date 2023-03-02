import { Component, Input } from '@angular/core';
import { Indicator } from '../indicator';
import { IndicatorService } from '../indicator.service';
import { getMetrics, Metrics } from '../indicator/backtest';
import { getMaxSeriesDrawdown } from '../indicator/utils';
import { Position } from '../position';
import { PositionService } from '../position.service';
import { Strategy } from '../strategy';

@Component({
  selector: 'app-strategy-performance',
  templateUrl: './strategy-performance.component.html',
  styleUrls: ['./strategy-performance.component.less']
})
export class StrategyPerformanceComponent {

  @Input() strategy!: Strategy;

  loading: Boolean = false;
  positions?: Position[];
  indicators?: Indicator;
  perfLog?: Metrics[];

  constructor(
    private positionService: PositionService,
    private indicatorService: IndicatorService,
  ) { }

  getPerfLog(): void {
    this.loading = true;
    this.positionService.getPositionsByStrategyId(this.strategy.id).subscribe({
      next: (res) => {
        this.positions = res;
        this.indicatorService.getIndicators(this.strategy).subscribe({
          next: (res) => {
            this.loading = false;
            this.indicators = res;
            this.perfLog = getMetrics(this.positions!, getMaxSeriesDrawdown(res.close));
          }
        });
      }
    });
  }

}
