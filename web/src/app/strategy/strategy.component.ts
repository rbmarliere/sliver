import { AfterViewInit, Component, Input, OnInit, ViewChild } from '@angular/core';
import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { PriceService } from '../price.service';
import { Strategy } from '../strategy';
import { StrategyService } from '../strategy.service';

@Component({
  selector: 'app-strategy',
  templateUrl: './strategy.component.html',
  styleUrls: ['./strategy.component.less']
})
export class StrategyComponent implements OnInit, AfterViewInit {

  @ViewChild('sidenav')
  private sidenav: any;

  strategies: Strategy[] = [];
  backtest_log?: string;
  data: any;
  layout = {
    width: 969,
    height: 969,
    showlegend: false,
    title: '',
    xaxis: {
      rangeslider: { visible: false },
      autorange: true,
      type: 'date'
    },
    grid: {rows: 3, columns: 1},
  }

  @Input('selected') selected?: Strategy;

  private handleError(error: HttpErrorResponse) {
    const dialogConfig = new MatDialogConfig;

    dialogConfig.data = {
      msg: error.error.message
    };

    console.log(error);
    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.sidenav.open();
    }, 50);
  }

  constructor(
    private strategyService: StrategyService,
    private priceService: PriceService,
    private dialog: MatDialog,
  ) { }

  ngOnInit(): void {
    this.getStrategies();
  }

  getStrategies(): void {
    this.strategyService.getStrategies().subscribe({
      next: (res) => {
        this.strategies = res;
        this.selectStrategy(this.strategies[0]);
      },
      error: (err) => this.handleError(err)
    });
  }

  selectStrategy(strategy: Strategy): void {
    this.selected = strategy;
    this.layout.title = this.selected.symbol
    this.getPrices(strategy.id);
  }

  subscribe(strategy: Strategy): void {
    this.strategyService.updateStrategy(strategy).subscribe({
      next: () => location.reload(),
      error: (err) => this.handleError(err)
    });
  }

  getPrices(strategy_id: number): void {
    this.priceService.getPrices(strategy_id).subscribe({
      next: (res) => {
        this.backtest_log = res.backtest_log;
        this.data = [
          {
            name: 'price',
            x: res.time,
            open: res.open,
            high: res.high,
            low: res.low,
            close: res.close,
            type: 'candlestick',
            xaxis: 'x',
            yaxis: 'y'
          },{
            name: 'i_score',
            x: res.time,
            y: res.i_score,
            type: 'line',
            xaxis: 'x',
            yaxis: 'y2'
          },{
            name: 'p_score',
            x: res.time,
            y: res.p_score,
            type: 'line',
            xaxis: 'x',
            yaxis: 'y3'
          },{
            name: 'buy signal',
            x: res.time,
            y: res.buys,
            type: 'scatter',
            mode: 'markers',
            marker: { color: 'green', size: 8 },
            xaxis: 'x',
            yaxis: 'y'
          },{
            name: 'sell signal',
            x: res.time,
            y: res.sells,
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
