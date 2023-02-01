import { Component, Input } from '@angular/core';
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
  perf_log: any;
  displayedColumns: string[] = [
    'id',
    'strategy_id',
    'market',
    'status',
    'entry_amount',
    'entry_price',
    'exit_price',
    'exit_amount',
    'pnl',
    'roi',
    'actions'
  ];

  constructor(
    private positionService: PositionService,
  ) { }

  getPositions() {
    this.loading = true;
    this.positionService.getPositionsByStrategyId(this.strategy.id).subscribe({
      next: (res) => {
        this.positions = res;
        this.loading = false;
        this.perf_log = this.getPerfLog();
      }
    });
  }

  getPerfLog() {
    if (this.positions) {
      return `
total pnl = ${(this.positions.reduce((a, b) => a + b.pnl, 0)).toFixed(2)}
average roi = ${(this.positions.reduce((a, b) => a + b.roi, 0) / this.positions.length).toFixed(4)}%
`
    }

    return ``;

  }

}
