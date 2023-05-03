import { Component, OnInit } from '@angular/core';
import { FormArray, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Engine } from '../engine';
import { EngineService } from '../engine.service';
import { EnginesService } from '../engines.service';
import { Exchange } from '../exchange';
import { ExchangeService } from '../exchange.service';
import { Market } from '../market';
import { StrategiesService } from '../strategies.service';
import { Strategy } from '../strategy';
import { StrategyFactory, StrategyType } from '../strategy-types/factory';
import { StrategyService } from '../strategy.service';

@Component({
  selector: 'app-strategy',
  templateUrl: './strategy.component.html',
  styleUrls: ['./strategy.component.less'],
})
export class StrategyComponent implements OnInit {
  loading: Boolean = true;
  loadingInd: Boolean = true;
  form: FormGroup = this.formBuilder.group(this.strategy);
  timeframes: String[] = [];
  engines: Engine[] = [];
  stopEngine: Engine | null = null;
  markets: Market[] = [];
  available_mixins: Strategy[] = [];
  private _strategy?: Strategy;
  readonly StrategyType = StrategyType;

  // https://stackoverflow.com/questions/73119114/how-to-iterate-through-enums-with-integer-as-value-in-typescript
  readonly StrategyTypes = Object.values(StrategyType).reduce(
    (acc, curr): { keys: string[]; values: StrategyType } =>
      isNaN(+curr)
        ? { ...acc, keys: [...acc.keys, curr as string] }
        : { ...acc, values: [...acc.values, curr as StrategyType] },
    <any>{ keys: [], values: [] }
  );

  get mixins() {
    return this.form.controls["mixins"] as FormArray;
  }

  set exchanges(exchanges: Exchange[]) {
    for (let exchange of exchanges) {
      for (let market of exchange.markets) {
        const m = market;
        m.exchange_name = exchange.name;
        this.markets.push(m);
      }
      for (let timeframe of exchange.timeframes) {
        if (!this.timeframes.includes(timeframe)) {
          this.timeframes.push(timeframe);
        }
      }
    }
    this.timeframes.sort();
  }

  get strategy(): Strategy {
    if (this._strategy) {
      return this._strategy;
    }
    return new Strategy();
  }

  set strategy(strategy: any) {
    this._strategy = strategy;

    this.form = this.formBuilder.group(strategy);

    this.form.get('id')?.disable();
    this.form.get('timeframe')?.disable();
    this.form.get('signal')?.disable();
    this.form.get('side')?.disable();
    this.form.get('market_id')?.disable();
    this.form.get('type')?.disable();

    this.form.get('lanina_cross_buyback_offset')?.disable();
    this.form.get('lanina_cross_reversed_below')?.disable();

    if (strategy.type == StrategyType.MANUAL) {
      this.form.get('signal')?.enable();

    } else if (strategy.type == StrategyType.MIXER) {
      this.form.removeControl("mixins");
      this.form.addControl("mixins", this.formBuilder.array([]));

      this.strategiesService.getStrategiesByMarketId(strategy.market_id!).subscribe({
        next: (strategies) => this.available_mixins = strategies
      });
    }

    if (strategy.id > 0) {
      this.form.patchValue(strategy);

      if (strategy.type == StrategyType.MIXER) {
        for (let mixin of strategy.mixins!) {
          this.mixins.push(this.formBuilder.group(mixin));
        }
      }

    } else {
      this.form.get('timeframe')?.enable();
      this.form.get('market_id')?.enable();
      this.form.get('type')?.enable();
      this.form.get('side')?.enable();
    }
  }

  constructor(
    private strategyService: StrategyService,
    private strategiesService: StrategiesService,
    private enginesService: EnginesService,
    private engineService: EngineService,
    private exchangeService: ExchangeService,
    private formBuilder: FormBuilder,
    private route: ActivatedRoute,
    private router: Router
  ) {
    const strategy_id = Number(this.route.snapshot.paramMap.get('strategy_id'));

    if (strategy_id == 0) {

      this.loading = false;
      this.loadingInd = false;
      this.strategy = new Strategy();

    } else {

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
  }

  ngOnInit(): void {
    this.getEngines();
    this.getExchanges();
  }

  getEngines(): void {
    this.enginesService.getEngines().subscribe({
      next: (res) => this.engines = res,
    });
  }

  getExchanges(): void {
    this.exchangeService.getExchanges().subscribe({
      next: (res) => this.exchanges = res,
    });
  }

  formatLabel(value: number) {
    return Math.round(value * 100) + '%';
  }

  updateStrategy() {
    const strategy = this.form.getRawValue();
    if (!strategy.stop_engine_id) {
      strategy.stop_engine_id = null;
    }

    if (strategy.id > 0) {
      if (strategy.type == StrategyType.MIXER) {
        strategy.strategies = this.mixins.controls.map((m) => m.value.strategy_id);
        strategy.buy_weights = this.mixins.controls.map((m) => m.value.buy_weight);
        strategy.sell_weights = this.mixins.controls.map((m) => m.value.sell_weight);
      }

      this.strategyService.updateStrategy(strategy).subscribe({
        // next: () => location.reload(),
      });
    } else {
      this.strategiesService.createStrategy(strategy).subscribe({
        next: () => this.router.navigate(['/strategies']),
      });
    }
  }

  updateSubscription(strategy: Strategy): void {
    this.strategyService.updateSubscription(strategy).subscribe({
      next: () => location.reload(),
    });
  }

  addMixin(strategy_id: number, buy_weight: number, sell_weight: number) {
    const group = this.formBuilder.group({
      strategy_id: [strategy_id, Validators.required],
      buy_weight: [buy_weight, Validators.required],
      sell_weight: [sell_weight, Validators.required],
    });

    this.mixins.push(group);
  }

  removeMixin(index: number) {
    this.mixins.removeAt(index);
  }

  typeof(value: any) {
    return typeof value;
  }

  updateActive(strategy: Strategy): void {
    this.strategyService.updateActive(strategy).subscribe({
      next: () => this.strategy.active = !this.strategy.active,
    });
  }

  resetStrategy(strategy: Strategy): void {
    this.strategyService.resetStrategy(strategy).subscribe({
      // next: () => this.strategy.active = !this.strategy.active,
    });
  }
}
