import { Component, Input } from '@angular/core';
import { Engine } from '../engine';
import { Indicator, sliceIndicators } from '../indicator';
import { Metrics } from '../metrics';
import { getPositions, Position } from '../position';
import { Strategy } from '../strategy';

@Component({
  selector: 'app-indicator',
  templateUrl: './indicator.component.html',
  styleUrls: ['./indicator.component.less']
})
export class IndicatorComponent {

  @Input() strategy!: Strategy;
  @Input() indicators!: Indicator;
  @Input() stopEngine!: Engine | null;

  backtestLog?: Metrics[];
  positions: Position[] = [];
  plot?: any;

  constructor(
  ) { }

  ngOnInit(): void {
    if (!this.indicators.time) {
      return;
    }

    this.plot = this.strategy.getPlot(this.indicators);
    this.zoom(0);
  }

  zoom(event: any): void {
    let start: Date;
    let end: Date;

    if (event['xaxis.range[0]'] === undefined) {
      start = this.indicators.time[0];
      end = this.indicators.time[this.indicators.time.length - 1];
    } else {
      let start_str = event['xaxis.range[0]'].replace(' ', 'T').replace(/$/, 'Z');
      let end_str = event['xaxis.range[1]'].replace(' ', 'T').replace(/$/, 'Z');
      start = new Date(start_str);
      end = new Date(end_str);
    }

    let startIdx = this.indicators.time.findIndex((t) => t >= start);
    let endIdx = this.indicators.time.findIndex((t) => t >= end);
    let indicators = sliceIndicators(this.indicators, startIdx, endIdx);

    this.positions = getPositions(indicators, this.stopEngine);
    this.backtestLog = this.strategy.getMetrics(this.positions, indicators);
  }

}
