import { Component, Input, OnInit } from '@angular/core';
import { Position } from '../position';

@Component({
  selector: 'app-positions-table',
  templateUrl: './positions-table.component.html',
  styleUrls: ['./positions-table.component.less']
})
export class PositionsTableComponent implements OnInit {
  @Input() positions: Position[] = [];
  @Input() displayMode: string = '';

  displayedColumns: string[] = [];

  // strategy-performance
  // getDisplayedColumns(): string[] {
  // }

  ngOnInit(): void {
    this.displayedColumns = this.getDisplayedColumns(this.displayMode);
  }

  getDisplayedColumns(displayMode: string): string[] {
    if (displayMode === 'full') {
      if (window.innerWidth < 768) {
        return [
          'id',
          'strategy_id',
          'market',
          'status',
        ];
      } else {
        return [
          'id',
          'strategy_id',
          'market',
          'status',
          'entry_amount',
          'entry_price',
          'exit_price',
          'exit_amount',
          'pnl',
          'roi',
          'stopped',
        ];
      }

    } else if (displayMode === 'compact') {
      if (window.innerWidth < 768) {
        return [
          'id',
          'pnl',
          'roi',
        ];
      } else {
        return [
          'id',
          'entry_amount',
          'entry_price',
          'exit_price',
          'exit_amount',
          'pnl',
          'roi',
        ];
      }

    } else {
      if (window.innerWidth < 768) {
        return [
          'pnl',
          'roi',
        ];
      } else {
        return [
          'entry_amount',
          'entry_price',
          'exit_price',
          'exit_amount',
          'pnl',
          'roi',
        ];
      }
    }

  }

}
