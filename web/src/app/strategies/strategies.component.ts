import { Component, OnInit } from '@angular/core';
import { StrategiesService } from '../strategies.service';
import { BaseStrategy, Strategy } from '../strategy';
import { StrategyService } from '../strategy.service';
import { getStrategyTypes } from '../strategy/strategy-types';

@Component({
  selector: 'app-strategies',
  templateUrl: './strategies.component.html',
  styleUrls: ['./strategies.component.less'],
})
export class StrategiesComponent implements OnInit {
  displayedColumns: string[] = this.getDisplayedColumns();

  loading: Boolean = true;

  strategies: BaseStrategy[] = [];

  constructor(
    private strategyService: StrategyService,
    private strategiesService: StrategiesService,
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
        'exchange',
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
    this.strategyService.deleteStrategy(strategy_id).subscribe({
      next: () => location.reload(),
    });
  }

  getTypeName(type: number): string {
    let name = '';
    getStrategyTypes().forEach((strategy_type) => {
      if (strategy_type.value === type) {
        name = strategy_type.name;
      }
    });

    return name;
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
