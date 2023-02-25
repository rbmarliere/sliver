import { Component, Input } from '@angular/core';
import { getMetrics } from '../indicator/backtest';
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
  perfLog: any;
  displayedColumns: string[] = this.getDisplayedColumns();

  public keepOriginalOrder = (a: any, b: any) => a.key

  constructor(
    private positionService: PositionService,
  ) { }

  getDisplayedColumns(): string[] {
    if (window.innerWidth < 768) {
      return [
        'id',
        // 'strategy_id',
        // 'market',
        // 'status',
        // 'entry_amount',
        // 'entry_price',
        // 'exit_price',
        // 'exit_amount',
        'pnl',
        'roi',
        // 'actions'
      ];
    } else {
      return [
        'id',
        // 'strategy_id',
        'market',
        'status',
        'entry_amount',
        'entry_price',
        'exit_price',
        'exit_amount',
        'pnl',
        'roi',
        // 'actions'
      ];
    }
  }

  getPositions() {
    this.loading = true;
    this.positionService.getPositionsByStrategyId(this.strategy.id).subscribe({
      next: (res) => {
        this.positions = res;
        this.loading = false;
        this.perfLog = this.getPerfLog();
      }
    });
  }

  getPerfLog() {
    if (this.positions) {
      let last_index = this.positions.length - 1;
      let start = new Date(this.positions[last_index].entry_time);
      let first_price = this.positions[last_index].entry_price;

      // order positions by exit_time desc
      let positions = this.positions.sort((a, b) => {
        return new Date(b.exit_time).getTime() - new Date(a.exit_time).getTime();
      });

      let end = new Date(positions[0].exit_time);
      let last_price = positions[0].exit_price;

      return getMetrics(this.positions, start, end, first_price, last_price);
    }

    return ``;
  }

}
