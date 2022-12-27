import { HttpErrorResponse } from '@angular/common/http';
import { Component, Input, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { ActivatedRoute, Router } from '@angular/router';
import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';
import { Exchange } from '../exchange';
import { ExchangeService } from '../exchange.service';
import { Market } from '../market';
import { StrategiesService } from '../strategies.service';
import { Strategy } from '../strategy';
import { StrategyService } from '../strategy.service';

@Component({
  selector: 'app-strategy',
  templateUrl: './strategy.component.html',
  styleUrls: ['./strategy.component.less'],
})
export class StrategyComponent implements OnInit {
  private empty_strat = {
    symbol: '',
    exchange: '',
    market_id: 0,
    id: 0,
    subscribed: false,
    active: false,
    description: '',
    type: 0,
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
      sells: [],
    },
  };

  plot_layout = {
    // width: 880,
    height: 900,
    showlegend: false,
    title: '',
    xaxis: {
      rangeslider: { visible: false },
      autorange: true,
      type: 'date',
    },
    grid: { rows: 3, columns: 1 },
  };

  plot_config = {
    modeBarButtonsToRemove: ['select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d'],
  };

  plot_data: any;

  backtest_log: any;

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

  get strategy(): Strategy {
    return this._strategy;
  }
  set strategy(strategy: Strategy) {
    this._strategy = strategy;

    if (strategy.type == 2) {
      this.form.get('signal')?.disable();
      this.form.get('i_threshold')?.enable();
      this.form.get('p_threshold')?.enable();
    } else if (strategy.type == 0) {
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
    const dialogConfig = new MatDialogConfig();

    console.log(error);
    dialogConfig.data = {
      msg: error.error.message.type,
    };

    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

  constructor(
    private strategyService: StrategyService,
    private strategiesService: StrategiesService,
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
          (this.strategy = res), (this.loading = false);
          this.plot_layout.title = this.strategy.symbol;
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
              yaxis: 'y',
            },
            {
              name: 'i_score',
              x: res.prices.time,
              y: res.prices.i_score,
              type: 'line',
              xaxis: 'x',
              yaxis: 'y2',
            },
            {
              name: 'p_score',
              x: res.prices.time,
              y: res.prices.p_score,
              type: 'line',
              xaxis: 'x',
              yaxis: 'y3',
            },
            {
              name: 'buy signal',
              x: res.prices.time,
              y: res.prices.buys,
              type: 'scatter',
              mode: 'markers',
              marker: { color: 'green', size: 8 },
              xaxis: 'x',
              yaxis: 'y',
            },
            {
              name: 'sell signal',
              x: res.prices.time,
              y: res.prices.sells,
              type: 'scatter',
              mode: 'markers',
              marker: { color: 'red', size: 8 },
              xaxis: 'x',
              yaxis: 'y',
            },
          ];
          this.zoom(0);
        },
        error: (err) => this.handleError(err),
      });
    }
  }

  getExchanges(): void {
    this.exchangeService.getExchanges().subscribe({
      next: (res) => (this.exchanges = res),
      error: (err) => this.handleError(err),
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
        error: (err) => this.handleError(err),
      });
    } else {
      this.strategiesService.createStrategy(strategy).subscribe({
        next: () => this.router.navigate(['/strategies']),
        error: (err) => this.handleError(err),
      });
    }
  }

  subscribe(strategy: Strategy): void {
    this.strategyService.updateSubscription(strategy).subscribe({
      next: () => location.reload(),
      error: (err) => this.handleError(err),
    });
  }

  formatLabel(value: number) {
    return Math.round(value * 100) + '%';
  }

  zoom(event: any): void {
    const start = event['xaxis.range[0]'];
    const end = event['xaxis.range[1]'];
    if (start) {
      this.backtest(start, end);
    } else {
      this.backtest(
        this.strategy.prices.time[0],
        this.strategy.prices.time[this.strategy.prices.time.length - 1]
      );
    }
  }

  backtest(_start: string, _end: string): void {
    // filter data based on zoomed region
    if (this.strategy.prices.i_score && this.strategy.prices.p_score) {
      var start = new Date(_start);
      var end = new Date(_end);
      var times = this.strategy.prices.time;
      var buys = this.strategy.prices.buys;
      var sells = this.strategy.prices.sells;
      var all_intensities = this.strategy.prices.i_score;
      var all_polarities = this.strategy.prices.p_score;
      var len = times.length;
      var indexes = [];
      for (var i = 0; i < len; i++) {
        var element = this.strategy.prices.time[i];
        if (new Date(element) >= start && new Date(element) <= end) {
          indexes.push(i);
        }
      }

      // get existing positions in filtered data
      var intensities = [];
      var polarities = [];
      var positions = [];
      var curr = false;
      var currPos = {
        entry_price: 0,
        entry_time: new Date(0),
        exit_price: 0,
        exit_time: new Date(0),
      };
      for (i = 0; i < indexes.length; i++) {
        var idx = indexes[i];
        intensities.push(all_intensities[idx]);
        polarities.push(all_polarities[idx]);
        if (buys[idx] > 0) {
          if (!curr) {
            curr = true;
            currPos.entry_price = buys[idx];
            currPos.entry_time = new Date(times[idx]);
          }
        } else if (sells[idx] > 0) {
          if (curr) {
            curr = false;
            currPos.exit_price = sells[idx];
            currPos.exit_time = new Date(times[idx]);
            positions.push({
              entry_price: currPos.entry_price,
              entry_time: currPos.entry_time,
              exit_price: currPos.exit_price,
              exit_time: currPos.exit_time,
            });
          }
        }
      }

      var i_median = this.median(intensities);
      var i_mean = this.mean(intensities);
      var p_median = this.median(polarities);
      var p_mean = this.mean(polarities);
      this.backtest_log = `
intensity median = ${i_median.toFixed(4)}
intensity mean = ${i_mean.toFixed(4)}
polarity median = ${p_median.toFixed(4)}
polarity mean = ${p_mean.toFixed(4)}
`;

      if (positions.length == 0) {
        this.backtest_log += 'no positions opened';
        return;
      }

      // compute metrics based on found positions
      var init_balance = 10000;
      var balance = 10000;
      var avg_time = 0;
      var avg_roi = 0;
      for (i = 0; i < positions.length; i++) {
        var pos = positions[i];

        var entry_amount = balance / pos.entry_price;
        var pricedelta = pos.exit_price - pos.entry_price;
        var pnl = pricedelta * entry_amount;
        var timedelta = pos.exit_time.getTime() - pos.entry_time.getTime();

        avg_time = (avg_time * i + timedelta) / (i + 1);

        var new_balance = balance + pnl;
        var roi = (new_balance / balance - 1) * 100;
        avg_roi = (avg_roi * i + roi) / (i + 1);

        balance = new_balance;
      }

      var init_bh_amount = init_balance / this.strategy.prices.open[indexes[0]];
      var exit_bh_value =
        init_bh_amount * this.strategy.prices.open[indexes[indexes.length - 1]];

      var roi = (balance / init_balance - 1) * 100;
      var roi_bh = (exit_bh_value / init_balance - 1) * 100;

      this.backtest_log += `
initial balance = ${init_balance.toFixed(2)}
final balance = ${balance.toFixed(2)}
pnl = ${(balance - init_balance).toFixed(2)}
roi = ${roi.toFixed(2)}%
total timedelta = ${this.msToString(end.getTime() - start.getTime())}
number of trades = ${positions.length}
average timedelta in position = ${this.msToString(avg_time)}
average position roi = ${avg_roi.toFixed(2)}%
buy and hold amount at first candle = ${init_bh_amount.toFixed(8)}
buy and hold value at last candle = ${exit_bh_value.toFixed(2)}
buy and hold roi = ${roi_bh.toFixed(2)}%
`;
    }
  }

  msToString(ms: number): string {
    // https://stackoverflow.com/questions/29816872/how-can-i-convert-milliseconds-to-hhmmss-format-using-javascript
    var seconds = ms / 1000;
    const days = parseInt((seconds / 86400).toString());
    seconds = seconds % 86400;
    const hours = parseInt((seconds / 3600).toString());
    seconds = seconds % 3600;
    const minutes = parseInt((seconds / 60).toString());
    return `${days}d ${hours}h ${minutes}m`;
  }

  median(values: any): any {
    // https://stackoverflow.com/questions/45309447/calculating-median-javascript
    if (values.length === 0) return 0;
    if (this.containsNaN(values)) return 0;

    values.sort(function(a: number, b: number) {
      return a - b;
    });

    var half = Math.floor(values.length / 2);

    if (values.length % 2) return values[half];

    return (values[half - 1] + values[half]) / 2.0;
  }

  mean(values: any): any {
    if (values.length === 0) return 0;
    if (this.containsNaN(values)) return 0;

    const sum = values.reduce((a: any, b: any) => a + b, 0);
    const avg = sum / values.length || 0;
    return avg;
  }

  // function that checks if a list contains a NaN value
  containsNaN(values: any): boolean {
    for (var i = 0; i < values.length; i++) {
      if (isNaN(values[i])) {
        return true;
      }
    }
    return false;
  }

}
