import { Component, OnInit } from '@angular/core';
import { DialogService } from '../dialog.service';
import { StrategiesService } from '../strategies.service';
import { Strategy } from '../strategy';
import { StrategyType } from '../strategy-types/factory';
import { StrategyService } from '../strategy.service';

@Component({
  selector: 'app-strategies',
  templateUrl: './strategies.component.html',
  styleUrls: ['./strategies.component.less'],
})
export class StrategiesComponent implements OnInit {
  displayedColumns: string[] = this.getDisplayedColumns();
  loading: Boolean = true;
  strategies: Strategy[] = [];
  readonly StrategyType = StrategyType;

  constructor(
    private strategyService: StrategyService,
    private strategiesService: StrategiesService,
    private dialogService: DialogService
  ) { }

  ngOnInit(): void {
    this.getStrategies();
  }

  getDisplayedColumns(): string[] {
    if (window.innerWidth < 768) {
      // mobile
      return [
        'id',
        // 'active',
        // 'subscribed',
        // 'timeframe',
        // 'type',
        'description',
        // 'symbol',
        // 'exchange',
        'actions',
      ];
    } else {
      return [
        'id',
        // 'active',
        // 'subscribed',
        'timeframe',
        'type',
        'description',
        'symbol',
        'exchange',
        'actions',
      ];
    }
  }

  getStrategies(): void {
    this.strategiesService.getStrategies().subscribe({
      next: (res) => {
        this.strategies = res;
        this.loading = false;
      },
    });
  }

  deleteStrategy(strategy_id: number) {
    this.dialogService.confirm('Are you sure you want to delete this strategy?').subscribe((res) => {
      if (res) {
        this.strategyService.deleteStrategy(strategy_id).subscribe({
          next: () => location.reload(),
        });
      }
    });
  }

  updateSubscription(strategy: Strategy): void {
    this.strategyService.updateSubscription(strategy).subscribe({
      next: () => location.reload(),
    });
  }

  updateActive(strategy: Strategy): void {
    this.strategyService.updateActive(strategy).subscribe({
      next: () => location.reload(),
    });
  }
}
