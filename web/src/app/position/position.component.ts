import { Component, OnInit } from '@angular/core';
import { PositionService } from '../position.service';

import { Position } from '../position';

@Component({
  selector: 'app-position',
  templateUrl: './position.component.html',
  styleUrls: ['./position.component.less']
})
export class PositionComponent implements OnInit {

  positions: Position[] = [];
  displayedColumns: string[] = [
    'id',
    'strategy_id',
    'market',
    'status',
    'entry_amount',
    'entry_price',
    'exit_price',
    'exit_amount',
    'pnl',
    'actions'
  ];

  loading: Boolean = true;

  constructor(private positionService: PositionService) { }

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

}
