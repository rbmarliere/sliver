import { Component, Input } from '@angular/core';
import { Engine } from '../engine';
import { sliceIndicators } from '../indicator';
import { Metrics } from '../metrics';
import { getLongPositions, getShortPositions, Position } from '../position';
import { Strategy } from '../strategy';

@Component({
  selector: 'app-indicator',
  templateUrl: './indicator.component.html',
  styleUrls: ['./indicator.component.less']
})
export class IndicatorComponent {
  @Input() strategy!: Strategy;
  @Input() stopEngine!: Engine | null;

  backtestLog?: Metrics[];
  positions: Position[] = [];
  plot?: any;

  constructor(
  ) { }

  ngOnInit(): void {
    if (!this.strategy.indicators || !this.strategy.indicators.time) {
      return;
    }

    this.plot = this.strategy.getPlot();
    this.zoom(0);
  }

  zoom(event: any): void {
    let start: Date;
    let end: Date;

    if (event['xaxis.range[0]'] === undefined) {
      start = this.strategy.indicators!.time[0];
      end = this.strategy.indicators!.time[this.strategy.indicators!.time.length - 1];
    } else {
      let start_str = event['xaxis.range[0]'].replace(' ', 'T').replace(/$/, 'Z');
      let end_str = event['xaxis.range[1]'].replace(' ', 'T').replace(/$/, 'Z');
      start = new Date(start_str);
      end = new Date(end_str);
    }

    let startIdx = this.strategy.indicators!.time.findIndex((t) => t >= start);
    let endIdx = this.strategy.indicators!.time.findIndex((t) => t >= end);
    let indicators = sliceIndicators(this.strategy.indicators!, startIdx, endIdx);

    if (this.strategy.side == "long") {
      this.positions = getLongPositions(indicators, this.stopEngine);
    } else if (this.strategy.side == "short") {
      this.positions = getShortPositions(indicators, this.stopEngine);
    }

    this.backtestLog = this.strategy.getMetrics(this.positions, indicators);
  }

}
