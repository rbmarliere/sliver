import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Engine } from '../engine';
import { EngineService } from '../engine.service';
import { IndicatorService } from '../indicator.service';
import { Metrics } from '../metrics';
import { Position } from '../position';
import { PositionService } from '../position.service';
import { Strategy } from '../strategy';
import { StrategyFactory } from '../strategy-types/factory';
import { StrategyService } from '../strategy.service';

@Component({
  selector: 'app-strategy-performance',
  templateUrl: './strategy-performance.component.html',
  styleUrls: ['./strategy-performance.component.less']
})
export class StrategyPerformanceComponent {
  loading: Boolean = true;
  strategy!: Strategy;
  stopEngine: Engine | null = null;
  positions?: Position[];
  perfLog?: Metrics[];

  constructor(
    private positionService: PositionService,
    private strategyService: StrategyService,
    private engineService: EngineService,
    private indicatorService: IndicatorService,
    private route: ActivatedRoute,
  ) {
    const strategy_id = Number(this.route.snapshot.paramMap.get('strategy_id'));

    this.loading = true;

    this.strategyService.getStrategy(strategy_id).subscribe({
      next: (res) => {
        this.strategy = StrategyFactory(res);

        if (res.stop_engine_id) {
          this.engineService.getEngine(res.stop_engine_id).subscribe({
            next: (res) => {
              this.stopEngine = res;
            }
          });
        }

        this.positionService.getPositionsByStrategyId(this.strategy.id).subscribe({
          next: (res) => {
            this.positions = res;
            this.setPerfLog()
          }
        });

        this.indicatorService.getIndicators(this.strategy.id).subscribe({
          next: (res) => {
            this.loading = false;
            this.strategy.indicators = res;
            this.setPerfLog()
          }
        });
      }
    });
  }

  setPerfLog() {
    if (this.positions && this.strategy.indicators) {
      this.perfLog = this.strategy.getMetrics(this.positions, this.strategy.indicators);
    }
  }

}
