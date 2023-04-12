import { Component, Input, OnInit } from '@angular/core';
import { Indicator } from '../indicator';
import { Metrics } from '../metrics';
import { Position } from '../position';
import { PositionService } from '../position.service';
import { Strategy } from '../strategy';

@Component({
  selector: 'app-strategy-performance',
  templateUrl: './strategy-performance.component.html',
  styleUrls: ['./strategy-performance.component.less']
})
export class StrategyPerformanceComponent implements OnInit {

  @Input() strategy!: Strategy;
  @Input() indicators!: Indicator;

  positions?: Position[];
  perfLog?: Metrics[];

  constructor(
    private positionService: PositionService,
  ) { }

  ngOnInit(): void {
    this.positionService.getPositionsByStrategyId(this.strategy.id).subscribe({
      next: (res) => {
        this.positions = res;
        if (this.positions.length > 0) {
          this.perfLog = this.strategy.getMetrics(this.positions, this.indicators);
        }
      }
    });
  }

}
