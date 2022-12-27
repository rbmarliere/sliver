import { Component, OnInit } from '@angular/core';
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
}
