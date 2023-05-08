import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Engine } from '../engine';
import { EngineService } from '../engine.service';
import { sliceIndicators } from '../indicator';
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
  plot?: any;
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

            this.indicatorService.getIndicators(this.strategy.id).subscribe({
              next: (res) => {
                this.loading = false;

                res.sells = res.sells.map(() => null)
                res.buys = res.buys.map(() => null)

                // for each position, find the index of the time in the indicators
                // and set the buy/sell indicator to the price
                this.positions!.forEach((pos) => {
                  let idx = res.time.findIndex((t) => t.getTime() >= pos.entry_time.getTime());
                  if (idx !== -1) {
                    if (pos.side === 'long') {
                      res.buys[idx] = pos.entry_price * 1.005;
                    } else {
                      res.sells[idx] = pos.entry_price * 0.995;
                    }
                  }
                  idx = res.time.findIndex((t) => t.getTime() >= pos.exit_time!.getTime());
                  if (idx !== -1) {
                    if (pos.side === 'long') {
                      res.sells[idx] = pos.exit_price * 0.995;
                    } else {
                      res.buys[idx] = pos.exit_price * 1.005;
                    }
                  }
                });

                this.strategy.indicators = res;
                this.plot = this.strategy.getPlot();
                this.zoom(0);
              }
            });
          }
        });
      }
    });
  }

  zoom(event: any): void {
    let start: Date;
    let end: Date;

    if (event['xaxis.range[0]'] === undefined) {
      start = this.strategy.indicators!.time[0];
      end = this.strategy.indicators!.time[this.strategy.indicators!.time.length - 1];
    } else {
      let start_str = event['xaxis.range[0]'].replace(' ', 'T').replace(/$/, 'Z');
      let end_str = event['xaxis.range[1]'].replace(' ', 'T').replace(/$/, 'Z');
      start = new Date(start_str);
      end = new Date(end_str);
    }

    let startIdx = this.strategy.indicators!.time.findIndex((t) => t >= start);
    let endIdx = this.strategy.indicators!.time.findIndex((t) => t >= end);
    let indicators = sliceIndicators(this.strategy.indicators!, startIdx, endIdx);

    this.perfLog = this.strategy.getMetrics(this.positions!, indicators);
  }


}
