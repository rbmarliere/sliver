import { Component, Input } from '@angular/core';
import { getMetrics, Metrics } from '../indicator/backtest';
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
  perfLog?: Metrics[];

  constructor(
    private positionService: PositionService,
  ) { }

  getPositions(): void {
    this.loading = true;
    this.positionService.getPositionsByStrategyId(this.strategy.id).subscribe({
      next: (res) => {
        this.positions = res;
        this.loading = false;
        this.perfLog = this.getPerfLog();
      }
    });
  }

  getPerfLog(): Metrics[] {
    if (this.positions && this.positions.length > 0) {
      return getMetrics(this.positions);
    }

    return [];
  }

}
