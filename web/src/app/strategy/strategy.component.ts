import { Component, Input, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
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
    signal: '',
    market_id: null,
    timeframe: '',
    // next_refresh: new Date().toISOString().slice(0, 16),
    orders_interval: 1,
    num_orders: 1,
    min_buckets: 1,
    bucket_interval: 1,
    spread: 0.01,
    stop_gain: 0,
    stop_loss: 0,
    lm_ratio: 0,
    subscribed: false,

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
  };

  loading: Boolean = true;

  form = this.createForm(this.empty_strat);

  timeframes: String[] = [];

  markets: Market[] = [];

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

    this.form.get('signal')?.disable();
    this.form.get('market_id')?.disable();
    this.form.get('type')?.disable();

    if (strategy.id > 0) {
      this.form.patchValue(strategy);

      if (strategy.type === 0) {
        this.form.get('signal')?.enable();
      }

    } else {
      this.form.patchValue(this.empty_strat);

      this.form.get('market_id')?.enable();
      this.form.get('signal')?.enable();
      this.form.get('type')?.enable();
    }
  }

  private _strategy: Strategy = this.empty_strat;

  constructor(
    private strategyService: StrategyService,
    private strategiesService: StrategiesService,
    private exchangeService: ExchangeService,
    private formBuilder: FormBuilder,
    private route: ActivatedRoute,
    private router: Router
  ) { }

  ngOnInit(): void {
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

  getExchanges(): void {
    this.exchangeService.getExchanges().subscribe({
      next: (res) => (this.exchanges = res),
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

}
