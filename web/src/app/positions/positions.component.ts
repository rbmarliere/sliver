import { Component, OnInit } from '@angular/core';
import { PositionService } from '../position.service';

import { Position } from '../position';

@Component({
  selector: 'app-positions',
  templateUrl: './positions.component.html',
  styleUrls: ['./positions.component.less']
})
export class PositionsComponent implements OnInit {

  positions: Position[] = [];
  displayedColumns: string[] = this.getDisplayedColumns();
  loading: Boolean = true;

  constructor(
    private positionService: PositionService
  ) { }

  ngOnInit(): void {
    this.getPositions();
  }

  getPositions(): void {
    this.positionService.getPositions().subscribe({
      next: (res) => {
        this.positions = res;
        this.loading = false;
      }
    });
  }

  getDisplayedColumns(): string[] {
    if (window.innerWidth < 768) {
      // mobile
      return [
        'id',
        'strategy_id',
        'market',
        'status',
        // 'entry_amount',
        // 'entry_price',
        // 'exit_price',
        // 'exit_amount',
        // 'pnl',
        // 'roi',
        // 'actions'
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
        // 'actions'
      ];
    }
  }


}
