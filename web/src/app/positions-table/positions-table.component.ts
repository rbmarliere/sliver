import { Component, Input, OnInit } from '@angular/core';
import { DialogService } from '../dialog.service';
import { Position } from '../position';
import { PositionService } from '../position.service';

@Component({
  selector: 'app-positions-table',
  templateUrl: './positions-table.component.html',
  styleUrls: ['./positions-table.component.less']
})
export class PositionsTableComponent implements OnInit {
  @Input() positions: Position[] = [];
  @Input() displayMode: string = '';

  displayedColumns: string[] = [];

  constructor(
    private positionService: PositionService,
    private dialogService: DialogService,
  ) { }

  ngOnInit(): void {
    this.displayedColumns = this.getDisplayedColumns(this.displayMode);
  }

  getDisplayedColumns(displayMode: string): string[] {
    if (displayMode === 'full') {
      // position component
      if (window.innerWidth < 768) {
        return [
          'id',
          'strategy_id',
          'market',
          'status',
          'actions',
        ];
      } else {
        return [
          'id',
          'strategy_id',
          'market',
          'status',
          'side',
          'entry_amount',
          'entry_price',
          'exit_price',
          'exit_amount',
          'roi',
          'actions',
        ];
      }

    } else if (displayMode === 'compact') {
      // strategy performance component
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
      // indicator component
      if (window.innerWidth < 768) {
        return [
          'pnl',
          'roi',
          'balance'
        ];
      } else {
        return [
          'entry_amount',
          'entry_price',
          'exit_price',
          'exit_amount',
          'pnl',
          'roi',
          'balance',
          'stopped'
        ];
      }
    }

  }

  deletePosition(position_id: number) {
    this.dialogService.confirm('Are you sure you want to delete this position? All of its orders will also be erased.').subscribe((res) => {
      if (res) {
        this.positionService.deletePosition(position_id).subscribe({
          next: () => location.reload(),
        });
      }
    });
  }

}
