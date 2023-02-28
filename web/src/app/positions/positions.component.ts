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

}
