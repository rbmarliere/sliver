import { Component, Input } from '@angular/core';
import { Engine } from '../engine';
import { Indicator, sliceIndicators } from '../indicator';
import { getPositions, Position } from '../position';
import { Strategy } from '../strategy';
import { backtest, Metrics } from './backtest';
import { getPlot } from './plot';

@Component({
  selector: 'app-indicator',
  templateUrl: './indicator.component.html',
  styleUrls: ['./indicator.component.less']
})
export class IndicatorComponent {

  @Input() strategy!: Strategy;
  @Input() indicators!: Indicator;
  @Input() stopEngine!: Engine;

  backtestLog?: Metrics[];
  positions: Position[] = [];
  plot?: any;

  constructor(
  ) { }

  ngOnInit(): void {
    if (!this.indicators.time) {
      return;
    }

    this.plot = getPlot(this.strategy, this.indicators);
    this.zoom(0);
  }

  zoom(event: any): void {
    let start: Date;
    let end: Date;

    if (event['xaxis.range[0]'] === undefined) {
      start = this.indicators.time[0];
      end = this.indicators.time[this.indicators.time.length - 1];
    } else {
      start = new Date(event['xaxis.range[0]']);
      end = new Date(event['xaxis.range[1]']);
    }

    let startIdx = this.indicators.time.findIndex((t) => t >= start);
    let endIdx = this.indicators.time.findIndex((t) => t >= end);
    let indicators = sliceIndicators(this.indicators, startIdx, endIdx);

    this.positions = getPositions(indicators, this.stopEngine);
    this.backtestLog = backtest(this.strategy, indicators, this.positions);
  }

}
