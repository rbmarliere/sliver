import { AfterViewInit, Component, Input, OnInit, ViewChild } from '@angular/core';
import { StrategyService } from '../strategy.service';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';

import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';
import { Strategy } from '../strategy';

@Component({
  selector: 'app-strategy',
  templateUrl: './strategy.component.html',
  styleUrls: ['./strategy.component.less']
})
export class StrategyComponent implements OnInit, AfterViewInit {

  @ViewChild('sidenav')
  private sidenav: any;

  strategies: Strategy[] = [];

  @Input('selected') selected?: Strategy;

  private handleError(error: HttpErrorResponse) {
    const dialogConfig = new MatDialogConfig;

    dialogConfig.data = {
      msg: error.error.message
    };

    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.sidenav.open();
    }, 50);
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
        this.selectStrategy(this.strategies[0]);
      },
      error: (err) => this.handleError(err)
    });
  }

  selectStrategy(strategy: Strategy): void {
    this.selected = strategy;
  }

}
