import { Component, OnInit } from '@angular/core';
import { PositionService } from '../position.service';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';

import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';
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
    'market_id',
    'status',
    'entry_amount',
    'entry_price',
    'exit_price',
    'exit_amount',
    'actions'
  ];

  constructor(
    private positionService: PositionService,
    private dialog: MatDialog
  ) { }

  ngOnInit(): void {
    this.getPositions();
  }

  private handleError(error: HttpErrorResponse) {
    const dialogConfig = new MatDialogConfig;

    dialogConfig.data = {
      msg: error.error.message
    };

    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

  getPositions(): void {
    this.positionService.getPositions().subscribe({
      next: (res) => this.positions = res,
      error: (err) => this.handleError(err)
    });
  }

}
