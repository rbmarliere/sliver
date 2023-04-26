import { formatDate } from '@angular/common';
import { Component } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Engine } from '../engine';
import { EngineService } from '../engine.service';
import { IndicatorService } from '../indicator.service';
import { Strategy } from '../strategy';
import { StrategyFactory } from '../strategy-types/factory';
import { StrategyService } from '../strategy.service';

@Component({
  selector: 'app-backtest',
  templateUrl: './backtest.component.html',
  styleUrls: ['./backtest.component.less']
})
export class BacktestComponent {
  loading: Boolean = true;
  loadingInd: Boolean = false;
  strategy!: Strategy;
  stopEngine: Engine | null = null;
  form: FormGroup = this.createForm();

  createForm(): FormGroup {
    const now = new Date();
    const since = new Date(now.getFullYear() - 5, 0, 1);

    return this.formBuilder.group({
      since: [formatDate(since, 'yyyy-MM-ddTHH:mm', 'en'), Validators.required],
      until: [formatDate(now, 'yyyy-MM-ddTHH:mm', 'en'), Validators.required],
    });
  }

  constructor(
    private formBuilder: FormBuilder,
    private strategyService: StrategyService,
    private engineService: EngineService,
    private indicatorService: IndicatorService,
    private route: ActivatedRoute,
  ) {
    const strategy_id = Number(this.route.snapshot.paramMap.get('strategy_id'));

    this.loading = true;

    this.strategyService.getStrategy(strategy_id).subscribe({
      next: (res) => {
        this.loading = false;
        this.strategy = StrategyFactory(res);

        if (res.stop_engine_id) {
          this.engineService.getEngine(res.stop_engine_id).subscribe({
            next: (res) => {
              this.stopEngine = res;
            }
          });
        }
      }
    });
  }

  loadIndicators(): void {
    this.loadingInd = true;

    const since = this.form.value.since;
    const until = this.form.value.until;

    this.indicatorService.getIndicators(this.strategy.id, since, until).subscribe({
      next: (res) => {
        this.strategy.indicators = res;
        this.loadingInd = false;
      }
    });
  }

}

