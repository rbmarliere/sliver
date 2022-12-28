import { Component, OnInit } from '@angular/core';
import { StrategiesService } from '../strategies.service';
import { BaseStrategy } from '../strategy';
import { StrategyService } from '../strategy.service';
import { getStrategyTypes } from '../strategy/strategy-types';

@Component({
  selector: 'app-strategies',
  templateUrl: './strategies.component.html',
  styleUrls: ['./strategies.component.less'],
})
export class StrategiesComponent implements OnInit {
  displayedColumns: string[] = [
    'id',
    'active',
    'type',
    'description',
    'symbol',
    'exchange',
    'actions',
  ];

  loading: Boolean = true;

  strategies: BaseStrategy[] = [];

  constructor(
    private strategyService: StrategyService,
    private strategiesService: StrategiesService,
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
}
