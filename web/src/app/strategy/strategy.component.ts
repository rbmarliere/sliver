import { AfterViewInit, Component, Input, OnInit, ViewChild } from '@angular/core';
import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { Price } from '../price';
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
  data: any;
  layout = {
    width: 969,
    height: 820,
    title: '',
    xaxis: {
      rangeslider: { visible: false },
      autorange: true,
      type: 'date'
    },
  }

  @Input('selected') selected?: Strategy;

  private handleError(error: HttpErrorResponse) {
    const dialogConfig = new MatDialogConfig;

    dialogConfig.data = {
      msg: error.error.message
    };

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

  getPrices(strategy_id: number): void {
    this.priceService.getPrices(strategy_id).subscribe({
      next: (res) => {
        this.data = [{
          x: res.time,
          open: res.open,
          high: res.high,
          low: res.low,
          close: res.close,
          type: 'ohlc',
          xaxis: 'x',
          yaxis: 'y'
        }];
      },
      error: (err) => this.handleError(err)
    });
  }

}
