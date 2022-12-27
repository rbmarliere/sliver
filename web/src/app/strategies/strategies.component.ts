import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';
import { StrategiesService } from '../strategies.service';
import { BaseStrategy } from '../strategy';
import { StrategyService } from '../strategy.service';

@Component({
  selector: 'app-strategies',
  templateUrl: './strategies.component.html',
  styleUrls: ['./strategies.component.less'],
})
export class StrategiesComponent implements OnInit {
  displayedColumns: string[] = [
    'id',
    'active',
    'description',
    'symbol',
    'exchange',
    'actions',
  ];

  loading: Boolean = true;

  strategies: BaseStrategy[] = [];

  private handleError(error: HttpErrorResponse) {
    const dialogConfig = new MatDialogConfig();

    dialogConfig.data = {
      msg: error.error.message,
    };

    console.log(error);
    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

  constructor(
    private strategyService: StrategyService,
    private strategiesService: StrategiesService,
    private dialog: MatDialog
  ) { }

  ngOnInit(): void {
    this.getStrategies();
  }

  getStrategies(): void {
    this.strategiesService.getStrategies().subscribe({
      next: (res) => {
        this.strategies = res;
        this.loading = false;
      },
      error: (err) => this.handleError(err),
    });
  }

  deleteStrategy(strategy_id: number) {
    this.strategyService.deleteStrategy(strategy_id).subscribe({
      next: () => location.reload(),
      error: (err) => this.handleError(err),
    });
  }
}
