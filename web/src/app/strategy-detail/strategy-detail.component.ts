import { HttpErrorResponse } from '@angular/common/http';
import { Component, Input, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { ActivatedRoute, Router } from '@angular/router';
import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';
import { Exchange } from '../exchange';
import { ExchangeService } from '../exchange.service';
import { Market } from '../market';
import { Strategy } from '../strategy';
import { StrategyService } from '../strategy.service';

@Component({
  selector: 'app-strategy-detail',
  templateUrl: './strategy-detail.component.html',
  styleUrls: ['./strategy-detail.component.less']
})
export class StrategyDetailComponent implements OnInit {

  private empty_strat = {
    symbol: '',
    exchange: '',
    market_id: 0,
    id: 0,
    subscribed: false,
    active: false,
    description: '',
    mode: '',
    timeframe: '',
    signal: '',
    refresh_interval: 0,
    next_refresh: new Date().toISOString().slice(0, 16),
    num_orders: 0,
    bucket_interval: 0,
    spread: 0,
    min_roi: 0,
    stop_loss: 0,
    i_threshold: 0,
    p_threshold: 0,
    tweet_filter: '',
    lm_ratio: 0,
    model_i: '',
    model_p: '',
    prices: {
      time: [],
      open: [],
      high: [],
      low: [],
      close: [],
      volume: [],
      i_score: [],
      p_score: [],
      buys: [],
      sells: []
    }
  };

  plot_layout = {
    // width: 880,
    height: 900,
    showlegend: false,
    title: '',
    xaxis: {
      rangeslider: { visible: false },
      autorange: true,
      type: 'date'
    },
    grid: {rows: 3, columns: 1},
  }

  plot_data: any;

  loading: Boolean = true;

  form = this.createForm(this.empty_strat);

  timeframes: String[] = [];

  markets: Market[] = [];

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

  get strategy(): Strategy { return this._strategy; }
  set strategy(strategy: Strategy) {
    this._strategy = strategy;

    if (strategy.mode == "auto") {
      this.form.get('signal')?.disable();
      this.form.get('i_threshold')?.enable();
      this.form.get('p_threshold')?.enable();
    } else if (strategy.mode == "manual") {
      this.form.get('signal')?.enable();
      this.form.get('i_threshold')?.disable();
      this.form.get('p_threshold')?.disable();
    }

    if (strategy.id > 0) {
      this.form.patchValue(strategy);
      this.form.get('market_id')?.disable();
    } else {
      this.form.patchValue(this.empty_strat);
      this.form.get('market_id')?.enable();
      this.form.get('signal')?.enable();
    }
  }

  private _strategy: Strategy = this.empty_strat;

  private handleError(error: HttpErrorResponse) {
    const dialogConfig = new MatDialogConfig;

    dialogConfig.data = {
      msg: error.error.message
    };

    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

  constructor(
    private strategyService: StrategyService,
    private exchangeService: ExchangeService,
    private formBuilder: FormBuilder,
    private dialog: MatDialog,
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
          this.strategy = res,
          this.loading = false;
          this.plot_layout.title = this.strategy.symbol
          this.plot_data = [
            {
              name: 'price',
              x: res.prices.time,
              open: res.prices.open,
              high: res.prices.high,
              low: res.prices.low,
              close: res.prices.close,
              type: 'candlestick',
              xaxis: 'x',
              yaxis: 'y'
            },{
              name: 'i_score',
              x: res.prices.time,
              y: res.prices.i_score,
              type: 'line',
              xaxis: 'x',
              yaxis: 'y2'
            },{
              name: 'p_score',
              x: res.prices.time,
              y: res.prices.p_score,
              type: 'line',
              xaxis: 'x',
              yaxis: 'y3'
            },{
              name: 'buy signal',
              x: res.prices.time,
              y: res.prices.buys,
              type: 'scatter',
              mode: 'markers',
              marker: { color: 'green', size: 8 },
              xaxis: 'x',
              yaxis: 'y'
            },{
              name: 'sell signal',
              x: res.prices.time,
              y: res.prices.sells,
              type: 'scatter',
              mode: 'markers',
              marker: { color: 'red', size: 8 },
              xaxis: 'x',
              yaxis: 'y'
            }
          ];
        },
        error: (err) => this.handleError(err)
      });
    }

  }

  getExchanges(): void {
    this.exchangeService.getExchanges().subscribe({
      next: (res) => this.exchanges = res,
      error: (err) => this.handleError(err)
    });
  }

  createForm(model: Strategy): FormGroup {
    return this.formBuilder.group(model);
  }

  updateStrategy() {
    const strategy = this.form.getRawValue();

    if (strategy.id > 0) {
      this.strategyService.updateStrategy(strategy).subscribe({
        next: () => location.reload(),
        error: (err) => this.handleError(err)
      });
    } else {
      this.strategyService.createStrategy(strategy).subscribe({
        next: () => this.router.navigate(['/strategies']),
        error: (err) => this.handleError(err)
      });
    }
  }

  subscribe(strategy: Strategy): void {
    this.strategyService.updateSubscription(strategy).subscribe({
      next: () => location.reload(),
      error: (err) => this.handleError(err)
    });
  }

  formatLabel(value: number) {
    return Math.round(value * 100) + '%';
  }
}
