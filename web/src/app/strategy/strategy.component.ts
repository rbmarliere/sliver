import { Component, OnInit } from '@angular/core';
import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { Strategy } from '../strategy';
import { StrategyService } from '../strategy.service';

@Component({
  selector: 'app-strategy',
  templateUrl: './strategy.component.html',
  styleUrls: ['./strategy.component.less']
})
export class StrategyComponent implements OnInit {

  displayedColumns: string[] = [
    "id",
    "description",
    "symbol",
    "exchange",
    "actions"
  ];

  loading: Boolean = true;

  strategies: Strategy[] = [];

  private handleError(error: HttpErrorResponse) {
    const dialogConfig = new MatDialogConfig;

    dialogConfig.data = {
      msg: error.error.message
    };

    console.log(error);
    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

  constructor(
    private strategyService: StrategyService,
    private dialog: MatDialog,
  ) { }

  ngOnInit(): void {
    this.getStrategies();
  }

  getStrategies(): void {
    this.strategyService.getStrategies().subscribe({
      next: (res) => {
        this.strategies = res;
        this.loading = false;
      },
      error: (err) => this.handleError(err)
    });
  }

  deleteStrategy(strategy_id: number) {
    this.strategyService.deleteStrategy(strategy_id).subscribe({
      next: () => location.reload(),
      error: (err) => this.handleError(err)
    });
  }
}
