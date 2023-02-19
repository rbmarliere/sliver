import { Component, Input, OnInit } from '@angular/core';
import { FormArray, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Engine } from '../engine';
import { EnginesService } from '../engines.service';
import { Exchange } from '../exchange';
import { ExchangeService } from '../exchange.service';
import { Market } from '../market';
import { StrategiesService } from '../strategies.service';
import { Strategy } from '../strategy';
import { StrategyService } from '../strategy.service';
import { getStrategyTypes, StrategyType } from './strategy-types';

@Component({
  selector: 'app-strategy',
  templateUrl: './strategy.component.html',
  styleUrls: ['./strategy.component.less'],
})
export class StrategyComponent implements OnInit {
  private empty_strat = {
    id: 0,
    symbol: '',
    exchange: '',
    // creator_id: 0,
    description: '',
    type: null,
    active: false,
    // deleted: false,
    signal: 0,
    market_id: null,
    timeframe: '',
    // next_refresh: new Date().toISOString().slice(0, 16),
    subscribed: false,
    buy_engine_id: null,
    sell_engine_id: null,
    stop_engine_id: null,

    // hypnox
    i_threshold: 0,
    p_threshold: 0,
    tweet_filter: '',
    model_i: '',
    model_p: '',

    // dd3
    ma1_period: 3,
    ma2_period: 8,
    ma3_period: 20,

    // mixer
    buy_threshold: 1,
    sell_threshold: -1,
    strategies: [],
    buy_weights: [],
    sell_weights: [],
    mixins: this.formBuilder.array([]),

    // bb
    use_ema: false,
    ma_period: 20,
    num_std: 2,
  };

  loading: Boolean = true;

  form = this.createForm(this.empty_strat);

  timeframes: String[] = [];

  engines: Engine[] = [];

  markets: Market[] = [];

  get mixins() {
    return this.form.controls["mixins"] as FormArray;
  }

  available_mixins: Strategy[] = [];

  strategyTypes: StrategyType[] = getStrategyTypes();

  set exchanges(exchanges: Exchange[]) {
    for (let exchange of exchanges) {
      for (let market of exchange.markets) {
        const m = market;
        m.exchange_name = exchange.name;
        this.markets.push(m);
      }
      this.timeframes = exchange.timeframes;
    }
  }

  @Input() strategy_id: number = 0;

  get strategy(): Strategy {
    return this._strategy;
  }
  set strategy(strategy: Strategy) {
    this._strategy = strategy;

    this.form.get('timeframe')?.disable();
    this.form.get('signal')?.disable();
    this.form.get('market_id')?.disable();
    this.form.get('type')?.disable();

    if (strategy.id > 0) {
      if (strategy.strategies && strategy.buy_weights && strategy.sell_weights) {
        for (let i = 0; i < strategy.strategies.length; i++) {
          this.addMixin(strategy.strategies[i], strategy.buy_weights[i], strategy.sell_weights[i]);
        }
      }
      this.form.patchValue(strategy);

      if (strategy.type === 0) {
        this.form.get('signal')?.enable();
      } else if (strategy.type === 4) {
        if (strategy.market_id) {
          this.strategiesService.getStrategiesByMarketId(strategy.market_id).subscribe({
            next: (strategies) => this.available_mixins = strategies
          });
        }
      }

    } else {
      this.form.get('timeframe')?.enable();
      this.form.get('market_id')?.enable();
      this.form.get('signal')?.enable();
      this.form.get('type')?.enable();
    }
  }

  private _strategy: Strategy = this.empty_strat;

  constructor(
    private strategyService: StrategyService,
    private strategiesService: StrategiesService,
    private enginesService: EnginesService,
    private exchangeService: ExchangeService,
    private formBuilder: FormBuilder,
    private route: ActivatedRoute,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.getEngines();
    this.getExchanges();

    const strategy_id = Number(this.route.snapshot.paramMap.get('strategy_id'));

    if (!strategy_id) {
      this.loading = false;
      this.strategy = this.empty_strat;
    } else {
      this.strategyService.getStrategy(strategy_id).subscribe({
        next: (res) => {
          this.strategy = res;
          this.loading = false;
        }
      });
    }
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

  createForm(model: Strategy): FormGroup {
    return this.formBuilder.group(model);
  }

  formatLabel(value: number) {
    return Math.round(value * 100) + '%';
  }

  updateStrategy() {
    const strategy = this.form.getRawValue();

    if (strategy.id > 0) {
      strategy.strategies = this.mixins.controls.map((m) => m.value.strategy_id);
      strategy.buy_weights = this.mixins.controls.map((m) => m.value.buy_weight);
      strategy.sell_weights = this.mixins.controls.map((m) => m.value.sell_weight);

      this.strategyService.updateStrategy(strategy).subscribe({
        next: () => location.reload(),
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

}
