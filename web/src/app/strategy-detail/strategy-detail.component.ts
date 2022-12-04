import { HttpErrorResponse } from '@angular/common/http';
import { Component, Input, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';
import { Exchange } from '../exchange';
import { Market } from '../market';
import { Strategy } from '../strategy';
import { StrategyService } from '../strategy.service';

@Component({
  selector: 'app-strategy-detail',
  templateUrl: './strategy-detail.component.html',
  styleUrls: ['./strategy-detail.component.less']
})
export class StrategyDetailComponent implements OnInit {

  // private test = new Date().toISOString();
  private empty_strat = {
    symbol: '',
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
    tweet_filter: ''
  }

  form = this.createForm(this.empty_strat);

  timeframes: String[] = [];

  markets: Market[] = [];

  @Input() exchanges: Exchange[] = [];

  @Input()
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

  private _strategy = {} as Strategy;

  private handleError(error: HttpErrorResponse) {
    const dialogConfig = new MatDialogConfig;

    dialogConfig.data = {
      msg: error.error.message
    };

    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

  constructor(
    private strategyService: StrategyService,
    private formBuilder: FormBuilder,
    private dialog: MatDialog,
  ) { }

  ngOnInit(): void {
    for (let exchange of this.exchanges) {
      for (let market of exchange.markets) {
        const m = market;
        m.exchange_name = exchange.name;
        this.markets.push(m);
      }
      this.timeframes = exchange.timeframes;
    }
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
        next: () => location.reload(),
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

}
